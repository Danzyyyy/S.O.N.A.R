# 🧹 Log Pembersihan & Deduplikasi Data (Task D-02)

**Tanggal Eksekusi:** 2026-11-18 10:06:39
**Input File:** `data/raw/youtube_comments_raw.csv`
**Output Clean File:** `data/processed/comments_cleaned.csv`
**Status Task:** ✅ **SELESAI (DONE)**

---

## 1. Ringkasan Eksekusi Pembersihan

| Metrik | Nilai |
| :--- | :---: |
| **Total Data Mentah Awal** | **1,500** baris |
| **Total Data Dihapus (Duplikat & Noise)** | **2** baris |
| **Total Data Bersih Akhir** | **1,498** baris |
| **Tingkat Kebersihan (Retention Rate)** | **99.87%** |

---

## 2. Kategori Pembersihan & Alasan Penghapusan

| Kategori Alasan | Jumlah Dihapus | Deskripsi Aturan |
| :--- | :---: | :--- |
| `Duplikat persis (Exact duplicate)` | 2 | Komentar teks identik (case-insensitive) yang diposting berulang |

### Contoh Data yang Dihapus:

| ID Awal | Pengguna | Alasan | Snippet Teks Asli |
| :---: | :--- | :--- | :--- |
| 1053 | @isenginaja13 | `Duplikat persis (Exact duplicate)` | "Bang saran : untuk hp2 yang bagus kualitas dan harganya, har..." |
| 1060 | @TianEko-w2f | `Duplikat persis (Exact duplicate)` | "semoga saya dan kalian semua bisa sukses dunia dan akhirat, ..." |

---

## 3. Perbandingan Distribusi Sebelum vs Sesudah

### A. Distribusi Sentimen

| Sentimen | Sebelum (Raw) | Sesudah (Clean) | Retensi (%) |
| :--- | :---: | :---: | :---: |
| **Positive** | 374 | 372 | 99.5% |
| **Neutral** | 1,004 | 1,004 | 100.0% |
| **Negative** | 122 | 122 | 100.0% |

### B. Distribusi Topik

| Topik | Sebelum (Raw) | Sesudah (Clean) |
| :--- | :---: | :---: |
| `public_policy_politics` | 450 | 450 |
| `tech_gadget_review` | 300 | 298 |
| `digital_privacy_security` | 300 | 300 |
| `product_recommendation` | 150 | 150 |
| `social_financial_issues` | 150 | 150 |
| `history_education` | 150 | 150 |

---

## 4. Integritas Metadata Wajib (Kriteria PM Selesai)

Seluruh kolom yang dibutuhkan untuk formatting konteks chat dipertahankan 100%:
- [x] `id` (Sequential integer 1..N)
- [x] `timestamp` (Tanggal valid YYYY-MM-DD)
- [x] `platform` (Platform sumber 'YouTube')
- [x] `username` (Handle/nama pengguna untuk atribusi chat)
- [x] `comment` (Teks bersih bebas noise)
- [x] `sentiment` (Label sentimen: positive/neutral/negative)
- [x] `topic` (Label topik terstandar)
- [x] `likes` (Jumlah interaksi netizen)
