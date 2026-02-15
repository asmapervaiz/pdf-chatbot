"""
Embeddings and vector store for semantic search over document chunks.

Main functionality:
- add_chunks: embed text chunks using OpenAI embeddings and store in ChromaDB.
- search: embed query using OpenAI, run similarity search, return top-k chunk texts.
- count / clear: for status and reset.

Uses a single shared instance (get_embeddings_service)
so upload and chat use the same OpenAI-based collection (1536-dim).
"""



from pathlib import Path
from typing import List, Optional

import chromadb
from chromadb.config import Settings as ChromaSettings
from openai import OpenAI


OPENAI_EMBED_BATCH_SIZE = 100


class EmbeddingsService:
    """Manage document embeddings using OpenAI + ChromaDB."""

    def __init__(
        self,
        persist_directory: Path = None,
        collection_name: str = "pdf_chunks_openai",
        openai_api_key: Optional[str] = None,
        openai_embedding_model: str = "text-embedding-3-small",
    ):
        if not openai_api_key:
            raise ValueError("OpenAI API key is required.")

        self.openai_api_key = openai_api_key
        self.openai_embedding_model = openai_embedding_model
        self._client: chromadb.PersistentClient | None = None
        self._collection = None
        self.persist_directory = Path(persist_directory) if persist_directory else None
        self.collection_name = collection_name

        # Initialize OpenAI client once
        self.openai_client = OpenAI(api_key=self.openai_api_key)

    def _embed(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings from OpenAI."""
        all_embeddings = []

        for i in range(0, len(texts), OPENAI_EMBED_BATCH_SIZE):
            batch = texts[i : i + OPENAI_EMBED_BATCH_SIZE]

            resp = self.openai_client.embeddings.create(
                model=self.openai_embedding_model,
                input=batch,
            )

            batch_embeddings = [
                e.embedding for e in sorted(resp.data, key=lambda x: x.index)
            ]
            all_embeddings.extend(batch_embeddings)

        return all_embeddings

    def _get_client(self) -> chromadb.PersistentClient:
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
        if self._collection is None:
            client = self._get_client()
            self._collection = client.get_or_create_collection(
                name=self.collection_name,
                metadata={"description": "PDF document chunks for RAG"},
            )
        return self._collection

    def add_chunks(self, chunks: List[str], metadata: dict | None = None) -> int:
        if not chunks:
            return 0

        embeddings = self._embed(chunks)

        ids = [f"chunk_{i}_{abs(hash(c)) % 10**8}" for i, c in enumerate(chunks)]
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
        query_embedding = self._embed([query])

        results = self.collection.query(
            query_embeddings=query_embedding,
            n_results=min(top_k, self.collection.count() or 1),
            include=["documents"],
        )

        docs = results.get("documents", [[]])
        return list(docs[0]) if docs else []

    def count(self) -> int:
        return self.collection.count()

    def clear(self) -> None:
        client = self._get_client()
        client.delete_collection(name=self.collection_name)
        self._collection = None


# Shared instance
_embeddings_service: Optional[EmbeddingsService] = None


def get_embeddings_service() -> EmbeddingsService:
    global _embeddings_service

    if _embeddings_service is None:
        from app.config import get_settings
        s = get_settings()

        _embeddings_service = EmbeddingsService(
            persist_directory=s.vector_store_path,
            openai_api_key=s.openai_api_key,
            openai_embedding_model=s.openai_embedding_model,
        )

    return _embeddings_service