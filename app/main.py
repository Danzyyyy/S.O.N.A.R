import json
import os
from typing import List, Optional

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel, Field

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")

app = FastAPI(
    title="S.O.N.A.R Social Media Chatbot API",
    description="REST API backend terhubung dengan Ollama LLM untuk analisis media sosial & chatbot interaktif.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class MessageItem(BaseModel):
    role: str = Field(..., description="Role: 'user', 'assistant', atau 'system'")
    content: str = Field(..., description="Isi teks pesan")


class ChatRequest(BaseModel):
    message: str = Field(..., description="Pesan atau pertanyaan dari pengguna")
    history: Optional[List[MessageItem]] = Field(default=[], description="Riwayat percakapan sebelumnya")
    temperature: Optional[float] = Field(default=0.2, ge=0.0, le=1.0, description="Kreativitas model LLM")
    model: Optional[str] = Field(default=None, description="Nama model Ollama yang dipilih pengguna")


class ChatResponse(BaseModel):
    response: str
    model: str
    done: bool = True


@app.get("/health", tags=["Status"])
async def health_check():
    """Memeriksa status API dan koneksi ke Ollama."""
    ollama_status = "unreachable"
    available_models = []
    chat_models = []
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            res = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            if res.status_code == 200:
                ollama_status = "connected"
                data = res.json()
                for m in data.get("models", []):
                    name = m.get("name", "")
                    available_models.append(name)
                    # Filter model non-embedding (chat models only)
                    if "embed" not in name.lower():
                        chat_models.append(name)
    except Exception as e:
        ollama_status = f"error: {str(e)}"

    return {
        "status": "healthy",
        "ollama_base_url": OLLAMA_BASE_URL,
        "ollama_status": ollama_status,
        "configured_model": OLLAMA_MODEL,
        "available_models": available_models,
        "chat_models": chat_models or ["llama3.2:3b", "qwen2.5:3b"]
    }


@app.post("/api/chat", response_model=ChatResponse, tags=["Chat"])
async def chat_endpoint(payload: ChatRequest):
    """Mengirim pesan chat ke Ollama dan mendapatkan jawaban lengkap."""
    messages = []
    selected_model = payload.model or OLLAMA_MODEL
    
    # Tambahkan system prompt
    messages.append({
        "role": "system",
        "content": (
            "Anda adalah S.O.N.A.R AI, asisten analis media sosial dan komunikasi publik profesional. "
            "Berikan jawaban yang jelas, solutif, analitis, dan ramah menggunakan bahasa Indonesia yang baik."
        )
    })

    # Tambahkan history
    if payload.history:
        for item in payload.history:
            messages.append({"role": item.role, "content": item.content})

    # Tambahkan pertanyaan terkini
    messages.append({"role": "user", "content": payload.message})

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            req_data = {
                "model": selected_model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": payload.temperature
                }
            }
            res = await client.post(f"{OLLAMA_BASE_URL}/api/chat", json=req_data)
            
            if res.status_code != 200:
                raise HTTPException(
                    status_code=res.status_code,
                    detail=f"Ollama API error: {res.text}"
                )
            
            data = res.json()
            reply = data.get("message", {}).get("content", "")
            return ChatResponse(response=reply, model=selected_model, done=True)

    except httpx.RequestError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Tidak dapat terhubung ke Ollama di {OLLAMA_BASE_URL}: {str(e)}"
        )


@app.post("/api/chat/stream", tags=["Chat"])
async def chat_stream_endpoint(payload: ChatRequest):
    """Streaming respons chat dari Ollama secara real-time via Server-Sent Events (SSE)."""
    messages = []
    selected_model = payload.model or OLLAMA_MODEL

    messages.append({
        "role": "system",
        "content": (
            "Anda adalah S.O.N.A.R AI, asisten analis media sosial dan komunikasi publik profesional. "
            "Berikan jawaban yang jelas, solutif, analitis, dan ramah menggunakan bahasa Indonesia yang baik."
        )
    })
    if payload.history:
        for item in payload.history:
            messages.append({"role": item.role, "content": item.content})
    messages.append({"role": "user", "content": payload.message})

    async def event_generator():
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                req_data = {
                    "model": selected_model,
                    "messages": messages,
                    "stream": True,
                    "options": {
                        "temperature": payload.temperature
                    }
                }
                async with client.stream("POST", f"{OLLAMA_BASE_URL}/api/chat", json=req_data) as response:
                    async for line in response.aiter_lines():
                        if line:
                            try:
                                chunk = json.loads(line)
                                text_chunk = chunk.get("message", {}).get("content", "")
                                if text_chunk:
                                    yield f"data: {json.dumps({'content': text_chunk})}\n\n"
                                if chunk.get("done", False):
                                    yield f"data: {json.dumps({'done': True})}\n\n"
                                    break
                            except Exception:
                                pass
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/", response_class=HTMLResponse, tags=["Web UI"])
async def serve_chatbot_ui():
    """Tampilan web interaktif Chatbot S.O.N.A.R — Desain Modern AI Canvas (Gemini & ChatGPT style)."""
    html_content = """<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>S.O.N.A.R — Social Media AI Analyst</title>
    <!-- Google Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    
    <!-- Marked.js Markdown Parser -->
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>

    <!-- Highlight.js Syntax Highlighting -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github-dark-dimmed.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>

    <!-- Lucide Icons -->
    <script src="https://unpkg.com/lucide@latest"></script>

    <style>
        :root {
            --bg-canvas: #131314;
            --bg-sidebar: #1e1f20;
            --bg-surface: #1e1f20;
            --bg-card: #282a2c;
            --bg-card-hover: #333538;
            --border-subtle: rgba(255, 255, 255, 0.08);
            --border-light: rgba(255, 255, 255, 0.14);
            --accent-blue: #4285f4;
            --accent-purple: #9b72cb;
            --accent-gradient: linear-gradient(135deg, #4285f4 0%, #9b72cb 100%);
            --text-primary: #e3e3e3;
            --text-secondary: #9aa0a6;
            --text-muted: #70757a;
            --user-bubble: #282a2c;
            --code-bg: #18191a;
            --sidebar-width: 280px;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            -webkit-font-smoothing: antialiased;
        }

        body {
            background-color: var(--bg-canvas);
            color: var(--text-primary);
            display: flex;
            height: 100vh;
            width: 100vw;
            overflow: hidden;
        }

        /* ================= SIDEBAR ================= */
        .sidebar {
            width: var(--sidebar-width);
            min-width: var(--sidebar-width);
            background-color: var(--bg-sidebar);
            border-right: 1px solid var(--border-subtle);
            display: flex;
            flex-direction: column;
            transition: all 0.28s cubic-bezier(0.4, 0, 0.2, 1);
            position: relative;
            z-index: 50;
        }

        .sidebar.collapsed {
            width: 0;
            min-width: 0;
            padding: 0;
            border-right: 1px solid transparent;
            overflow: hidden;
        }

        .sidebar-header {
            padding: 16px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .sidebar-brand {
            display: flex;
            align-items: center;
            gap: 10px;
            text-decoration: none;
            color: inherit;
        }

        .brand-logo-icon {
            width: 34px;
            height: 34px;
            border-radius: 9px;
            background: var(--accent-gradient);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            box-shadow: 0 4px 14px rgba(66, 133, 244, 0.35);
        }

        .brand-title {
            font-weight: 700;
            font-size: 15px;
            letter-spacing: -0.2px;
            color: #fff;
        }

        .brand-tag {
            font-size: 10px;
            color: var(--text-secondary);
            font-weight: 500;
        }

        .sidebar-collapse-btn {
            background: transparent;
            border: none;
            color: var(--text-secondary);
            cursor: pointer;
            padding: 8px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: background 0.15s, color 0.15s;
        }

        .sidebar-collapse-btn:hover {
            background: rgba(255, 255, 255, 0.08);
            color: var(--text-primary);
        }

        /* New Chat Button */
        .new-chat-wrapper {
            padding: 0 14px 14px 14px;
        }

        .btn-new-chat {
            width: 100%;
            background: rgba(255, 255, 255, 0.06);
            border: 1px solid var(--border-subtle);
            color: var(--text-primary);
            padding: 11px 16px;
            border-radius: 24px;
            font-size: 13.5px;
            font-weight: 600;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 10px;
            transition: all 0.2s ease;
        }

        .btn-new-chat:hover {
            background: rgba(255, 255, 255, 0.12);
            border-color: rgba(255, 255, 255, 0.22);
            transform: translateY(-1px);
        }

        /* History List */
        .history-section {
            flex: 1;
            overflow-y: auto;
            padding: 0 10px;
            display: flex;
            flex-direction: column;
            gap: 4px;
        }

        .history-label {
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.6px;
            color: var(--text-muted);
            padding: 8px 10px 4px 10px;
        }

        .history-item {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 9px 12px;
            border-radius: 10px;
            color: var(--text-secondary);
            font-size: 13px;
            cursor: pointer;
            transition: all 0.15s ease;
            position: relative;
            group: item;
        }

        .history-item:hover, .history-item.active {
            background: rgba(255, 255, 255, 0.06);
            color: var(--text-primary);
        }

        .history-item.active {
            font-weight: 600;
            color: #fff;
            border-left: 3px solid var(--accent-blue);
        }

        .history-title {
            display: flex;
            align-items: center;
            gap: 8px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            max-width: 190px;
        }

        .history-actions {
            display: none;
            align-items: center;
            gap: 4px;
        }

        .history-item:hover .history-actions {
            display: flex;
        }

        .history-btn {
            background: transparent;
            border: none;
            color: var(--text-muted);
            cursor: pointer;
            padding: 3px;
            border-radius: 4px;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .history-btn:hover {
            color: #f87171;
            background: rgba(255, 255, 255, 0.1);
        }

        /* Sidebar Footer */
        .sidebar-footer {
            padding: 14px 16px;
            border-top: 1px solid var(--border-subtle);
            display: flex;
            flex-direction: column;
            gap: 10px;
        }

        .status-pill {
            display: flex;
            align-items: center;
            justify-content: space-between;
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid var(--border-subtle);
            border-radius: 8px;
            padding: 8px 10px;
            font-size: 12px;
        }

        .status-indicator {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            font-weight: 500;
        }

        .status-dot {
            width: 7px;
            height: 7px;
            border-radius: 50%;
            background: #94a3b8;
        }

        .status-dot.online {
            background: #34d399;
            box-shadow: 0 0 8px rgba(52, 211, 153, 0.6);
        }

        .status-dot.offline {
            background: #ef4444;
        }

        .footer-link-btn {
            display: flex;
            align-items: center;
            gap: 8px;
            color: var(--text-secondary);
            text-decoration: none;
            font-size: 12.5px;
            padding: 6px 8px;
            border-radius: 6px;
            transition: all 0.15s;
        }

        .footer-link-btn:hover {
            background: rgba(255, 255, 255, 0.05);
            color: var(--text-primary);
        }

        /* ================= MAIN CHAT CANVAS ================= */
        .main-canvas {
            flex: 1;
            display: flex;
            flex-direction: column;
            height: 100vh;
            background-color: var(--bg-canvas);
            position: relative;
            overflow: hidden;
        }

        /* Top Header */
        .canvas-header {
            height: 56px;
            padding: 0 20px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            border-bottom: 1px solid rgba(255, 255, 255, 0.04);
            flex-shrink: 0;
            z-index: 20;
        }

        .header-left {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .header-btn {
            background: transparent;
            border: none;
            color: var(--text-secondary);
            cursor: pointer;
            padding: 8px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.15s;
        }

        .header-btn:hover {
            background: rgba(255, 255, 255, 0.08);
            color: var(--text-primary);
        }

        .model-select-wrapper {
            position: relative;
            display: inline-flex;
            align-items: center;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid var(--border-light);
            border-radius: 20px;
            padding: 3px 12px 3px 12px;
            gap: 8px;
            transition: all 0.2s ease;
        }

        .model-select-wrapper:hover, .model-select-wrapper:focus-within {
            background: rgba(255, 255, 255, 0.09);
            border-color: rgba(66, 133, 244, 0.5);
            box-shadow: 0 0 14px rgba(66, 133, 244, 0.2);
        }

        .model-select-icon {
            width: 15px;
            height: 15px;
            color: var(--accent-blue);
            flex-shrink: 0;
        }

        .model-select-dropdown {
            background: transparent;
            border: none;
            color: var(--text-primary);
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            outline: none;
            padding-right: 20px;
            appearance: none;
            -webkit-appearance: none;
            -moz-appearance: none;
        }

        .model-select-dropdown option {
            background: #1e1f20;
            color: #fff;
            padding: 8px 12px;
        }

        .model-select-arrow {
            position: absolute;
            right: 10px;
            pointer-events: none;
            width: 14px;
            height: 14px;
            color: var(--text-secondary);
        }

        /* Scrollable Chat Area */
        .chat-scroll-area {
            flex: 1;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            scroll-behavior: smooth;
        }

        .chat-content-container {
            max-width: 800px;
            width: 100%;
            margin: 0 auto;
            padding: 24px 20px 140px 20px;
            display: flex;
            flex-direction: column;
            gap: 24px;
        }

        /* ================= ZERO STATE ================= */
        .zero-state {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            min-height: 55vh;
            text-align: center;
            padding: 20px;
            animation: fadeIn 0.4s ease;
        }

        .zero-icon-glow {
            width: 64px;
            height: 64px;
            border-radius: 20px;
            background: var(--accent-gradient);
            display: flex;
            align-items: center;
            justify-content: center;
            color: #fff;
            margin-bottom: 20px;
            box-shadow: 0 12px 30px rgba(66, 133, 244, 0.35);
        }

        .zero-title {
            font-size: 28px;
            font-weight: 700;
            color: #f1f3f4;
            letter-spacing: -0.5px;
            margin-bottom: 8px;
            background: linear-gradient(135deg, #ffffff 60%, #9aa0a6 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .zero-subtitle {
            font-size: 14px;
            color: var(--text-secondary);
            max-width: 500px;
            line-height: 1.5;
            margin-bottom: 36px;
        }

        /* Prompt Suggestions Grid */
        .suggestions-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 12px;
            width: 100%;
            max-width: 680px;
        }

        .prompt-card {
            background: var(--bg-card);
            border: 1px solid var(--border-subtle);
            border-radius: 14px;
            padding: 16px;
            cursor: pointer;
            text-align: left;
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
            position: relative;
            overflow: hidden;
        }

        .prompt-card:hover {
            background: var(--bg-card-hover);
            border-color: rgba(66, 133, 244, 0.4);
            transform: translateY(-2px);
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
        }

        .prompt-card-icon {
            font-size: 20px;
            margin-bottom: 8px;
        }

        .prompt-card-title {
            font-size: 13.5px;
            font-weight: 600;
            color: #fff;
            margin-bottom: 4px;
        }

        .prompt-card-desc {
            font-size: 12px;
            color: var(--text-secondary);
            line-height: 1.4;
        }

        /* ================= CHAT MESSAGES ================= */
        .message-group {
            display: flex;
            flex-direction: column;
            gap: 18px;
            animation: fadeIn 0.25s ease;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(6px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .turn-row {
            display: flex;
            gap: 14px;
            width: 100%;
        }

        .turn-row.user {
            justify-content: flex-end;
        }

        .avatar-box {
            width: 32px;
            height: 32px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
            font-size: 14px;
        }

        .turn-row.assistant .avatar-box {
            background: var(--accent-gradient);
            color: #fff;
            box-shadow: 0 2px 10px rgba(66, 133, 244, 0.3);
        }

        .turn-row.user .avatar-box {
            background: #3c4043;
            color: #fff;
        }

        .message-body {
            flex: 1;
            max-width: 90%;
            display: flex;
            flex-direction: column;
            gap: 8px;
        }

        .turn-row.user .message-body {
            align-items: flex-end;
            max-width: 80%;
        }

        .user-text-bubble {
            background: var(--user-bubble);
            color: #ffffff;
            padding: 12px 18px;
            border-radius: 18px;
            font-size: 14.5px;
            line-height: 1.5;
            white-space: pre-wrap;
            border: 1px solid rgba(255, 255, 255, 0.06);
        }

        .assistant-content {
            font-size: 14.5px;
            line-height: 1.65;
            color: var(--text-primary);
            overflow-wrap: break-word;
        }

        /* Markdown Styling */
        .assistant-content h1, .assistant-content h2, .assistant-content h3 {
            color: #fff;
            margin: 14px 0 8px 0;
            font-weight: 600;
        }
        .assistant-content h1 { font-size: 18px; }
        .assistant-content h2 { font-size: 16px; }
        .assistant-content h3 { font-size: 14.5px; }
        .assistant-content p { margin-bottom: 10px; }
        .assistant-content ul, .assistant-content ol {
            margin: 8px 0 12px 20px;
        }
        .assistant-content li { margin-bottom: 4px; }
        .assistant-content blockquote {
            border-left: 3px solid var(--accent-blue);
            background: rgba(66, 133, 244, 0.05);
            padding: 8px 14px;
            border-radius: 0 8px 8px 0;
            margin: 10px 0;
            color: #c4c7c5;
            font-style: italic;
        }
        .assistant-content table {
            width: 100%;
            border-collapse: collapse;
            margin: 14px 0;
            font-size: 13.5px;
        }
        .assistant-content th, .assistant-content td {
            border: 1px solid var(--border-subtle);
            padding: 8px 12px;
            text-align: left;
        }
        .assistant-content th {
            background: rgba(255, 255, 255, 0.04);
            color: #fff;
        }

        /* Code Block Container with Copy Code Button */
        .code-container {
            position: relative;
            background: var(--code-bg);
            border: 1px solid var(--border-subtle);
            border-radius: 10px;
            margin: 12px 0;
            overflow: hidden;
        }
        .code-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            background: rgba(255, 255, 255, 0.03);
            padding: 6px 12px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            font-size: 11px;
            color: var(--text-muted);
            text-transform: uppercase;
            font-weight: 600;
        }
        .copy-code-btn {
            background: transparent;
            border: none;
            color: var(--text-secondary);
            font-size: 11.5px;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 4px;
            padding: 2px 6px;
            border-radius: 4px;
            transition: all 0.15s;
        }
        .copy-code-btn:hover {
            background: rgba(255, 255, 255, 0.1);
            color: #fff;
        }
        .code-container pre {
            margin: 0;
            padding: 12px 14px;
            overflow-x: auto;
            font-family: 'Consolas', 'Courier New', monospace;
            font-size: 13px;
            line-height: 1.5;
        }

        /* Message Action Buttons (Copy, Regenerate, Thumbs) */
        .message-action-bar {
            display: flex;
            align-items: center;
            gap: 6px;
            margin-top: 4px;
            opacity: 0.85;
        }

        .action-chip-btn {
            background: transparent;
            border: none;
            color: var(--text-muted);
            cursor: pointer;
            padding: 5px 8px;
            border-radius: 6px;
            font-size: 12px;
            display: inline-flex;
            align-items: center;
            gap: 5px;
            transition: all 0.15s;
        }

        .action-chip-btn:hover {
            background: rgba(255, 255, 255, 0.08);
            color: var(--text-primary);
        }

        .action-chip-btn.active {
            color: var(--accent-blue);
            background: rgba(66, 133, 244, 0.1);
        }

        /* Thinking / Shimmer Indicator */
        .thinking-indicator {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 8px 14px;
            background: rgba(66, 133, 244, 0.08);
            border: 1px solid rgba(66, 133, 244, 0.2);
            border-radius: 20px;
            font-size: 12.5px;
            color: #8ab4f8;
            margin-top: 4px;
            animation: pulseGlow 1.8s infinite;
        }

        @keyframes pulseGlow {
            0%, 100% { opacity: 0.7; transform: scale(0.99); }
            50% { opacity: 1; transform: scale(1); }
        }

        .dot-flashing {
            display: flex;
            gap: 4px;
        }
        .dot-flashing span {
            width: 4px;
            height: 4px;
            background-color: #8ab4f8;
            border-radius: 50%;
            animation: flash 1.2s infinite ease-in-out;
        }
        .dot-flashing span:nth-child(2) { animation-delay: 0.2s; }
        .dot-flashing span:nth-child(3) { animation-delay: 0.4s; }
        @keyframes flash {
            0%, 80%, 100% { opacity: 0.3; transform: scale(0.8); }
            40% { opacity: 1; transform: scale(1.2); }
        }

        /* ================= SMART FLOATING INPUT BAR ================= */
        .input-dock {
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;
            background: linear-gradient(180deg, transparent 0%, rgba(19, 19, 20, 0.95) 40%, #131314 100%);
            padding: 10px 20px 18px 20px;
            display: flex;
            flex-direction: column;
            align-items: center;
            pointer-events: none;
            z-index: 30;
        }

        .input-dock-inner {
            max-width: 768px;
            width: 100%;
            pointer-events: auto;
            display: flex;
            flex-direction: column;
            gap: 8px;
        }

        .input-pill-container {
            background: #1e1f20;
            border: 1px solid var(--border-light);
            border-radius: 24px;
            padding: 8px 12px 8px 16px;
            display: flex;
            align-items: flex-end;
            gap: 10px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.45);
            transition: border-color 0.2s, box-shadow 0.2s;
        }

        .input-pill-container:focus-within {
            border-color: rgba(66, 133, 244, 0.6);
            box-shadow: 0 10px 30px rgba(66, 133, 244, 0.15);
        }

        .input-action-btn {
            background: transparent;
            border: none;
            color: var(--text-secondary);
            cursor: pointer;
            width: 34px;
            height: 34px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
            margin-bottom: 2px;
            transition: all 0.15s;
        }

        .input-action-btn:hover {
            background: rgba(255, 255, 255, 0.08);
            color: var(--text-primary);
        }

        .chat-textarea {
            flex: 1;
            background: transparent;
            border: none;
            color: #fff;
            font-size: 14.5px;
            line-height: 1.5;
            padding: 6px 0;
            outline: none;
            resize: none;
            max-height: 200px;
            min-height: 24px;
            overflow-y: auto;
        }

        .chat-textarea::placeholder {
            color: var(--text-muted);
        }

        /* Send / Stop Generating Button */
        .btn-send-dock {
            width: 36px;
            height: 36px;
            border-radius: 50%;
            border: none;
            background: #fff;
            color: #131314;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
            transition: all 0.2s ease;
            margin-bottom: 2px;
        }

        .btn-send-dock:hover {
            transform: scale(1.05);
            background: #f1f3f4;
        }

        .btn-send-dock:disabled {
            background: rgba(255, 255, 255, 0.2);
            color: rgba(255, 255, 255, 0.4);
            cursor: not-allowed;
            transform: none;
        }

        .btn-send-dock.is-streaming {
            background: #ea4335;
            color: #fff;
            animation: pulseStop 1.5s infinite;
        }

        @keyframes pulseStop {
            0%, 100% { box-shadow: 0 0 0 0 rgba(234, 67, 53, 0.4); }
            50% { box-shadow: 0 0 0 6px rgba(234, 67, 53, 0); }
        }

        .dock-disclaimer {
            font-size: 11.5px;
            color: var(--text-muted);
            text-align: center;
            letter-spacing: -0.1px;
        }

        /* Custom Scrollbars */
        ::-webkit-scrollbar {
            width: 6px;
            height: 6px;
        }
        ::-webkit-scrollbar-track {
            background: transparent;
        }
        ::-webkit-scrollbar-thumb {
            background: rgba(255, 255, 255, 0.12);
            border-radius: 4px;
        }
        ::-webkit-scrollbar-thumb:hover {
            background: rgba(255, 255, 255, 0.25);
        }

        @media (max-width: 768px) {
            .sidebar {
                position: absolute;
                top: 0;
                bottom: 0;
                left: 0;
                box-shadow: 10px 0 30px rgba(0,0,0,0.5);
            }
            .suggestions-grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>

    <!-- ================= SIDEBAR ================= -->
    <aside class="sidebar" id="sidebar">
        <div class="sidebar-header">
            <a href="/" class="sidebar-brand">
                <div class="brand-logo-icon">
                    <i data-lucide="sparkles" style="width:18px; height:18px;"></i>
                </div>
                <div>
                    <div class="brand-title">S.O.N.A.R AI</div>
                    <div class="brand-tag">Social Net Analyst</div>
                </div>
            </a>
            <button class="sidebar-collapse-btn" id="btn-collapse-sidebar" title="Tutup Sidebar">
                <i data-lucide="panel-left-close" style="width:18px; height:18px;"></i>
            </button>
        </div>

        <div class="new-chat-wrapper">
            <button class="btn-new-chat" onclick="startNewChat()">
                <i data-lucide="plus" style="width:18px; height:18px;"></i>
                <span>Obrolan Baru</span>
            </button>
        </div>

        <div class="history-section" id="history-list">
            <div class="history-label">Riwayat Analisis</div>
            <!-- Session Items Injected dynamically -->
        </div>

        <div class="sidebar-footer">
            <div class="status-pill">
                <span class="status-indicator">
                    <span class="status-dot" id="ollama-dot"></span>
                    <span id="ollama-text" style="color:var(--text-secondary);">Ollama Backend</span>
                </span>
                <span id="sidebar-model-badge" style="font-size:11px; color:var(--text-muted); font-weight:600;">""" + OLLAMA_MODEL + """</span>
            </div>
            <a href="/docs" target="_blank" class="footer-link-btn">
                <i data-lucide="book-open" style="width:15px; height:15px;"></i>
                <span>Dokumentasi API (Swagger)</span>
            </a>
        </div>
    </aside>

    <!-- ================= MAIN CHAT CANVAS ================= -->
    <main class="main-canvas" id="main-canvas">
        <!-- Canvas Top Header -->
        <header class="canvas-header">
            <div class="header-left">
                <button class="header-btn" id="btn-expand-sidebar" title="Buka Sidebar" style="display:none;">
                    <i data-lucide="panel-left-open" style="width:19px; height:19px;"></i>
                </button>
                <div class="model-select-wrapper" title="Ganti Model AI">
                    <i data-lucide="bot" class="model-select-icon"></i>
                    <select id="model-selector" class="model-select-dropdown" onchange="onModelChange(this.value)">
                        <option value="llama3.2:3b">Meta Llama 3.2 (3B)</option>
                        <option value="qwen2.5:3b">Qwen 2.5 (3B)</option>
                    </select>
                    <i data-lucide="chevron-down" class="model-select-arrow"></i>
                </div>
            </div>

            <div style="display:flex; align-items:center; gap:8px;">
                <button class="header-btn" onclick="startNewChat()" title="Obrolan Baru (Ctrl + Shift + O)">
                    <i data-lucide="square-pen" style="width:18px; height:18px;"></i>
                </button>
            </div>
        </header>

        <!-- Scrollable Chat View -->
        <div class="chat-scroll-area" id="chat-scroll-area">
            <div class="chat-content-container" id="chat-content-container">
                
                <!-- Zero State / Empty Banner -->
                <div class="zero-state" id="zero-state">
                    <div class="zero-icon-glow">
                        <i data-lucide="compass" style="width:32px; height:32px;"></i>
                    </div>
                    <h1 class="zero-title">Mau analisis isu media sosial apa hari ini?</h1>
                    <p class="zero-subtitle">
                        Investigasi sentimen publik, akar masalah keluhan pelanggan, dan rekomendasi respons mitigasi krisis komunikasi secara instan.
                    </p>

                    <div class="suggestions-grid">
                        <div class="prompt-card" onclick="sendSuggestion('Apa akar penyebab utama lonjakan keluhan transaksi QRIS yang timeout dan gagal belakangan ini?')">
                            <div class="prompt-card-icon">💳</div>
                            <div class="prompt-card-title">Isu Transaksi QRIS Gagal</div>
                            <div class="prompt-card-desc">Analisis faktor pemicu kegagalan payment gateway dan sentimen saldo terpotong.</div>
                        </div>

                        <div class="prompt-card" onclick="sendSuggestion('Bagaimana respon netizen terhadap update aplikasi v2.4 dan keluhan performa lag atau force close?')">
                            <div class="prompt-card-icon">📱</div>
                            <div class="prompt-card-title">Respon Update App v2.4</div>
                            <div class="prompt-card-desc">Review keluhan bug, crash, dan perubahan UX pasca pembaruan versi.</div>
                        </div>

                        <div class="prompt-card" onclick="sendSuggestion('Mengapa netizen banyak mengeluhkan respon Customer Service yang lambat dan jawaban bot yang berulang?')">
                            <div class="prompt-card-icon">🎧</div>
                            <div class="prompt-card-title">Analisis Komplain CS</div>
                            <div class="prompt-card-desc">Kajian waktu respon layanan pelanggan dan sentimen penanganan tiket kendala.</div>
                        </div>

                        <div class="prompt-card" onclick="sendSuggestion('Berikan rekomendasi rencana holding statement dan strategi mitigasi krisis komunikasi untuk meredakan komplain massal.')">
                            <div class="prompt-card-icon">🛡️</div>
                            <div class="prompt-card-title">Mitigasi Krisis Komunikasi</div>
                            <div class="prompt-card-desc">Rekomendasi pernyataan resmi dan mitigasi taktis lintas tim teknis & PR.</div>
                        </div>
                    </div>
                </div>

                <!-- Chat Messages Feed -->
                <div id="messages-feed" style="display:none; flex-direction:column; gap:24px;"></div>

            </div>
        </div>

        <!-- ================= SMART FLOATING INPUT BAR ================= -->
        <div class="input-dock">
            <div class="input-dock-inner">
                <div class="input-pill-container">
                    <button class="input-action-btn" title="Lampirkan Dokumen / Dataset CSV" onclick="alert('Dataset aktif: data/social_media_comments.csv')">
                        <i data-lucide="paperclip" style="width:18px; height:18px;"></i>
                    </button>
                    
                    <textarea 
                        id="chat-input" 
                        class="chat-textarea" 
                        placeholder="Ketik pertanyaan investigasi media sosial di sini... (Shift + Enter untuk baris baru)" 
                        rows="1"
                    ></textarea>

                    <button id="btn-send" class="btn-send-dock" title="Kirim Pesan (Enter)" onclick="handleSendClick()">
                        <i data-lucide="arrow-up" style="width:19px; height:19px;" id="send-icon"></i>
                    </button>
                </div>
                <div class="dock-disclaimer">
                    S.O.N.A.R dapat membuat kesalahan. Verifikasi data kritis media sosial Anda. Tekan <b>Ctrl+K</b> untuk fokus input.
                </div>
            </div>
        </div>
    </main>

    <!-- ================= JAVASCRIPT LOGIC ================= -->
    <script>
        // DOM Elements
        const sidebar = document.getElementById('sidebar');
        const btnCollapseSidebar = document.getElementById('btn-collapse-sidebar');
        const btnExpandSidebar = document.getElementById('btn-expand-sidebar');
        const chatInput = document.getElementById('chat-input');
        const btnSend = document.getElementById('btn-send');
        const sendIcon = document.getElementById('send-icon');
        const chatScrollArea = document.getElementById('chat-scroll-area');
        const zeroState = document.getElementById('zero-state');
        const messagesFeed = document.getElementById('messages-feed');
        const historyList = document.getElementById('history-list');

        // State Management
        let isStreaming = false;
        let currentAbortController = null;
        let activeSessionId = null;
        let sessions = [];
        let currentSelectedModel = localStorage.getItem('sonar_selected_model') || '""" + OLLAMA_MODEL + """';

        function onModelChange(newModel) {
            currentSelectedModel = newModel;
            localStorage.setItem('sonar_selected_model', newModel);
            updateModelBadges();
        }

        function updateModelBadges() {
            const selector = document.getElementById('model-selector');
            if (selector && selector.value !== currentSelectedModel) {
                selector.value = currentSelectedModel;
            }
            const sidebarBadge = document.getElementById('sidebar-model-badge');
            if (sidebarBadge) {
                sidebarBadge.textContent = currentSelectedModel;
            }
        }

        // Configure Marked with Highlight.js
        marked.setOptions({
            breaks: true,
            gfm: true,
            highlight: function(code, lang) {
                if (lang && hljs.getLanguage(lang)) {
                    return hljs.highlight(code, { language: lang }).value;
                }
                return hljs.highlightAuto(code).value;
            }
        });

        // Initialize Lucide Icons
        function refreshIcons() {
            if (window.lucide) {
                window.lucide.createIcons();
            }
        }

        // ================= SESSION & LOCALSTORAGE =================
        function loadSessionsFromStorage() {
            try {
                const stored = localStorage.getItem('sonar_sessions');
                sessions = stored ? JSON.parse(stored) : [];
            } catch (e) {
                sessions = [];
            }
        }

        function saveSessionsToStorage() {
            try {
                localStorage.setItem('sonar_sessions', JSON.stringify(sessions));
            } catch (e) {}
        }

        function getActiveSession() {
            return sessions.find(s => s.id === activeSessionId);
        }

        function renderSessionsList() {
            // Keep header label
            historyList.innerHTML = '<div class="history-label">Riwayat Analisis</div>';
            
            if (sessions.length === 0) {
                const emptyMsg = document.createElement('div');
                emptyMsg.style.cssText = 'font-size:12px; color:var(--text-muted); padding:10px; font-style:italic;';
                emptyMsg.textContent = 'Belum ada riwayat obrolan.';
                historyList.appendChild(emptyMsg);
                return;
            }

            sessions.forEach(sess => {
                const item = document.createElement('div');
                item.className = `history-item ${sess.id === activeSessionId ? 'active' : ''}`;
                item.onclick = (e) => {
                    if (e.target.closest('.history-btn')) return;
                    switchSession(sess.id);
                };

                const titleBox = document.createElement('div');
                titleBox.className = 'history-title';
                titleBox.innerHTML = `<i data-lucide="message-square" style="width:14px; height:14px; flex-shrink:0;"></i> <span>${escapeHtml(sess.title)}</span>`;

                const actionsBox = document.createElement('div');
                actionsBox.className = 'history-actions';

                const deleteBtn = document.createElement('button');
                deleteBtn.className = 'history-btn';
                deleteBtn.title = 'Hapus Obrolan';
                deleteBtn.innerHTML = '<i data-lucide="trash-2" style="width:13px; height:13px;"></i>';
                deleteBtn.onclick = (e) => {
                    e.stopPropagation();
                    deleteSession(sess.id);
                };

                actionsBox.appendChild(deleteBtn);
                item.appendChild(titleBox);
                item.appendChild(actionsBox);
                historyList.appendChild(item);
            });

            refreshIcons();
        }

        function switchSession(sessionId) {
            if (isStreaming) return;
            activeSessionId = sessionId;
            renderSessionsList();
            renderActiveSessionMessages();
        }

        function deleteSession(sessionId) {
            if (confirm('Hapus sesi obrolan ini?')) {
                sessions = sessions.filter(s => s.id !== sessionId);
                saveSessionsToStorage();
                if (activeSessionId === sessionId) {
                    activeSessionId = sessions.length > 0 ? sessions[0].id : null;
                }
                renderSessionsList();
                renderActiveSessionMessages();
            }
        }

        function startNewChat() {
            if (isStreaming && currentAbortController) {
                currentAbortController.abort();
            }
            activeSessionId = null;
            renderSessionsList();
            renderActiveSessionMessages();
            chatInput.value = '';
            autoResizeTextarea();
            chatInput.focus();
        }

        function renderActiveSessionMessages() {
            const current = getActiveSession();
            messagesFeed.innerHTML = '';

            if (!current || current.messages.length === 0) {
                zeroState.style.display = 'flex';
                messagesFeed.style.display = 'none';
            } else {
                zeroState.style.display = 'none';
                messagesFeed.style.display = 'flex';

                current.messages.forEach(msg => {
                    renderMessageBubble(msg.role, msg.content, false);
                });
                chatScrollArea.scrollTop = chatScrollArea.scrollHeight;
            }
            refreshIcons();
        }

        // ================= AUTO RESIZE TEXTAREA =================
        function autoResizeTextarea() {
            chatInput.style.height = 'auto';
            chatInput.style.height = Math.min(chatInput.scrollHeight, 200) + 'px';
            btnSend.disabled = !chatInput.value.trim() && !isStreaming;
        }

        chatInput.addEventListener('input', autoResizeTextarea);

        // Keyboard Shortcuts
        chatInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                if (!btnSend.disabled) {
                    handleSendClick();
                }
            }
        });

        window.addEventListener('keydown', (e) => {
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                chatInput.focus();
            }
        });

        // Sidebar Toggle
        btnCollapseSidebar.addEventListener('click', () => {
            sidebar.classList.add('collapsed');
            btnExpandSidebar.style.display = 'flex';
        });

        btnExpandSidebar.addEventListener('click', () => {
            sidebar.classList.remove('collapsed');
            btnExpandSidebar.style.display = 'none';
        });

        // ================= MESSAGE RENDERING =================
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        function renderMessageBubble(role, content, isStreamingBubble = false) {
            const turnRow = document.createElement('div');
            turnRow.className = `turn-row ${role}`;

            const avatarBox = document.createElement('div');
            avatarBox.className = 'avatar-box';

            if (role === 'assistant') {
                avatarBox.innerHTML = '<i data-lucide="sparkles" style="width:16px; height:16px;"></i>';
            } else {
                avatarBox.innerHTML = '<i data-lucide="user" style="width:16px; height:16px;"></i>';
            }

            const messageBody = document.createElement('div');
            messageBody.className = 'message-body';

            if (role === 'user') {
                const bubble = document.createElement('div');
                bubble.className = 'user-text-bubble';
                bubble.textContent = content;
                messageBody.appendChild(bubble);
            } else {
                const assistantContent = document.createElement('div');
                assistantContent.className = 'assistant-content';
                assistantContent.innerHTML = formatMarkdownWithCodeCopy(content);
                messageBody.appendChild(assistantContent);

                if (!isStreamingBubble) {
                    const actionBar = createMessageActionBar(content, assistantContent);
                    messageBody.appendChild(actionBar);
                }
            }

            turnRow.appendChild(avatarBox);
            turnRow.appendChild(messageBody);
            messagesFeed.appendChild(turnRow);
            refreshIcons();
            return { turnRow, messageBody };
        }

        function formatMarkdownWithCodeCopy(rawText) {
            if (!rawText) return '';
            let html = marked.parse(rawText);

            // Wrap <pre><code> into .code-container with copy button
            const temp = document.createElement('div');
            temp.innerHTML = html;

            temp.querySelectorAll('pre').forEach(pre => {
                const codeEl = pre.querySelector('code');
                const langClass = codeEl ? Array.from(codeEl.classList).find(c => c.startsWith('language-')) : null;
                const langName = langClass ? langClass.replace('language-', '') : 'CODE';

                const container = document.createElement('div');
                container.className = 'code-container';

                const header = document.createElement('div');
                header.className = 'code-header';
                header.innerHTML = `<span>${langName}</span><button class="copy-code-btn" onclick="copyCodeSnippet(this)"><i data-lucide="copy" style="width:13px; height:13px;"></i> Salin Kode</button>`;

                pre.parentNode.insertBefore(container, pre);
                container.appendChild(header);
                container.appendChild(pre);
            });

            return temp.innerHTML;
        }

        window.copyCodeSnippet = function(button) {
            const pre = button.closest('.code-container').querySelector('pre code');
            if (!pre) return;
            navigator.clipboard.writeText(pre.innerText).then(() => {
                const originalHtml = button.innerHTML;
                button.innerHTML = '<i data-lucide="check" style="width:13px; height:13px; color:#34d399;"></i> Tersalin!';
                refreshIcons();
                setTimeout(() => {
                    button.innerHTML = originalHtml;
                    refreshIcons();
                }, 2000);
            });
        };

        function createMessageActionBar(text, contentElement) {
            const bar = document.createElement('div');
            bar.className = 'message-action-bar';

            // Copy button
            const btnCopy = document.createElement('button');
            btnCopy.className = 'action-chip-btn';
            btnCopy.innerHTML = '<i data-lucide="copy" style="width:14px; height:14px;"></i> <span>Salin</span>';
            btnCopy.onclick = () => {
                navigator.clipboard.writeText(text).then(() => {
                    btnCopy.innerHTML = '<i data-lucide="check" style="width:14px; height:14px; color:#34d399;"></i> <span>Tersalin!</span>';
                    refreshIcons();
                    setTimeout(() => {
                        btnCopy.innerHTML = '<i data-lucide="copy" style="width:14px; height:14px;"></i> <span>Salin</span>';
                        refreshIcons();
                    }, 2000);
                });
            };

            // Regenerate button
            const btnRegen = document.createElement('button');
            btnRegen.className = 'action-chip-btn';
            btnRegen.innerHTML = '<i data-lucide="rotate-ccw" style="width:14px; height:14px;"></i> <span>Buat Ulang</span>';
            btnRegen.onclick = () => {
                const current = getActiveSession();
                if (current && current.messages.length >= 2) {
                    const lastUserMsg = [...current.messages].reverse().find(m => m.role === 'user');
                    if (lastUserMsg) {
                        chatInput.value = lastUserMsg.content;
                        handleSendClick();
                    }
                }
            };

            // Thumbs Up / Down
            const btnUp = document.createElement('button');
            btnUp.className = 'action-chip-btn';
            btnUp.innerHTML = '<i data-lucide="thumbs-up" style="width:14px; height:14px;"></i>';
            btnUp.onclick = () => {
                btnUp.classList.toggle('active');
                btnDown.classList.remove('active');
            };

            const btnDown = document.createElement('button');
            btnDown.className = 'action-chip-btn';
            btnDown.innerHTML = '<i data-lucide="thumbs-down" style="width:14px; height:14px;"></i>';
            btnDown.onclick = () => {
                btnDown.classList.toggle('active');
                btnUp.classList.remove('active');
            };

            bar.appendChild(btnCopy);
            bar.appendChild(btnRegen);
            bar.appendChild(btnUp);
            bar.appendChild(btnDown);
            return bar;
        }

        // ================= SENDING & STREAMING =================
        function sendSuggestion(text) {
            chatInput.value = text;
            autoResizeTextarea();
            handleSendClick();
        }

        function setStreamingState(streaming) {
            isStreaming = streaming;
            if (streaming) {
                btnSend.disabled = false;
                btnSend.classList.add('is-streaming');
                btnSend.title = 'Stop Generating (■)';
                btnSend.innerHTML = '<i data-lucide="square" style="width:16px; height:16px;"></i>';
            } else {
                btnSend.classList.remove('is-streaming');
                btnSend.title = 'Kirim Pesan (Enter)';
                btnSend.innerHTML = '<i data-lucide="arrow-up" style="width:19px; height:19px;"></i>';
                autoResizeTextarea();
            }
            refreshIcons();
        }

        async function handleSendClick() {
            if (isStreaming) {
                // User wants to STOP generating
                if (currentAbortController) {
                    currentAbortController.abort();
                }
                setStreamingState(false);
                return;
            }

            const query = chatInput.value.trim();
            if (!query) return;

            // Ensure Session exists
            let current = getActiveSession();
            if (!current) {
                const newId = 'sess_' + Date.now();
                current = {
                    id: newId,
                    title: query.length > 32 ? query.substring(0, 32) + '...' : query,
                    createdAt: new Date().toISOString(),
                    messages: []
                };
                sessions.unshift(current);
                activeSessionId = newId;
                saveSessionsToStorage();
                renderSessionsList();
            }

            // Append User Message to Session State
            current.messages.push({ role: 'user', content: query });
            saveSessionsToStorage();

            // Clear Input
            chatInput.value = '';
            autoResizeTextarea();

            // Switch to Chat View
            zeroState.style.display = 'none';
            messagesFeed.style.display = 'flex';

            // Render User Bubble
            renderMessageBubble('user', query);
            chatScrollArea.scrollTop = chatScrollArea.scrollHeight;

            // Create Placeholder for Assistant with Shimmer Indicator
            const turnRow = document.createElement('div');
            turnRow.className = 'turn-row assistant';

            const avatarBox = document.createElement('div');
            avatarBox.className = 'avatar-box';
            avatarBox.innerHTML = '<i data-lucide="sparkles" style="width:16px; height:16px;"></i>';

            const messageBody = document.createElement('div');
            messageBody.className = 'message-body';

            const thinkingBadge = document.createElement('div');
            thinkingBadge.className = 'thinking-indicator';
            thinkingBadge.innerHTML = `
                <div class="dot-flashing"><span></span><span></span><span></span></div>
                <span>S.O.N.A.R (${currentSelectedModel}) sedang memproses konteks...</span>
            `;
            messageBody.appendChild(thinkingBadge);

            const assistantContent = document.createElement('div');
            assistantContent.className = 'assistant-content';
            assistantContent.style.display = 'none';
            messageBody.appendChild(assistantContent);

            turnRow.appendChild(avatarBox);
            turnRow.appendChild(messageBody);
            messagesFeed.appendChild(turnRow);
            refreshIcons();
            chatScrollArea.scrollTop = chatScrollArea.scrollHeight;

            // Prepare SSE Stream
            setStreamingState(true);
            currentAbortController = new AbortController();
            let accumulatedText = '';

            try {
                // Prepare conversation history (exclude system)
                const historyPayload = current.messages.slice(0, -1).map(m => ({
                    role: m.role,
                    content: m.content
                }));

                const response = await fetch('/api/chat/stream', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        message: query,
                        history: historyPayload,
                        temperature: 0.2,
                        model: currentSelectedModel
                    }),
                    signal: currentAbortController.signal
                });

                if (!response.ok) {
                    throw new Error(`Server status ${response.status}`);
                }

                // Remove thinking indicator upon first stream
                thinkingBadge.remove();
                assistantContent.style.display = 'block';

                const reader = response.body.getReader();
                const decoder = new TextDecoder('utf-8');

                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;

                    const chunkStr = decoder.decode(value);
                    const lines = chunkStr.split('\\n');
                    for (const line of lines) {
                        if (line.startsWith('data: ')) {
                            const dataJson = line.substring(6).trim();
                            if (!dataJson) continue;
                            try {
                                const parsed = JSON.parse(dataJson);
                                if (parsed.content) {
                                    accumulatedText += parsed.content;
                                    assistantContent.innerHTML = formatMarkdownWithCodeCopy(accumulatedText);
                                    chatScrollArea.scrollTop = chatScrollArea.scrollHeight;
                                }
                            } catch (err) {}
                        }
                    }
                }

                // Streaming finished cleanly
                current.messages.push({ role: 'assistant', content: accumulatedText });
                saveSessionsToStorage();

                // Append Action Bar
                const actionBar = createMessageActionBar(accumulatedText, assistantContent);
                messageBody.appendChild(actionBar);
                refreshIcons();

            } catch (err) {
                if (err.name === 'AbortError') {
                    // Stopped by user
                    thinkingBadge.remove();
                    assistantContent.style.display = 'block';
                    if (accumulatedText) {
                        current.messages.push({ role: 'assistant', content: accumulatedText + '\\n\\n*(Respons dihentikan oleh pengguna)*' });
                        assistantContent.innerHTML = formatMarkdownWithCodeCopy(accumulatedText + '\\n\\n*(Respons dihentikan oleh pengguna)*');
                        saveSessionsToStorage();
                        const actionBar = createMessageActionBar(accumulatedText, assistantContent);
                        messageBody.appendChild(actionBar);
                        refreshIcons();
                    }
                } else {
                    thinkingBadge.remove();
                    assistantContent.style.display = 'block';
                    assistantContent.innerHTML = `<span style="color:#f87171;">⚠️ Gagal mendapatkan jawaban: ${err.message}. Pastikan backend FastAPI & Ollama aktif.</span>`;
                }
            } finally {
                setStreamingState(false);
                chatInput.focus();
            }
        }

        // ================= HEALTH CHECK =================
        async function checkBackendHealth() {
            const dot = document.getElementById('ollama-dot');
            const text = document.getElementById('ollama-text');
            const selector = document.getElementById('model-selector');
            try {
                const res = await fetch('/health');
                const data = await res.json();
                if (data.ollama_status === 'connected') {
                    dot.className = 'status-dot online';
                    text.textContent = 'Ollama Terhubung';

                    // Populate model options from backend if available
                    if (data.chat_models && data.chat_models.length > 0) {
                        const currentVal = currentSelectedModel;
                        selector.innerHTML = '';
                        data.chat_models.forEach(m => {
                            const opt = document.createElement('option');
                            opt.value = m;
                            let label = m;
                            if (m.includes('llama3.2')) label = 'Meta Llama 3.2 (3B)';
                            else if (m.includes('qwen2.5')) label = 'Qwen 2.5 (3B)';
                            opt.textContent = label;
                            selector.appendChild(opt);
                        });
                        if (data.chat_models.includes(currentVal)) {
                            selector.value = currentVal;
                        } else {
                            currentSelectedModel = data.chat_models[0];
                            selector.value = currentSelectedModel;
                        }
                    }
                } else {
                    dot.className = 'status-dot offline';
                    text.textContent = 'Ollama Terputus';
                }
            } catch (e) {
                dot.className = 'status-dot offline';
                text.textContent = 'Backend Offline';
            }
            updateModelBadges();
        }

        // Initialize App
        loadSessionsFromStorage();
        if (sessions.length > 0) {
            activeSessionId = sessions[0].id;
        }
        renderSessionsList();
        renderActiveSessionMessages();
        checkBackendHealth();
        autoResizeTextarea();
        refreshIcons();
    </script>
</body>
</html>
"""
    return HTMLResponse(content=html_content)
