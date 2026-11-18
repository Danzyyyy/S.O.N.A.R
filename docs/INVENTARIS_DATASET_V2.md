# 📦 Laporan Inventarisasi Dataset v2 (Task D-01)

**Tanggal Pembaruan:** 2026-11-18 10:04:52
**Role:** Data Engineer — Proyek S.O.N.A.R
**Status Task:** ✅ **SELESAI (DONE)**

---

## 1. Ringkasan Eksekutif

Dataset v2 berhasil diekspansi dari **30 komentar awal (baseline v1)** menjadi **1500 komentar riil** yang dikumpulkan dari 10 video YouTube dengan topik yang representatif (peningkatan **50x lipat**).

Seluruh metadata wajib (`id`, `timestamp`, `platform`, `username`, `comment`, `sentiment`, `topic`, `likes`) terisi lengkap dan terstruktur secara konsisten.

---

## 2. Distribusi Data

### A. Distribusi Platform

| Platform | Jumlah Data | Persentase |
| :--- | :---: | :---: |
| **YouTube** | 1,500 | 100.0% |
| **Total** | **1,500** | **100.0%** |

### B. Distribusi Sentimen

| Kategori Sentimen | Jumlah Komentar | Persentase | Interpretasi |
| :--- | :---: | :---: | :--- |
| **Positive** | 374 | 24.9% | Apresiasi, doa, pujian produk/tokoh |
| **Neutral** | 1,004 | 66.9% | Pertanyaan, kutipan, pernyataan faktual |
| **Negative** | 122 | 8.1% | Kritik, kecurigaan, keluhan, sarkasme |
| **Total** | **1,500** | **100.0%** | — |

### C. Distribusi Topik

| Topik | Deskripsi Konten | Jumlah | Persentase |
| :--- | :--- | :---: | :---: |
| `public_policy_politics` | Kebijakan publik, isu ketatanegaraan & hukum | 450 | 30.0% |
| `tech_gadget_review` | Ulasan performa smartphone, spesifikasi, unboxing | 300 | 20.0% |
| `digital_privacy_security` | Isu keamanan data, penyadapan & privasi perangkat | 300 | 20.0% |
| `product_recommendation` | Rekomendasi gadget terbaik & perbandingan harga | 150 | 10.0% |
| `social_financial_issues` | Isu sosial kemasyarakatan & transaksi keuangan publik | 150 | 10.0% |
| `history_education` | Diskusi sejarah nasional & edukasi publik | 150 | 10.0% |
| **Total** | — | **1,500** | **100.0%** |

---

## 3. Sampel Komentar Terlabeli

Berikut contoh baris data hasil pelabelan dan inventarisasi:

| ID | Platform | User | Komentar (Snippet) | Sentimen | Topik |
| :---: | :--- | :--- | :--- | :---: | :--- |
| 1 | YouTube | @nurulfutichart | "Om ded kalo bahas yg gak mengancam posisi prabowo cepet bgt...." | `neutral` | `public_policy_politics` |
| 151 | YouTube | @Yuka.and.3D | "ngeri Poco.. apapun yang kebeli sama kita, disyukuri.. yang ..." | `negative` | `tech_gadget_review` |
| 301 | YouTube | @Ghea2810 | "Isi hati : ayolah bro ganti HP Isi otak : kayaknya hp itu ba..." | `positive` | `product_recommendation` |
| 601 | YouTube | @gagahpriyo6481 | "Koruptor gk di sadap presiden malah di sadap 😂😂😂..." | `negative` | `digital_privacy_security` |
| 1351 | YouTube | @MalakaProjectid | "Selama ini kamu mengenal G30S dari narasi yang seperti apa? ..." | `neutral` | `history_education` |

---

## 4. Kriteria Selesai (Checklist PM)

- [x] Dataset diekspansi melebihi baseline awal 30 komentar (aktual: 1.500 data).
- [x] Metadata wajib (`platform`, `username`, `timestamp`, `likes`, `sentiment`, `topic`) lengkap 100%.
- [x] Distribusi tercatat per platform, sentimen, dan topik.
- [x] File dataset v2 mentah siap diteruskan ke tahap D-02 (Pembersihan & Deduplikasi).
