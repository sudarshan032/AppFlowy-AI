from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import List, Optional, Any
import uuid

from .models import Database, Property, Record, Embedding

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
