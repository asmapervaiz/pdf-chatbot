"""
PDF Chatbot - Streamlit UI.

Main functionality:
- Sidebar: file uploader, "Upload & index" (POST /documents/upload), "Clear index" (POST /documents/clear).
- Main area: chat history (st.session_state.messages), st.chat_input for questions;
  each question is sent to POST /chat/ask and the answer + sources are appended.
- API_URL from env (default http://localhost:8000). Backend must be running first, or use python run.py.
"""

import os
import io
import streamlit as st
import httpx

API_URL = os.environ.get("API_URL", "http://localhost:8000").rstrip("/")

st.set_page_config(page_title="PDF Chatbot", page_icon="📄", layout="centered")
st.title("PDF Chatbot")
st.caption("Upload PDFs and ask questions — answers from your documents")

# Session state for chat history (list of {role, content, sources})
if "messages" not in st.session_state:
    st.session_state.messages = []


def upload_pdf(file):
    """POST file to /documents/upload. Returns (success, message). Uses BytesIO for httpx multipart."""
    if file is None:
        return False, "No file selected."
    try:
        raw = file.getvalue()
        if not raw or len(raw) == 0:
            return False, "File is empty or could not be read. Try selecting the file again."
        filename = file.name or "document.pdf"
        if not filename.lower().endswith(".pdf"):
            filename = filename + ".pdf"
        # httpx expects a file-like object for multipart, not raw bytes
        file_like = io.BytesIO(raw)
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(
                f"{API_URL}/documents/upload",
                files={"file": (filename, file_like, "application/pdf")},
            )
        data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
        if resp.status_code != 200:
            detail = data.get("detail", "Upload failed.")
            if isinstance(detail, list) and detail:
                detail = detail[0].get("msg", str(detail))
            return False, str(detail)
        return True, f'Uploaded "{data.get("filename", filename)}". {data.get("pages_processed", 0)} pages, {data.get("chunks_indexed", 0)} chunks indexed.'
    except httpx.ConnectError:
        return False, "Cannot reach API. Is the backend running? (uvicorn app.main:app --port 8000)"
    except Exception as e:
        return False, str(e)


def clear_index():
    """POST to /documents/clear. Returns (success, message)."""
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(f"{API_URL}/documents/clear")
        data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
        if resp.status_code != 200:
            return False, data.get("detail", "Failed to clear index.")
        return True, data.get("message", "Index cleared. You can upload PDFs again.")
    except httpx.ConnectError:
        return False, "Cannot reach API. Is the backend running?"
    except Exception as e:
        return False, str(e)


def ask_chat(question: str):
    """POST to /chat/ask with {question}. Returns (answer, sources) or (error_message, None) on error."""
    try:
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(
                f"{API_URL}/chat/ask",
                json={"question": question},
            )
        data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
        if resp.status_code != 200:
            return data.get("detail", "Something went wrong."), None
        return data.get("answer"), data.get("sources")
    except httpx.ConnectError:
        return "Cannot reach API. Is the backend running?", None
    except Exception as e:
        return str(e), None


# --- Sidebar: Upload & Clear ---
with st.sidebar:
    st.header("Documents")
    uploaded_file = st.file_uploader("Choose a PDF", type="pdf", accept_multiple_files=False)
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Upload & index", type="primary", use_container_width=True):
            if uploaded_file is not None:
                with st.spinner("Uploading and processing…"):
                    ok, msg = upload_pdf(uploaded_file)
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)
            else:
                st.warning("Select a PDF first.")
    with col2:
        if st.button("Clear index", use_container_width=True):
            with st.spinner("Clearing…"):
                ok, msg = clear_index()
            if ok:
                st.success(msg)
                if st.session_state.messages:
                    st.session_state.messages = []
                st.rerun()
            else:
                st.error(msg)
    st.divider()
    st.caption(f"API: `{API_URL}`")

# --- Main: Chat ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("sources"):
            with st.expander("Sources"):
                for s in msg["sources"]:
                    st.text(s[:500] + ("..." if len(s) > 500 else ""))

if prompt := st.chat_input("Ask a question about your document..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.spinner("Thinking…"):
        answer, sources = ask_chat(prompt)
    st.session_state.messages.append({
        "role": "assistant",
        "content": answer or "No answer.",
        "sources": sources or [],
    })
    st.rerun()
