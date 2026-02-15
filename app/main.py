"""
PDF Chatbot - FastAPI application entry point.

Main functionality:
- Mounts document upload and chat API routers.
- Lifespan: creates uploads/ and data/ dirs on startup.
- Serves a simple info page at / and health at /health.
UI: run Streamlit with `streamlit run streamlit_app.py` or use `python run.py`.
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
        <p>Or run both with: <code>python run.py</code></p>
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
