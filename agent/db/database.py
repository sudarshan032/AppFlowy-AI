"""
Database Engine Configuration

Supports PostgreSQL (production/Docker) and SQLite (testing).
Connection string comes from DATABASE_URL environment variable.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

from .models import Base

# Load .env from agent/.env (local dev) or environment (Docker)
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
if os.path.exists(env_path):
    load_dotenv(env_path)

# Also load root .env if present
root_env = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env")
if os.path.exists(root_env):
    load_dotenv(root_env, override=False)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./agent.db")

# Handle SQLite-specific options
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Dependency injection for database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables (useful for testing or initial setup)."""
    Base.metadata.create_all(bind=engine)
