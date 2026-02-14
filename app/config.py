"""
Application configuration and environment settings.
"""

import os
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings


# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
UPLOADS_DIR = BASE_DIR / "uploads"
DATA_DIR = BASE_DIR / "data"
VECTOR_STORE_PATH = DATA_DIR / "chroma_db"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # API
    app_name: str = "PDF Chatbot API"
    debug: bool = False

    # Document processing
    max_upload_size_mb: int = 20
    allowed_content_types: tuple = ("application/pdf",)
    chunk_size: int = 500
    chunk_overlap: int = 50

    # Embeddings & NLP
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    openai_embedding_model: str = "text-embedding-3-small"
    top_k_chunks: int = 8

    # LLM (optional: set OPENAI_API_KEY for OpenAI, else uses local HuggingFace model)
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-3.5-turbo"
    fallback_model: str = "google/flan-t5-small"

    # Paths (override for Docker)
    uploads_dir: Path = UPLOADS_DIR
    vector_store_path: Path = VECTOR_STORE_PATH

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


def get_settings() -> Settings:
    """Return application settings singleton."""
    return Settings()
