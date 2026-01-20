from datetime import datetime, timezone
from typing import List, Optional, Any
import uuid

from sqlalchemy import String, ForeignKey, DateTime, JSON, Boolean, Text, Uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass

class Database(Base):
    __tablename__ = "databases"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, index=True)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    properties: Mapped[List["Property"]] = relationship("Property", back_populates="database", cascade="all, delete-orphan")
    records: Mapped[List["Record"]] = relationship("Record", back_populates="database", cascade="all, delete-orphan")

class Property(Base):
    __tablename__ = "properties"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    db_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("databases.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)  # text, number, date, select, person, relation
    options: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)  # For select options, etc.
    required: Mapped[bool] = mapped_column(Boolean, default=False)

    database: Mapped["Database"] = relationship("Database", back_populates="properties")

class Record(Base):
    __tablename__ = "records"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    db_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("databases.id"), nullable=False)
    data: Mapped[Any] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    database: Mapped["Database"] = relationship("Database", back_populates="records")
    embeddings: Mapped[List["Embedding"]] = relationship("Embedding", back_populates="record", cascade="all, delete-orphan")

class Embedding(Base):
    __tablename__ = "embeddings"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    record_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("records.id"), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    # Storing vector here is optional if using Chroma, but keeping a placeholder or backup is fine.
    # For now, we'll skip the actual vector column in SQL unless we use pgvector.
    # vector: Mapped[Optional[List[float]]] = ... 

    record: Mapped["Record"] = relationship("Record", back_populates="embeddings")
