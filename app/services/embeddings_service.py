"""
Embeddings and vector store for semantic search over document chunks.

Main functionality:
- add_chunks: embed text chunks (OpenAI or sentence-transformers), store in ChromaDB.
- search: embed query, run similarity search, return top-k chunk texts.
- count / clear: for status and reset. Uses a single shared instance (get_embeddings_service)
  so upload and chat use the same collection. Separate collection name for OpenAI (1536-dim)
  vs local (384-dim) to avoid dimension mismatch.
"""

from pathlib import Path
from typing import List, Optional

import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer


# Batch size for OpenAI embedding API (avoids token limits)
OPENAI_EMBED_BATCH_SIZE = 100


class EmbeddingsService:
    """Manage document embeddings and ChromaDB vector store (add, search, count, clear)."""

    def __init__(
        self,
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
        persist_directory: Path = None,
        collection_name: str = "pdf_chunks",
        openai_api_key: Optional[str] = None,
        openai_embedding_model: str = "text-embedding-3-small",
    ):
        self.embedding_model_name = embedding_model
        self.openai_api_key = openai_api_key
        self.openai_embedding_model = openai_embedding_model
        self._model: SentenceTransformer | None = None
        self._client: chromadb.PersistentClient | None = None
        self._collection = None
        self.persist_directory = Path(persist_directory) if persist_directory else None
        # Use separate collections per embedding dim (384 local vs 1536 OpenAI) to avoid dimension mismatch
        self.collection_name = "pdf_chunks_openai" if openai_api_key else collection_name

    def _use_openai(self) -> bool:
        return bool(self.openai_api_key)

    @property
    def model(self) -> SentenceTransformer:
        """Lazy-load the sentence transformer model (used when not using OpenAI)."""
        if self._model is None:
            self._model = SentenceTransformer(self.embedding_model_name)
        return self._model

    def _embed_openai(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings from OpenAI text-embedding-3-small."""
        from openai import OpenAI
        client = OpenAI(api_key=self.openai_api_key)
        all_embeddings = []
        for i in range(0, len(texts), OPENAI_EMBED_BATCH_SIZE):
            batch = texts[i : i + OPENAI_EMBED_BATCH_SIZE]
            resp = client.embeddings.create(
                model=self.openai_embedding_model,
                input=batch,
            )
            batch_embeddings = [e.embedding for e in sorted(resp.data, key=lambda x: x.index)]
            all_embeddings.extend(batch_embeddings)
        return all_embeddings

    def _get_client(self) -> chromadb.PersistentClient:
        """Get or create ChromaDB persistent client."""
        if self._client is None:
            path = str(self.persist_directory) if self.persist_directory else None
            if path:
                self.persist_directory.mkdir(parents=True, exist_ok=True)
            self._client = chromadb.PersistentClient(
                path=path or "./chroma_db",
                settings=ChromaSettings(anonymized_telemetry=False),
            )
        return self._client

    @property
    def collection(self):
        """Get or create the document chunks collection."""
        if self._collection is None:
            client = self._get_client()
            self._collection = client.get_or_create_collection(
                name=self.collection_name,
                metadata={"description": "PDF document chunks for RAG"},
            )
        return self._collection

    def _encode(self, texts: List[str]):
        """Return list of embedding vectors (OpenAI or local)."""
        if self._use_openai():
            return self._embed_openai(texts)
        emb = self.model.encode(texts, show_progress_bar=False)
        return emb.tolist() if hasattr(emb, "tolist") else list(emb)

    def add_chunks(self, chunks: List[str], metadata: dict | None = None) -> int:
        """
        Embed and add text chunks to the vector store.
        Returns the number of chunks added.
        """
        if not chunks:
            return 0
        embeddings = self._encode(chunks)
        ids = [f"chunk_{i}_{id(hash(c)) % 10**8}" for i, c in enumerate(chunks)]
        meta = metadata or {}
        metadatas = [dict(meta) for _ in chunks]
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=chunks,
            metadatas=metadatas,
        )
        return len(chunks)

    def search(self, query: str, top_k: int = 5) -> List[str]:
        """
        Return the top_k most relevant chunk texts for the query.
        """
        query_embedding = self._encode([query])
        results = self.collection.query(
            query_embeddings=query_embedding,
            n_results=min(top_k, self.collection.count() or 1),
            include=["documents"],
        )
        docs = results.get("documents", [[]])
        return list(docs[0]) if docs else []

    def count(self) -> int:
        """Return number of chunks in the collection."""
        return self.collection.count()

    def clear(self) -> None:
        """Remove all chunks (e.g. for fresh re-indexing)."""
        client = self._get_client()
        client.delete_collection(name=self.collection_name)
        self._collection = None


# Single shared instance so upload and chat always use the same ChromaDB collection
_embeddings_service: Optional[EmbeddingsService] = None


def get_embeddings_service() -> EmbeddingsService:
    """Return the shared EmbeddingsService (same store for upload and chat)."""
    global _embeddings_service
    if _embeddings_service is None:
        from app.config import get_settings
        s = get_settings()
        _embeddings_service = EmbeddingsService(
            embedding_model=s.embedding_model,
            persist_directory=s.vector_store_path,
            openai_api_key=s.openai_api_key,
            openai_embedding_model=s.openai_embedding_model,
        )
    return _embeddings_service
