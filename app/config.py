"""
Application configuration and environment settings.

Main functionality:
- Defines all config keys (API, document limits, embedding/LLM model names, paths).
- Loads from .env and environment variables via pydantic-settings.
- BASE_DIR / UPLOADS_DIR / VECTOR_STORE_PATH used for file and ChromaDB storage.
"""

from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings


# --- Base paths (project root, uploads folder, ChromaDB persistence)
BASE_DIR = Path(__file__).resolve().parent.parent
UPLOADS_DIR = BASE_DIR / "uploads"
DATA_DIR = BASE_DIR / "data"
VECTOR_STORE_PATH = DATA_DIR / "chroma_db"


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables and .env.
    Used by API, PDF service, embeddings service, and chat service.
    """

    # --- API
    app_name: str = "PDF Chatbot API"
    debug: bool = False

    # --- Document processing: max file size, allowed type, chunk size/overlap for RAG
    max_upload_size_mb: int = 20
    allowed_content_types: tuple = ("application/pdf",)
    chunk_size: int = 500
    chunk_overlap: int = 50

    # --- Embeddings: local model name; OpenAI model when OPENAI_API_KEY is set
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    openai_embedding_model: str = "text-embedding-3-small"
    top_k_chunks: int = 8

    # --- LLM: if OPENAI_API_KEY set, use OpenAI; else local HuggingFace FLAN-T5
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-3.5-turbo"
    fallback_model: str = "google/flan-t5-small"

    # --- Paths (override for Docker or custom deployment)
    uploads_dir: Path = UPLOADS_DIR
    vector_store_path: Path = VECTOR_STORE_PATH

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


def get_settings() -> Settings:
    """Return application settings (new instance per call; reads env each time)."""
    return Settings()
