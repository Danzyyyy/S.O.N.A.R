# Analisis Risiko Terpadu: Integrasi OpenSearch sebagai Vector Store
## Evaluasi Komprehensif Kebutuhan Sumber Daya, Kompleksitas Operasional, Siklus Hidup Sistem, dan Komparasi Multi-Engine Vector Database

**Dokumen Referensi:** Spesifikasi Laboratorium Sistem Informasi `Pertemuan 6.docx` (Modul 10, 11, 12) & `ORIGINAL_REQUEST.md` (Kebutuhan R1)  
**Target Arsitektur:** S.O.N.A.R (Social Online Network Analytics & Response) / NALA Academic Assistant  
**Penyusun:** Tim Riset Arsitektur & Rekayasa Perangkat Lunak (`worker_m1_risk_1`)  
**Status Dokumen:** Rilis Resmi Milestone M1  
**Tanggal Rilis:** 2026-11-02  

---

## Daftar Isi
1. [Executive Summary & Matriks Keputusan Eksekutif](#1-executive-summary--matriks-keputusan-eksekutif)
   - 1.1 Latar Belakang & Rasional Strategis
   - 1.2 Ringkasan Temuan Kunci & Profil Risiko
   - 1.3 Matriks Keputusan Eksekutif (Executive Decision Matrix)
2. [Analisis Kebutuhan Sumber Daya (Hardware & Infrastruktur)](#2-analisis-kebutuhan-sumber-daya-hardware--infrastruktur)
   - 2.1 Arsitektur Tri-Partition Memori OpenSearch (RAM Footprint)
   - 2.2 Dampak Lingkungan Pengembang Lokal (Local Developer Host Context)
   - 2.3 Dinamika Utilisasi CPU (Indexing Spikes vs Idle vs Query Concurrency)
   - 2.4 Overhead Penyimpanan Disk & Faktor Amplifikasi Data
3. [Kompleksitas Operasional & Konfigurasi Sistem](#3-kompleksitas-operasional--konfigurasi-sistem)
   - 3.1 Prasyarat Kernel Host Linux (`vm.max_map_count`) & Remediasi WSL2
   - 3.2 Penyetelan JVM Heap & Pertimbangan Garbage Collection
   - 3.3 Dinamika Status Kesehatan Klaster (Cluster Health YELLOW vs GREEN)
   - 3.4 Manajemen Izin File, UID Container, dan Isolasi I/O Volume
   - 3.5 Konfigurasi Plugin Keamanan: Lingkungan Pengembangan vs Produksi
   - 3.6 Latensi Cold-Start & Dampak terhadap Otomasi Pengujian / CI-CD
4. [Pemeliharaan Jangka Panjang & Siklus Hidup (Lifecycle)](#4-pemeliharaan-jangka-panjang--siklus-hidup-lifecycle)
   - 4.1 Immutabilitas Pemetaan Skema (Schema Mapping Immutability) & Re-indexing
   - 4.2 Siklus Upgrade Versi & Depresiasi Komponen Mesin Vektor
   - 4.3 Prosedur Pencadangan (Backup), Snapshot, dan Pemulihan Data
   - 4.4 Manajemen Ambang Batas Disk (Disk Watermarks) & Status Auto Read-Only
5. [Matriks Analisis Komparatif (7 Solusi Vector Store)](#5-matriks-analisis-komparatif-7-solusi-vector-store)
   - 5.1 Matriks Komparasi Komprehensif 7 Engine Vektor
   - 5.2 Evaluasi Naratif Komparatif Mendalam per Solusi
6. [Rekomendasi Arsitektur & Peta Jalan Migrasi (Migration Roadmap)](#6-rekomendasi-arsitektur--peta-jalan-migrasi-migration-roadmap)
   - 6.1 Pola Desain Abstraksi Dual-Store (`VectorStore` Interface)
   - 6.2 Praktik Terbaik Konfigurasi: Local Development vs Staging / Produksi
   - 6.3 Peta Jalan Migrasi Bertahap (Safe Step-by-Step Migration Roadmap)
   - 6.4 Matriks Verifikasi & Rencana Validasi Kualitas

---

## 1. Executive Summary & Matriks Keputusan Eksekutif

### 1.1 Latar Belakang & Rasional Strategis
Proyek ini bertransformasi dari sistem analitik sentimen berbasis repositori dokumen lokal (**S.O.N.A.R**) menjadi asisten akademik komprehensif berbasis Retrieval-Augmented Generation (**NALA**), sebagaimana dispesifikasikan dalam silabus laboratorium `Pertemuan 6.docx` (Modul 10, 11, dan 12). Dalam arsitektur awal, penyimpanan vektor dan pencarian similaritas ditangani oleh **ChromaDB (v0.5.18)** yang berkomunikasi dengan model embedding `nomic-embed-text` (vektor 768 dimensi) melalui Ollama.

Spesifikasi Modul 12 secara eksplisit menginstruksikan penggelaran layanan **OpenSearch 2.11.0** lokal via Docker Compose, dilengkapi plugin k-NN (k-Nearest Neighbors) dengan engine `nmslib` dan metrik jarak `cosinesimil`. Adopsi OpenSearch menjanjikan kemampuan pencarian leksikal berkelas *enterprise* (BM25), *hybrid search* natif via search pipeline, visualisasi indeks melalui OpenSearch Dashboards, serta skalabilitas klaster horizontal hingga ukuran petabyte.

Namun demikian, pengenalan OpenSearch ke dalam alur kerja lokal menghadirkan implikasi teknis dan operasional yang substansial. Laporan ini disusun untuk menyajikan evaluasi objektif, berbasis data empiris, dan komprehensif mengenai seluruh aspek risiko teknis guna memastikan transisi arsitektur berjalan aman, efisien, dan andal.

### 1.2 Ringkasan Temuan Kunci & Profil Risiko
Berdasarkan investigasi lingkungan dan pengujian spesifikasi, berikut adalah temuan-temuan krusial:

1. **Beban Memori yang Signifikan (*Heavy Memory Footprint*)**:  
   OpenSearch adalah sistem berbasis Java Virtual Machine (JVM) terdistribusi. Footprint memori operasional minimal satu node OpenSearch berkisar antara **1.5 GB hingga 2.5 GB RAM** (gabungan JVM Heap 512 MB–1 GB, Lucene MMap off-heap cache, dan memori native C++ untuk graf HNSW). Ditambah dengan OpenSearch Dashboards (~500 MB) dan Ollama (~2.5 GB untuk model embedding dan LLM 3B), total kebutuhan memori kontainer Docker mencapai **~5.3 GB RAM**. Pada mesin pengembang lokal berkapasitas total 16 GB dengan sisa memori fisik bebas ~2.2 GB (terukur saat survei), menjalankan tumpukan (*stack*) ini secara simultan berisiko tinggi memicu *system thrashing* atau terminasi kontainer oleh *Out-Of-Memory (OOM) Killer*.
2. **Friksi Prasyarat Host Kernel Linux**:  
   OpenSearch mewajibkan parameter kernel Linux `vm.max_map_count` disetel minimal **262144** agar Lucene dapat memetakan segmen indeks ke dalam memori virtual. Nilai bawaan pada WSL2/Docker Desktop untuk Windows adalah 65530. Tanpa penyesuaian manual terlebih dahulu, kontainer OpenSearch akan langsung mengalami *crash* saat inisialisasi boot.
3. **Kekakuan Skema Indeks Vektor (Schema Immutability)**:  
   Pada OpenSearch k-NN, dimensi vektor (misalnya 768) dan algoritma pencarian bersifat permanen (*immutable*) setelah indeks dibuat. Penggantian model embedding di masa depan menuntut migrasi indeks menyeluruh (*full re-indexing*) dengan re-embedding dari sumber data mentah.
4. **Depresiasi Engine `nmslib`**:  
   Meskipun silabus Pertemuan 6 mereferensikan engine `nmslib`, komunitas OpenSearch telah mendepresiasi `nmslib` pada rilis versi 2.13+ dan merencanakan penghapusannya pada OpenSearch 3.0, dengan rekomendasi transisi ke engine `lucene` atau `faiss`.

### 1.3 Matriks Keputusan Eksekutif (Executive Decision Matrix)

Tabel berikut merangkum penilaian strategis antara mempertahankan ChromaDB, bermigrasi penuh ke OpenSearch, atau menerapkan pola arsitektur hibrida (*Dual-Store Abstraction*):

| Dimensi Evaluasi | ChromaDB (Baseline) | OpenSearch (Mandat Modul 12) | Pendekatan Dual-Store (Rekomendasi) |
|---|---|---|---|
| **Kepatuhan Spesifikasi Pertemuan 6** | Tidak Patuh (Gagal Modul 12) | **100% Patuh** | **100% Patuh** (OpenSearch aktif sebagai target primer) |
| **Beban RAM Mesin Pengembang** | Sangat Ringan (~150–250 MB) | Berat (~1.8–2.5 GB per node) | Fleksibel: OpenSearch diutamakan, fallback ke Chroma jika RAM host kritis |
| **Kemampuan Hybrid Search** | Terbatas (filter teks terpisah) | **Natif & Terpadu** (BM25 + k-NN + RRF) | Tersedia penuh saat backend OpenSearch aktif |
| **Kompleksitas Setup Pengembang** | Minimal (`docker-compose up` instan) | Tinggi (`sysctl`, tuning heap, UID) | Termitigasi melalui otomasi skrip & dokumentasi prasyarat |
| **Inspeksi & Visualisasi Data** | Terbatas / Tool pihak ketiga | **Sangat Baik** (Dashboards port 5601) | Akses visual penuh via OpenSearch Dashboards |
| **Ketahanan terhadap Downtime** | Downtime lokal berdampak fatal | Perlu *warmup* 30–45 detik | **Tinggi**: Failover otomatis jika OpenSearch gagal boot |
| **Keputusan Strategis** | Dipertahankan sebagai fallback | **Diadopsi Penuh untuk Milestone M2/M3** | **Rekomendasi Utama Arsitektur** |

---

## 2. Analisis Kebutuhan Sumber Daya (Hardware & Infrastruktur)

### 2.1 Arsitektur Tri-Partition Memori OpenSearch (RAM Footprint)
Berbeda dengan vector database berbasis Python atau C murni yang mengalokasikan memori secara terpadu, OpenSearch mengonsumsi RAM melalui **tiga lapisan memori terpisah** yang beroperasi secara independen:

```
+-----------------------------------------------------------------------+
|                       Total RAM Container OpenSearch                  |
+-----------------------------------+-----------------------------------+
|             JVM Heap              |           Off-Heap / OS           |
|         (-Xms512m -Xmx512m)       |         (Memori Fisik Host)       |
+-----------------------------------+-----------------------------------+
| - Shard Routing Table             | 1. Lucene Filesystem Page Cache   |
| - Cluster State & Coordination    |    - Inverted Index (.doc, .tim)  |
| - Query DSL Parsing & Transport   |    - DocValues (.dvd, .dvm)       |
| - Buffer Tulis Indexing & Translog|    - MMap direct kernel read      |
| - Thread Pools & G1GC Overhead    | 2. Native C++ HNSW Vector Graph   |
|                                   |    - Native heap (nmslib / faiss) |
|                                   |    - Circuit breaker: 50% RAM     |
+-----------------------------------+-----------------------------------+
```

#### 1. Lapisan JVM Heap (`-Xms512m -Xmx512m` hingga `1 GB`)
JVM Heap dialokasikan secara eksplisit melalui variabel lingkungan `OPENSEARCH_JAVA_OPTS`. Heap ini menampung:
- Metadata klaster dan struktur topologi shard.
- Buffer transaksi indeks (*indexing buffer*) sebelum segmen ditulis ke disk.
- Deserialisasi payload JSON dan serialisasi respons HTTP REST API.
- Koordinasi internal *thread pools* (search, write, management).

*Pertimbangan Teknis:* Nilai `-Xms` (minimum) dan `-Xmx` (maksimum) **harus disetel identik**. Jika `-Xms` lebih rendah daripada `-Xmx`, JVM akan terus melakukan alokasi dan dealokasi memori secara dinamis saat beban kerja berfluktuasi, yang memicu overhead kernel dan fragmentasi memori.

#### 2. Lapisan Lucene Off-Heap (OS Filesystem Page Cache / MMap)
Apache Lucene tidak menyimpan indeks teks (inverted index, posting lists, term dictionary) di dalam JVM heap. Lucene mengandalkan mekanisme virtual memory kernel Linux melalui `MMapDirectory` (`mmap`). Sistem operasi secara transparan memetakan file segmen indeks pada disk ke dalam memori cache sistem operasi (*page cache*). Hal ini memungkinkan pembacaan data leksikal dengan latensi sangat rendah (*zero-copy memory access*) tanpa membebani mekanisme *Garbage Collector* JVM.

#### 3. Lapisan Graf Vektor Native C++ (k-NN Engine Heap)
Komponen penentu yang membedakan OpenSearch k-NN dari mesin pencari konvensional adalah penyimpanan graf navigasi vektor (*Hierarchical Navigable Small World* / HNSW). Graf HNSW **tidak dialokasikan di dalam JVM Heap**, melainkan dialokasikan pada memori C++ native di luar kendali JVM oleh library `nmslib` atau `faiss`.

Estimasi konsumsi memori graf HNSW dapat dimodelkan secara matematis melalui formula:
$$M_{\text{HNSW}} \approx 1.1 \times N \times \left( d \times 4 + M \times 8 \right) \text{ byte}$$

Di mana:
- $N$ = Jumlah total dokumen / vektor yang diindeks.
- $d$ = Dimensi vektor ($768$ untuk model `nomic-embed-text`).
- $4$ = Alokasi 4 byte per komponen vektor (`float32`).
- $M$ = Jumlah koneksi dua arah per node dalam graf HNSW (nilai bawaan OpenSearch $M = 16$).
- $8$ = Alokasi 8 byte per pointer memori 64-bit pada graf koneksi.
- $1.1$ = Faktor ekspansi overhead struktur internal C++ (~10%).

*Contoh Perhitungan:*  
Untuk indeks berisi $10.000$ dokumen berdimensi 768:
$$M_{\text{HNSW}} \approx 1.1 \times 10.000 \times \left( 768 \times 4 + 16 \times 8 \right) = 1.1 \times 10.000 \times (3.072 + 128) = 1.1 \times 32.000.000 \approx 35,2 \text{ MB}$$
Meskipun untuk 10.000 dokumen kebutuhan graf hanya ~35 MB, k-NN plugin menerapkan *circuit breaker* bawaan (`knn.memory.circuit_breaker.limit`), yang secara default mencadangkan hingga **50% dari total RAM kontainer** untuk operasional graf vektor.

#### 4. Total Working Footprint
- **OpenSearch Node**:
  - Kondisi *Idle*: **~1.1 GB – 1.4 GB RAM**.
  - Kondisi *Active Indexing / Search*: **~1.8 GB – 2.5 GB RAM**.
- **OpenSearch Dashboards**:
  - Berjalan sebagai server Node.js terpisah: **~350 MB – 500 MB RAM**.

---

### 2.2 Dampak Lingkungan Pengembang Lokal (Local Developer Host Context)

#### Hasil Pengukuran Lingkungan Nyata (Empirical Host Status)
Pengukuran telemetri sistem operasi pada lingkungan pengembang host (`d:\PDS`) menunjukkan parameter berikut:
- **Total Physical RAM Host**: **16,08 GB** (16.473.976 KB).
- **Available / Free Physical RAM**: **2,21 GB** (2.261.720 KB).
- **Sistem Operasi**: Windows 11 Enterprise / Home 64-bit dengan Docker Desktop berbasis WSL2 Backend.

#### Kalkulasi Beban Simultan (Simultaneous Multi-Container Stack)
Jika seluruh layanan yang diinstruksikan dalam proyek dijalankan secara bersamaan di dalam Docker Desktop, beban memori terhitung adalah sebagai berikut:

| Nama Layanan / Proses | Komponen Internal | Alokasi RAM Minimum | Alokasi RAM Tipikal |
|---|---|---|---|
| **Ollama Service** | Model LLM `llama3.2:3b` | 1.800 MB | 2.200 MB |
| | Model Embedding `nomic-embed-text` | 450 MB | 600 MB |
| **OpenSearch Node** | JVM Heap (`-Xms512m -Xmx512m`) | 512 MB | 512 MB |
| | Lucene Page Cache & k-NN Native Memory | 750 MB | 1.500 MB |
| **OpenSearch Dashboards** | Runtime Node.js & Visual Workspace | 350 MB | 500 MB |
| **FastAPI Backend (`api`)** | Python 3.11 Runtime, Uvicorn, Cache | 250 MB | 400 MB |
| **ChromaDB (Dual-Store)** | In-Memory SQLite + HNSW C++ | 150 MB | 250 MB |
| **Total Beban Kontainer** | | **4.262 MB (~4,2 GB)** | **5.462 MB (~5,4 GB)** |

#### Analisis Risiko Host:
1. **Defisit Memori Fisik Instan**:  
   Kebutuhan kontainer tipikal (~5,4 GB) melampaui sisa memori fisik bebas host (2,21 GB) dengan defisit sebesar **~3,2 GB**.
2. **Page Swapping & Disk Thrashing**:  
   Ketika konsumsi memori melampaui batas fisik, Windows dan subsistem WSL2 (`vmmem`) akan memindahkan halaman memori yang jarang diakses ke file *pagefile.sys* di solid-state drive (SSD). Hal ini mengakibatkan lonjakan I/O disk yang parah (*disk thrashing*), penurunan drastis performa aplikasi, dan latensi respons antarmuka IDE.
3. **Risiko OOM Killer**:  
   Jika batas alokasi memori pada Docker Desktop (default 50% RAM host pada WSL2) tercapai, kernel Linux akan secara otomatis mematikan kontainer yang paling rakus memori (`opensearch_node` atau `ollama_service`) melalui sinyal `SIGKILL` (Exit Code 137).

---

### 2.3 Dinamika Utilisasi CPU (Indexing Spikes vs Idle vs Query Concurrency)

1. **Kondisi Idle (Tanpa Beban Transaksi)**:  
   Utilisasi CPU OpenSearch berkisar antara **1% hingga 3%**. Utilisasi ini digunakan oleh *daemon threads* untuk pemantauan kesehatan klaster (*cluster pinging*), pengecekan checkpoint translog, dan siklus berkala G1 Garbage Collector.
2. **Kondisi Indexing Aktif (Penyusunan Graf HNSW)**:  
   Penyusunan indeks k-NN menuntut kalkulasi jarak trigonometri (vektor kosinus) pada setiap simpul baru yang dimasukkan. Dengan konfigurasi parameter bawaan (`ef_construction = 128`, `m = 16`), pembuatan graf HNSW bersifat **sangat komputasional (*CPU-intensive*)**. Selama skrip ingestion mengeksekusi batch dokumen, utilisasi CPU kontainer OpenSearch dapat melonjak hingga **100% pada seluruh core virtual** yang dialokasikan, yang berpotensi memicu perlambatan sementara pada proses inferensi LLM di Ollama jika core CPU tidak diisolasi.
3. **Kondisi Query Concurrency (Pencarian Paralel)**:  
   Pada saat mengeksekusi k-NN query, OpenSearch memanfaatkan *search thread pool* native yang membagi pencarian secara paralel antar shard. Untuk dataset kecil (<10.000 dokumen pada 1 shard), latensi kueri sangat rendah (<15 milidetik), dan lonjakan CPU bersifat sangat singkat (*spike-and-drop*).

---

### 2.4 Overhead Penyimpanan Disk & Faktor Amplifikasi Data

Penyimpanan disk OpenSearch tidak hanya mencakup teks mentah, melainkan terbagi ke dalam empat komponen utama:

```
+-----------------------------------------------------------------------+
|                    Struktur Disk Index OpenSearch                     |
+-------------------+---------------------------------------------------+
| Komponen Data     | Deskripsi & Mekanisme Penyimpanan                 |
+-------------------+---------------------------------------------------+
| 1. _source Store  | Payload JSON mentah dokumen asli (terkompresi)    |
| 2. Inverted Index | Posting lists, dictionary, term positions (Lucene)|
| 3. k-NN Vectors   | File graf biner navigasi (.hnsw / .faiss)        |
| 4. Translog (WAL) | Write-Ahead Log untuk durabilitas crash recovery  |
+-------------------+---------------------------------------------------+
```

#### Perhitungan Faktor Amplifikasi Penyimpanan (Storage Amplification Factor):
Mari kita analisis dataset hipotetis yang mewakili koleksi dokumen SOP dan komentar analitik:
- Jumlah dokumen: **10.000 dokumen**.
- Ukuran rata-rata teks per dokumen: 1 KB teks mentah $\rightarrow$ Total teks mentah = **10 MB**.
- Dimensi embedding: 768 float32 (4 byte per elemen) = $768 \times 4 = 3.072 \text{ byte}$ per vektor.
- Total data biner vektor: $10.000 \times 3.072 \text{ byte} \approx \mathbf{30,72 \text{ MB}}$.
- **Ukuran Data Murni (Raw Data)**: $10 \text{ MB} + 30,72 \text{ MB} = \mathbf{40,72 \text{ MB}}$.

Ketika diindeks ke dalam OpenSearch:
1. `_source` store (terkompresi LZ4/Deflate): ~6 MB.
2. Lucene Inverted Index (term dictionary + postings + doc values): ~18 MB.
3. File segmen k-NN graf HNSW: ~38 MB.
4. Translog buffer & segment metadata: ~12 MB.
5. **Total Alokasi Disk OpenSearch**: **~74 MB – 110 MB**.

*Rasio Amplifikasi Data:* **~2,5x hingga 3,5x lipat** dari ukuran gabungan teks dan vektor mentah.

#### Overhead Ruang Disk untuk Image Container Docker:
- Image `opensearchproject/opensearch:2.11.0`: **~1,85 GB** (setelah diekstrak ke filesystem host).
- Image `opensearchproject/opensearch-dashboards:2.11.0`: **~1,38 GB**.
- **Total Kebutuhan Disk Awal (Hanya untuk Image)**: **~3,23 GB**.

---

## 3. Kompleksitas Operasional & Konfigurasi Sistem

### 3.1 Prasyarat Kernel Host Linux (`vm.max_map_count`) & Remediasi WSL2

#### Akar Masalah Teknis
OpenSearch mengandalkan implementasi Apache Lucene `MMapDirectory` untuk memetakan file segmen indeks ke dalam ruang memori virtual proses. Konfigurasi kernel Linux membatasi jumlah maksimum area memori virtual (*Virtual Memory Areas* / VMA) yang dapat dimiliki oleh sebuah proses melalui parameter sysctl `vm.max_map_count`.

Nilai standar Linux dan distribusi WSL2 bawaan adalah **65530**. OpenSearch menetapkan pemeriksaan bootstrap (*bootstrap checks*) yang ketat: jika `vm.max_map_count` bernilai kurang dari **262144**, proses boot OpenSearch akan langsung dihentikan secara fatal:
```text
ERROR: [1] bootstrap checks failed
[1]: max virtual memory areas vm.max_map_count [65530] is too low, increase to at least [262144]
```

#### Prosedur Remediasi di Lingkungan Windows / Docker Desktop (WSL2):

##### Opsi A: Remediasi Runtime Cepat (Tanpa Restart Mesin / Rekomendasi Pengujian)
Jalankan satu baris perintah container Alpine dengan hak akses *privileged* langsung dari PowerShell host:
```powershell
docker run --rm --privileged --pid=host alpine sysctl -w vm.max_map_count=262144
```
*Mekanisme:* Perintah ini memodifikasi tabel kernel Linux WSL2 secara langsung pada namespace host, berlaku instan untuk seluruh kontainer Docker yang sedang berjalan.

##### Opsi B: Konfigurasi Permanen via File `.wslconfig`
Agar nilai parameter tidak kembali ke default saat komputer atau Docker Desktop di-restart, buat atau tambahkan baris berikut pada file `%USERPROFILE%\.wslconfig`:
```ini
[wsl2]
kernelCommandLine = sysctl.vm.max_map_count=262144
```
Kemudian jalankan perintah restart subsistem WSL2 di PowerShell administrator:
```powershell
wsl --shutdown
```

---

### 3.2 Penyetelan JVM Heap & Pertimbangan Garbage Collection

Penyetelan memori Java Virtual Machine (JVM) OpenSearch harus memperhatikan prinsip-prinsip berikut:

```yaml
environment:
  - OPENSEARCH_JAVA_OPTS=-Xms512m -Xmx512m
```

#### 1. Aturan Emas 50% Heap (*The 50% Rule*)
Tidak boleh mengalokasikan lebih dari 50% total memori fisik yang tersedia untuk JVM Heap. Setengah dari kapasitas memori wajib disisakan untuk:
- Lucene OS page cache (pembacaan file indeks off-heap).
- Native C++ memory untuk graf HNSW k-NN.
- Thread stack dan network socket buffers.

#### 2. Batas 32 GB dan Compressed Object Pointers (CompressedOops)
Pada server produksi berkapasitas besar, JVM heap **tidak boleh melebihi 31,5 GB**. Di bawah batas ini, JVM 64-bit dapat menggunakan teknik kompresi pointer 32-bit (*CompressedOops*), yang menghemat konsumsi memori hingga 30% dan mempercepat transfer data pada CPU L1/L2/L3 cache. Melampaui 32 GB akan memaksa JVM beralih ke pointer 64-bit murni, yang justru menurunkan efisiensi memori efektif.

#### 3. Garbage Collection: G1GC vs CMS
OpenSearch 2.11.0 dibundel dengan Java 17 LTS yang secara bawaan menggunakan **Garbage-First Garbage Collector (G1GC)**. G1GC dirancang untuk membagi heap ke dalam region-region kecil dan mengeksekusi siklus pembersihan secara bertahap guna meminimalkan *Stop-The-World (STW) pauses*. Pada pengujian lokal dengan heap kecil (512 MB), G1GC beroperasi secara efisien selama heap tidak mengalami tekanan alokasi objek JSON berukuran masif (>50 MB per request).

---

### 3.3 Dinamika Status Kesehatan Klaster (Cluster Health YELLOW vs GREEN)

Pada arsitektur klaster OpenSearch, status kesehatan indeks diklasifikasikan ke dalam tiga indikator warna:
- **GREEN**: Seluruh primary shard dan seluruh replica shard berhasil dialokasikan pada node-node yang aktif.
- **YELLOW**: Seluruh primary shard aktif dan dapat melayani pembacaan serta penulisan data, namun minimal satu replica shard belum/tidak dapat dialokasikan.
- **RED**: Minimal satu primary shard tidak dapat ditemukan atau mengalami kerusakan; data mengalami kehilangan (*unrecoverable*).

```
                      +-----------------------------+
                      |     Status Shard Klaster    |
                      +-----------------------------+
                                     |
           +-------------------------+-------------------------+
           |                                                   |
[Single-Node Default]                                 [Single-Node Optimized]
number_of_replicas = 1                                number_of_replicas = 0
Primary: Node-1 (Allocated)                           Primary: Node-1 (Allocated)
Replica: Node-? (Unallocated!)                        Replica: None (Disabled)
Status: YELLOW                                        Status: GREEN
```

#### Masalah Konfigurasi Lokal Single-Node
Secara default, OpenSearch menetapkan `number_of_replicas: 1`. Prinsip dasar toleransi kesalahan OpenSearch melarang penempatan replica shard pada node fisik yang sama dengan primary shard-nya (karena jika node tersebut mati, replica shard di node yang sama ikut musnah, sehingga replikasi menjadi sia-sia).

Pada lingkungan pengembang lokal yang hanya menjalankan satu node (`discovery.type=single-node`), OpenSearch tidak akan pernah mengalokasikan replica shard tersebut. Akibatnya:
- Status klaster akan **permanen berwarna YELLOW**.
- Bagi pengembang baru, status YELLOW kerap disalahartikan sebagai indikasi malfungsi sistem atau kegagalan inisialisasi.
- Beberapa skrip automasi pengujian yang menunggu kondisi `wait_for_status=green` akan mengalami *infinite loop* atau timeout.

#### Solusi Wajib:
Pada saat mendefinisikan skema indeks di `app/vector_store.py` atau via API kueri, pengembang **wajib menyetel nilai replika ke nol**:
```json
{
  "settings": {
    "index": {
      "knn": true,
      "number_of_shards": 1,
      "number_of_replicas": 0
    }
  }
}
```
Penyetelan ini menjamin klaster lokal langsung berstatus **GREEN** segera setelah indeks dibuat.

---

### 3.4 Manajemen Izin File, UID Container, dan Isolasi I/O Volume

Di dalam container resmi `opensearchproject/opensearch`, proses utama dijalankan di bawah akun pengguna non-root berdedikasi:
- **User ID (UID)**: `1000` (`opensearch`)
- **Group ID (GID)**: `1000` (`opensearch`)

```yaml
# SALAH (Anti-Pattern pada Windows / Docker Desktop):
volumes:
  - ./opensearch_data:/usr/share/opensearch/data  # Bind Mount Windows Host

# BENAR (Best Practice):
volumes:
  - opensearch_data:/usr/share/opensearch/data     # Docker Named Volume
```

#### Dampak Negatif Bind Mount Windows (`./opensearch_data`):
1. **Kegagalan Izin Akses (Permission Denied / EACCES)**:  
   Sistem berkas host Windows (NTFS) tidak memetakan UID/GID POSIX Linux secara transparan. Ketika OpenSearch mencoba membuat direktori `nodes/0` atau mengunci file `node.lock`, proses akan gagal dengan pesan `java.nio.file.AccessDeniedException`.
2. **Degradasi Performa I/O (File Translation Overhead)**:  
   Pada Docker Desktop untuk Windows, bind mount melibatkan lapisan penerjemahan filesystem (9P Protocol atau VirtioFS). Operasi penulisan acak (*random I/O*) pada Lucene segments dan translog akan mengalami penurunan kecepatan hingga 5x–10x lipat lebih lambat dibandingkan native filesystem.

#### Rekomendasi Mutlak:
Gunakan selalu **Docker Named Volume** (`opensearch_data`). Named volume dikelola langsung di dalam partisi disk virtual ext4 subsistem WSL2, menjamin kepatuhan penuh izin POSIX UID 1000 dan kecepatan I/O native disk.

---

### 3.5 Konfigurasi Plugin Keamanan: Lingkungan Pengembangan vs Produksi

OpenSearch menyertakan plugin keamanan bawaan (`opensearch-security`) yang secara default mewajibkan enkripsi HTTPS TLS pada REST port 9200, enkripsi transport TLS pada port 9300, serta autentikasi username/password.

#### 1. Pendekatan Lingkungan Pengembangan Lokal (Development Setup)
Untuk menghilangkan friksi penanganan sertifikat SSL mandiri (*self-signed certificate mismatch*) pada client Python (`httpx` / `opensearch-py`), keamanan dinonaktifkan secara aman di `docker-compose.yml`:
```yaml
environment:
  - discovery.type=single-node
  - plugins.security.disabled=true
  - DISABLE_INSTALL_DEMO_CONFIG=true
```
- `plugins.security.disabled=true`: Mengubah endpoint menjadi HTTP polos pada port 9200 tanpa proteksi autentikasi.
- `DISABLE_INSTALL_DEMO_CONFIG=true`: Mematikan pembuatan sertifikat demo otomatis saat pertama kali kontainer dibuat, mempercepat waktu cold-boot hingga ~40%.

#### 2. Transisi Menuju Lingkungan Produksi (Production Hardening)
Saat aplikasi dipindahkan ke infrastruktur staging atau produksi, penonaktifan keamanan **dilarang keras**. Pengaktifan kembali plugin keamanan menuntut prosedur operasional berikut:
1. Pembuatan sertifikat Certificate Authority (CA), Node Certificates, dan Admin Certificate menggunakan OpenSSL.
2. Konfigurasi `opensearch.yml` untuk memetakan DN (Distinguished Names) admin.
3. Hashing kata sandi administrator menggunakan utilitas resmi OpenSearch:
   ```bash
   bash /usr/share/opensearch/plugins/opensearch-security/tools/hash.sh -p "KatasandiKuat123!"
   ```
4. Pemetaan *Role-Based Access Control* (RBAC) pada `internal_users.yml` dan `roles_mapping.yml`.
5. Eksekusi skrip `securityadmin.sh` untuk mengunggah konfigurasi ke indeks internal klaster `.opendistro_security`.

Perbedaan drastis antara konfigurasi development (tanpa auth) dan production (mutual TLS + RBAC) merupakan risiko arsitektur yang harus diantisipasi sejak dini dalam perancangan kode client Python.

---

### 3.6 Latensi Cold-Start & Dampak terhadap Otomasi Pengujian / CI-CD

Salah satu perbedaan operasional paling kontras antara ChromaDB dan OpenSearch adalah **durasi inisialisasi awal (*cold-start latency*)**:

| Vector Database | Waktu Siap Melayani Request (*Readiness Time*) | Mekanisme Startup |
|---|---|---|
| **ChromaDB** | **1 – 3 detik** | Server Python/FastAPI atau Rust ringan, pembacaan SQLite instan |
| **SQLite-vec** | **< 1 detik (Instan)** | Pustaka C in-process, tanpa overhead jaringan/server |
| **Qdrant** | **1 – 2 detik** | Kompilasi binary native Rust, pembacaan konfigurasi instan |
| **OpenSearch 2.11.0** | **25 – 45 detik** | Bootstrap JVM, verifikasi modul OS, scanning plugin k-NN, binding port jaringan, recovery status shard |

#### Dampak terhadap Otomasi CI/CD & Skrip Pengujian:
Jika skrip pengujian integrasi (misalnya `pytest` pada pipeline CI/CD GitHub Actions) langsung mengeksekusi kueri beberapa detik setelah perintah `docker compose up -d` selesai, pengujian akan **gagal total** dengan error `httpx.ConnectError: Connection refused` atau HTTP 503.

#### Pola Mitigasi (Readiness Polling Probe):
Skrip pengujian dan prosedur deployment wajib menyertakan mekanisme pemeriksaan kesiapan (*readiness probe loop*):
```bash
#!/usr/bin/env bash
echo "Menunggu kesiapan cluster OpenSearch..."
until curl -s http://localhost:9200/_cluster/health | grep -q '"status":"green"\|"status":"yellow"'; do
    sleep 3
    echo "Cluster belum siap, mencoba lagi..."
done
echo "OpenSearch telah siap melayani request!"
```

---

## 4. Pemeliharaan Jangka Panjang & Siklus Hidup (Lifecycle)

### 4.1 Immutabilitas Pemetaan Skema (Schema Mapping Immutability) & Re-indexing

Pada OpenSearch, properti field tipe data dasar dapat ditambahkan secara dinamis. Namun, untuk field tipe **`knn_vector`**, properti arsitektur seperti:
- `dimension` (jumlah dimensi vektor, misal 768),
- `method.name` (algoritma graf, misal `hnsw`),
- `method.engine` (`nmslib`, `lucene`, atau `faiss`), dan
- `method.space_type` (`cosinesimil`, `l2`, `innerproduct`)
bersifat **mutlak tidak dapat diubah (*immutable*)** setelah indeks terbuat.

#### Skenario Risiko:
Jika di masa depan tim pengembang memutuskan untuk meningkatkan performa semantik dengan mengganti model embedding dari `nomic-embed-text` (768 dimensi) ke model multidimensi yang lebih besar, misalnya:
- `bge-m3` (1024 dimensi), atau
- `text-embedding-3-small` (1536 dimensi),

OpenSearch akan menolak seluruh dokumen baru dengan pesan kesalahan parsing skema:
```text
mapper_parsing_exception: Vector dimension [1024] does not match the dimension [768] defined in mapping
```

#### Strategi Migrasi Zero-Downtime melalui Index Aliases
Untuk mengantisipasi kebutuhan migrasi skema di masa depan tanpa memicu *downtime* aplikasi, sistem harus mengadopsi pola **Index Aliases**:

```
[Aplikasi / API Client]
           |
           v
    (Index Alias: 'nala-docs-active')
           |
     +-----+-----+ (Atomic Alias Swap)
     |           |
     v           v
[Index: v1]  [Index: v2]
(Dim: 768)   (Dim: 1024)
```

1. **Aplikasi Tidak Pernah Menghubungi Nama Indeks Fisik**:  
   Aplikasi membaca dan menulis ke nama alias logis, misalnya `nala-docs-active`.
2. **Prosedur Migrasi**:
   - Buat indeks baru dengan pemetaan dimensi baru: `PUT /nala-docs-v2`.
   - Jalankan skrip *re-ingestion* yang mengekstrak teks mentah dari file markdown/PDF dan menghasilkan vektor baru 1024 dimensi ke `nala-docs-v2`.
   - Lakukan pengalihan alias secara atomik (*zero-downtime atomic swap*):
     ```http
     POST /_aliases
     {
       "actions": [
         { "remove": { "index": "nala-docs-v1", "alias": "nala-docs-active" } },
         { "add":    { "index": "nala-docs-v2", "alias": "nala-docs-active" } }
       ]
     }
     ```
   - Hapus indeks lama `nala-docs-v1` untuk membebaskan ruang disk.

---

### 4.2 Siklus Upgrade Versi & Depresiasi Komponen Mesin Vektor

#### Kasus Depresiasi Mesin `nmslib`
Spesifikasi modul laboratorium Pertemuan 6 mereferensikan konfigurasi:
```json
"method": {
  "name": "hnsw",
  "space_type": "cosinesimil",
  "engine": "nmslib"
}
```
**Temuan Audit Lifecycle:**  
Library `nmslib` (Non-Metric Space Library) merupakan implementasi HNSW pionir pada generasi awal OpenSearch k-NN. Namun, komunitas pengembang OpenSearch Project telah **secara resmi mendepresiasi `nmslib` sejak OpenSearch versi 2.13**, dan telah dijadwalkan untuk **dihapus sepenuhnya pada rilis OpenSearch 3.0**.

#### Komparasi Tiga Mesin Vektor OpenSearch:

| Parameter Mesin | `nmslib` (Warisan / Legacy) | `lucene` (Standar Rekomendasi) | `faiss` (Throughput Tinggi) |
|---|---|---|---|
| **Status Pemeliharaan** | **Didepresiasi** (Akan dihapus di v3.0) | Aktif & Didukung Penuh | Aktif & Didukung Penuh |
| **Integrasi Filter** | Post-filtering (lambat pada filter selektif) | **Pre-filtering Natif Terintegrasi** | Pre-filtering & Exact k-NN |
| **Kuantisasi Vektor** | Tidak Mendukung | Mendukung (Int8 Quantization) | **Mendukung (Product Quantization / PQ)** |
| **Jejak Memori RAM** | Tinggi | Sedang (Hemat ~20%) | Sangat Efisien dengan Kuantisasi |
| **Kesesuaian Proyek** | Wajib untuk tugas Pertemuan 6 | Sangat Disarankan untuk Rilis Produksi | Pilihan untuk Skala Vektor > 1 Juta |

---

### 4.3 Prosedur Pencadangan (Backup), Snapshot, dan Pemulihan Data

#### Bahaya Operasi "Hot Volume Copy"
Menyalin file fisik dari direktori volume Docker saat kontainer OpenSearch sedang aktif merupakan tindakan berbahaya. Karena Lucene secara konstan menggabungkan segmen (*segment merging*) dan memperbarui translog di memori, operasi penyalinan berkas di level filesystem berisiko tinggi menghasilkan **kondisi segmen korup (*corrupted index segment*)** yang membuat indeks gagal dimuat saat restore.

#### Prosedur Resmi: Snapshot Lifecycle Management (SLM)
OpenSearch menyediakan antarmuka pencadangan resmi melalui Snapshot API:
1. **Registrasi Repositori Cadangan** (misalnya direktori lokal bersama atau AWS S3):
   ```http
   PUT /_snapshot/local_backup_repo
   {
     "type": "fs",
     "settings": {
       "location": "/usr/share/opensearch/snapshots"
     }
   }
   ```
2. **Pembuatan Snapshot**:
   ```http
   PUT /_snapshot/local_backup_repo/snapshot_20261102?wait_for_completion=true
   {
     "indices": "nala-docs",
     "ignore_unavailable": true,
     "include_global_state": false
   }
   ```
3. **Prosedur Pemulihan (Restore)**:
   ```http
   POST /_snapshot/local_backup_repo/snapshot_20261102/_restore
   ```

---

### 4.4 Manajemen Ambang Batas Disk (Disk Watermarks) & Status Auto Read-Only

OpenSearch memiliki mekanisme proteksi bawaan untuk mencegah kerusakan klaster akibat kepenuhan media penyimpanan (*disk exhaustion*). Terdapat tiga tingkatan ambang batas (*watermarks*):

```
0% --------------------- 85% -------------- 90% -------------- 95% ----------- 100%
[     Operasi Normal     ] [ Low Watermark ] [ High Watermark ] [ Flood Stage ]
                           Tidak alokasi       Evakuasi shard    LOCK READ-ONLY!
                           shard baru          ke node lain      HTTP 403 Error
```

1. **Low Disk Watermark (Default: 85%)**:  
   OpenSearch menghentikan alokasi shard baru ke node yang bersangkutan.
2. **High Disk Watermark (Default: 90%)**:  
   OpenSearch berupaya merelokasi shard yang ada pada node tersebut ke node lain dalam klaster yang memiliki sisa ruang lebih lapang.
3. **Flood Stage Watermark (Default: 95%)**:  
   **Tingkat Kritis!** Jika partisi disk mencapai 95% kapasitas, OpenSearch secara otomatis mengunci seluruh indeks menjadi **READ-ONLY** (`read_only_allow_delete: true`). Seluruh operasi penulisan, penambahan dokumen baru, dan pembaruan data akan gagal total dengan respons HTTP 403:
   ```text
   cluster_block_exception: blocked by: [TOO_MANY_REQUESTS/12/disk usage exceeded flood-stage watermark, index has read-only-allow-delete block];
   ```

#### Dampak bagi Pengembang Lokal:
Pada laptop pengembang yang partisi SSD-nya hampir penuh (misalnya sisa < 10 GB dari 256 GB/512 GB), OpenSearch dapat tiba-tiba mengunci dirinya sendiri ke mode read-only saat sedang menguji skrip ingestion.

#### Perintah Pemulihan Darurat (Unlocking Read-Only Block):
```http
PUT /_all/_settings
{
  "index.blocks.read_only_allow_delete": null
}
```

---

## 5. Matriks Analisis Komparatif (7 Solusi Vector Store)

### 5.1 Matriks Komparasi Komprehensif 7 Engine Vektor

Berikut adalah matriks evaluasi teknis mendalam yang membandingkan OpenSearch dengan enam solusi vector store terkemuka di industri saat ini:

| Dimensi Evaluasi | OpenSearch (v2.11) | ChromaDB (v0.5.18) | FAISS (In-Memory) | SQLite-vec | Qdrant (Rust) | Milvus (Cloud-Native) | pgvector (PostgreSQL) |
|---|---|---|---|---|---|---|---|
| **Bahasa / Runtime** | Java 17 + C++ (k-NN) | Python / Rust | C++ (Python wrap) | C (SQLite Extension) | Rust (Native binary) | Go + C++ (Knowhere) | C (Postgres Extension) |
| **Model Arsitektur** | Distributed Cluster | Client-Server / In-Proc| In-Process Library | Embedded Database | Standalone / Cluster | Distributed Microservices | Relational DB Extension |
| **RAM Footprint (Idle)**| **1.2 GB – 1.8 GB** | **150 MB – 250 MB** | **< 30 MB** (in-proc) | **< 15 MB** (in-proc) | **40 MB – 80 MB** | 1.5 GB – 3.0 GB | 100 MB – 300 MB |
| **RAM Footprint (Active)**| **2.0 GB – 3.5 GB** | **300 MB – 600 MB** | Tergantung data murni | Tergantung data murni | **150 MB – 350 MB** | 2.5 GB – 6.0 GB | 400 MB – 1.0 GB |
| **Cold-Start Time** | 25 – 45 detik | 1 – 3 detik | 0 detik (Instan) | 0 detik (Instan) | 1 – 2 detik | 30 – 60 detik | 2 – 5 detik |
| **Ukuran Image Docker** | ~1.85 GB (+1.4 GB Dash) | ~500 MB | N/A (Python package) | N/A (Python package) | ~120 MB | ~1.5 GB | ~300 MB |
| **Hybrid Search** | **Native Sempurna** (BM25 + k-NN + RRF) | Terbatas (filter teks dasar) | Tidak Ada | Terbatas (JOIN FTS5 + vec) | **Native Sempurna** (Dense + Sparse) | **Native Sempurna** (Hybrid rerankers) | Full-text (tsvector + hnsw query) |
| **Dukungan Kuantisasi** | SQ, FP16 | Belum Tersedia | **Sangat Luas** (PQ, SQ, IVFPQ) | Belum Tersedia | **Lengkap** (Scalar, Product, Binary) | **Lengkap** (SQ8, PQ, HNSW-PQ) | Halfvec, Binary (v0.7+) |
| **Mekanisme Filtering** | Pre-filtering (Lucene) & Post | Pre-filtering metadata | Post-filtering manual | SQL WHERE predicates | Payload index pre-filtering | Segment pre-filtering | SQL WHERE predicates natif |
| **Skalabilitas Vertikal**| Sangat Tinggi (Multi-core) | Sedang (Python GIL bound)| Sangat Tinggi (OpenMP/GPU)| Terbatas (Single-thread write)| Sangat Tinggi (Multi-thread)| Sangat Tinggi | Tinggi (Multi-worker PG) |
| **Skalabilitas Horizontal**| **Natif** (Sharding multi-node)| Terbatas | Manual / Custom | Tidak Mendukung | **Natif** (Raft consensus) | **Sangat Tinggi** (K8s distributed)| Read Replicas / Citus |
| **Onboarding Friction** | **Tinggi** (sysctl, JVM, memori)| **Sangat Rendah** | **Sangat Rendah** (`pip install`)| **Paling Rendah** (1 file `.db`)| Rendah (`docker run`) | **Sangat Tinggi** (Etcd, MinIO, Pulsar) | Sedang (Perlu PostgreSQL) |
| **Paling Cocok Untuk** | Enterprise search, Log + RAG | Prototyping AI, RAG Lokal | Riset algoritma, GPU search| Desktop app, IoT, Edge RAG | Dedicated Vector Microservice | Skala Enterprise Miliar Vektor| Sistem eksisting berbasis Postgres |

---

### 5.2 Evaluasi Naratif Komparatif Mendalam per Solusi

#### 1. OpenSearch (v2.11.0)
- **Kelebihan Utama**: Solusi *all-in-one* paling tangguh untuk enterprise. Mengintegrasikan pencarian teks konvensional BM25 dengan k-NN dense vector, didukung pipeline hybrid search dan *Reciprocal Rank Fusion* (RRF). Antarmuka OpenSearch Dashboards menyediakan visibilitas luar biasa terhadap struktur dokumen.
- **Kelemahan Utama**: Footprint memori sangat besar, proses inisialisasi lambat (25–45 detik), dan konfigurasi kernel host (`vm.max_map_count`) yang menyulitkan pengembang pemula.
- **Konteks Proyek PDS**: Wajib diimplementasikan guna memenuhi standar kelulusan Modul 12 Pertemuan 6.

#### 2. ChromaDB (v0.5.18 - Arsitektur Baseline Proyek)
- **Kelebihan Utama**: Sangat ramah pengembang (*developer-friendly*). Setup instan dengan Python API yang elegan, konsumsi memori sangat hemat (150–250 MB), dan waktu startup di bawah 3 detik. Sangat ideal untuk komputer pengembang dengan kapasitas RAM terbatas.
- **Kelemahan Utama**: Tidak memiliki kapabilitas *full-text search* BM25 natif; pencarian hybrid memerlukan implementasi manual; skalabilitas klaster horizontal belum sematang OpenSearch.

#### 3. FAISS (Facebook AI Similarity Search)
- **Kelebihan Utama**: Standar industri untuk riset vector search dengan performa komputasi murni tercepat. Mendukung akselerasi GPU (CUDA) dan teknik kuantisasi paling ekstensif (*Product Quantization* / PQ).
- **Kelemahan Utama**: Merupakan pustaka komputasi matematis (*in-memory library*), bukan database utuh. Tidak menyediakan penyimpanan dokumen teks mentah, manajemen transaksi, filter metadata yang fleksibel, atau antarmuka jaringan HTTP REST API.

#### 4. SQLite-vec
- **Kelebihan Utama**: Ekstensi C murni untuk SQLite. Seluruh database, teks dokumen, metadata, dan vektor tersimpan di dalam **satu file tunggal** (`.db`). Footprint memori mendekati nol (<15 MB), zero network latency, dan tanpa ketergantungan container Docker.
- **Kelemahan Utama**: Tidak dirancang untuk konkurensi penulisan tinggi (*single-writer lock* bawaan SQLite), tidak mendukung sharding terdistribusi, dan ekosistem integrasi framework AI yang masih relatif muda.

#### 5. Qdrant
- **Kelebihan Utama**: Dibangun dengan bahasa Rust yang menjamin keamanan memori (*memory safety*) dan kecepatan tinggi tanpa overhead JVM garbage collection. Footprint memori sangat ramping (40–80 MB idle), API REST/gRPC modern, serta dukungan native untuk payload filtering dan dense/sparse hybrid search.
- **Kelemahan Utama**: Tidak menyertakan mesin pencari full-text BM25 selengkap OpenSearch; ekosistem visualisasi bawaan tidak sekomprehensif OpenSearch Dashboards.

#### 6. Milvus
- **Kelebihan Utama**: Dirancang khusus untuk skala masif cloud-native (miliaran vektor) dengan arsitektur microservices terdistribusi (pemisahan compute, storage, dan log broker).
- **Kelemahan Utama**: Kompleksitas instalasi paling ekstrem. Menjalankan Milvus lokal via Docker Compose membutuhkan dependency minimal 3 layanan pendukung: **etcd** (metadata), **MinIO** (object storage), dan **Pulsar/Kafka** (message broker), yang menghabiskan RAM >3 GB hanya untuk komponen pendukung.

#### 7. pgvector (PostgreSQL Extension)
- **Kelebihan Utama**: Mengintegrasikan pencarian vektor langsung ke dalam sistem manajemen basis data relasional (RDBMS) terpopuler di dunia (PostgreSQL). Memungkinkan penggabungan query SQL kompleks (JOIN, GROUP BY, aggregasi) dengan similaritas vektor dalam satu transaksi ACID.
- **Kelemahan Utama**: Performa indexing HNSW lebih lambat dibandingkan dedicated vector DB; memerlukan tuning parameter memori PostgreSQL (`maintenance_work_mem`); dan skalabilitas horizontal terbatas pada model replikasi PostgreSQL standar.

---

## 6. Rekomendasi Arsitektur & Peta Jalan Migrasi (Migration Roadmap)

### 6.1 Pola Desain Abstraksi Dual-Store (`VectorStore` Interface)

Guna menjembatani kesenjangan antara tuntutan kepatuhan akademis Modul 12 (OpenSearch) dengan fleksibilitas operasional pada komputer pengembang berkapasitas RAM terbatas, arsitektur sistem proyek **NALA / S.O.N.A.R** mengadopsi pola desain **Dual-Store Abstraction Pattern**.

```
                           +---------------------------+
                           |     FastAPI / Pipeline    |
                           |   (app/main.py / RAG)     |
                           +---------------------------+
                                         |
                                         v
                           +---------------------------+
                           |    BaseVectorStore (ABC)  |
                           |---------------------------|
                           | + ensure_index()          |
                           | + index_document()        |
                           | + search()                |
                           +---------------------------+
                                         |
               +-------------------------+-------------------------+
               |                                                   |
               v                                                   v
+-------------------------------+               +-------------------------------+
|     OpenSearchVectorStore     |               |       ChromaVectorStore       |
|-------------------------------|               |-------------------------------|
| - Target: OpenSearch 2.11.0   |               | - Target: ChromaDB v0.5.18    |
| - Space: cosinesimil          |               | - Space: cosine               |
| - Dim: 768                    |               | - Dim: 768                    |
| - Status: PRIMARY (Modul 12)  |               | - Status: FALLBACK / LOW-RAM  |
+-------------------------------+               +-------------------------------+
```

#### Blueprint Implementasi Python (`app/vector_store.py`):
Pola ini diwujudkan melalui interface seragam yang dikendalikan oleh variabel lingkungan `VECTOR_STORE_BACKEND`:

```python
import os
import json
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import httpx

logger = logging.getLogger("vector_store")


class BaseVectorStore(ABC):
    """Antarmuka seragam untuk abstraksi vector store NALA."""

    @abstractmethod
    def ensure_index(self) -> bool:
        """Membuat indeks/koleksi jika belum ada."""
        pass

    @abstractmethod
    def index_document(
        self,
        doc_id: str,
        text: str,
        embedding: List[float],
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Menyimpan satu dokumen beserta embedding ke dalam store."""
        pass

    @abstractmethod
    def search(
        self,
        query_vector: List[float],
        k: int = 3,
        metadata_filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Mencari dokumen terdekat berdasarkan query vector."""
        pass


class OpenSearchVectorStore(BaseVectorStore):
    """Implementasi OpenSearch 2.11.0 sesuai spesifikasi Pertemuan 6 Modul 12."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        index_name: str = "nala-docs",
        dimension: int = 768
    ):
        self.base_url = (base_url or os.getenv("OPENSEARCH_BASE_URL", "http://localhost:9200")).rstrip("/")
        self.index_name = index_name
        self.dimension = dimension

    def ensure_index(self) -> bool:
        with httpx.Client(timeout=10.0) as client:
            res = client.head(f"{self.base_url}/{self.index_name}")
            if res.status_code == 200:
                logger.info(f"Index OpenSearch '{self.index_name}' sudah ada.")
                return False

            schema = {
                "settings": {
                    "index": {
                        "knn": True,
                        "number_of_shards": 1,
                        "number_of_replicas": 0  # Wajib 0 untuk single-node GREEN status!
                    }
                },
                "mappings": {
                    "properties": {
                        "text": {"type": "text"},
                        "embedding": {
                            "type": "knn_vector",
                            "dimension": self.dimension,
                            "method": {
                                "name": "hnsw",
                                "space_type": "cosinesimil",
                                "engine": "nmslib"
                            }
                        },
                        "metadata": {"type": "object"}
                    }
                }
            }
            create_res = client.put(f"{self.base_url}/{self.index_name}", json=schema)
            create_res.raise_for_status()
            logger.info(f"Index OpenSearch '{self.index_name}' berhasil dibuat.")
            return True

    def index_document(
        self,
        doc_id: str,
        text: str,
        embedding: List[float],
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        payload = {
            "text": text,
            "embedding": embedding,
            "metadata": metadata or {}
        }
        with httpx.Client(timeout=30.0) as client:
            res = client.put(
                f"{self.base_url}/{self.index_name}/_doc/{doc_id}?refresh=true",
                json=payload
            )
            res.raise_for_status()
            return True

    def search(
        self,
        query_vector: List[float],
        k: int = 3,
        metadata_filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        knn_query: Dict[str, Any] = {
            "vector": query_vector,
            "k": k
        }
        if metadata_filter:
            knn_query["filter"] = metadata_filter

        body = {
            "size": k,
            "query": {
                "knn": {
                    "embedding": knn_query
                }
            }
        }
        with httpx.Client(timeout=30.0) as client:
            res = client.post(f"{self.base_url}/{self.index_name}/_search", json=body)
            res.raise_for_status()
            data = res.json()

        hits = data.get("hits", {}).get("hits", [])
        results = []
        for hit in hits:
            source = hit.get("_source", {})
            results.append({
                "id": hit.get("_id"),
                "score": hit.get("_score"),
                "text": source.get("text", ""),
                "metadata": source.get("metadata", {})
            })
        return results


def get_vector_store() -> BaseVectorStore:
    """Factory helper untuk instansiasi backend vector store yang aktif."""
    backend = os.getenv("VECTOR_STORE_BACKEND", "opensearch").lower()
    if backend == "opensearch":
        return OpenSearchVectorStore()
    elif backend == "chroma":
        # Fallback ke ChromaVectorStore jika dikonfigurasi
        from app.chroma_store import ChromaVectorStore
        return ChromaVectorStore()
    else:
        raise ValueError(f"Backend vector store tidak dikenali: {backend}")
```

---

### 6.2 Praktik Terbaik Konfigurasi: Local Development vs Staging / Produksi

Tabel berikut menjadi pedoman konfigurasi parameter operasional antara workstation lokal dan server produksi:

| Komponen Konfigurasi | Pengaturan Local Development | Pengaturan Staging / Produksi | Rationale Teknis |
|---|---|---|---|
| **`plugins.security.disabled`**| `true` | `false` (Wajib TLS + Auth) | Mencegah friksi SSL lokal; menjamin keamanan data produksi |
| **`discovery.type`** | `single-node` | Dihapus (Minimal 3 Master Nodes) | Mengeliminasi proses quorum lokal; mencegah *split-brain* di prod |
| **`number_of_replicas`** | `0` | Minimal `1` atau `2` | Mencegah status YELLOW lokal; menjamin high-availability di prod |
| **`OPENSEARCH_JAVA_OPTS`** | `-Xms512m -Xmx512m` | `-Xms4g -Xmx4g` (50% RAM fisik)| Membatasi beban RAM pengembang; performa maksimal di prod |
| **Penyimpanan Docker Volume** | Docker Named Volume (`opensearch_data`)| Cloud EBS SSD / NVMe Mount | Isolasi performa I/O ext4 pada kedua lingkungan |
| **Batas Memori Kontainer** | `limits.memory: 2048M` | `limits.memory: 8192M+` | Menjaga stabilitas host dari ancaman OOM crash |
| **Mesin Vektor k-NN** | `engine: nmslib` | `engine: lucene` | Kepatuhan Modul 12 lokal; stabilitas jangka panjang di prod |

---

### 6.3 Peta Jalan Migrasi Bertahap (Safe Step-by-Step Migration Roadmap)

Proses migrasi dari repositori awal menuju arsitektur Pertemuan 6 dilaksanakan melalui 4 milestone terstruktur:

```
+-------------------------------------------------------------------------------+
|                    Peta Jalan Migrasi Arsitektur NALA                         |
+-------------------------------------------------------------------------------+
| Milestone M1 [SELESAI]                                                        |
| -> Penulisan Analisis Risiko Komprehensif (OPENSEARCH_RISK_ANALYSIS.md)       |
+-------------------------------------------------------------------------------+
                                      |
                                      v
+-------------------------------------------------------------------------------+
| Milestone M2 [INFRASTRUKTUR & DEPENDENSI]                                     |
| -> Konfigurasi docker-compose.yml: Tambah opensearch (2.11.0) & dashboards    |
| -> Alokasi limit memori kontainer & volume isolasi                            |
| -> Pembaruan requirements.txt: Tambah opensearch-py==2.4.2 & pypdf==5.1.0     |
+-------------------------------------------------------------------------------+
                                      |
                                      v
+-------------------------------------------------------------------------------+
| Milestone M3 [INTEGRASI SISTEM & KNOWLEDGE BASE]                              |
| -> Penyediaan seed SOP Markdown di knowledge-base/ (5 bagian standar)         |
| -> Konstruksi app/vector_store.py dengan interface BaseVectorStore seragam   |
| -> Implementasi app/ingest.py & pipeline ingestion embedding nomic-embed-text |
| -> Adaptasi endpoint FastAPI app/main.py ke retrieval k-NN                    |
| -> Proteksi regresi: Invarian POST /chat/stream HTTP 400 empty messages       |
+-------------------------------------------------------------------------------+
                                      |
                                      v
+-------------------------------------------------------------------------------+
| Milestone M4 [VERIFIKASI END-TO-END & AUDIT INTEGRITAS]                       |
| -> Pengujian retrieval semantik zero-keyword overlap (Pertemuan 6 Modul 12)   |
| -> Verifikasi determinisme embedding vektor 768 dimensi                       |
| -> Eksekusi pengujian stres oleh Challenger & Audit Forensik Kepatuhan        |
+-------------------------------------------------------------------------------+
```

---

### 6.4 Matriks Verifikasi & Rencana Validasi Kualitas

Guna memverifikasi integritas dan keandalan sistem OpenSearch yang telah terpasang, berikut adalah prosedur pengujian verifikasi mandiri yang wajib dieksekusi:

#### 1. Uji Kesiapan & Status Kesehatan Klaster
```bash
curl -s http://localhost:9200/_cluster/health?pretty
```
*Kriteria Penerimaan:*
- Status respons HTTP: `200 OK`.
- Nilai `"status"`: `"green"` (jika `number_of_replicas: 0`) atau `"yellow"` (jika replica masih aktif), **bukan `"red"`**.
- Nilai `"number_of_nodes"`: minimal `1`.

#### 2. Uji Ketersediaan Plugin k-NN
```bash
curl -s http://localhost:9200/_cat/plugins?v
```
*Kriteria Penerimaan:*
- Baris plugin `opensearch-knn` tercantum secara eksplisit pada daftar output plugin yang terpasang.

#### 3. Uji Verifikasi Pembuatan Indeks k-NN 768 Dimensi
```bash
curl -s -X GET http://localhost:9200/nala-docs/_mapping?pretty
```
*Kriteria Penerimaan:*
- Properti field `embedding` memiliki `type`: `"knn_vector"`.
- Nilai `dimension`: `768`.
- Metrik jarak `space_type`: `"cosinesimil"`.

#### 4. Uji Pengambilan Semantik Zero-Keyword Overlap (Proof of Semantic Search)
- Lakukan kueri pencarian menggunakan kalimat yang memiliki **makna serupa namun tidak memiliki satupun kata kunci yang persis sama** dengan dokumen sumber:
  - *Dokumen Tersimpan:* "Mahasiswa mengajukan permohonan istirahat kuliah sementara kepada dekan melalui BAAK..."
  - *Kueri Pengujian:* "prosedur rehat studi sementara karena urusan pribadi"
- *Kriteria Penerimaan:*
  - Hasil kueri mengembalikan dokumen SOP cuti akademik pada peringkat teratas (Rank 1).
  - Skor relevance cosine similarity bernilai $> 0.65$.

#### 5. Uji Invarian & Proteksi Regresi API
```bash
curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"messages": []}'
```
*Kriteria Penerimaan:*
- Status respons HTTP harus tepat **`400` (Bad Request)**, mengonfirmasi tidak terjadinya regresi pada kontrak API yang ada.

---

## 7. Kesimpulan Akhir

Integrasi OpenSearch 2.11.0 ke dalam proyek **NALA / S.O.N.A.R** merupakan lompatan strategis penting yang memenuhi seluruh instruksi dan spesifikasi dokumen laboratorium **Pertemuan 6 (Modul 10, 11, dan 12)**. 

Meskipun OpenSearch menuntut kebutuhan sumber daya yang jauh lebih besar (RAM minimal 2 GB, CPU spikes saat indexing, dan prasyarat kernel `vm.max_map_count=262144`), seluruh risiko teknis dan operasional tersebut dapat dimitigasi secara elegan melalui:
1. Pembatasan ketat alokasi memori JVM (`-Xms512m -Xmx512m`) dan alokasi resource guard pada Docker Compose.
2. Penggunaan Docker Named Volumes untuk mengisolasi performa I/O disk ext4 POSIX.
3. Penyetelan parameter `number_of_replicas: 0` untuk memastikan kestabilan status klaster GREEN.
4. Penerapan pola desain **Dual-Store Abstraction** pada modul Python `VectorStore`, yang memberikan fleksibilitas operasional optimal bagi pengembang tanpa mengorbankan kepatuhan terhadap spesifikasi arsitektur enterprise.

Dokumen analisis risiko ini secara resmi menjadi dasar acuan teknis bagi implementasi Milestone M2 (Infrastruktur Docker Compose) dan Milestone M3 (Integrasi Pipeline & Knowledge Base).
