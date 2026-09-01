# Konteks Penelitian

Pilot skripsi memetakan kemiripan/perbedaan kompetensi occupation O*NET-SOC dalam sistem pekerjaan Amerika Serikat menggunakan O*NET 31.0.

- Domain utama: Essential Skills, Transferable Skills, Knowledge.
- Matriks dan similarity utama: seluruh occupation dengan coverage complete-case memadai.
- Pairwise-complete hanya uji sensitivitas dan wajib menyimpan `n_common_elements` serta `coverage_ratio`.
- Analisis utama hanya `Scale ID == "IM"`; Level/scale lain dikeluarkan.
- Importance dinormalisasi dengan `(x - 1) / (5 - 1)` untuk nilai valid.
- Missing, Not Relevant, dan Recommend Suppress tidak boleh menjadi nol.
- Clinical Data Managers hanya sensitivity analysis secara default.
- `all-MiniLM-L6-v2` adalah baseline yang dapat diganti melalui konfigurasi.
- Related Occupations adalah referensi internal O*NET, bukan ground truth atau benchmark independen.
- Jangan scraping lowongan kerja, fine-tuning, prediksi, klasifikasi, atau klaim di luar data AS.

