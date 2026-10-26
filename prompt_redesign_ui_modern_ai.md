# SYSTEM & IMPLEMENTATION PROMPT: MODERN AI CHATBOT UI (GEMINI / CHATGPT STYLE)

Prompt ini dirancang untuk diumpankan ke AI code generator atau frontend engineer guna mendesain ulang antarmuka web `main.py` S.O.N.A.R agar memiliki estetika, responsivitas, dan micro-interaction setara **ChatGPT, Google Gemini, dan Claude**.

---

## PROMPT INSTRUKSI (COPY-PASTE READY)

```text
Bertindaklah sebagai Senior Frontend Engineer dan UI/UX Designer spesialis conversational AI interface (setara ChatGPT, Claude 3.5 Sonnet, dan Google Gemini). 

Tugas Anda adalah merombak tampilan UI HTML/CSS/JS pada aplikasi S.O.N.A.R (FastAPI backend + Ollama) menjadi antarmuka modern, clean, minimalis, dan sangat interaktif.

### 1. Desain & Estetika Visual (Design System)
- Filosofi Desain: Minimalis, clean canvas dengan fokus utama pada percakapan (seperti layout ChatGPT/Gemini).
- Palette Warna:
  - Mendukung Dark Mode (default modern dark: background `#131314` atau `#212121`, kartu/sidebar `#1e1f20` atau `#171717`, border tipis transparan `rgba(255,255,255,0.1)`).
  - Aksen halus: Gradient Gemini glow (`#4285f4` ke `#9b72cb`) atau slate clean tone.
- Tipografi: Gunakan Google Fonts 'Inter' atau 'Plus Jakarta Sans', rendering teks tajam dengan line-height 1.6 untuk keterbacaan tinggi.
- Markdown & Code Rendering:
  - Jawaban bot harus dirender menggunakan parser Markdown (misal: markdown-it atau marked.js via CDN) lengkap dengan syntax highlighting (highlight.js atau Prism.js).
  - Terdapat tombol "Copy Code" di pojok kanan atas setiap code block.

### 2. Layout & Arsitektur Komponen
- Collapsible Sidebar (Kiri):
  - Tombol toggle collapse/expand sidebar (ikon hamburger / panel toggle).
  - Tombol "+ Obrolan Baru" (+ New Chat) model pill button di bagian atas.
  - Daftar riwayat sesi chat dengan opsi rename dan delete (disimpan ke localStorage).
  - Status koneksi backend Ollama & model selector pill di footer sidebar.
- Main Chat Canvas (Tengah):
  - Header minimalis: Hanya menampilkan nama model aktif (misal: "S.O.N.A.R Llama 3.2:3b") dan tombol toggle sidebar / full-width mode.
  - Zero-State (Tampilan Awal saat Chat Kosong):
    - Logo S.O.N.A.R dengan efek gradient subtil.
    - Sambutan personal: "Mau analisis isu media sosial apa hari ini?"
    - Grid 4 Kartu Prompt Cepat (Prompt Suggestion Cards) dengan hover glow effect (Transkrip QRIS, Respon Netizen Update v2.4, Analisis Komplain CS, Mitigasi Krisis Komunikasi).
  - Chat Feed:
    - Bubble pesan model responsif, rata kiri-kanan alami tanpa border kotak kaku.
    - Tombol aksi di bawah setiap respon asisten: "Salin Jawaban", "Regenerate", dan feedback jempol (👍/👎).

### 3. Smart Floating Input Bar (Gemini / ChatGPT Style)
- Input diletakkan mengambang (floating) di bagian bawah dengan `max-width: 768px` dan auto-centering.
- Multi-line Auto-expanding Textarea (menyesuaikan tinggi otomatis hingga maksimal 200px sebelum muncul scrollbar).
- Action Icons di dalam bar input:
  - Ikon lampiran dokumen / dataset CSV komplain.
  - Tombol Kirim berupa lingkaran rounded dengan animasi transisi ikon (panah atas ↑ saat siap kirim, ikon kotak ■ saat streaming untuk stop generating).
- Disclaimer teks kecil di bawah input: *"S.O.N.A.R dapat membuat kesalahan. Verifikasi data kritis media sosial Anda."*

### 4. Fitur Interaktif & Streaming Experience
- Real-time SSE Streaming: Karakter teks muncul secara halus (smooth typing animation atau progressive text chunk).
- Tombol "Stop Generating" yang memutus stream HTTP fetch jika pengguna ingin membatalkan jawaban.
- Indikator "Thinking / Retrieving Knowledge": Tampilkan animasi pulsing shimmer badge saat router agent dan vector store sedang mencari data sebelum token pertama muncul.
- Keyboard Shortcut:
  - `Enter` untuk mengirim, `Shift + Enter` untuk baris baru.
  - `Ctrl + K` / `Cmd + K` untuk fokus ke input bar.

### 5. Batasan Teknis
- Seluruh kode HTML, CSS, dan JavaScript vanilla harus digabungkan dalam satu file template string Python (pada function `serve_chatbot_ui` di `main.py`).
- Tidak memerlukan bundler (Webpack/Vite), gunakan CDN untuk library eksternal (Marked.js, Highlight.js, FontAwesome/Lucide Icons).
```

---

## CHECKLIST PERBANDINGAN FITUR DENGAN GEMINI / CHATGPT

| Fitur UX | ChatGPT / Gemini | UI Lama S.O.N.A.R | UI Baru (Target Prompt Ini) |
| :--- | :---: | :---: | :---: |
| **Input Bar** | Floating auto-resize pill | Fixed bottom bar kaku | Floating centered pill + auto-grow textarea |
| **Markdown Rendering** | Tabel, Bold, Codeblock, List rapi | Teks biasa (`\n` ke `<br>`) | Markdown-it / Marked.js + Syntax Highlight |
| **Empty State** | Greeting banner + kartu topik | Chat bubble awal langsung | Kartu rekomendasi modular dengan hover effect |
| **Sidebar Navigation** | Collapsible + New Chat + History | Fixed 320px static | Toggleable + New Chat + LocalStorage Session |
| **Message Actions** | Copy, Regenerate, Thumbs up/down | Tidak ada | Copy message, Copy code snippet, Feedback |
| **Streaming Control** | Tombol Stop Generation (■) | Hanya menunggu stream tuntas | Mendukung AbortController untuk memutus SSE |

---

## STRUKTUR INTEGRASI CDN YANG DIREKOMENDASIKAN

Saat mengimplementasikan prompt di atas ke dalam string HTML `main.py`, sisipkan CDN berikut pada tag `<head>`:

```html
<!-- Parser Markdown & Syntax Highlighting -->
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github-dark-dimmed.min.css">
<script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>

<!-- Icon Library modern (Lucide Icons) -->
<script src="https://unpkg.com/lucide@latest"></script>
```