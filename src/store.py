from __future__ import annotations

from typing import Any, Callable

from .chunking import _dot
from .embeddings import _mock_embed
from .models import Document


class EmbeddingStore:
    """
    A vector store for text chunks.

    Uses an in-memory store for the required lab exercises.
    The embedding_fn parameter allows injection of mock embeddings for tests.
    """

    def __init__(
        self,
        collection_name: str = "documents",
        embedding_fn: Callable[[str], list[float]] | None = None,
    ) -> None:
        self._embedding_fn = embedding_fn or _mock_embed
        self._collection_name = collection_name
        self._use_chroma = False
        self._store: list[dict[str, Any]] = []
        self._collection = None
        self._next_index = 0

    def _make_record(self, doc: Document) -> dict[str, Any]:
        # Build a normalized stored record for one document
        metadata_copy = dict(doc.metadata) if doc.metadata else {}
        if 'doc_id' not in metadata_copy:
            metadata_copy['doc_id'] = doc.id
        return {
            "id": doc.id,
            "content": doc.content,
            "metadata": metadata_copy,
            "embedding": self._embedding_fn(doc.content),
        }

    def _search_records(self, query: str, records: list[dict[str, Any]], top_k: int) -> list[dict[str, Any]]:
        if not records:
            return []
        
        query_embedding = self._embedding_fn(query)
        
        scored = []
        for record in records:
            score = _dot(query_embedding, record["embedding"])
            scored.append((score, record))
        
        scored.sort(key=lambda x: x[0], reverse=True)
        
        results = []
        for score, record in scored[:top_k]:
            result = {
                "id": record["id"],
                "content": record["content"],
                "metadata": record["metadata"],
                "score": score,
            }
            results.append(result)
        
        return results

    def add_documents(self, docs: list[Document]) -> None:
        """
        Embed each document's content and store it.

        Append embedded records to the in-memory store.
        """
        for doc in docs:
            record = self._make_record(doc)
            self._store.append(record)

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """
        Find the top_k most similar documents to query.

        For in-memory: compute dot product of query embedding vs all stored embeddings.
        """
        return self._search_records(query, self._store, top_k)

    def get_collection_size(self) -> int:
        """Return the total number of stored chunks."""
        return len(self._store)

    def search_with_filter(self, query: str, top_k: int = 3, metadata_filter: dict = None) -> list[dict]:
        """
        Search with optional metadata pre-filtering.

        First filter stored chunks by metadata_filter, then run similarity search.
        """
        if metadata_filter is None:
            return self.search(query, top_k)
        
        filtered_records = []
        for record in self._store:
            match = True
            for key, value in metadata_filter.items():
                if record["metadata"].get(key) != value:
                    match = False
                    break
            if match:
                filtered_records.append(record)
        
        return self._search_records(query, filtered_records, top_k)

    def delete_document(self, doc_id: str) -> bool:
        """
        Remove all chunks belonging to a document.

        Returns True if any chunks were removed, False otherwise.
        """
        initial_size = len(self._store)
        self._store = [
            record for record in self._store
            if record["metadata"].get("doc_id") != doc_id
        ]
        return len(self._store) < initial_size
