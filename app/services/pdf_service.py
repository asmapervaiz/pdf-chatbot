"""
PDF text extraction and chunking for the chatbot knowledge base.
"""

import re
from pathlib import Path
from typing import List

import fitz  # PyMuPDF


class PDFService:
    """Extract and chunk text from PDF documents."""

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def extract_text(self, file_path: Path) -> tuple[str, int]:
        """
        Extract raw text from a PDF file.
        Returns (full_text, number_of_pages).
        """
        doc = fitz.open(file_path)
        pages = []
        for page in doc:
            text = page.get_text()
            pages.append(text)
        doc.close()
        full_text = "\n\n".join(pages)
        return full_text.strip(), len(pages)

    def _normalize_whitespace(self, text: str) -> str:
        """Normalize multiple spaces to one; preserve paragraph breaks (double newline)."""
        if not text:
            return ""
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def chunk_text(self, text: str) -> List[str]:
        """
        Split text into overlapping chunks. Uses paragraph boundaries first so
        policy/list content (e.g. "Leave Entitlement", "18 Annual Leaves") stays
        together in focused chunks for better retrieval.
        """
        text = self._normalize_whitespace(text)
        if not text:
            return []

        # Split into paragraphs (double newline) so sections stay together
        raw_paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        if not raw_paras:
            return []

        # If no paragraph breaks, fall back to sentence split
        if len(raw_paras) == 1:
            sentences = re.split(r"(?<=[.!?])\s+", raw_paras[0])
            raw_paras = [s for s in sentences if s.strip()]

        chunks = []
        current = []
        current_len = 0

        for para in raw_paras:
            para_len = len(para) + 2  # +2 for "\n\n"
            if current_len + para_len > self.chunk_size and current:
                chunk = "\n\n".join(current)
                chunks.append(chunk)
                # Overlap: keep last paragraphs that fit in overlap
                overlap_len = 0
                overlap_paras = []
                for p in reversed(current):
                    if overlap_len + len(p) + 2 <= self.chunk_overlap:
                        overlap_paras.insert(0, p)
                        overlap_len += len(p) + 2
                    else:
                        break
                current = overlap_paras
                current_len = sum(len(p) + 2 for p in current)
            current.append(para)
            current_len += para_len

        if current:
            chunks.append("\n\n".join(current))
        return chunks

    def process_pdf(self, file_path: Path) -> tuple[List[str], int]:
        """
        Extract text from PDF and return chunked paragraphs and page count.
        Returns (chunks, page_count).
        """
        full_text, page_count = self.extract_text(file_path)
        chunks = self.chunk_text(full_text)
        return chunks, page_count
