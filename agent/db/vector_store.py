from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, Distance, VectorParams
import uuid
from typing import List, Dict, Any, Optional

class VectorStore:
    def __init__(self, persistence_path: str = "./agent_qdrant_db", collection_name: str = "agent_records"):
        self.client = QdrantClient(path=persistence_path)
        self.collection_name = collection_name
        self._ensure_collection()

    def _ensure_collection(self):
        # We need to know the dimension of nomic-embed-text. It's 768.
        # Ideally this is configurable or dynamic, but hardcoding for the specific model is fine for MVP.
        if not self.client.collection_exists(self.collection_name):
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=768, distance=Distance.COSINE),
            )

    def add_record(self, record_id: str, text: str, embedding: List[float], metadata: Dict[str, Any] = None):
        if not embedding:
            return
            
        if metadata is None:
            metadata = {}
        
        # Add text to payload for retrieval
        payload = metadata.copy()
        payload["page_content"] = text

        self.client.upsert(
            collection_name=self.collection_name,
            points=[
                PointStruct(
                    id=record_id, # Qdrant supports UUID strings directly
                    vector=embedding,
                    payload=payload
                )
            ]
        )

    def search(self, query_embedding: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        if not query_embedding:
            return []
            
        search_result = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=top_k
        )
        
        # Format results
        hits = []
        for hit in search_result:
            hits.append({
                "record_id": hit.id,
                "score": hit.score,
                "metadata": hit.payload,
                "text": hit.payload.get("page_content", "")
            })
        return hits
    
    def delete_record(self, record_id: str):
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=[record_id]
        )
