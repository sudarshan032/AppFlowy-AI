"""
SQLAlchemy ORM Models — All Phases

Covers: Databases, Properties, Records, Embeddings, Pages,
        AI Properties, Agents, Connectors, Meetings, Analytics
"""

from datetime import datetime, timezone
from typing import List, Optional, Any
import uuid

from sqlalchemy import (
    String, ForeignKey, DateTime, JSON, Boolean, Text, Uuid,
    Integer, Float, Enum as SAEnum
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
import enum


class Base(DeclarativeBase):
    pass


# =============================================================================
# PHASE 1 — Core Models (Existing + Enhanced)
# =============================================================================

class Database(Base):
    __tablename__ = "databases"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    icon: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    template_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    properties: Mapped[List["Property"]] = relationship("Property", back_populates="database", cascade="all, delete-orphan")
    records: Mapped[List["Record"]] = relationship("Record", back_populates="database", cascade="all, delete-orphan")
    ai_properties: Mapped[List["AIProperty"]] = relationship("AIProperty", back_populates="database", cascade="all, delete-orphan")


class Property(Base):
    __tablename__ = "properties"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    db_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("databases.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    options: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    required: Mapped[bool] = mapped_column(Boolean, default=False)
    order: Mapped[int] = mapped_column(Integer, default=0)

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

    record: Mapped["Record"] = relationship("Record", back_populates="embeddings")


class Page(Base):
    __tablename__ = "pages"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    icon: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    content: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("pages.id"), nullable=True)
    workspace_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_indexed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    children: Mapped[List["Page"]] = relationship("Page", back_populates="parent", cascade="all, delete-orphan")
    parent: Mapped[Optional["Page"]] = relationship("Page", back_populates="children", remote_side=[id])


# =============================================================================
# PHASE 2 — AI Properties for Database Autofill
# =============================================================================

class AIPropertyType(str, enum.Enum):
    SUMMARY = "ai_summary"
    KEY_INFO = "ai_key_info"
    TRANSLATION = "ai_translation"
    CUSTOM = "ai_custom"


class AIProperty(Base):
    """AI-powered database properties that auto-populate with AI-generated content."""
    __tablename__ = "ai_properties"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    db_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("databases.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    ai_type: Mapped[str] = mapped_column(String(50), nullable=False)  # AIPropertyType
    prompt_template: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_properties: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    target_language: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    auto_update: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    database: Mapped["Database"] = relationship("Database", back_populates="ai_properties")


# =============================================================================
# PHASE 4 — Agents
# =============================================================================

class AgentStatus(str, enum.Enum):
    IDLE = "idle"
    PLANNING = "planning"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


class Agent(Base):
    """AI Agent definitions with instructions and configuration."""
    __tablename__ = "agents"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    instructions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    max_steps: Mapped[int] = mapped_column(Integer, default=50)
    timeout_minutes: Mapped[int] = mapped_column(Integer, default=20)
    schedule_cron: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    permissions: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    memory: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    runs: Mapped[List["AgentRun"]] = relationship("AgentRun", back_populates="agent", cascade="all, delete-orphan")


class AgentRun(Base):
    """Execution history for agent runs."""
    __tablename__ = "agent_runs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agents.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="running")
    task: Mapped[str] = mapped_column(Text, nullable=False)
    steps_completed: Mapped[int] = mapped_column(Integer, default=0)
    steps_total: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    result: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    plan: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    agent: Mapped["Agent"] = relationship("Agent", back_populates="runs")


# =============================================================================
# PHASE 5 — Connectors
# =============================================================================

class ConnectorType(str, enum.Enum):
    SLACK = "slack"
    GOOGLE_DRIVE = "google_drive"
    GITHUB = "github"
    JIRA = "jira"
    EMAIL = "email"


class Connector(Base):
    """External service connector configurations."""
    __tablename__ = "connectors"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    connector_type: Mapped[str] = mapped_column(String(50), nullable=False)
    config: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    credentials: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_indexed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    index_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    indexed_items: Mapped[List["ConnectorIndex"]] = relationship("ConnectorIndex", back_populates="connector", cascade="all, delete-orphan")


class ConnectorIndex(Base):
    """Indexed content from external connectors."""
    __tablename__ = "connector_index"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    connector_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("connectors.id"), nullable=False)
    source_id: Mapped[str] = mapped_column(String(500), nullable=False)
    source_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    metadata: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    indexed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    connector: Mapped["Connector"] = relationship("Connector", back_populates="indexed_items")


# =============================================================================
# PHASE 6 — Meeting Notes
# =============================================================================

class MeetingNote(Base):
    """Meeting transcriptions and summaries."""
    __tablename__ = "meeting_notes"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    transcript: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    attendees: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    meeting_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    audio_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    page_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("pages.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    action_items: Mapped[List["MeetingActionItem"]] = relationship("MeetingActionItem", back_populates="meeting", cascade="all, delete-orphan")


class MeetingActionItem(Base):
    """Action items extracted from meetings."""
    __tablename__ = "meeting_action_items"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meeting_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("meeting_notes.id"), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    assignee: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    priority: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    meeting: Mapped["MeetingNote"] = relationship("MeetingNote", back_populates="action_items")


# =============================================================================
# PHASE 7 — Analytics & User Preferences
# =============================================================================

class AIUsageLog(Base):
    """Track AI feature usage for analytics."""
    __tablename__ = "ai_usage_logs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    feature: Mapped[str] = mapped_column(String(100), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    tokens_used: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class UserPreference(Base):
    """User AI preferences and settings."""
    __tablename__ = "user_preferences"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    preferred_provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    preferred_model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    language: Mapped[Optional[str]] = mapped_column(String(50), default="en")
    auto_model_selection: Mapped[bool] = mapped_column(Boolean, default=True)
    settings: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
