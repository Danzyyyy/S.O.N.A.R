import os
import pandas as pd
import streamlit as st
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama

import ingest

# Konfigurasi Halaman Streamlit
st.set_page_config(
    page_title="RAG Sentiment Root-Cause Analysis",
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
# SIDEBAR
# ==========================================================
with st.sidebar:
    st.title("⚙️ Kontrol Sistem")
    st.caption("RAG Media Sosial Root-Cause Analyzer")

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

    top_k = st.slider("Top-K Dokumen Relevan", min_value=1, max_value=20, value=5, step=1)

    st.divider()
    st.caption("ℹ️ **Status Koneksi Service:**")
    st.caption(f"- ChromaDB: `{CHROMA_HOST}:{CHROMA_PORT}`")
    st.caption(f"- Ollama API: `{OLLAMA_BASE_URL}`")
    st.caption(f"- LLM Model: `{LLM_MODEL}`")
    st.caption(f"- Embedding: `{EMBED_MODEL}`")


# ==========================================================
# HEADER UTAMA
# ==========================================================
st.title("📊 RAG Root-Cause Analysis Media Sosial")
st.markdown(
    "Sistem analisis akar masalah perubahan sentimen publik terhadap aplikasi/layanan digital "
    "menggunakan **Retrieval-Augmented Generation (RAG)**, **ChromaDB**, dan **Ollama**."
)

tab1, tab2 = st.tabs([
    "📈 Exploratory Sentiment Overview",
    "🤖 RAG Root-Cause Analysis Agent"
])

df_comments = load_csv_data()

# ==========================================================
# TAB 1: OVERVIEW DATA
# ==========================================================
with tab1:
    if df_comments.empty:
        st.warning(f"File data `{CSV_PATH}` belum ditemukan. Silakan pastikan file tersedia.")
    else:
        st.subheader("Ringkasan Metrik Sentimen & Platform")
        
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
            st.bar_chart(platform_counts, color="#3b82f6")

        with col_chart2:
            st.markdown("##### Distribusi Topik Pembahasan")
            topic_counts = df_comments["topic"].value_counts()
            st.bar_chart(topic_counts, color="#10b981")

        st.subheader("Tabel Komentar Media Sosial")
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


# ==========================================================
# TAB 2: RAG AGENT
# ==========================================================
with tab2:
    st.subheader("Investigasi Masalah & Analisis Akar Penyebab")
    st.markdown(
        "Ajukan pertanyaan terkait keluhan atau perubahan sentimen pengguna. "
        "LLM akan mengekstrak bukti dari komentar yang terindeks dan merumuskan analisis akar masalah beserta rekomendasinya."
    )

    default_query = "Apa penyebab utama lonjakan sentimen negatif terkait pembayaran dan update aplikasi?"
    user_query = st.text_area("Pertanyaan / Topik Investigasi:", value=default_query, height=90)

    # Susun Chroma filter berdasarkan sidebar
    conditions = []
    if selected_sentiment != "All":
        conditions.append({"sentiment": selected_sentiment})
    if selected_platform != "All":
        conditions.append({"platform": selected_platform})

    if len(conditions) == 1:
        chroma_filter = conditions[0]
    elif len(conditions) > 1:
        chroma_filter = {"$and": conditions}
    else:
        chroma_filter = None

    if chroma_filter:
        st.info(f"🔎 Filter Metadata Aktif: `{chroma_filter}`")

    if st.button("🚀 Jalankan Root-Cause Analysis", type="primary"):
        if not user_query.strip():
            st.warning("Silakan masukkan pertanyaan terlebih dahulu.")
        else:
            with st.spinner("Mengambil dokumen relevan dari ChromaDB & memproses via Ollama..."):
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
                    st.warning(
                        "Tidak ditemukan dokumen yang cocok dengan query atau filter yang dipilih. "
                        "Pastikan Anda telah menekan tombol '🔄 Ingest / Reset Dataset ke ChromaDB' di sidebar "
                        "atau longgarkan filter pencarian."
                    )
                else:
                    # Format context untuk prompt
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

                    # Template Prompt
                    prompt_template = ChatPromptTemplate.from_messages([
                        (
                            "system",
                            "Anda adalah seorang Senior Social Media Data Scientist & Root-Cause Analyst profesional. "
                            "Tugas Anda adalah menganalisis kumpulan komentar netizen media sosial yang diberikan untuk "
                            "mengidentifikasi akar penyebab permasalahan (root cause), memverifikasi keluhan dengan bukti konkret, "
                            "dan merumuskan solusi mitigasi yang aplikatif.\n\n"
                            "Gunakan format laporan berikut secara ketat:\n"
                            "### 1. Ringkasan Eksekutif Akar Masalah (Root Cause)\n"
                            "Jelaskan apa yang sebenarnya terjadi, faktor pemicu utama, serta komponen sistem/layanan yang terdampak secara komprehensif.\n\n"
                            "### 2. Bukti Kutipan Komentar Netizen (beserta platform & tanggal)\n"
                            "Sertakan kutipan langsung komentar netizen yang relevan dari data yang tersedia, lengkap dengan platform, username, dan tanggalnya sebagai bukti empiris.\n\n"
                            "### 3. Rekomendasi Mitigasi Konkret\n"
                            "Berikan langkah penanganan jangka pendek (hotfix/CS response/klarifikasi) dan langkah jangka panjang (perbaikan arsitektur/infrastruktur/SLA/monitoring)."
                        ),
                        (
                            "human",
                            "Berikut adalah data komentar media sosial yang berhasil di-retrieve:\n\n"
                            "=== KONTEKS KOMENTAR MEDIA SOSIAL ===\n"
                            "{context}\n"
                            "====================================\n\n"
                            "Pertanyaan / Isu yang Diinvestigasi: {question}\n\n"
                            "Berikan laporan Root-Cause Analysis lengkap sesuai format di atas."
                        )
                    ])

                    llm = ChatOllama(
                        base_url=OLLAMA_BASE_URL,
                        model=LLM_MODEL,
                        temperature=0.2
                    )

                    rag_chain = prompt_template | llm

                    try:
                        response_container = st.container()
                        with response_container:
                            st.markdown("### 📋 Hasil Root-Cause Analysis")
                            response = rag_chain.invoke({
                                "context": context_text,
                                "question": user_query
                            })
                            st.markdown(response.content)

                        # Expander untuk melihat dokumen yang di-retrieve
                        with st.expander("📄 Lihat Konteks Dokumen yang Di-retrieve (Vector Search)", expanded=False):
                            for i, doc in enumerate(retrieved_docs, start=1):
                                m = doc.metadata
                                st.markdown(f"**Dokumen #{i}** — `{m.get('platform')}` | `{m.get('timestamp')}` | Sentimen: `{m.get('sentiment')}` | Topik: `{m.get('topic')}` | Likes: `{m.get('likes')}`")
                                st.markdown(f"> *{doc.page_content}*")
                                st.caption(f"Author: {m.get('username')} (ID: {m.get('id')})")
                                st.divider()

                    except Exception as e:
                        st.error(f"Gagal menjalankan LLM ChatOllama: {e}")
                        st.info("Pastikan Ollama berjalan di host dengan model yang sesuai dan mengizinkan koneksi dari container Docker.")
