# STANDAR OPERASIONAL PROSEDUR (SOP)
## PENANGANAN BUG DAN KENDALA RILIS UPDATE APLIKASI (v2.4)

---

### 1. Tujuan
Menjadi pedoman penanganan cepat ketika rilis versi aplikasi terbaru memicu lonjakan ulasan negatif, penurunan rating bintang di toko aplikasi (Google Play Store & App Store), atau keluhan performa (lag, freeze, crash, kendala otentikasi biometrik).

---

### 2. Kriteria dan Pemicu Investigasi
1. **Penurunan Rating Harian:** Rata-rata rating harian di Google Play Store turun di bawah 3.8 bintang pasca peluncuran versi baru.
2. **Lonjakan Kata Kunci Masalah:** Terdeteksi peningkatan frekuensi kata kunci *"force close"*, *"layar hitam"*, *"lag parah"*, *"gagal login"*, atau *"update bikin rusak"* sebanyak > 30 keluhan per jam.
3. **Peningkatan Crash Rate:** Crash-free users turun di bawah 98.5% pada platform APM (Firebase Crashlytics).

---

### 3. Alur Analisis Akar Masalah (S.O.N.A.R)
1. **Pencarian Semantik Komplain:** Operator meminta S.O.N.A.R mengekstrak pola keluhan dari ulasan Play Store dan komentar media sosial.
2. **Pengelompokan Isu Berdasarkan Tipe Perangkat:**
   - Memetakan apakah bug terkonsentrasi pada versi OS Android tertentu (misal: Android 13/14).
   - Memeriksa ketidakcocokan dependensi library UI pada arsitektur perangkat lawas.
3. **Verifikasi Jalur Otentikasi:** Mendiagnosis apakah terjadi *token invalidation* massal saat migrasi database lokal aplikasi.

---

### 4. Tindakan Perbaikan dan Mitigasi Teknis
1. **Hotfix Release:** Jika bug mematikan fungsi utama (*critical crash*), tim mobile engineer wajib menerbitkan patch darurat (v2.4.1) dalam kurun waktu 1x24 jam.
2. **Halt / Rollback Rollout:** Jika rilis bertahap (*staged rollout*) masih di bawah 50%, segera hentikan peluncuran (Halt rollout) di Google Play Console.
3. **Pembaruan Konfigurasi Remote Config:** Nonaktifkan modul fitur baru yang bermasalah secara dinamis melalui server tanpa memerlukan update aplikasi di sisi pengguna.

---

### 5. Strategi Komunikasi dan Penanganan Ulasan
1. **Respon Balasan Toko Aplikasi:** Tim Customer Support membalas ulasan bintang 1 secara proaktif dengan instruksi mitigasi sementara:
   > *"Halo, mohon maaf atas kendala yang dialami pasca update v2.4. Mohon coba lakukan bersihkan cache aplikasi (Pengaturan > Aplikasi > Hapus Cache) atau restart perangkat. Tim kami sedang menyiapkan pembaruan perbaikan (patch v2.4.1) yang akan segera tersedia."*
2. **Panduan FAQ Media Sosial:** Bagikan infografis langkah penanganan sementara di kanal media sosial resmi untuk menekan laju komplain berulang.

---

### 6. Batas Waktu Tindakan (SLA)
- Analisis pola komplain via S.O.N.A.R: < 45 menit.
- Keputusan penundaan rollout (Halt): < 2 jam.
- Peluncuran hotfix patch: < 24 jam.
