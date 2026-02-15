"""
API request/response schemas (Pydantic models).

Main functionality: define request/response shapes for /health, /documents/upload,
/chat/ask (ChatRequest, ChatResponse), and DocumentUploadResponse for validation and OpenAPI.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "ok"
    message: str = "PDF Chatbot API is running"


class DocumentUploadResponse(BaseModel):
    """Response after successful PDF upload."""

    message: str = "Document uploaded and processed successfully"
    filename: str
    pages_processed: int
    chunks_indexed: int


class ChatRequest(BaseModel):
    """Incoming chat message from the user."""

    question: str = Field(..., min_length=1, max_length=2000)
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    """Chatbot reply with optional sources."""

    answer: str
    sources: Optional[List[str]] = None
