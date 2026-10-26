import datetime
import os
import pandas as pd
import streamlit as st
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama

import ingest

# ==========================================================
# KONFIGURASI HALAMAN STREAMLIT
# ==========================================================
st.set_page_config(
    page_title="S.O.N.A.R - RAG Root-Cause Analysis Chatbot",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Konfigurasi Environment
CHROMA_HOST = os.getenv("CHROMA_HOST", "localhost")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", 8000))
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
LLM_MODEL = os.getenv("LLM_MODEL", "llama3.2")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")
CSV_PATH = os.getenv("CSV_PATH", "data/social_media_comments.csv")


def load_csv_data():
    """Memuat data mentah dari CSV."""
    if os.path.exists(CSV_PATH):
        return pd.read_csv(CSV_PATH)
    return pd.DataFrame()


# ==========================================================
# CUSTOM CSS / STYLING AESTHETICS
# ==========================================================
st.markdown("""
<style>
    /* Styling Header & Badge */
    .sonar-header {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 20px 24px;
        margin-bottom: 20px;
        color: #f8fafc;
    }
    .sonar-title {
        font-size: 26px;
        font-weight: 700;
        margin-bottom: 4px;
        color: #38bdf8;
    }
    .sonar-subtitle {
        font-size: 14px;
        color: #94a3b8;
        margin-bottom: 12px;
    }
    .status-badge-container {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
    }
    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: rgba(255, 255, 255, 0.08);
        border: 1px solid rgba(255, 255, 255, 0.15);
        border-radius: 20px;
        padding: 4px 12px;
        font-size: 12px;
        color: #e2e8f0;
    }
    
    /* Citation / Context Card */
    .citation-card {
        background: rgba(255, 255, 255, 0.03);
        border-left: 4px solid #38bdf8;
        border-radius: 0 8px 8px 0;
        padding: 10px 14px;
        margin: 8px 0;
        border-top: 1px solid rgba(255, 255, 255, 0.05);
        border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        border-right: 1px solid rgba(255, 255, 255, 0.05);
    }
    .citation-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 6px;
        font-size: 12px;
    }
    .platform-tag {
        font-weight: 600;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 11px;
    }
    .platform-x { background: #0f1419; color: #fff; border: 1px solid #536471; }
    .platform-instagram { background: #e1306c; color: #fff; }
    .platform-tiktok { background: #000; color: #00f2fe; border: 1px solid #fe2c55; }
    .platform-youtube { background: #ff0000; color: #fff; }

    .sentiment-pill-neg {
        background: #ef444420;
        color: #f87171;
        border: 1px solid #ef444450;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 11px;
        font-weight: 600;
    }
    .sentiment-pill-pos {
        background: #22c55e20;
        color: #4ade80;
        border: 1px solid #22c55e50;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 11px;
        font-weight: 600;
    }
    .sentiment-pill-neu {
        background: #6b728020;
        color: #9ca3af;
        border: 1px solid #6b728050;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 11px;
        font-weight: 600;
    }

    /* Welcome Banner */
    .welcome-card {
        background: linear-gradient(135deg, rgba(56, 189, 248, 0.08) 0%, rgba(99, 102, 241, 0.08) 100%);
        border: 1px solid rgba(56, 189, 248, 0.25);
        border-radius: 12px;
        padding: 18px 22px;
        margin-bottom: 16px;
    }
</style>
""", unsafe_allow_html=True)


# ==========================================================
# SIDEBAR
# ==========================================================
with st.sidebar:
    st.markdown("### ⚙️ Panel Kontrol & Filter")
    st.caption("S.O.N.A.R Media Sosial RAG Analyzer")

    st.subheader("Database & Vector Store")
    if st.button("🔄 Ingest / Reset Dataset ke ChromaDB", use_container_width=True, type="primary"):
        with st.spinner("Sedang memproses indexing ke ChromaDB..."):
            try:
                total_docs = ingest.ingest_data(CSV_PATH)
                st.success(f"Berhasil mengindeks {total_docs} komentar ke ChromaDB!")
            except Exception as e:
                st.error(f"Gagal melakukan ingest: {e}")

    st.divider()

    st.subheader("Filter Retrieval Metadata")
    sentiment_options = ["All", "negative", "neutral", "positive"]
    selected_sentiment = st.selectbox("Sentimen", sentiment_options, index=0)

    platform_options = ["All", "X", "Instagram", "TikTok", "YouTube"]
    selected_platform = st.selectbox("Platform", platform_options, index=0)

    top_k = st.slider("Top-K Dokumen Relevan", min_value=1, max_value=15, value=5, step=1)
    temperature = st.slider("Temperature LLM", min_value=0.0, max_value=1.0, value=0.2, step=0.1)

    st.divider()

    st.subheader("Opsi Percakapan")
    if st.button("🗑️ Hapus Riwayat Chat", use_container_width=True):
        st.session_state["messages"] = []
        st.rerun()

    st.divider()
    st.caption("ℹ️ **Status Koneksi Layanan:**")
    st.caption(f"- **ChromaDB**: `{CHROMA_HOST}:{CHROMA_PORT}`")
    st.caption(f"- **Ollama API**: `{OLLAMA_BASE_URL}`")
    st.caption(f"- **Model LLM**: `{LLM_MODEL}`")
    st.caption(f"- **Embedding**: `{EMBED_MODEL}`")


# ==========================================================
# HEADER UTAMA
# ==========================================================
st.markdown("""
<div class="sonar-header">
    <div class="sonar-title">🔍 S.O.N.A.R — Social Online Network Analytics & Root-Cause</div>
    <div class="sonar-subtitle">
        Asisten AI Berbasis Retrieval-Augmented Generation (RAG) untuk investigasi mendalam perubahan sentimen publik, 
        analisis akar masalah kegagalan teknis/layanan, dan perumusan mitigasi strategis.
    </div>
    <div class="status-badge-container">
        <span class="status-badge">⚡ <b>Engine:</b> LangChain + ChromaDB</span>
        <span class="status-badge">🤖 <b>LLM:</b> Ollama (llama3.2)</span>
        <span class="status-badge">🧠 <b>Embedding:</b> nomic-embed-text</span>
        <span class="status-badge">🎯 <b>Chroma Filter:</b> """ + f"{selected_sentiment} | {selected_platform}" + """</span>
    </div>
</div>
""", unsafe_allow_html=True)

# Tabs Navigasi
tab_chat, tab_overview = st.tabs([
    "💬 Chatbot Asisten Root-Cause Analysis",
    "📈 Exploratory Sentiment Overview"
])

df_comments = load_csv_data()


# ==========================================================
# HELPER FUNCTIONS
# ==========================================================
def build_chroma_filter(sentiment: str, platform: str):
    """Membangun query filter metadata untuk ChromaDB."""
    conditions = []
    if sentiment != "All":
        conditions.append({"sentiment": sentiment})
    if platform != "All":
        conditions.append({"platform": platform})

    if len(conditions) == 1:
        return conditions[0]
    elif len(conditions) > 1:
        return {"$and": conditions}
    return None


def get_platform_badge_class(platform: str) -> str:
    p = platform.lower()
    if "x" in p or "twitter" in p:
        return "platform-x"
    elif "instagram" in p:
        return "platform-instagram"
    elif "tiktok" in p:
        return "platform-tiktok"
    elif "youtube" in p:
        return "platform-youtube"
    return "platform-x"


def get_sentiment_badge_html(sentiment: str) -> str:
    s = sentiment.lower()
    if s == "negative":
        return '<span class="sentiment-pill-neg">🔴 Negatif</span>'
    elif s == "positive":
        return '<span class="sentiment-pill-pos">🟢 Positif</span>'
    return '<span class="sentiment-pill-neu">⚪ Netral</span>'


def render_citation_box(retrieved_docs):
    """Menampilkan expander konteks dokumen bukti dari ChromaDB."""
    if not retrieved_docs:
        return

    with st.expander(f"📄 Bukti Dokumen Terkait ({len(retrieved_docs)} Komentar Di-retrieve)", expanded=False):
        for i, doc in enumerate(retrieved_docs, start=1):
            m = doc.metadata
            platform = m.get("platform", "Unknown")
            sentiment = m.get("sentiment", "neutral")
            topic = m.get("topic", "-")
            likes = m.get("likes", 0)
            user = m.get("username", "-")
            tgl = m.get("timestamp", "-")
            content = doc.page_content

            platform_class = get_platform_badge_class(platform)
            sentiment_html = get_sentiment_badge_html(sentiment)

            st.markdown(f"""
            <div class="citation-card">
                <div class="citation-header">
                    <div>
                        <span class="platform-tag {platform_class}">{platform}</span>
                        {sentiment_html}
                        <span style="color:#94a3b8; margin-left:6px; font-size:11px;">Topik: <b>{topic}</b> | ❤️ {likes} likes</span>
                    </div>
                    <div style="color:#64748b; font-size:11px;">{tgl} • <b>{user}</b></div>
                </div>
                <div style="color:#cbd5e1; font-size:13px; font-style: italic; line-height:1.4;">
                    "{content}"
                </div>
            </div>
            """, unsafe_allow_html=True)


# ==========================================================
# TAB 1: CHATBOT ASISTEN ROOT-CAUSE
# ==========================================================
with tab_chat:
    # Inisialisasi Session State Messages
    if "messages" not in st.session_state:
        st.session_state["messages"] = [
            {
                "role": "assistant",
                "content": (
                    "👋 **Halo! Saya S.O.N.A.R AI**, asisten spesialis Root-Cause Analysis media sosial.\n\n"
                    "Saya dapat membantu Anda mengidentifikasi akar permasalahan di balik lonjakan komplain netizen, "
                    "mengumpulkan bukti komentar autentik lintas platform, dan merumuskan langkah mitigasi teknis maupun operasional.\n\n"
                    "Silakan ketik pertanyaan Anda atau pilih salah satu template investigasi cepat di bawah!"
                ),
                "retrieved_docs": [],
                "timestamp": datetime.datetime.now().strftime("%H:%M")
            }
        ]

    # Tombol Pertanyaan Cepat (Suggestion Chips)
    st.markdown("##### 💡 Rekomendasi Investigasi Cepat:")
    col_q1, col_q2 = st.columns(2)
    with col_q1:
        if st.button("💳 Mengapa transaksi QRIS & Top-up sering gagal?", use_container_width=True):
            st.session_state["pending_prompt"] = "Apa penyebab utama kegagalan transaksi QRIS dan top-up saldo yang dikeluhkan pengguna?"
            st.rerun()
        if st.button("📱 Apa akar masalah force close & lag di update v2.4?", use_container_width=True):
            st.session_state["pending_prompt"] = "Jelaskan akar penyebab aplikasi sering force close dan lag setelah update ke versi 2.4."
            st.rerun()
    with col_q2:
        if st.button("🎧 Bagaimana keluhan terkait respons Customer Service?", use_container_width=True):
            st.session_state["pending_prompt"] = "Mengapa netizen banyak mengeluhkan respon Customer Service yang lambat dan bot muter-muter?"
            st.rerun()
        if st.button("🌟 Apa tanggapan positif pengguna terhadap fitur baru?", use_container_width=True):
            st.session_state["pending_prompt"] = "Fitur baru apa saja yang mendapat apresiasi positif dari netizen dan apa alasannya?"
            st.rerun()

    st.markdown("---")

    # Render Riwayat Chat
    for msg in st.session_state["messages"]:
        role = msg["role"]
        avatar = "🧑‍💻" if role == "user" else "🤖"
        with st.chat_message(role, avatar=avatar):
            st.markdown(msg["content"])
            if role == "assistant" and msg.get("retrieved_docs"):
                render_citation_box(msg["retrieved_docs"])

    # Tangkap Input Chat (dari chat_input atau dari tombol rekomendasi)
    chat_input_val = st.chat_input("Tanyakan analisis sentimen atau akar masalah (misal: Mengapa transaksi QRIS gagal?)...")
    
    user_query = None
    if "pending_prompt" in st.session_state and st.session_state["pending_prompt"]:
        user_query = st.session_state.pop("pending_prompt")
    elif chat_input_val:
        user_query = chat_input_val

    # Proses Pertanyaan User
    if user_query:
        # Tampilkan Pesan User
        st.session_state["messages"].append({
            "role": "user",
            "content": user_query,
            "timestamp": datetime.datetime.now().strftime("%H:%M")
        })
        with st.chat_message("user", avatar="🧑‍💻"):
            st.markdown(user_query)

        # Siapkan Filter Chroma
        chroma_filter = build_chroma_filter(selected_sentiment, selected_platform)

        # Proses Retrieval & Streaming LLM
        with st.chat_message("assistant", avatar="🤖"):
            retrieved_docs = []
            with st.spinner("🔍 Mengambil komentar relevan dari ChromaDB & memproses via Ollama..."):
                try:
                    vector_store = ingest.get_vector_store()
                    retrieved_docs = vector_store.similarity_search(
                        query=user_query,
                        k=top_k,
                        filter=chroma_filter
                    )
                except Exception as e:
                    st.error(f"Gagal melakukan similarity search pada ChromaDB: {e}")
                    retrieved_docs = []

            if not retrieved_docs:
                fallback_msg = (
                    "⚠️ **Tidak ditemukan dokumen yang cocok** dengan query atau filter yang aktif saat ini.\n\n"
                    "**Saran Perbaikan:**\n"
                    "1. Pastikan Anda telah menekan tombol **'🔄 Ingest / Reset Dataset ke ChromaDB'** di sidebar.\n"
                    "2. Jika filter sentimen/platform di sidebar aktif, coba ubah ke **'All'**.\n"
                    "3. Gunakan kata kunci yang relevan dengan keluhan, transaksi, update aplikasi, atau layanan."
                )
                st.markdown(fallback_msg)
                st.session_state["messages"].append({
                    "role": "assistant",
                    "content": fallback_msg,
                    "retrieved_docs": [],
                    "timestamp": datetime.datetime.now().strftime("%H:%M")
                })
            else:
                # Format context dari retrieved documents
                context_entries = []
                for idx, doc in enumerate(retrieved_docs, start=1):
                    meta = doc.metadata
                    entry = (
                        f"[Dokumen #{idx}]\n"
                        f"ID: {meta.get('id', '-')}\n"
                        f"Platform: {meta.get('platform', '-')}\n"
                        f"Tanggal: {meta.get('timestamp', '-')}\n"
                        f"Pengguna: {meta.get('username', '-')}\n"
                        f"Sentimen: {meta.get('sentiment', '-')}\n"
                        f"Topik: {meta.get('topic', '-')}\n"
                        f"Likes: {meta.get('likes', 0)}\n"
                        f"Isi Komentar: \"{doc.page_content}\"\n"
                    )
                    context_entries.append(entry)

                context_text = "\n---\n".join(context_entries)

                # Prompt Template
                prompt_template = ChatPromptTemplate.from_messages([
                    (
                        "system",
                        "Anda adalah seorang Senior Social Media Data Scientist & Root-Cause Analyst profesional bernama S.O.N.A.R AI. "
                        "Tugas Anda adalah menganalisis kumpulan komentar netizen media sosial yang diberikan untuk "
                        "mengidentifikasi akar penyebab permasalahan (root cause), memverifikasi keluhan dengan bukti konkret, "
                        "dan merumuskan solusi mitigasi yang aplikatif dan tajam.\n\n"
                        "Gunakan format laporan berikut secara terstruktur dan rapi:\n"
                        "### 1. 🔍 Ringkasan Eksekutif Akar Masalah (Root Cause)\n"
                        "Jelaskan apa yang sebenarnya terjadi, faktor pemicu utama, serta komponen sistem/layanan yang terdampak secara komprehensif.\n\n"
                        "### 2. 💬 Bukti Kutipan Komentar Netizen (beserta platform & tanggal)\n"
                        "Sertakan kutipan langsung komentar netizen yang relevan dari data yang tersedia, lengkap dengan platform, username, dan tanggalnya sebagai bukti empiris.\n\n"
                        "### 3. 🛠️ Rekomendasi Mitigasi Konkret\n"
                        "- **Mitigasi Jangka Pendek (Immediate/Hotfix):** Tindakan taktis segera (CS response, recovery, pengumuman publik, rollback jika perlu).\n"
                        "- **Mitigasi Jangka Panjang (Preventive/Structural):** Perbaikan arsitektur, kapasitas load testing, SLA payment gateway, monitoring observabilitas."
                    ),
                    (
                        "human",
                        "Berikut adalah data komentar media sosial yang berhasil di-retrieve:\n\n"
                        "=== KONTEKS KOMENTAR MEDIA SOSIAL ===\n"
                        "{context}\n"
                        "====================================\n\n"
                        "Pertanyaan / Isu yang Diinvestigasi: {question}\n\n"
                        "Berikan analisis lengkap, objektif, dan terstruktur sesuai format di atas."
                    )
                ])

                try:
                    llm = ChatOllama(
                        base_url=OLLAMA_BASE_URL,
                        model=LLM_MODEL,
                        temperature=temperature
                    )
                    rag_chain = prompt_template | llm

                    # Stream output secara real-time
                    def generate_stream():
                        for chunk in rag_chain.stream({
                            "context": context_text,
                            "question": user_query
                        }):
                            yield chunk.content

                    full_response = st.write_stream(generate_stream())

                    # Tampilkan box konteks bukti
                    render_citation_box(retrieved_docs)

                    # Simpan ke session history
                    st.session_state["messages"].append({
                        "role": "assistant",
                        "content": full_response,
                        "retrieved_docs": retrieved_docs,
                        "timestamp": datetime.datetime.now().strftime("%H:%M")
                    })

                except Exception as e:
                    error_msg = f"❌ Gagal memproses query melalui LLM: {e}"
                    st.error(error_msg)
                    st.info("Pastikan service Ollama berjalan di host OS dan model `llama3.2` sudah diunduh.")

    # Tombol Ekspor Chat di bawah tab
    if len(st.session_state["messages"]) > 1:
        st.markdown("<br>", unsafe_allow_html=True)
        # Susun transkrip Markdown
        transcript_lines = ["# Transkrip Percakapan S.O.N.A.R Root-Cause Analysis\n"]
        for m in st.session_state["messages"]:
            speaker = "AI Analyst" if m["role"] == "assistant" else "Investigator"
            transcript_lines.append(f"### {speaker} ({m.get('timestamp', '-')})\n{m['content']}\n")
        
        st.download_button(
            label="📥 Unduh Transkrip Percakapan (.md)",
            data="\n".join(transcript_lines),
            file_name=f"sonar_analysis_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
            mime="text/markdown",
            help="Download ringkasan dan transkrip chat untuk dokumentasi insiden"
        )


# ==========================================================
# TAB 2: OVERVIEW DATA & SENTIMEN METRIK
# ==========================================================
with tab_overview:
    if df_comments.empty:
        st.warning(f"File data `{CSV_PATH}` belum ditemukan. Silakan pastikan file tersedia.")
    else:
        st.subheader("📊 Ringkasan Metrik Sentimen & Platform")
        
        total_rows = len(df_comments)
        neg_count = len(df_comments[df_comments["sentiment"] == "negative"])
        neu_count = len(df_comments[df_comments["sentiment"] == "neutral"])
        pos_count = len(df_comments[df_comments["sentiment"] == "positive"])

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Komentar", f"{total_rows} data")
        col2.metric("Sentimen Negatif 🔴", f"{neg_count}", f"{(neg_count/total_rows)*100:.1f}%")
        col3.metric("Sentimen Netral ⚪", f"{neu_count}", f"{(neu_count/total_rows)*100:.1f}%")
        col4.metric("Sentimen Positif 🟢", f"{pos_count}", f"{(pos_count/total_rows)*100:.1f}%")

        st.divider()

        col_chart1, col_chart2 = st.columns(2)
        with col_chart1:
            st.markdown("##### Distribusi Komentar per Platform")
            platform_counts = df_comments["platform"].value_counts()
            st.bar_chart(platform_counts, color="#38bdf8")

        with col_chart2:
            st.markdown("##### Distribusi Topik Pembahasan")
            topic_counts = df_comments["topic"].value_counts()
            st.bar_chart(topic_counts, color="#10b981")

        st.subheader("📋 Dataset Komentar Media Sosial")
        st.dataframe(
            df_comments,
            use_container_width=True,
            column_config={
                "id": st.column_config.NumberColumn("ID", width="small"),
                "timestamp": st.column_config.DateColumn("Tanggal"),
                "platform": st.column_config.TextColumn("Platform"),
                "username": st.column_config.TextColumn("User"),
                "comment": st.column_config.TextColumn("Komentar", width="large"),
                "sentiment": st.column_config.TextColumn("Sentimen"),
                "topic": st.column_config.TextColumn("Topik"),
                "likes": st.column_config.NumberColumn("Likes", format="%d")
            },
            hide_index=True
        )
