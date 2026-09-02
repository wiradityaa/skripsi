# Penjelasan Proyek Skripsi

## Intinya

Kamu sedang membuat **pilot analisis kemiripan kompetensi pekerjaan** berdasarkan database resmi O*NET 31.0.

Pertanyaan sederhananya:

> Seberapa mirip profil kompetensi beberapa pekerjaan bidang data jika dibandingkan dengan pekerjaan lain dalam sistem pekerjaan Amerika Serikat?

Kamu bukan sedang memprediksi apakah seseorang akan menjadi Data Scientist. Kamu juga bukan sedang membuat klasifikasi pekerjaan. Kamu membandingkan profil pekerjaan yang sudah tersedia di O*NET.

## Apa itu O*NET?

O*NET adalah database pekerjaan Amerika Serikat. Isinya antara lain:

- kode dan nama occupation;
- deskripsi pekerjaan;
- kompetensi yang terkait dengan occupation;
- nilai Importance untuk setiap kompetensi;
- daftar occupation yang dianggap related oleh O*NET.

Karena sumbernya O*NET, hasil penelitianmu hanya menjelaskan konteks pekerjaan Amerika Serikat. Hasilnya tidak otomatis berlaku untuk pasar kerja Indonesia.

## Tiga domain kompetensi

Pilot ini hanya memakai tiga domain:

1. **Essential Skills** — keterampilan dasar yang penting untuk pekerjaan.
2. **Transferable Skills** — keterampilan yang dapat digunakan di berbagai pekerjaan.
3. **Knowledge** — pengetahuan yang diperlukan dalam suatu pekerjaan.

Jumlah elemen:

- Essential Skills: 10;
- Transferable Skills: 25;
- Knowledge: 33.

Ketiga domain dipisahkan agar perbedaan maknanya tidak hilang karena semuanya dicampur menjadi satu angka.

## Arti Importance

O*NET memberikan nilai Importance pada scale IM. Pada data ini, rentangnya 1 sampai 5:

- 1: relatif kurang penting;
- 5: sangat penting.

Normalisasinya:

**importance_norm = (Importance - 1) / (5 - 1)**

Contoh:

- Importance 1 menjadi 0;
- Importance 3 menjadi 0,5;
- Importance 5 menjadi 1.

Missing, Not Relevant, dan Recommend Suppress bukan nol. Ketiganya disimpan sebagai status invalid atau tidak tersedia dan tidak dijadikan bobot 0.

## Complete-case

Tidak semua occupation memiliki rating valid lengkap. Karena itu, analisis utama memakai complete-case.

Sebuah occupation harus memiliki:

- 10 dari 10 elemen Essential Skills;
- 25 dari 25 elemen Transferable Skills;
- 33 dari 33 elemen Knowledge.

Analisis utama memakai irisan occupation yang lolos ketiga syarat tersebut.

Pada run terakhir:

- 1.016 occupation diperiksa;
- 910 memenuhi Essential Skills;
- 910 memenuhi Transferable Skills;
- 884 memenuhi Knowledge;
- 884 occupation memenuhi ketiganya.

Jadi, 884 occupation menjadi universe analisis utama. Occupation fokus hanya digunakan untuk tabel interpretasi dan visualisasi.

## Pairwise-complete

Pairwise-complete adalah uji sensitivitas.

Dalam skenario ini, dua occupation dibandingkan hanya berdasarkan elemen yang sama-sama memiliki rating valid. Setiap perbandingan menyimpan:

- jumlah elemen yang sama-sama tersedia;
- rasio coverage.

Tujuannya untuk melihat apakah hasil berubah ketika aturan data dibuat lebih longgar.

Jadi:

- complete-case = hasil utama;
- pairwise-complete = pemeriksaan kestabilan hasil.

## Matriks kompetensi

Secara konseptual, kamu membuat tabel seperti ini:

| Occupation | Reading | Writing | Knowledge A |
|---|---:|---:|---:|
| Data Scientist | 0,90 | 0,75 | 0,80 |
| Statistician | 0,85 | 0,70 | 0,95 |
| Database Architect | 0,60 | 0,55 | 0,88 |

Baris adalah occupation. Kolom adalah elemen kompetensi. Angka adalah Importance yang sudah dinormalisasi.

Lalu baris-baris tersebut dibandingkan untuk menemukan occupation yang profil kompetensinya mirip.

## Dua metode similarity

### 1. Text embedding

Untuk setiap elemen kompetensi, kamu mengambil nama dan deskripsi dari Content Model Reference.

Teks tersebut diubah menjadi vektor oleh model embedding bahasa Inggris. Kemudian:

1. setiap kompetensi memiliki vektor;
2. vektor kompetensi digabungkan untuk setiap occupation;
3. Importance dipakai sebagai bobot;
4. dua occupation dibandingkan memakai cosine similarity.

Embedding terutama menangkap kemiripan makna dan bahasa pada deskripsi kompetensi.

Model **all-MiniLM-L6-v2** hanya baseline pilot dan dapat diganti lewat konfigurasi.

### 2. Skill graph

Pada metode graph, kamu membuat hubungan antara occupation dan competency.

Contoh:

**Data Scientist — Reading Comprehension — 0,90**

Angka di edge adalah Importance yang sudah dinormalisasi.

Dua occupation dibandingkan dengan generalized Jaccard:

**sum(min(weight A, weight B)) / sum(max(weight A, weight B))**

Metode graph lebih langsung menunjukkan kompetensi yang sama dan bobotnya pada masing-masing occupation.

## Arti skor similarity

Skor berada pada rentang 0 sampai 1:

- mendekati 1: profil relatif mirip;
- mendekati 0: profil relatif berbeda.

Skor ini bukan:

- peluang seseorang mendapat pekerjaan;
- persentase kecocokan individu;
- ukuran gaji;
- ukuran kualitas pekerjaan;
- bukti bahwa dua occupation adalah jenjang karier;
- bukti bahwa seseorang pasti dapat berpindah pekerjaan.

Skor hanya menunjukkan kemiripan profil kompetensi berdasarkan data O*NET.

## Mengapa similarity dihitung per domain?

Dua occupation bisa sangat mirip dalam Essential Skills, tetapi berbeda dalam Knowledge. Jika semua elemen langsung dicampur, perbedaan itu dapat tertutup.

Karena itu, hasil utama dibaca sebagai:

- similarity Essential Skills;
- similarity Transferable Skills;
- similarity Knowledge.

Jika skor keseluruhan digunakan, ia hanya menjadi analisis tambahan:

**overall_similarity = (similarity Essential + similarity Transferable + similarity Knowledge) / 3**

Ini bukan generalized Jaccard langsung atas 68 elemen mentah.

## Occupation fokus

Universe analisis berisi seluruh occupation yang lolos complete-case. Untuk interpretasi, fokus core pilot adalah:

- 15-2051.00 Data Scientists
- 15-2051.01 Business Intelligence Analysts
- 15-1242.00 Database Administrators
- 15-1243.00 Database Architects
- 15-1243.01 Data Warehousing Specialists
- 15-2031.00 Operations Research Analysts
- 15-2041.00 Statisticians

- 15-2051.02 Clinical Data Managers menjadi sensitivity analysis karena sifatnya lebih lintas domain.

“Data Engineer” tidak dibuat sebagai occupation O*NET-SOC mandiri tanpa verifikasi resmi.

## Shared competencies dan competency gap

Untuk setiap pasangan occupation fokus, kamu melihat kompetensi yang sama.

### Shared competencies

Tabel ini berisi:

- occupation A dan B;
- domain;
- ID, nama, dan deskripsi elemen;
- bobot A dan B;
- shared weight, yaitu nilai minimum dari kedua bobot.

Jika A = 0,90 dan B = 0,70, maka shared weight = 0,70.

### Competency gap

Gap menunjukkan perbedaan bobot:

**gap = weight A - weight B**

Contoh:

- A = 0,90;
- B = 0,70;
- gap = +0,20.

Nilai positif berarti elemen tersebut lebih penting pada A. Nilai negatif berarti lebih penting pada B.

## Related Occupations

O*NET juga menyediakan daftar occupation yang dianggap related.

Daftar tersebut digunakan sebagai:

> referensi internal O*NET untuk evaluasi keselarasan peringkat, bukan ground truth dan bukan benchmark independen.

Kamu memeriksa apakah occupation yang dinilai mirip oleh embedding atau graph juga muncul pada daftar Related Occupations.

Metriknya:

- Recall@5;
- Recall@10;
- NDCG@10.

Metrik ini dihitung untuk seluruh occupation dalam universe complete-case, bukan hanya occupation fokus.

## Diagnostics embedding

Diagnostics membantu melihat apakah skor embedding terlalu berkumpul.

Pada run terakhir, Essential Skills memiliki standard deviation sekitar 0,0073 dan ditandai terlalu terkonsentrasi menurut heuristik std < 0,01.

Artinya, banyak skor embedding berada sangat dekat dengan 1. Ini tidak otomatis berarti model salah. Namun, model mungkin kurang mampu membedakan occupation pada domain tersebut.

Karena itu, hasil embedding harus dibaca bersama hasil graph.

## Apa yang sedang dihasilkan?

Pipeline dan notebook menghasilkan:

- audit kualitas data;
- daftar occupation yang dieksklusi dan alasannya;
- matriks kompetensi;
- matriks similarity embedding;
- matriks similarity graph;
- sensitivity pairwise-complete;
- top-3 occupation terdekat;
- shared competencies;
- competency gaps;
- validasi enam matriks;
- diagnostics embedding;
- evaluasi Related Occupations;
- visualisasi graph.

Notebook **onet_pilot_walkthrough.ipynb** menampilkan proses tersebut langsung sebagai cell Markdown dan output, sehingga kamu dapat mengikuti langkahnya tanpa membaca semua CSV.

## Apa yang tidak kamu klaim?

Penelitianmu tidak menyatakan bahwa:

- satu pekerjaan lebih baik daripada pekerjaan lain;
- satu occupation pasti merupakan jalur karier menuju occupation lain;
- kompetensi saja cukup untuk menentukan perpindahan kerja;
- hasil O*NET berlaku langsung untuk Indonesia;
- embedding atau graph adalah ground truth;
- Related Occupations adalah label benar mutlak;
- similarity berarti kecocokan individu dengan lowongan.

## Ringkasan satu kalimat

Kamu sedang membangun **pilot penelitian reproducible untuk memetakan dan membandingkan profil kompetensi occupation di Amerika Serikat menggunakan tiga domain O*NET, dengan dua metode similarity yang hasilnya dibandingkan secara deskriptif**.

