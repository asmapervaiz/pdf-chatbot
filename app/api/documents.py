"""
Document upload API: accept PDF files and index them for the chatbot.
"""

from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.config import get_settings
from app.models.schemas import DocumentUploadResponse
from app.services.pdf_service import PDFService
from app.services.embeddings_service import get_embeddings_service

router = APIRouter(prefix="/documents", tags=["Documents"])


def get_pdf_service() -> PDFService:
    settings = get_settings()
    return PDFService(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """
    Upload a PDF document. Text is extracted, chunked, and indexed
    for the chatbot knowledge base.
    """
    settings = get_settings()
    # Accept PDF by content-type or by extension (browsers may send different MIME types)
    filename = (file.filename or "").lower()
    is_pdf_type = file.content_type in settings.allowed_content_types
    is_pdf_extension = filename.endswith(".pdf")
    if not is_pdf_type and not is_pdf_extension:
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are allowed.",
        )
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(contents) > max_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"File size exceeds {settings.max_upload_size_mb} MB limit.",
        )

    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
    safe_name = "".join(c for c in file.filename or "document.pdf" if c.isalnum() or c in "._- ") or "document"
    if not safe_name.lower().endswith(".pdf"):
        safe_name += ".pdf"
    file_path = settings.uploads_dir / safe_name
    file_path.write_bytes(contents)

    pdf_service = get_pdf_service()
    embeddings_service = get_embeddings_service()
    try:
        chunks, page_count = pdf_service.process_pdf(file_path)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to process PDF: {str(e)}")

    if not chunks:
        raise HTTPException(
            status_code=422,
            detail="No text could be extracted from the PDF.",
        )

    chunks_indexed = embeddings_service.add_chunks(
        chunks,
        metadata={"filename": file.filename or "document.pdf"},
    )
    return DocumentUploadResponse(
        message="Document uploaded and processed successfully",
        filename=file.filename or "document.pdf",
        pages_processed=page_count,
        chunks_indexed=chunks_indexed,
    )


@router.get("/status")
async def index_status():
    """Return how many chunks are in the index (for debugging / UI)."""
    embeddings = get_embeddings_service()
    return {"chunks_indexed": embeddings.count()}


@router.post("/clear")
async def clear_index():
    """
    Clear the document index (vector store). Use this before re-uploading
    if you want to apply updated chunking or start fresh.
    """
    embeddings_service = get_embeddings_service()
    embeddings_service.clear()
    return {"message": "Document index cleared. You can upload PDFs again."}
