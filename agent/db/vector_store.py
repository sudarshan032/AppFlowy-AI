"""
Vector Store — Qdrant Integration

Supports both local file-based Qdrant (dev) and remote Docker Qdrant (production).
"""

import os
import uuid
from typing import List, Dict, Any, Optional

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, Distance, VectorParams, Filter, FieldCondition, MatchValue


class VectorStore:
    """Qdrant vector database wrapper with support for local and remote modes."""

    def __init__(
        self,
        url: Optional[str] = None,
        persistence_path: Optional[str] = None,
        collection_name: str = "agent_records"
    ):
        self.collection_name = collection_name
        qdrant_url = url or os.getenv("QDRANT_URL")

        if qdrant_url:
            # Remote Qdrant (Docker)
            self.client = QdrantClient(url=qdrant_url, timeout=30)
        else:
            # Local file-based Qdrant (development)
            path = persistence_path or os.getenv("QDRANT_PATH", "./agent_qdrant_db")
            self.client = QdrantClient(path=path)

        self._ensure_collection()

    def _ensure_collection(self, dimension: int = 768):
        """Create collection if it doesn't exist. nomic-embed-text = 768 dims."""
        try:
            if not self.client.collection_exists(self.collection_name):
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=dimension, distance=Distance.COSINE),
                )
        except Exception:
            # Collection may already exist or Qdrant not yet ready
            pass

    def ensure_collection(self, name: str, dimension: int = 768):
        """Create a named collection (for multi-collection support)."""
        try:
            if not self.client.collection_exists(name):
                self.client.create_collection(
                    collection_name=name,
                    vectors_config=VectorParams(size=dimension, distance=Distance.COSINE),
                )
        except Exception:
            pass

    def add_record(
        self,
        record_id: str,
        text: str,
        embedding: List[float],
        metadata: Optional[Dict[str, Any]] = None,
        collection_name: Optional[str] = None
    ):
        """Add or update a record in the vector store."""
        if not embedding:
            return

        payload = (metadata or {}).copy()
        payload["page_content"] = text

        col = collection_name or self.collection_name
        self.client.upsert(
            collection_name=col,
            points=[
                PointStruct(
                    id=record_id,
                    vector=embedding,
                    payload=payload
                )
            ]
        )

    def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        collection_name: Optional[str] = None,
        filter_conditions: Optional[Dict[str, str]] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar records by embedding vector."""
        if not query_embedding:
            return []

        col = collection_name or self.collection_name

        # Build filter if conditions provided
        search_filter = None
        if filter_conditions:
            conditions = [
                FieldCondition(key=k, match=MatchValue(value=v))
                for k, v in filter_conditions.items()
            ]
            search_filter = Filter(must=conditions)

        search_result = self.client.query_points(
            collection_name=col,
            query=query_embedding,
            limit=top_k,
            query_filter=search_filter,
        )

        hits = []
        for hit in search_result.points:
            hits.append({
                "record_id": hit.id,
                "score": hit.score,
                "metadata": hit.payload,
                "text": hit.payload.get("page_content", "")
            })
        return hits

    def delete_record(self, record_id: str, collection_name: Optional[str] = None):
        """Delete a record from the vector store."""
        col = collection_name or self.collection_name
        self.client.delete(
            collection_name=col,
            points_selector=[record_id]
        )

    def count(self, collection_name: Optional[str] = None) -> int:
        """Get the number of records in the collection."""
        col = collection_name or self.collection_name
        try:
            info = self.client.get_collection(col)
            return info.points_count
        except Exception:
            return 0

    def health_check(self) -> bool:
        """Check if Qdrant is reachable."""
        try:
            self.client.get_collections()
            return True
        except Exception:
            return False
