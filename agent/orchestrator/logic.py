from sqlalchemy.orm import Session
from typing import Any, Dict, List, Optional
import uuid
import json

from agent.db import service as db_service
from agent.orchestrator.embeddings import EmbeddingsService
from agent.db.vector_store import VectorStore
from agent.db.models import Record
from agent.templates.definitions import get_template, list_templates
from agent.orchestrator import projection

class AgentLogic:
    def __init__(self, db_session: Session, vector_store: VectorStore = None):
        self.db_session = db_session
        self.embeddings_service = EmbeddingsService()
        self.vector_store = vector_store if vector_store else VectorStore()

    def apply_template(self, template_name: str, db_name: Optional[str] = None):
        template = get_template(template_name)
        if not template:
            raise ValueError(f"Template '{template_name}' not found.")
            
        final_db_name = db_name if db_name else template["name"]
        
        # Create DB
        db_obj = self.create_database(final_db_name, template.get("description"))
        
        # Add properties
        for prop in template["properties"]:
            self.add_property(
                db_id=db_obj.id,
                name=prop["name"],
                type=prop["type"],
                options=prop.get("options")
            )
            
        # 3. Project to AppFlowy
        projection.write_db_page(self.db_session, db_obj.id)
            
        return db_obj

    def list_templates(self) -> List[str]:
        return list_templates()

    def create_database(self, name: str, description: Optional[str] = None):
        db_obj = db_service.create_database(self.db_session, name, description)
        projection.write_db_page(self.db_session, db_obj.id)
        return db_obj

    def add_property(self, db_id: uuid.UUID, name: str, type: str, options: Optional[Any] = None):
        prop = db_service.add_property(self.db_session, db_id, name, type, options)
        projection.write_db_page(self.db_session, db_id)
        return prop

    def create_record(self, db_id: uuid.UUID, data: Dict[str, Any]):
        # 1. Create record in SQL
        record = db_service.create_record(self.db_session, db_id, data)
        
        # 2. Generate text representation for embedding
        # Naive approach: JSON dump of data
        # Better approach: "Name: Value, Prop: Value"
        text_repr = "\n".join([f"{k}: {v}" for k, v in data.items()])
        
        # 3. Generate Embedding
        embedding = self.embeddings_service.embed_text(text_repr)
        
        # 4. Store in Vector DB
        if embedding:
            # Metadata for filtering?
            metadata = {"db_id": str(db_id)}
            self.vector_store.add_record(
                record_id=str(record.id),
                text=text_repr,
                embedding=embedding,
                metadata=metadata
            )
            
            # 5. Store in SQL Embedding table (optional reference)
            db_service.create_embedding(self.db_session, record.id, text_repr)
            
        # 6. Project to AppFlowy
        projection.write_db_page(self.db_session, db_id)
            
        return record

    def semantic_search(self, query: str, limit: int = 5):
        query_embedding = self.embeddings_service.embed_query(query)
        results = self.vector_store.search(query_embedding, top_k=limit)
        return results
