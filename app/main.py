


"""
PDF Chatbot - FastAPI application entry point.

Main functionality:
- Mounts document upload and chat API routers.
- Lifespan: creates uploads/ and data/ dirs on startup.
- Serves a simple info page at / and health at /health.

Dev runner:
- Run backend only:
    python -m app.main --backend-only
- Run backend + Streamlit UI):
    python -m app.main
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from app.config import get_settings
from app.models.schemas import HealthResponse
from app.api import documents, chat


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ensure required directories (uploads, vector store) exist on startup."""
    settings = get_settings()
    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
    settings.vector_store_path.parent.mkdir(parents=True, exist_ok=True)
    yield


def create_app() -> FastAPI:
    """Create and configure the FastAPI application with all routes."""
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        description="Chatbot that answers questions using content from uploaded PDF documents.",
        version="1.0.0",
        lifespan=lifespan,
    )

    # Document upload (POST /documents/upload, GET /documents/status, POST /documents/clear)
    app.include_router(documents.router)
    # Chat (POST /chat/ask)
    app.include_router(chat.router)

    @app.get("/", include_in_schema=False, response_class=HTMLResponse)
    def root():
        """Serve a simple HTML page with instructions to run Streamlit UI."""
        return """
        <!DOCTYPE html>
        <html><head><meta charset="utf-8"><title>PDF Chatbot API</title></head>
        <body style="font-family:system-ui;max-width:40rem;margin:2rem auto;padding:0 1rem;">
        <h1>PDF Chatbot API</h1>
        <p>Backend is running. Use the <strong>Streamlit UI</strong> to upload PDFs and chat:</p>
        <pre style="background:#eee;padding:1rem;border-radius:6px;">streamlit run streamlit_app.py</pre>
        <p>Or run both with: <code>python -m app.main</code></p>
        <p>Then open <a href="http://localhost:8501">http://localhost:8501</a>.</p>
        <p><a href="/docs">API docs (OpenAPI)</a> &middot; <a href="/health">Health</a></p>
        </body></html>
        """

    @app.get("/health", response_model=HealthResponse)
    def health():
        """Health check endpoint for monitoring and load balancers."""
        return HealthResponse()

    return app


app = create_app()

# ----------------------------
# Dev runner (replaces run.py)
# ----------------------------
def _run_dev_launcher():
    """
    Starts:
      - Uvicorn backend in a daemon thread
      - Streamlit UI as a subprocess
    Similar to the old run.py, but lives in this module.
    """
    import atexit
    import os
    import subprocess
    import sys
    import threading
    import time
    from pathlib import Path

    ROOT = Path(__file__).resolve().parents[1]  # project root (contains streamlit_app.py)
    os.chdir(ROOT)
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    backend_host = os.getenv("BACKEND_HOST", "0.0.0.0")
    backend_port = int(os.getenv("BACKEND_PORT", "8000"))
    ui_port = int(os.getenv("UI_PORT", "8501"))

    streamlit_proc = None

    def run_backend():
        import uvicorn
        uvicorn.run(
            "app.main:app",
            host=backend_host,
            port=backend_port,
            log_level="info",
        )

    def kill_streamlit():
        nonlocal streamlit_proc
        if streamlit_proc and streamlit_proc.poll() is None:
            streamlit_proc.terminate()
            try:
                streamlit_proc.wait(timeout=3)
            except Exception:
                streamlit_proc.kill()
        streamlit_proc = None

    # Precheck streamlit installed (friendlier error)
    try:
        import streamlit  # noqa: F401
    except ImportError:
        print("Streamlit is not installed. Run: pip install streamlit")
        print("Or install all deps: pip install -r requirements.txt")
        raise SystemExit(1)

    backend_thread = threading.Thread(target=run_backend, daemon=True)
    backend_thread.start()

    time.sleep(1.5)
    if not backend_thread.is_alive():
        print(f"Backend failed to start (port {backend_port} may be in use).")
        raise SystemExit(1)

    streamlit_proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            "streamlit_app.py",
            "--server.port",
            str(ui_port),
            "--server.headless",
            "true",
        ],
        cwd=str(ROOT),
    )

    atexit.register(kill_streamlit)

    # Best-effort signal handling (mirrors old run.py)
    try:
        import signal

        def _shutdown(_sig, _frame):
            kill_streamlit()
            raise SystemExit(0)

        signal.signal(signal.SIGINT, _shutdown)
        signal.signal(signal.SIGTERM, _shutdown)
    except Exception:
        pass

    print(f"Backend: http://localhost:{backend_port}  |  UI: http://localhost:{ui_port}")
    streamlit_proc.wait()
    kill_streamlit()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="PDF Chatbot dev runner")
    parser.add_argument(
        "--backend-only",
        action="store_true",
        help="Run only the FastAPI backend (no Streamlit).",
    )
    args = parser.parse_args()

    if args.backend_only:
        import os
        import uvicorn

        host = os.getenv("BACKEND_HOST", "0.0.0.0")
        port = int(os.getenv("BACKEND_PORT", "8000"))
        uvicorn.run("app.main:app", host=host, port=port, log_level="info")
    else:
        _run_dev_launcher()
