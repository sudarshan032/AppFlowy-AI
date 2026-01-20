from typing import List, Dict, Any, Optional
from langchain_core.tools import Tool, StructuredTool
from agent.orchestrator.logic import AgentLogic
from agent.db.service import get_database_by_name

def get_agent_tools(logic: AgentLogic) -> List[StructuredTool]:
    
    def create_database_tool(name: str, description: Optional[str] = None):
        """Create a new database with a name and optional description."""
        try:
            db = logic.create_database(name, description)
            return f"Database '{db.name}' created with ID: {db.id}"
        except Exception as e:
            return f"Error creating database: {e}"

    def create_record_tool(db_name: str, data: Dict[str, Any]):
        """
        Create a new record in the specified database. 
        Args:
            db_name: The name of the database.
            data: A dictionary of property names and values.
        """
        try:
            # Resolve db_name to db_id
            db = get_database_by_name(logic.db_session, db_name)
            if not db:
                return f"Error: Database '{db_name}' not found."
            
            record = logic.create_record(db.id, data)
            return f"Record created in '{db_name}' with ID: {record.id}"
        except Exception as e:
            return f"Error creating record: {e}"

    def query_tool(query: str):
        """
        Search for records using semantic search (meaning/vector search).
        """
        try:
            results = logic.semantic_search(query)
            if not results:
                return "No relevant records found."
            
            # Format results
            formatted = []
            for r in results:
                formatted.append(f"Content: {r['text']}, Score: {r['score']}")
            return "\n---\n".join(formatted)
        except Exception as e:
            return f"Error searching: {e}"

    return [
        StructuredTool.from_function(
            func=create_database_tool,
            name="create_database",
            description="Create a new database schema."
        ),
        StructuredTool.from_function(
            func=create_record_tool,
            name="create_record",
            description="Add a new record to a database."
        ),
        StructuredTool.from_function(
            func=query_tool,
            name="semantic_search",
            description="Search database records by meaning."
        )
    ]
