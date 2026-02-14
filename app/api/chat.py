"""
Chat API: submit questions and receive answers from the document knowledge base.
"""

from fastapi import APIRouter

from app.config import get_settings
from app.models.schemas import ChatRequest, ChatResponse
from app.services.embeddings_service import get_embeddings_service
from app.services.chat_service import ChatService

router = APIRouter(prefix="/chat", tags=["Chat"])


def get_chat_service() -> ChatService:
    settings = get_settings()
    return ChatService(
        embeddings_service=get_embeddings_service(),
        top_k_chunks=settings.top_k_chunks,
        openai_api_key=settings.openai_api_key,
        openai_model=settings.openai_model,
        fallback_model=settings.fallback_model,
    )


@router.post("/ask", response_model=ChatResponse)
async def ask(request: ChatRequest):
    """
    Send a question to the chatbot. The answer is generated using
    the indexed document content (RAG) and NLP/AI models.
    """
    chat = get_chat_service()
    answer, sources = chat.answer(request.question)
    return ChatResponse(answer=answer, sources=sources if sources else None)
