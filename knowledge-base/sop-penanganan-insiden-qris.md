# STANDAR OPERASIONAL PROSEDUR (SOP)
## PENANGANAN DAN MITIGASI INSIDEN TRANSAKSI QRIS

---

### 1. Tujuan
Memberikan panduan operasional baku bagi Tim Teknis, Customer Care, dan Public Relations dalam mendeteksi, mendiagnosis, dan menyelesaikan insiden kegagalan transaksi QRIS (seperti transaksi *timeout*, saldo terpotong namun status gagal/pending, dan kegagalan notifikasi *merchant*).

---

### 2. Kriteria dan Indikator Insiden
Insiden transaksi QRIS diklasifikasikan sebagai insiden prioritas tinggi apabila memenuhi salah satu indikator berikut:
1. **Tingkat Kegagalan (Failure Rate):** Kegagalan transaksi QRIS melebihi 5% dari total volume transaksi per 15 menit.
2. **Lonjakan Keluhan Media Sosial:** Terdeteksi lebih dari 20 komplain netizen terkait "QRIS timeout" atau "saldo terpotong" dalam kurun waktu 30 menit di kanal Twitter/X, Instagram, atau TikTok.
3. **Kendala Mitra Switching:** Adanya laporan *degraded service* atau *downtime* dari *payment gateway* / *switching provider* QRIS.

---

### 3. Alur Investigasi dan Root-Cause Analysis (S.O.N.A.R)
1. **Penarikan Bukti Komentar:** Operator memasukkan kueri investigasi ke sistem S.O.N.A.R:
   > *"Analisis akar masalah keluhan transaksi QRIS gagal dan saldo terpotong hari ini."*
2. **Validasi Bukti (Document Grader):** Sistem memastikan data komplain nasabah terverifikasi valid dan tidak bias.
3. **Diagnosis Akar Masalah:**
   - Cek *network timeout* antara Core Banking dengan API Switching QRIS.
   - Periksa antrean pesan (message queue) transaksi yang tertahan (*choked*).
   - Identifikasi *merchant-side timeout* akibat *response time* melebihi 30 detik.

---

### 4. Tindakan Mitigasi Teknis
1. **Penyelarasan Saldo (Reconciliation):** Jalankan skrip *auto-reversal* otomatis dalam SLA maksimal 1x24 jam untuk transaksi berstatus *indeterminate*.
2. **Failover Gateway:** Alihkan *traffic routing* QRIS ke *switching gateway* cadangan jika gateway utama mengalami *packet loss* > 10%.
3. **Peningkatan Kapasitas Pods:** Lakukan *horizontal autoscaling* pada *service worker payment* untuk mengatasi lonjakan *throughput*.

---

### 5. Komunikasi Publik dan Customer Care
1. **Holding Statement Tim PR:** Rilis pernyataan resmi bernada empati dalam waktu < 30 menit sejak insiden terdeteksi:
   > *"Kami memohon maaf atas ketidaknyamanan yang dialami terkait kendala transaksi QRIS. Tim teknis kami sedang melakukan investigasi dan penanganan intensif. Bagi nasabah yang saldonya terpotong namun transaksi belum berhasil, dana Anda aman dan proses rekonsiliasi/pengembalian sedang berjalan otomatis."*
2. **Panduan Tim Customer Care:**
   - Gunakan skrip respon terpadu agar tidak memicu kebingungan nasabah.
   - Catat ID transaksi nasabah (RRN - *Retrieval Reference Number*) untuk validasi manual prioritas.

---

### 6. Estimasi Waktu Penyelesaian (SLA)
- Deteksi dan draf holding statement: < 30 menit.
- Perbaikan teknis / failover: < 2 jam.
- Normalisasi pemulihan saldo nasabah terdampak: Maksimal 1 x 24 jam kerja.
