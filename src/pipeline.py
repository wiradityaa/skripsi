"""Reproducible O*NET 31.0 competency similarity pilot."""
from __future__ import annotations

import hashlib
import json
import random
from itertools import combinations
from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
TABLES = ROOT / "outputs" / "tables"
FIGURES = ROOT / "outputs" / "figures"
CONFIG = ROOT / "config" / "occupations.json"
DOMAINS = {
    "essential_skills": "essential_skills.csv",
    "transferable_skills": "transferable_skills.csv",
    "knowledge": "knowledge.csv",
}


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")


def load() -> tuple[dict, dict[str, pd.DataFrame], pd.DataFrame, pd.DataFrame]:
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    ratings = {domain: pd.read_csv(RAW / filename) for domain, filename in DOMAINS.items()}
    occupations = pd.read_csv(RAW / "occupation_data.csv")
    content = pd.read_csv(RAW / "content_model_reference.csv")
    related = pd.read_csv(RAW / "related_occupations.csv")
    return cfg, ratings, occupations.merge(content, how="cross").iloc[:0], related


def audit(ratings: dict[str, pd.DataFrame], occupations: pd.DataFrame) -> tuple[dict, dict[str, pd.DataFrame]]:
    reports = {}
    valid_by_domain = {}
    expected = {}
    for domain, df in ratings.items():
        im = df[df["Scale ID"].eq("IM")].copy()
        im["Data Value"] = pd.to_numeric(im["Data Value"], errors="coerce")
        suppress = im["Recommend Suppress"].fillna("").astype(str).str.upper().eq("Y")
        not_relevant = im["Not Relevant"].fillna("").astype(str).str.upper().eq("Y")
        im["status"] = np.select(
            [im["Data Value"].isna(), not_relevant, suppress],
            ["missing", "not_relevant", "recommend_suppress"],
            default="valid",
        )
        im["importance_norm"] = np.where(
            im["status"].eq("valid"), (im["Data Value"] - 1.0) / 4.0, np.nan
        )
        im["competency"] = im["Element ID"].astype(str)
        expected[domain] = sorted(im["competency"].dropna().unique())
        valid = im[im["status"].eq("valid")].drop_duplicates(["O*NET-SOC Code", "competency"])
        valid_by_domain[domain] = valid
        reports[domain] = {
            "rows": int(len(df)), "columns": int(len(df.columns)),
            "im_rows": int(len(im)), "missing": int(im["status"].eq("missing").sum()),
            "not_relevant": int(im["status"].eq("not_relevant").sum()),
            "recommend_suppress": int(im["status"].eq("recommend_suppress").sum()),
            "duplicates_all": int(df.duplicated().sum()),
            "scale_ids": sorted(df["Scale ID"].dropna().unique().tolist()),
            "date_values": sorted(df["Date"].dropna().astype(str).unique().tolist()),
            "expected_elements_im": len(expected[domain]),
        }
    complete = []
    for domain, df in valid_by_domain.items():
        complete.append(set(df["O*NET-SOC Code"]))
    complete_codes = set.intersection(*complete)
    reports["occupation"] = {
        "rows": int(len(occupations)), "columns": int(len(occupations.columns)),
        "duplicate_codes": int(occupations["O*NET-SOC Code"].duplicated().sum()),
        "complete_case_occupation_count": len(complete_codes),
        "complete_case_codes": sorted(complete_codes),
    }
    return {"domains": reports, "expected_elements": expected}, valid_by_domain


def matrices(valid: dict[str, pd.DataFrame], all_codes: list[str], expected: dict[str, list[str]]) -> dict[str, pd.DataFrame]:
    out = {}
    for domain, df in valid.items():
        table = df.pivot(index="O*NET-SOC Code", columns="competency", values="importance_norm")
        out[domain] = table.reindex(index=all_codes, columns=expected[domain])
    return out


def pairwise_jaccard(matrix: pd.DataFrame, expected_count: int) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    codes = matrix.index.tolist(); values = matrix.to_numpy(dtype=float); n_codes = len(codes)
    sim_values = np.eye(n_codes); common_values = np.zeros((n_codes, n_codes), dtype=int); coverage_values = np.full((n_codes, n_codes), np.nan)
    for i in range(n_codes):
        for j in range(i + 1, n_codes):
            mask = np.isfinite(values[i]) & np.isfinite(values[j]); n = int(mask.sum())
            low = np.minimum(values[i, mask], values[j, mask]); high = np.maximum(values[i, mask], values[j, mask]); denom = high.sum()
            value = float(low.sum() / denom) if n and denom else 0.0
            sim_values[i, j] = sim_values[j, i] = value; common_values[i, j] = common_values[j, i] = n; coverage_values[i, j] = coverage_values[j, i] = n / expected_count
    np.fill_diagonal(common_values, expected_count); np.fill_diagonal(coverage_values, 1.0)
    sim = pd.DataFrame(sim_values, index=codes, columns=codes); common = pd.DataFrame(common_values, index=codes, columns=codes); coverage = pd.DataFrame(coverage_values, index=codes, columns=codes)
    return sim, common, coverage


def embedding_similarity(matrix: pd.DataFrame, texts: pd.Series, model, pairwise: bool) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    elements = matrix.columns.tolist()
    encoded = model.encode([texts.get(e, e) for e in elements], normalize_embeddings=True, show_progress_bar=False)
    codes = matrix.index.tolist(); values = matrix.to_numpy(dtype=float); n_codes = len(codes)
    sim_values = np.eye(n_codes); common_values = np.zeros((n_codes, n_codes), dtype=int); coverage_values = np.full((n_codes, n_codes), np.nan)
    for i in range(n_codes):
        for j in range(i + 1, n_codes):
            idx = np.flatnonzero(np.isfinite(values[i]) & np.isfinite(values[j])); n = len(idx)
            if not n: continue
            weights_a = values[i, idx]; weights_b = values[j, idx]
            va = np.average(encoded[idx], axis=0, weights=weights_a) if weights_a.sum() else np.mean(encoded[idx], axis=0)
            vb = np.average(encoded[idx], axis=0, weights=weights_b) if weights_b.sum() else np.mean(encoded[idx], axis=0)
            denom = np.linalg.norm(va) * np.linalg.norm(vb); value = float(np.dot(va, vb) / denom) if denom else 0.0
            sim_values[i, j] = sim_values[j, i] = value; common_values[i, j] = common_values[j, i] = n; coverage_values[i, j] = coverage_values[j, i] = n / len(elements)
    np.fill_diagonal(common_values, len(elements)); np.fill_diagonal(coverage_values, 1.0)
    sim = pd.DataFrame(sim_values, index=codes, columns=codes); common = pd.DataFrame(common_values, index=codes, columns=codes); coverage = pd.DataFrame(coverage_values, index=codes, columns=codes)
    return sim, common, coverage


def top_table(similarities: dict, focus: list[str]) -> pd.DataFrame:
    rows = []
    for method, domains in similarities.items():
        for domain, sim in domains.items():
            for code in focus:
                if code not in sim.index: continue
                for rank, (other, score) in enumerate(sim.loc[code].drop(labels=code).sort_values(ascending=False).head(3).items(), 1):
                    rows.append({"method": method, "domain": domain, "occupation": code, "rank": rank, "neighbor": other, "similarity": score})
    return pd.DataFrame(rows)


def related_metrics(sim: pd.DataFrame, related: pd.DataFrame) -> dict:
    universe = set(sim.index); rows = []
    for code in sim.index:
        relevant = related[related["O*NET-SOC Code"].eq(code)]["Related O*NET-SOC Code"].astype(str)
        relevant = set(relevant) & universe - {code}
        if not relevant: continue
        ranked = sim.loc[code].drop(labels=code).sort_values(ascending=False).index.tolist()
        rows.append({"recall_at_5": len(set(ranked[:5]) & relevant) / len(relevant), "recall_at_10": len(set(ranked[:10]) & relevant) / len(relevant), "ndcg_at_10": ndcg(ranked[:10], relevant)})
    return {key: float(np.mean([r[key] for r in rows])) for key in rows[0]} if rows else {"recall_at_5": np.nan, "recall_at_10": np.nan, "ndcg_at_10": np.nan}


def ndcg(ranked: list[str], relevant: set[str]) -> float:
    gains = [1 if x in relevant else 0 for x in ranked]
    dcg = sum(g / np.log2(i + 2) for i, g in enumerate(gains)); ideal = sum(1 / np.log2(i + 2) for i in range(min(len(relevant), len(ranked))))
    return dcg / ideal if ideal else 0.0


def make_graph(matrix: pd.DataFrame, names: dict[str, str], focus: list[str], path: Path) -> None:
    graph = nx.Graph()
    selected = [x for x in focus if x in matrix.index]
    for code in selected:
        graph.add_node(code, bipartite="occupation", label=names.get(code, code))
        for element, weight in matrix.loc[code].dropna().nlargest(10).items():
            node = f"c:{element}"; graph.add_node(node, bipartite="competency", label=element); graph.add_edge(code, node, weight=float(weight))
    pos = nx.spring_layout(graph, seed=42, k=1.4)
    plt.figure(figsize=(14, 10)); nx.draw_networkx_nodes(graph, pos, nodelist=selected, node_color="#2563eb", node_size=900)
    c_nodes = [n for n in graph if n not in selected]; nx.draw_networkx_nodes(graph, pos, nodelist=c_nodes, node_color="#f59e0b", node_size=350)
    nx.draw_networkx_edges(graph, pos, alpha=.35); nx.draw_networkx_labels(graph, pos, labels={n: graph.nodes[n]["label"] for n in graph}, font_size=7)
    plt.axis("off"); plt.tight_layout(); plt.savefig(path, dpi=180); plt.close()


def main() -> None:
    random.seed(42); np.random.seed(42); TABLES.mkdir(parents=True, exist_ok=True); FIGURES.mkdir(parents=True, exist_ok=True)
    cfg = json.loads(CONFIG.read_text(encoding="utf-8")); ratings = {d: pd.read_csv(RAW / f) for d, f in DOMAINS.items()}; occupations = pd.read_csv(RAW / "occupation_data.csv"); content = pd.read_csv(RAW / "content_model_reference.csv"); related = pd.read_csv(RAW / "related_occupations.csv")
    audit_report, valid = audit(ratings, occupations); complete_codes = audit_report["domains"]["occupation"]["complete_case_codes"]
    expected = audit_report["expected_elements"]
    all_codes = sorted(set().union(*(set(df["O*NET-SOC Code"]) for df in valid.values())))
    matrices_all = matrices(valid, all_codes, expected)
    matrices_main = {domain: matrix.loc[complete_codes] for domain, matrix in matrices_all.items()}
    names = occupations.set_index("O*NET-SOC Code")["Title"].to_dict(); text = content.set_index("Element ID")["Element Name"].fillna("") + " " + content.set_index("Element ID")["Description"].fillna("")
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(cfg["embedding_model"])
    similarities = {"graph": {}, "embedding": {}}; sensitivity = {"graph": {}, "embedding": {}}; metric_rows = []
    for domain, matrix in matrices_main.items():
        g, gc, gv = pairwise_jaccard(matrix, len(expected[domain])); e, ec, ev = embedding_similarity(matrix, text, model, False)
        similarities["graph"][domain] = g; similarities["embedding"][domain] = e
        g.to_csv(TABLES / f"similarity_graph_{domain}.csv"); e.to_csv(TABLES / f"similarity_embedding_{domain}.csv"); gc.to_csv(TABLES / f"n_common_graph_{domain}.csv"); gv.to_csv(TABLES / f"coverage_graph_{domain}.csv"); ec.to_csv(TABLES / f"n_common_embedding_{domain}.csv"); ev.to_csv(TABLES / f"coverage_embedding_{domain}.csv")
        for method, s in [("graph", g), ("embedding", e)]: metric_rows.append({"method": method, "domain": domain, **related_metrics(s, related)})
        pair = matrices_all[domain]
        sg, sgc, sgv = pairwise_jaccard(pair, len(expected[domain])); se, sec, sev = embedding_similarity(pair, text, model, True)
        sensitivity["graph"][domain] = sg; sensitivity["embedding"][domain] = se
        sg.to_csv(TABLES / f"sensitivity_graph_{domain}.csv"); se.to_csv(TABLES / f"sensitivity_embedding_{domain}.csv"); sgc.to_csv(TABLES / f"sensitivity_n_common_graph_{domain}.csv"); sgv.to_csv(TABLES / f"sensitivity_coverage_graph_{domain}.csv"); sec.to_csv(TABLES / f"sensitivity_n_common_embedding_{domain}.csv"); sev.to_csv(TABLES / f"sensitivity_coverage_embedding_{domain}.csv")
    top_table(similarities, cfg["core"] + cfg["sensitivity"]).to_csv(TABLES / "top3_focus.csv", index=False)
    pd.DataFrame(metric_rows).to_csv(TABLES / "related_metrics.csv", index=False); write_json(TABLES / "data_audit.json", audit_report)
    pd.DataFrame({"occupation": complete_codes, **{d: matrices_main[d].notna().sum(axis=1).reindex(complete_codes).to_numpy() for d in matrices_main}}).to_csv(TABLES / "coverage_complete_case.csv", index=False)
    make_graph(matrices_main["essential_skills"], names, cfg["core"], FIGURES / "essential_skills_focus_graph.png")
    metadata = {"coverage_main": "complete-case", "coverage_sensitivity": "pairwise-complete", "scale_filter": "IM", "normalization": "(x - 1) / (5 - 1)", "model": cfg["embedding_model"], "model_revision": cfg.get("embedding_revision"), "seed": cfg["seed"], "raw_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in RAW.glob("*.csv")}}
    write_json(TABLES / "run_metadata.json", metadata)
    assert all(((m.to_numpy()[np.isfinite(m.to_numpy())] >= -1e-9) & (m.to_numpy()[np.isfinite(m.to_numpy())] <= 1 + 1e-9)).all() for m in matrices_main.values())
    assert all(np.allclose(m.to_numpy(), m.to_numpy().T, equal_nan=True) for m in similarities["graph"].values())
    print(f"Complete-case occupations: {len(complete_codes)}; outputs: {TABLES}")


if __name__ == "__main__":
    main()
