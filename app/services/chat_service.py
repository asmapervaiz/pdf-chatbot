"""
Chat service: RAG (retrieve + generate) for answering questions from documents.

Main functionality:
- _get_context: embed question, search ChromaDB for top-k chunks; optional extra queries
  from question words/phrases to improve retrieval for policy-style Q&A.
- _answer_with_openai / _answer_with_hf: generate answer from context (OpenAI or FLAN-T5).
- answer: orchestrate context retrieval, LLM call, return answer and source excerpts.
"""

from typing import List, Optional

from app.services.embeddings_service import EmbeddingsService


class ChatService:
    """Generate answers by retrieving relevant chunks (RAG) then calling an LLM."""

    def __init__(
        self,
        embeddings_service: EmbeddingsService,
        top_k_chunks: int = 5,
        openai_api_key: Optional[str] = None,
        openai_model: str = "gpt-3.5-turbo",
        fallback_model: str = "google/flan-t5-base",
    ):
        self.embeddings = embeddings_service
        self.top_k = top_k_chunks
        self.openai_api_key = openai_api_key
        self.openai_model = openai_model
        self.fallback_model = fallback_model
        self._hf_pipeline = None

    def _get_context(self, question: str) -> str:
        """Retrieve relevant document chunks (semantic + keyword-style queries)."""
        chunks = self.embeddings.search(question, top_k=self.top_k)
        # Also search for key phrases so policy-style questions (e.g. "annual leave")
        # retrieve the right section even if wording differs
        words = [w.strip() for w in question.replace("?", "").lower().split() if len(w.strip()) > 2]
        extra_queries = [" ".join(words[:3])] if words else []
        for i in range(len(words) - 1):
            extra_queries.append(" ".join(words[i : i + 2]))
        for q in extra_queries[:3]:  # at most 3 extra queries
            if not q:
                continue
            for c in self.embeddings.search(q, top_k=3):
                if c not in chunks:
                    chunks.append(c)
        return "\n\n---\n\n".join(chunks) if chunks else ""

    def _answer_with_openai(self, question: str, context: str) -> str:
        """Use OpenAI API for answer generation."""
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.openai_api_key)
            system = (
                "You are a helpful assistant. Answer the user's question using the "
                "following context from uploaded documents. Use the context to give a "
                "direct, concise answer (e.g. numbers, names, dates). Only say the "
                "context does not contain the information if the answer truly cannot be "
                "found in the context. Prefer answering from the context when relevant."
            )
            user = f"Context:\n{context}\n\nQuestion: {question}"
            resp = client.chat.completions.create(
                model=self.openai_model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                max_tokens=500,
            )
            return (resp.choices[0].message.content or "").strip()
        except Exception as e:
            return f"[OpenAI error: {e}. Falling back to local model.]"

    def _answer_with_hf(self, question: str, context: str) -> str:
        """Use HuggingFace pipeline (e.g. FLAN-T5) for local answer generation."""
        if self._hf_pipeline is None:
            from transformers import pipeline
            self._hf_pipeline = pipeline(
                "text2text-generation",
                model=self.fallback_model,
                max_length=200,
            )
        # Ask for a short answer so the model extracts from context (e.g. "18" for annual leave)
        prompt = (
            f"Based on the context below, answer the question with a short, direct answer. "
            f"If the context does not have the answer, say 'Not in context.'\n\n"
            f"Context: {context[:2500]}\n\nQuestion: {question}\n\nAnswer:"
        )
        out = self._hf_pipeline(prompt, max_length=150, do_sample=False)
        return (out[0].get("generated_text") or "").strip()

    def answer(self, question: str) -> tuple[str, List[str]]:
        """
        Answer the user question using RAG.
        Returns (answer_text, list of source chunk excerpts).
        """
        context = self._get_context(question)
        if not context:
            n = self.embeddings.count()
            if n == 0:
                msg = "No documents have been uploaded yet, or the knowledge base is empty. Please upload a PDF first."
            else:
                msg = f"No relevant context found for your question (index has {n} chunks). Try rephrasing or ask something that matches the document content."
            return (msg, [])
        if self.openai_api_key:
            answer = self._answer_with_openai(question, context)
        else:
            answer = self._answer_with_hf(question, context)
        # Use first 100 chars of each chunk as "source" for UI
        chunks = self.embeddings.search(question, top_k=self.top_k)
        sources = [c[:150] + ("..." if len(c) > 150 else "") for c in chunks]
        return answer, sources
