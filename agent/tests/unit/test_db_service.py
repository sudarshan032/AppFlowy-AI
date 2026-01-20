import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from agent.db.models import Base
from agent.db.service import create_database, add_property, create_record, get_database_by_name, get_record

# Use in-memory SQLite for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture
def session():
    engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

def test_create_database(session):
    db = create_database(session, name="TestDB", description="A test database")
    assert db.id is not None
    assert db.name == "TestDB"
    assert db.description == "A test database"

    fetched = get_database_by_name(session, "TestDB")
    assert fetched is not None
    assert fetched.id == db.id

def test_add_property(session):
    db = create_database(session, name="PropDB")
    prop = add_property(session, db.id, name="Status", type="select", options=["Todo", "Done"])
    assert prop.id is not None
    assert prop.name == "Status"
    assert prop.type == "select"
    assert prop.options == ["Todo", "Done"]
    assert prop.db_id == db.id

def test_create_record(session):
    db = create_database(session, name="RecordDB")
    data = {"Name": "Test Item", "Status": "Todo"}
    record = create_record(session, db.id, data=data)
    assert record.id is not None
    assert record.data == data
    assert record.db_id == db.id

    fetched = get_record(session, record.id)
    assert fetched.data["Name"] == "Test Item"
