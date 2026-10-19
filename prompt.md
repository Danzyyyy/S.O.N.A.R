# Task: Setup End-to-End RAG Social Media Sentiment Root-Cause Analysis Project

Kamu adalah Senior Data Science & AI Engineer. Buatkan struktur proyek lengkap dan jalankan inisialisasi untuk sistem **Retrieval-Augmented Generation (RAG) untuk Root-Cause Analysis Perubahan Sentimen Publik pada Data Media Sosial** menggunakan Docker, ChromaDB, LangChain, Streamlit, dan Ollama (yang sudah berjalan di host OS).

## 1. Struktur Direktori yang Harus Dibuat
Buat file dan folder berikut di workspace saat ini:
- `Dockerfile`
- `docker-compose.yml`
- `.dockerignore`
- `requirements.txt`
- `data/social_media_comments.csv` (buatkan dummy dataset realistis)
- `ingest.py` (script untuk proses indexing CSV ke ChromaDB)
- `app.py` (aplikasi Streamlit utama untuk UI RAG & Root-Cause Analysis)

## 2. Spesifikasi Teknis Setiap File

### A. `requirements.txt`
Masukkan library berikut:
- `langchain==0.3.7`
- `langchain-community==0.3.7`
- `langchain-core==0.3.15`
- `langchain-ollama==0.2.0`
- `langchain-chroma==0.1.4`
- `chromadb==0.5.18`
- `pandas==2.2.3`
- `streamlit==1.40.0`

### B. `Dockerfile`
- Base image: `python:3.11-slim`
- Working directory: `/app`
- Set env `PYTHONDONTWRITEBYTECODE=1` dan `PYTHONUNBUFFERED=1`
- Install `build-essential` dan `curl` via `apt-get`
- Copy dan install `requirements.txt`
- Copy seluruh kode ke `/app`
- Expose port `8501`
- Default command: `["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]`

### C. `docker-compose.yml`
Buat 2 services:
1. `chromadb`:
   - Image: `chromadb/chroma:0.5.18`
   - Container name: `chroma_vector_store`
   - Ports: `"8000:8000"`
   - Volumes: `./chroma_data:/chroma/chroma`
   - Environment: `IS_PERSISTENT=TRUE`, `ANONYMIZED_TELEMETRY=FALSE`
2. `rag-app`:
   - Build context: `.`
   - Container name: `rag_sentiment_app`
   - Ports: `"8501:8501"`
   - Volumes: `.:/app`
   - Environment:
     - `CHROMA_HOST=chromadb`
     - `CHROMA_PORT=8000`
     - `OLLAMA_BASE_URL=http://host.docker.internal:11434`
     - `LLM_MODEL=llama3.2`
     - `EMBED_MODEL=nomic-embed-text`
   - `extra_hosts`: `["host.docker.internal:host-gateway"]`
   - `depends_on`: `chromadb`

### D. `data/social_media_comments.csv`
Generate 30 baris data komentar media sosial berbahasa Indonesia yang realistis (misal: keluhan aplikasi digital / e-commerce / layanan streaming) dengan kolom:
- `id`: ID unik
- `timestamp`: Tanggal (`YYYY-MM-DD`, variasi antara `2026-10-15` s/d `2026-10-19`)
- `platform`: (`X`, `Instagram`, `TikTok`, `YouTube`)
- `username`: Handle user
- `comment`: Isi komentar netizen (berisi keluhan spesifik seperti gagal transaksi QRIS, server lag setelah update versi 2.4, customer service lambat, atau pujian fitur baru)
- `sentiment`: (`negative`, `neutral`, `positive`)
- `topic`: (`payment_issue`, `app_bug`, `customer_service`, `feature_praise`)
- `likes`: Jumlah likes (integer)

### E. `ingest.py`
Buat script Python modular yang bisa dijalankan baik dari CLI (`python ingest.py`) maupun di-import ke dalam `app.py`:
- Membaca `data/social_media_comments.csv` menggunakan `pandas`.
- Mengubah setiap baris menjadi objek `langchain_core.documents.Document` di mana `page_content` berisi teks komentar, dan `metadata` menyimpan `timestamp`, `platform`, `sentiment`, `topic`, serta `likes`.
- Menghubungkan ke ChromaDB via `chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)`.
- Menggunakan `OllamaEmbeddings(base_url=OLLAMA_BASE_URL, model=EMBED_MODEL)`.
- Menyimpan dokumen ke collection `"social_media_sentiments"`.

### F. `app.py`
Buat dashboard Streamlit interaktif dengan fitur:
- **Sidebar Konfigurasi & Filter Metadata:**
  - Tombol `"🔄 Ingest / Reset Dataset ke ChromaDB"` yang memanggil fungsi dari `ingest.py` dan menampilkan notifikasi sukses.
  - Filter dropdown untuk `Sentiment` (`All`, `negative`, `neutral`, `positive`) dan `Platform` (`All`, `X`, `Instagram`, `TikTok`, `YouTube`).
  - Slider jumlah dokumen `Top-K Retrieval` (default: 5).
- **Tab 1: Exploratory Sentiment Overview:**
  - Tampilkan ringkasan metrik jumlah komentar per sentimen & platform dari CSV.
- **Tab 2: RAG Root-Cause Analysis Agent:**
  - Input pertanyaan user (contoh default: *"Apa penyebab utama lonjakan sentimen negatif terkait pembayaran dan update aplikasi?"*).
  - Terapkan **Metadata Filtering** pada Chroma retriever jika user memilih filter sentimen/platform tertentu di sidebar.
  - Gunakan `ChatPromptTemplate` yang menginstruksikan LLM (`ChatOllama`) berperan sebagai Senior Social Media Data Scientist untuk menyusun:
    1. **Ringkasan Eksekutif Akar Masalah (Root Cause)**
    2. **Bukti Kutipan Komentar Netizen (beserta platform & tanggal)**
    3. **Rekomendasi Mitigasi Konkret**
  - Tampilkan juga expander `"📄 Lihat Konteks Dokumen yang Di-retrieve (Vector Search)"` lengkap dengan metadata-nya.

## 3. Langkah Eksekusi Terminal
Setelah semua file selesai dibuat:
1. Periksa apakah model Ollama `llama3.2` dan `nomic-embed-text` sudah tersedia di host dengan menjalankan `ollama list`. Jika belum ada, jalankan `ollama pull nomic-embed-text` dan `ollama pull llama3.2`.
2. Pastikan service Ollama di host mengizinkan koneksi dari container Docker (`OLLAMA_HOST=0.0.0.0` jika diperlukan).
3. Jalankan `docker compose up --build -d` dan pastikan kedua container berstatus `Running`.