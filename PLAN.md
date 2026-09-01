# Plan Pilot Reproducible

## Status

`APPROVED — implementasi diizinkan setelah persetujuan eksplisit pengguna.`

Folder kerja `E:\skripsi` saat ini belum berisi proyek penelitian. Direktori `graphify` dan `ponytail` yang sudah ada diperlakukan sebagai tool pendukung dan tidak akan diubah.

Tidak ada kode penelitian, data O*NET, model embedding, atau dependensi yang diunduh pada tahap penyusunan plan ini.

## Tujuan dan batasan yang sudah pasti

- Membangun pilot pipeline Python yang dapat dijalankan ulang dari data mentah ke output lokal.
- Sumber data utama adalah O*NET 31.0 resmi; unit analisis adalah occupation pada tingkat O*NET-SOC.
- Interpretasi dibatasi pada profil pekerjaan dalam sistem pekerjaan Amerika Serikat. Hasil tidak digeneralisasikan ke Indonesia.
- Analisis bersifat kuantitatif, eksploratif-deskriptif; tidak ada prediksi atau klasifikasi.
- Kompetensi utama hanya tiga domain: Essential Skills, Transferable Skills, dan Knowledge.
- Abilities dan Software Skills tidak masuk analisis utama.
- Importance menjadi bobot utama. Level tidak akan digabungkan tanpa keputusan metodologis terpisah.
- Analisis utama memfilter `Scale ID == "IM"`; Level dan scale lain tidak masuk matriks utama.
- Tidak ada web scraping lowongan kerja.
- Embedding dan graph dihitung sebagai dua metode terpisah pada masing-masing domain: Essential Skills, Transferable Skills, dan Knowledge.
- Skor keseluruhan tidak menggabungkan 68 elemen mentah secara langsung. Jika digunakan, skor keseluruhan adalah rata-rata setara dari tiga similarity domain dan tetap disertai hasil per domain; skor keseluruhan diperlakukan sebagai analisis tambahan.
- Semua output disimpan lokal; tidak ada publikasi atau pengiriman data ke layanan eksternal.
- Data dan model besar baru boleh diunduh setelah dijelaskan ukurannya/sumbernya dan disetujui pengguna.

## Keputusan implementasi awal

Keputusan berikut dipakai sebagai default kerja, tetapi tetap dapat diubah saat review:

1. **Korpus occupation dan fokus interpretasi.** Matriks serta similarity dihitung pada seluruh occupation yang memiliki coverage kompetensi memadai menurut kebijakan coverage yang dipilih setelah audit. Subset profesi data hanya digunakan untuk fokus interpretasi, tabel hasil, dan visualisasi. Konfigurasi fokus dapat diedit. Default core pilot adalah tujuh occupation pertama berikut:

   - `15-2051.00` — Data Scientists
   - `15-2051.01` — Business Intelligence Analysts
   - `15-1242.00` — Database Administrators
   - `15-1243.00` — Database Architects
   - `15-1243.01` — Data Warehousing Specialists
   - `15-2031.00` — Operations Research Analysts
   - `15-2041.00` — Statisticians
   **Kandidat tambahan / sensitivity analysis:**

   - `15-2051.02` — Clinical Data Managers. Occupation ini hanya masuk core jika pengguna memutuskan studi memang mencakup profesi data lintas domain.

   “Data Engineer” tidak akan dibuat sebagai occupation O*NET-SOC mandiri. Jika istilah itu dibahas, hanya setelah ada pemetaan resmi yang dapat diverifikasi dan alasan pemetaannya dicatat.

2. **Kunci kompetensi.** Kompetensi diidentifikasi dengan gabungan `domain` dan `Element ID`, bukan nama saja, agar nama yang sama lintas domain tidak tertukar. Nama dan deskripsi diambil dari `Content Model Reference`.

3. **Importance dan scale.** Hanya baris dengan `Scale ID == "IM"` yang masuk matriks utama. Dari `Scales Reference`, scale `IM` memiliki minimum 1 dan maksimum 5. Untuk rating Importance valid `x`, normalisasi eksplisitnya adalah:

   `importance_norm = (x - IM_min) / (IM_max - IM_min) = (x - 1) / (5 - 1)`

   sehingga `importance_norm` berada pada `[0, 1]`. Nilai missing, `Not Relevant`, dan `Recommend Suppress` tetap berstatus invalid/terpisah dan tidak diubah menjadi nol. Normalisasi bukan min-max terhadap subset occupation. Level dan scale lain tetap dapat diaudit, tetapi dikeluarkan dari analisis utama.

4. **Status nilai.** Missing, `Not Relevant`, `Recommend Suppress`, dan nilai numerik nol disimpan sebagai status terpisah. Nilai nol yang sah dipertahankan sebagai bobot `0`; missing/Not Relevant tidak diam-diam diubah menjadi nol. Baris suppressed ditandai dan kebijakan eksklusi final dicatat setelah audit format aktual.

5. **Embedding.** Teks kompetensi dibentuk dari `Element Name + Description`. `sentence-transformers/all-MiniLM-L6-v2` hanya menjadi baseline pilot. Model harus dapat diganti melalui konfigurasi tanpa mengubah pipeline; nama model, versi package, revision/checksum bila tersedia, seed, dan parameter agregasi dicatat di metadata output. Tidak ada fine-tuning.

6. **Agregasi embedding.** Untuk setiap domain dan occupation `o`, vektor agregat adalah rata-rata berbobot Importance yang dinormalisasi atas kompetensi valid. Cosine similarity dihitung per domain. Jika jumlah bobot valid nol, occupation diberi status tidak dapat diagregasi pada domain tersebut, bukan vektor nol yang menyesatkan.

7. **Graph similarity.** Graph adalah weighted bipartite graph occupation–competency terpisah per domain, dengan edge weight `importance_norm`. Similarity antaroccupation per domain memakai generalized Jaccard:

   `sum(min(w_o,c, w_p,c)) / sum(max(w_o,c, w_p,c))`

   Hanya kompetensi dengan observasi valid yang masuk perhitungan; aturan universe kompetensi dan perlakuan status missing/Not Relevant ditampilkan dalam metadata. Skor keseluruhan, bila diaktifkan, adalah rata-rata setara dari tiga similarity domain, bukan generalized Jaccard atas 68 elemen mentah sekaligus.

8. **Gap.** Tabel gap memuat kompetensi bersama, bobot masing-masing occupation, selisih absolut, arah perbedaan, dan status data. Threshold tidak akan disembunyikan; jika dipakai, nilainya menjadi konfigurasi.

9. **Related Occupations.** Related Occupations dipakai sebagai “referensi internal O*NET untuk evaluasi keselarasan peringkat, bukan ground truth dan bukan benchmark independen.” Evaluasi dilakukan terhadap seluruh occupation dalam universe analisis, bukan hanya subset profesi data. Metrik yang direncanakan adalah Recall@5, Recall@10, dan NDCG@10; output top-3 tetap digunakan untuk tabel ringkas.

10. **Coverage.** Dua skenario disiapkan dan didokumentasikan. **Complete-case adalah kebijakan coverage utama**; pairwise-complete hanya digunakan sebagai uji sensitivitas:

    - **Complete-case:** occupation masuk analisis utama jika seluruh rating Importance yang diperlukan untuk domain tersebut valid. Untuk skor keseluruhan, occupation harus memenuhi syarat valid di ketiga domain.
    - **Pairwise-complete:** similarity tiap pasangan dihitung hanya dari elemen valid yang dimiliki bersama. Setiap nilai similarity wajib menyimpan `n_common_elements` dan `coverage_ratio`, dengan `coverage_ratio = n_common_elements / n_required_elements` per domain.

    Pada kedua skenario, Missing, `Not Relevant`, dan `Recommend Suppress` bukan nol dan tidak boleh diubah menjadi edge berbobot nol. Occupation universe, alasan pemilihan complete-case, hasil uji sensitivitas, dan jumlah occupation yang terbuang dicatat setelah audit.

## Keputusan yang perlu dikonfirmasi

- Apakah tujuh occupation core dan satu Clinical Data Managers sebagai sensitivity analysis sudah sesuai?
- Complete-case menjadi kebijakan utama dan pairwise-complete menjadi uji sensitivitas; format `Recommend Suppress` tetap diverifikasi saat audit dan tidak pernah diperlakukan sebagai nol.
- Apakah ambang gap tertentu diperlukan, atau tabel gap cukup diurutkan berdasarkan selisih absolut?
- Apakah baseline `all-MiniLM-L6-v2` cukup untuk pilot, atau perlu model English lain melalui konfigurasi?
- Apakah diperlukan analisis tambahan Abilities atau Software Skills? Default plan: tidak.

## Struktur data yang diperlukan

Loader hanya akan menerima tujuh file resmi O*NET 31.0 berikut, dengan nama file aktual diverifikasi dari paket resmi sebelum implementasi:

- `occupation_data`
- `essential_skills`
- `transferable_skills`
- `knowledge`
- `content_model_reference`
- `scales_reference`
- `related_occupations`

Kolom yang akan dicari dan divalidasi, tanpa mengasumsikan nama kolom sebelum audit:

- occupation: `O*NET-SOC Code`, title/name, dan metadata sumber;
- rating: occupation code, element/competency ID, scale ID, data value, `Not Relevant`, `Recommend Suppress`, dan `Date` bila tersedia; audit mencakup scale selain `IM`, tetapi matriks utama hanya memakai `IM`;
- content model: element ID, element name, description, domain/level metadata;
- scales: scale ID, nama scale, batas/rentang, dan penjelasan nilai;
- related occupations: occupation code sumber, occupation code terkait, serta nilai/ranking bila tersedia.

Audit akan melaporkan jumlah baris/kolom, dtype, nilai hilang, duplikasi, kode occupation tidak valid, Scale ID yang tidak dikenal, status khusus, Date, coverage per domain, jumlah occupation yang memenuhi tiap skenario coverage, dan jumlah occupation yang beririsan pada ketiga domain. File audit juga menyimpan alasan seleksi occupation fokus.

## Rencana struktur proyek

Setelah plan disetujui, struktur minimum yang dibuat:

```text
data/raw/          # file resmi O*NET 31.0, read-only setelah diunduh
data/interim/      # hasil parsing/cleaning yang dapat dibangun ulang
data/processed/    # matriks dan tabel analisis
src/               # loader, audit, transformasi, embedding, graph, report
notebooks/         # eksplorasi tipis; pipeline utama tetap lewat script
outputs/tables/    # CSV/Parquet/metadata tabel
outputs/figures/   # PNG/SVG graph dan similarity
docs/              # sumber, asumsi, open decisions, metodologi pilot
config/            # konfigurasi occupation dan parameter run
```

File konteks `AGENTS.md` akan memuat batasan penelitian. `README.md` menjelaskan instalasi dan satu perintah run. Dependensi akan dipin di `requirements.txt` atau `pyproject.toml`; versi Python, model dari konfigurasi, seed, sumber data, tanggal unduh, dan hash file dicatat agar run dapat direproduksi. `docs/sources.md` atau `DATA_LICENSE.md` wajib mencatat lisensi dan atribusi data.

## Rencana pipeline

1. **Acquire/verify.** Setelah persetujuan, verifikasi halaman/paket resmi O*NET 31.0, tampilkan URL, ukuran perkiraan, dan file yang akan diunduh. Simpan archive/raw tanpa menimpa file yang ada; gunakan nama versi eksplisit dan checksum.
2. **Load.** Baca hanya tujuh dataset yang disetujui dengan encoding/delimiter yang ditentukan dari paket resmi.
3. **Audit.** Jalankan audit struktur dan isi; hasilkan `outputs/tables/data_audit.*` dan catatan sumber.
4. **Prepare.** Validasi kode, filter `Scale ID == "IM"`, join content model dan scale reference, pisahkan status nilai, audit kedua skenario coverage, normalisasi Importance, lalu bentuk matriks domain-spesifik untuk seluruh occupation yang eligible.
5. **Embedding.** Encode teks kompetensi sekali dengan model dari konfigurasi, agregasikan per occupation dan domain secara berbobot, hitung cosine similarity per domain, dan simpan matriks serta metadata model. Jika diaktifkan, hitung skor keseluruhan sebagai rata-rata setara tiga similarity domain.
6. **Graph.** Bangun weighted bipartite graph per domain, hitung generalized Jaccard per domain, simpan edge list, matriks similarity, `n_common_elements`, `coverage_ratio`, dan tabel top-3.
7. **Compare.** Buat tabel perbandingan dua metode per domain tanpa menggabungkan embedding dan graph menjadi skor gabungan. Perbedaan metode dibahas sebagai hasil eksploratif, bukan sebagai pemenang otomatis.
8. **Related-occupation framework.** Pada seluruh occupation universe, hitung Recall@5, Recall@10, dan NDCG@10 terhadap Related Occupations sebagai referensi internal O*NET untuk evaluasi keselarasan peringkat, bukan ground truth dan bukan benchmark independen.
9. **Report/figures.** Hasilkan kompetensi bersama, gap, daftar tiga tetangga terdekat per occupation fokus, serta visualisasi graph yang dibatasi pada fokus/ego network agar terbaca.
10. **Validate.** Jalankan pemeriksaan otomatis untuk struktur input, irisan domain, rentang bobot, simetri/diagonal matriks, nilai finite, dan konsistensi kode output.

## Risiko metodologis dan mitigasi

| Risiko | Mitigasi |
|---|---|
| Format/kolom O*NET berubah atau tidak sesuai asumsi | Audit schema eksplisit; loader gagal dengan pesan jelas, bukan menebak diam-diam. |
| Importance, Level, dan status khusus tertukar | Gunakan Scale ID dan Scales Reference; Level tidak dipakai pada analisis utama. |
| Missing/Not Relevant menjadi nol secara tidak sengaja | Simpan flag status dan uji terpisah; hanya nol numerik sah yang menjadi bobot nol. |
| Rata-rata embedding dipengaruhi jumlah kompetensi | Simpan denominator/bobot total, laporkan occupation yang tidak lengkap, dan dokumentasikan universe kompetensi. |
| Generalized Jaccard bias karena coverage berbeda | Siapkan complete-case dan pairwise-complete; laporkan `n_common_elements` serta `coverage_ratio` pada setiap similarity pairwise. |
| Similarity embedding mencerminkan bahasa/deskripsi, bukan kompetensi saja | Jelaskan bahwa embedding adalah representasi semantik deskripsi O*NET; bandingkan dengan graph secara terpisah. |
| Model embedding tidak reproducible | Pin dependency, catat model/revision, seed, dan metadata run; jangan fine-tune. |
| Daftar fokus terlalu sempit atau overlap kode | Audit irisan dan konfigurasi editable; alasan seleksi disimpan dalam tabel audit. |
| Related Occupations disalahartikan sebagai label benar atau benchmark independen | Gunakan istilah “referensi internal O*NET untuk evaluasi keselarasan peringkat”; laporkan Recall@5, Recall@10, dan NDCG@10 tanpa menyebutnya ground truth. |
| Visualisasi terlalu padat | Tampilkan ego network/fokus dan simpan edge list lengkap untuk analisis. |

## Sumber resmi yang akan diverifikasi sebelum akuisisi

- O*NET Resource Center — Database: <https://www.onetcenter.org/database.html>
- O*NET Resource Center — Content Model: <https://www.onetcenter.org/content.html>
- O*NET Resource Center — Main page: <https://www.onetcenter.org/>

## Lisensi dan atribusi

- Data O*NET 31.0 menggunakan lisensi **CC BY 4.0**.
- `docs/sources.md` atau `DATA_LICENSE.md` wajib mencatat atribusi O*NET Database dan U.S. Department of Labor / Employment and Training Administration (USDOL/ETA).
- Dokumen tersebut wajib memuat tautan lisensi <https://creativecommons.org/licenses/by/4.0/>, versi database, tanggal akses, URL sumber langsung, dan catatan modifikasi data bila ada.
- Tidak ada klaim bahwa output pilot merupakan produk resmi O*NET atau USDOL/ETA.

URL paket/berkas spesifik dan DOI artikel embedding/similarity tidak akan ditulis sebagai fakta final sampai diverifikasi. `docs/sources.md` nantinya memuat URL langsung, versi, tanggal akses, dan DOI yang benar-benar digunakan.

## Verifikasi sumber dan rencana unduhan

Diverifikasi pada 1 September 2026 dari halaman resmi [O*NET 31.0 Database](https://www.onetcenter.org/database.html). URL berikut adalah CSV resmi yang akan diunduh setelah persetujuan eksplisit pengguna. Ukuran berasal dari metadata HTTP `HEAD`; tidak ada isi file yang diunduh pada tahap ini.

| Data | URL resmi | Ukuran |
|---|---|---:|
| Occupation Data | <https://www.onetcenter.org/dl_files/database/db_31_0_csv/occupation_data.csv> | 268,030 bytes (261.75 KiB) |
| Essential Skills | <https://www.onetcenter.org/dl_files/database/db_31_0_csv/essential_skills.csv> | 2,328,135 bytes (2.22 MiB) |
| Transferable Skills | <https://www.onetcenter.org/dl_files/database/db_31_0_csv/transferable_skills.csv> | 6,081,245 bytes (5.80 MiB) |
| Knowledge | <https://www.onetcenter.org/dl_files/database/db_31_0_csv/knowledge.csv> | 8,013,560 bytes (7.64 MiB) |
| Content Model Reference | <https://www.onetcenter.org/dl_files/database/db_31_0_csv/content_model_reference.csv> | 235,856 bytes (230.33 KiB) |
| Scales Reference | <https://www.onetcenter.org/dl_files/database/db_31_0_csv/scales_reference.csv> | 1,006 bytes (1006 bytes) |
| Related Occupations | <https://www.onetcenter.org/dl_files/database/db_31_0_csv/related_occupations.csv> | 2,051,148 bytes (1.96 MiB) |

Total tujuh CSV: **18,978,980 bytes (18.10 MiB)** berdasarkan ukuran header saat verifikasi. Halaman resmi juga menyediakan [arsip Excel penuh](https://www.onetcenter.org/dl_files/database/db_31_0_excel.zip) berukuran 47,880,800 bytes (45.66 MiB), tetapi arsip penuh tidak diperlukan jika tujuh CSV di atas disetujui.

Model baseline yang akan diunduh hanya jika diperlukan dan disetujui:

- [sentence-transformers/all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2), revision yang diverifikasi pada model card/API: `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`.
- Bobot `model.safetensors`: 90,868,376 bytes (86.65 MiB) menurut metadata HTTP `HEAD`; model card melaporkan 22.7M parameter. File konfigurasi/tokenizer pendukung berukuran kecil dapat ikut diambil oleh `sentence-transformers` dan ukurannya akan dicatat setelah unduhan yang disetujui.
- Lisensi model: Apache-2.0. Model ini baseline yang dapat diganti melalui konfigurasi, bukan sumber data penelitian.

**Belum diunduh:** seluruh tujuh CSV, arsip Excel, bobot/model baseline, dan file pendukung model. Unduhan baru dilakukan setelah pengguna memberikan persetujuan eksplisit.

## Kriteria selesai pilot

- Pipeline berjalan dari raw data ke output tanpa langkah manual tersembunyi.
- Audit data tersedia dan mencakup semua pemeriksaan yang diminta.
- Matriks occupation × competency terbentuk per domain, menggunakan seluruh occupation dengan coverage memadai dan status nilai terdokumentasi.
- Similarity embedding dan generalized Jaccard dapat dihitung secara terpisah untuk Essential Skills, Transferable Skills, dan Knowledge.
- Jika skor keseluruhan dilaporkan, skor tersebut merupakan rata-rata setara tiga similarity domain dan bukan penggabungan 68 elemen mentah.
- Output fokus, shared competencies, gaps, top-3, dan visualisasi tersedia.
- Related Occupations dievaluasi pada seluruh occupation dengan Recall@5, Recall@10, dan NDCG@10 sebagai referensi internal O*NET, bukan ground truth atau benchmark independen.
- Lisensi, atribusi, versi, tanggal akses, dan modifikasi data terdokumentasi.
- `README.md`, dependensi, `AGENTS.md`, konfigurasi, metadata run, dan open decisions tersedia.
- Pemeriksaan otomatis minimum lulus.
- Asumsi yang belum diputuskan tetap tercatat di `docs/open-decisions.md` atau plan ini.

## Urutan kerja setelah persetujuan

1. Konfirmasi plan dan keputusan terbuka.
2. Verifikasi sumber resmi serta meminta persetujuan unduh data/model.
3. Buat struktur proyek, `AGENTS.md`, konfigurasi, dan dependency file.
4. Implementasikan loader + audit dan jalankan validasi awal.
5. Implementasikan matriks, embedding, graph, output, dan pemeriksaan otomatis.
6. Jalankan end-to-end pilot, review hasil, lalu dokumentasikan keterbatasan.
