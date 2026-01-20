import pytest
from unittest.mock import MagicMock, patch
import uuid
from agent.orchestrator.logic import AgentLogic
from agent.db.models import Record

def test_create_record_flow():
    # Mock DB session
    mock_session = MagicMock()
    
    # Mock DB service
    with patch('agent.orchestrator.logic.db_service') as mock_db_service:
        # Mock create_record return
        mock_record = Record(id=uuid.uuid4(), db_id=uuid.uuid4(), data={"Name": "Test"})
        mock_db_service.create_record.return_value = mock_record
        
        # Instantiate Logic
        logic = AgentLogic(mock_session)
        
        # Mock Embeddings and VectorStore
        logic.embeddings_service = MagicMock()
        logic.embeddings_service.embed_text.return_value = [0.1, 0.2, 0.3]
        
        logic.vector_store = MagicMock()
        
        # Action
        db_id = uuid.uuid4()
        data = {"Name": "Test Value"}
        result = logic.create_record(db_id, data)
        
        # Assertions
        mock_db_service.create_record.assert_called_once()
        logic.embeddings_service.embed_text.assert_called_once()
        logic.vector_store.add_record.assert_called_once()
        
        # Verify vector store call args
        # call_args matches (args, kwargs)
        args, kwargs = logic.vector_store.add_record.call_args
        # add_record(record_id, text, embedding, metadata)
        # These can be positional or keyword args depending on implementation call
        # in logic.py: add_record(record_id=..., text=..., embedding=..., metadata=...)
        
        # Check kwargs since logic.py uses keyword arguments
        assert kwargs['record_id'] == str(mock_record.id)
        assert kwargs['embedding'] == [0.1, 0.2, 0.3]
