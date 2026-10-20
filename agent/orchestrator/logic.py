from sqlalchemy.orm import Session
from typing import Any, Dict, List, Optional
import uuid
import json
import shutil
import os

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

    def drop_property(self, db_id: uuid.UUID, prop_name: str) -> bool:
        """Drop/delete a property (column) from a database."""
        success = db_service.delete_property(self.db_session, db_id, prop_name)
        if success:
            projection.write_db_page(self.db_session, db_id)
        return success

    def rename_property(self, db_id: uuid.UUID, old_name: str, new_name: str):
        """Rename a property in a database."""
        prop = db_service.rename_property(self.db_session, db_id, old_name, new_name)
        if prop:
            projection.write_db_page(self.db_session, db_id)
        return prop

    def list_properties(self, db_id: uuid.UUID):
        """List all properties (columns) in a database."""
        return db_service.list_properties(self.db_session, db_id)

    def edit_record(self, record_id: uuid.UUID, data: Dict[str, Any]):
        """Merge new data into an existing record, update embedding and projection."""
        record = db_service.get_record(self.db_session, record_id)
        if not record:
            raise ValueError(f"Record '{record_id}' not found")

        merged = record.data.copy() if record.data else {}
        merged.update(data)
        db_service.update_record(self.db_session, record_id, merged)

        # Re-embed
        text_repr = "\n".join([f"{k}: {v}" for k, v in merged.items()])
        embedding = self.embeddings_service.embed_text(text_repr)
        if embedding:
            self.vector_store.add_record(
                record_id=str(record_id),
                text=text_repr,
                embedding=embedding,
                metadata={"db_id": str(record.db_id)}
            )

        projection.write_db_page(self.db_session, record.db_id)
        return record

    def delete_record(self, db_id: uuid.UUID, record_id: uuid.UUID) -> bool:
        """Delete a record from SQL + vector store, re-project."""
        # Remove from vector store (ignore errors if not found)
        try:
            self.vector_store.delete_record(str(record_id))
        except Exception:
            pass

        success = db_service.delete_record(self.db_session, record_id)
        if success:
            projection.write_db_page(self.db_session, db_id)
        return success

    def delete_database(self, db_id: uuid.UUID) -> bool:
        """Delete a database, clean vector store entries, remove projection folder."""
        db_obj = db_service.get_database(self.db_session, db_id)
        if not db_obj:
            return False

        db_name = db_obj.name

        # Clean vector store entries for all records in this database
        records = db_service.list_records(self.db_session, db_id)
        for r in records:
            try:
                self.vector_store.delete_record(str(r.id))
            except Exception:
                pass

        # Delete from SQL (cascade handles properties, records, embeddings)
        db_service.delete_database(self.db_session, db_id)

        # Remove projection folder
        folder = os.path.join(projection.APPFLOWY_DB_FOLDER, db_name)
        if os.path.exists(folder):
            shutil.rmtree(folder)

        return True

