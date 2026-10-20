from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import List, Optional, Any
import uuid

from .models import Database, Property, Record, Embedding, Page

def create_database(session: Session, name: str, description: Optional[str] = None) -> Database:
    db = Database(name=name, description=description)
    session.add(db)
    session.commit()
    session.refresh(db)
    return db

def get_database(session: Session, db_id: uuid.UUID) -> Optional[Database]:
    return session.get(Database, db_id)

def get_database_by_name(session: Session, name: str) -> Optional[Database]:
    stmt = select(Database).where(Database.name == name)
    return session.scalar(stmt)

def list_records(session: Session, db_id: uuid.UUID) -> List[Record]:
    stmt = select(Record).where(Record.db_id == db_id)
    return list(session.scalars(stmt))

def add_property(session: Session, db_id: uuid.UUID, name: str, type: str, options: Optional[Any] = None, required: bool = False) -> Property:
    prop = Property(db_id=db_id, name=name, type=type, options=options, required=required)
    session.add(prop)
    session.commit()
    session.refresh(prop)
    return prop

def create_record(session: Session, db_id: uuid.UUID, data: Any) -> Record:
    record = Record(db_id=db_id, data=data)
    session.add(record)
    session.commit()
    session.refresh(record)
    return record

def update_record(session: Session, record_id: uuid.UUID, data: Any) -> Optional[Record]:
    record = session.get(Record, record_id)
    if record:
        record.data = data
        session.commit()
        session.refresh(record)
    return record

def get_record(session: Session, record_id: uuid.UUID) -> Optional[Record]:
    return session.get(Record, record_id)

def create_embedding(session: Session, record_id: uuid.UUID, text: str) -> Embedding:
    embedding = Embedding(record_id=record_id, text=text)
    session.add(embedding)
    session.commit()
    session.refresh(embedding)
    return embedding

def list_databases(session: Session) -> List[Database]:
    stmt = select(Database)
    return list(session.scalars(stmt))

def list_properties(session: Session, db_id: uuid.UUID) -> List[Property]:
    """List all properties (columns) for a database."""
    stmt = select(Property).where(Property.db_id == db_id)
    return list(session.scalars(stmt))

def get_property_by_name(session: Session, db_id: uuid.UUID, name: str) -> Optional[Property]:
    """Get a property by name in a database."""
    stmt = select(Property).where(Property.db_id == db_id, Property.name == name)
    return session.scalar(stmt)

def delete_property(session: Session, db_id: uuid.UUID, prop_name: str) -> bool:
    """Delete a property (column) from a database."""
    prop = get_property_by_name(session, db_id, prop_name)
    if prop:
        session.delete(prop)
        session.commit()
        return True
    return False

def rename_property(session: Session, db_id: uuid.UUID, old_name: str, new_name: str) -> Optional[Property]:
    """Rename a property in a database."""
    prop = get_property_by_name(session, db_id, old_name)
    if prop:
        prop.name = new_name
        session.commit()
        session.refresh(prop)
        return prop
    return None

def delete_record(session: Session, record_id: uuid.UUID) -> bool:
    """Delete a record by ID."""
    record = session.get(Record, record_id)
    if record:
        session.delete(record)
        session.commit()
        return True
    return False

def delete_database(session: Session, db_id: uuid.UUID) -> bool:
    """Delete a database and all its children (cascade handles properties, records, embeddings)."""
    db = session.get(Database, db_id)
    if db:
        session.delete(db)
        session.commit()
        return True
    return False

# --- Page CRUD ---

def create_page(session: Session, title: str, icon: Optional[str] = None,
                content: Optional[Any] = None, parent_id: Optional[uuid.UUID] = None) -> Page:
    page = Page(title=title, icon=icon, content=content, parent_id=parent_id)
    session.add(page)
    session.commit()
    session.refresh(page)
    return page

def get_page(session: Session, page_id: uuid.UUID) -> Optional[Page]:
    return session.get(Page, page_id)

def list_pages(session: Session) -> List[Page]:
    stmt = select(Page).where(Page.parent_id.is_(None))
    return list(session.scalars(stmt))

def update_page(session: Session, page_id: uuid.UUID, **kwargs) -> Optional[Page]:
    page = session.get(Page, page_id)
    if page:
        for key, value in kwargs.items():
            if hasattr(page, key):
                setattr(page, key, value)
        session.commit()
        session.refresh(page)
    return page

def delete_page(session: Session, page_id: uuid.UUID) -> bool:
    page = session.get(Page, page_id)
    if page:
        session.delete(page)
        session.commit()
        return True
    return False

