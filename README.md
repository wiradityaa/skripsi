# O*NET Competency Similarity Pilot

Pilot reproducible untuk tiga domain kompetensi O*NET 31.0. Pipeline utama memakai complete-case; pairwise-complete dijalankan sebagai sensitivity analysis.

## Menjalankan

```powershell
python -m pip install -r requirements.txt
python src/pipeline.py
```

Perintah pertama kali akan mengunduh model embedding baseline dari Hugging Face ke cache lokal. Data O*NET sudah berada di `data/raw/`.

Output berada di `outputs/tables/` dan `outputs/figures/`. Semua run mencatat metadata model, sumber data, jumlah elemen bersama, coverage, dan aturan status nilai.

