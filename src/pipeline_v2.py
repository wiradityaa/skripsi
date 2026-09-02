"""Validated O*NET 31.0 similarity pilot pipeline."""
from __future__ import annotations
import hashlib, json, random
from itertools import combinations
from pathlib import Path
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW, TABLES, FIGURES = ROOT / "data/raw", ROOT / "outputs/tables", ROOT / "outputs/figures"
CONFIG = ROOT / "config/occupations.json"
DOMAINS = {"essential_skills": "essential_skills.csv", "transferable_skills": "transferable_skills.csv", "knowledge": "knowledge.csv"}
EXPECTED = {"essential_skills": 10, "transferable_skills": 25, "knowledge": 33}

def write_json(path, value): path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")

def prepare(ratings, occupation_codes):
    valid, expected, report, eligibility = {}, {}, {}, {}
    for domain, df in ratings.items():
        im = df[df["Scale ID"].eq("IM")].copy()
        im["Data Value"] = pd.to_numeric(im["Data Value"], errors="coerce")
        suppress = im["Recommend Suppress"].fillna("").astype(str).str.upper().eq("Y")
        irrelevant = im["Not Relevant"].fillna("").astype(str).str.upper().eq("Y")
        im["status"] = np.select([im["Data Value"].isna(), irrelevant, suppress], ["missing", "not_relevant", "recommend_suppress"], default="valid")
        im["importance_norm"] = np.where(im["status"].eq("valid"), (im["Data Value"] - 1) / 4, np.nan)
        im["competency"] = im["Element ID"].astype(str)
        expected[domain] = sorted(im["competency"].unique())
        if len(expected[domain]) != EXPECTED[domain]: raise ValueError(f"{domain}: expected {EXPECTED[domain]} IM elements, found {len(expected[domain])}")
        v = im[im["status"].eq("valid")].drop_duplicates(["O*NET-SOC Code", "competency"])
        valid[domain] = v
        eligible = {}
        for code in occupation_codes:
            got = set(v.loc[v["O*NET-SOC Code"].eq(code), "competency"])
            missing = sorted(set(expected[domain]) - got)
            reasons = [] if not missing and len(got) == EXPECTED[domain] else [f"valid_IM_elements={len(got)}/{EXPECTED[domain]}"]
            if missing: reasons.append("missing_or_invalid_elements=" + ",".join(missing))
            eligible[code] = not reasons
        eligibility[domain] = eligible
        report[domain] = {"rows": len(df), "columns": len(df.columns), "im_rows": len(im), "valid_im_rows": len(v), "missing": int(im["status"].eq("missing").sum()), "not_relevant": int(im["status"].eq("not_relevant").sum()), "recommend_suppress": int(im["status"].eq("recommend_suppress").sum()), "duplicates_all": int(df.duplicated().sum()), "scale_ids": sorted(df["Scale ID"].dropna().unique()), "expected_elements_im": len(expected[domain]), "required_elements": EXPECTED[domain], "before_exclusion": len(occupation_codes), "eligible_after_exclusion": sum(eligible.values()), "exclusion_reasons": [{"occupation": c, "reasons": [";".join([])] if False else (["eligible"] if eligible[c] else [f"valid_IM_elements={len(v.loc[v['O*NET-SOC Code'].eq(c), 'competency'].unique())}/{EXPECTED[domain]}"])} for c in occupation_codes if not eligible[c]]}
    complete = set(occupation_codes)
    for d in DOMAIN_NAMES: complete &= {c for c, ok in eligibility[d].items() if ok}
    report["occupation"] = {"rows": len(occupation_codes), "before_exclusion": len(occupation_codes), "complete_case_occupation_count": len(complete), "complete_case_codes": sorted(complete), "excluded_from_complete_case": [{"occupation": c, "failed_domains": [d for d in DOMAIN_NAMES if not eligibility[d][c]]} for c in occupation_codes if c not in complete]}
    return valid, expected, report, sorted(complete)

DOMAIN_NAMES = list(DOMAINS)

def matrices(valid, codes, expected):
    return {d: v.pivot(index="O*NET-SOC Code", columns="competency", values="importance_norm").reindex(index=codes, columns=expected[d]) for d, v in valid.items()}

def similarity(matrix, kind):
    codes, a = matrix.index.tolist(), matrix.to_numpy(float); n = len(codes); s = np.eye(n); common = np.zeros((n,n), int); coverage = np.full((n,n), np.nan)
    for i, j in combinations(range(n), 2):
        mask = np.isfinite(a[i]) & np.isfinite(a[j]); common[i,j] = common[j,i] = int(mask.sum())
        if not mask.any(): continue
        if kind == "graph":
            lo, hi = np.minimum(a[i,mask], a[j,mask]), np.maximum(a[i,mask], a[j,mask]); value = lo.sum()/hi.sum() if hi.sum() else 0
        else: value = None
        if value is not None: s[i,j] = s[j,i] = value
    np.fill_diagonal(common, matrix.shape[1]); np.fill_diagonal(coverage, 1.0); coverage[np.triu_indices(n,1)] = common[np.triu_indices(n,1)] / matrix.shape[1]; coverage[np.tril_indices(n,-1)] = common[np.tril_indices(n,-1)] / matrix.shape[1]
    return pd.DataFrame(s,index=codes,columns=codes), pd.DataFrame(common,index=codes,columns=codes), pd.DataFrame(coverage,index=codes,columns=codes)

def embedding_similarity(matrix, texts, model):
    elements, a = matrix.columns.tolist(), matrix.to_numpy(float); encoded = model.encode([texts.get(e,e) for e in elements], normalize_embeddings=True, show_progress_bar=False); codes = matrix.index.tolist(); n = len(codes); s = np.eye(n); common = np.zeros((n,n), int); coverage = np.full((n,n), np.nan)
    for i, j in combinations(range(n), 2):
        idx = np.flatnonzero(np.isfinite(a[i]) & np.isfinite(a[j])); common[i,j] = common[j,i] = len(idx)
        if not len(idx): continue
        va, vb = np.average(encoded[idx],axis=0,weights=a[i,idx]), np.average(encoded[idx],axis=0,weights=a[j,idx]); denom = np.linalg.norm(va)*np.linalg.norm(vb); s[i,j] = s[j,i] = float(np.dot(va,vb)/denom) if denom else 0
    np.fill_diagonal(common, len(elements)); np.fill_diagonal(coverage, 1.0); coverage[np.triu_indices(n,1)] = common[np.triu_indices(n,1)]/len(elements); coverage[np.tril_indices(n,-1)] = common[np.tril_indices(n,-1)]/len(elements)
    return pd.DataFrame(s,index=codes,columns=codes), pd.DataFrame(common,index=codes,columns=codes), pd.DataFrame(coverage,index=codes,columns=codes)

def validate(name, m):
    a = m.to_numpy(float); result = {"shape": list(a.shape), "all_finite": bool(np.isfinite(a).all()), "symmetric": bool(np.allclose(a,a.T)), "diagonal_is_one": bool(np.allclose(np.diag(a),1)), "bounded_0_1": bool(((a>=0)&(a<=1)).all())}; result["passed"] = all(result.values()); return result

def ndcg(ranked, relevant):
    gains = [int(x in relevant) for x in ranked]; dcg = sum(g/np.log2(i+2) for i,g in enumerate(gains)); ideal = sum(1/np.log2(i+2) for i in range(min(len(relevant),len(ranked)))); return dcg/ideal if ideal else 0

def related_metrics(sim, related):
    universe = set(sim.index); rows=[]
    for code in sim.index:
        rel = set(related.loc[related["O*NET-SOC Code"].eq(code),"Related O*NET-SOC Code"].astype(str)) & universe - {code}
        if not rel: continue
        ranked = sim.loc[code].drop(code).sort_values(ascending=False).index.tolist(); rows.append([len(set(ranked[:5])&rel)/len(rel),len(set(ranked[:10])&rel)/len(rel),ndcg(ranked[:10],rel)])
    return dict(zip(["recall_at_5","recall_at_10","ndcg_at_10"],np.mean(rows,axis=0))) if rows else {}

def interpret(mats, content, focus):
    names = content.set_index("Element ID")["Element Name"].to_dict(); descriptions = content.set_index("Element ID")["Description"].to_dict(); shared=[]; gaps=[]
    for domain, matrix in mats.items():
        for a,b in combinations([x for x in focus if x in matrix.index],2):
            for element in matrix.columns:
                wa, wb = matrix.loc[a,element], matrix.loc[b,element]
                if pd.notna(wa) and pd.notna(wb):
                    shared.append({"domain":domain,"occupation_a":a,"occupation_b":b,"element_id":element,"element_name":names.get(element,""),"description":descriptions.get(element,""),"weight_a":wa,"weight_b":wb,"shared_weight":min(wa,wb)})
                    gaps.append({"domain":domain,"occupation_a":a,"occupation_b":b,"element_id":element,"element_name":names.get(element,""),"description":descriptions.get(element,""),"weight_a":wa,"weight_b":wb,"signed_difference_a_minus_b":wa-wb,"absolute_difference":abs(wa-wb)})
    pd.DataFrame(shared).sort_values(["domain","occupation_a","occupation_b","shared_weight"],ascending=[True,True,True,False]).to_csv(TABLES/"shared_competencies.csv",index=False); pd.DataFrame(gaps).sort_values(["domain","occupation_a","occupation_b","absolute_difference"],ascending=[True,True,True,False]).to_csv(TABLES/"competency_gap.csv",index=False)

def main():
    random.seed(42); np.random.seed(42); TABLES.mkdir(parents=True,exist_ok=True); FIGURES.mkdir(parents=True,exist_ok=True); cfg=json.loads(CONFIG.read_text(encoding="utf-8")); ratings={d:pd.read_csv(RAW/f) for d,f in DOMAINS.items()}; occupations=pd.read_csv(RAW/"occupation_data.csv"); content=pd.read_csv(RAW/"content_model_reference.csv"); related=pd.read_csv(RAW/"related_occupations.csv"); codes=occupations["O*NET-SOC Code"].astype(str).tolist(); valid,expected,audit,complete=prepare(ratings,codes); all_mats=matrices(valid,codes,expected); main_mats={d:m.loc[complete] for d,m in all_mats.items()}; texts=content.set_index("Element ID")["Element Name"].fillna("")+" "+content.set_index("Element ID")["Description"].fillna("")
    from sentence_transformers import SentenceTransformer
    model=SentenceTransformer(cfg["embedding_model"]); validations={}; similarities={"graph":{},"embedding":{}}; metrics=[]
    for d,m in main_mats.items():
        g,gc,gv=similarity(m,"graph"); e,ec,ev=embedding_similarity(m,texts,model); similarities["graph"][d]=g; similarities["embedding"][d]=e
        for method,x,common,coverage in [("graph",g,gc,gv),("embedding",e,ec,ev)]:
            x.to_csv(TABLES/f"similarity_{method}_{d}.csv"); common.to_csv(TABLES/f"n_common_{method}_{d}.csv"); coverage.to_csv(TABLES/f"coverage_{method}_{d}.csv"); validations[f"{method}_{d}"]=validate(f"{method}_{d}",x); metrics.append({"method":method,"domain":d,**related_metrics(x,related)})
        sg,sgc,sgv=similarity(all_mats[d],"graph"); se,sec,sev=embedding_similarity(all_mats[d],texts,model); sg.to_csv(TABLES/f"sensitivity_graph_{d}.csv"); se.to_csv(TABLES/f"sensitivity_embedding_{d}.csv"); sgc.to_csv(TABLES/f"sensitivity_n_common_graph_{d}.csv"); sgv.to_csv(TABLES/f"sensitivity_coverage_graph_{d}.csv"); sec.to_csv(TABLES/f"sensitivity_n_common_embedding_{d}.csv"); sev.to_csv(TABLES/f"sensitivity_coverage_embedding_{d}.csv")
    write_json(TABLES/"data_audit.json",audit); write_json(TABLES/"validation_report.json",validations); pd.DataFrame(metrics).to_csv(TABLES/"related_metrics.csv",index=False); interpret(main_mats,content,cfg["core"]+cfg["sensitivity"])
    diagnostics={}; overlap=[]
    for d in DOMAIN_NAMES:
        e,g=similarities["embedding"][d],similarities["graph"][d]; vals=e.to_numpy()[~np.eye(len(e),dtype=bool)]; diagnostics[d]={"min":float(vals.min()),"mean":float(vals.mean()),"median":float(np.median(vals)),"max":float(vals.max()),"std":float(vals.std()),"too_concentrated":bool(vals.std()<0.01),"concentration_heuristic":"std < 0.01"}
        for code in e.index:
            others=e.index[e.index!=code]; er=set(e.loc[code,others].sort_values(ascending=False).head(3).index); gr=set(g.loc[code,others].sort_values(ascending=False).head(3).index); overlap.append({"domain":d,"occupation":code,"spearman":e.loc[code,others].rank().corr(g.loc[code,others].rank()),"embedding_top3":";".join(sorted(er)),"graph_top3":";".join(sorted(gr)),"top3_overlap_count":len(er&gr),"top3_overlap_ratio":len(er&gr)/3})
    write_json(TABLES/"embedding_diagnostics.json",diagnostics); pd.DataFrame(overlap).to_csv(TABLES/"embedding_graph_diagnostics.csv",index=False); pd.DataFrame({"occupation":complete,**{d:main_mats[d].notna().sum(axis=1).to_numpy() for d in DOMAIN_NAMES}}).to_csv(TABLES/"coverage_complete_case.csv",index=False); write_json(TABLES/"run_metadata.json",{"coverage_main":"complete-case","coverage_sensitivity":"pairwise-complete","scale_filter":"IM","normalization":"(x - 1) / (5 - 1)","model":cfg["embedding_model"],"model_revision":cfg.get("embedding_revision"),"seed":cfg["seed"],"raw_sha256":{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in RAW.glob("*.csv")}}); print(f"Complete-case occupations: {len(complete)}")

if __name__ == "__main__": main()
