import os
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
import time
import uuid
from collections import deque

from agent.db.database import get_db, engine, Base
from agent.orchestrator.llm import LLMService
from agent.orchestrator.logic import AgentLogic
from agent.orchestrator.tools import get_agent_tools
from agent.db.vector_store import VectorStore
from agent.db import service as db_service # Import db_service
from agent.orchestrator import context_resolver, projection

app = FastAPI(title="Agent Orchestrator")

# Workspace Path for context
WORKSPACE_PATH = os.getenv("AGENT_WORKSPACE_PATH", "/Users/siddh/.gemini/antigravity/playground/volatile-belt/agent_inbox_test")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # For dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Logs Buffer
LOGS_BUFFER = deque(maxlen=50)

def log_event(message: str):
    LOGS_BUFFER.append({"time": time.strftime("%H:%M:%S"), "message": message})
    print(message)

# Initialize Services (Singletons)
llm_service = LLMService()
vector_store_service = VectorStore()

class PromptRequest(BaseModel):
    text: str
    context: Any = None
    scope: str = "page"

@app.on_event("startup")
def startup_event():
    # Ensure tables exist (if not using alembic at runtime, but we are)
    # Base.metadata.create_all(bind=engine)
    pass

def process_prompt(user_text: str, context: Any, db: Session):
    """
    Core logic for processing a prompt and executing actions.
    """
    print(f"Received prompt: {user_text}")
    log_event(f"Received prompt: {user_text}")

    # 1. Parse intent with context
    action_plan = llm_service.parse_action(user_text, context=context)
    print(f"Action Plan: {action_plan}")
    log_event(f"Action Plan: {action_plan}")

    if not action_plan or action_plan.get("action") == "none":
        return {"status": "ignored", "details": action_plan.get("params", {})}

    if action_plan.get("action") == "error":
        raise ValueError(action_plan.get("params", {}).get("error", "Unknown error"))

    # 2. Execute Action using Logic/Tools
    logic = AgentLogic(db, vector_store=vector_store_service)
    action = action_plan.get("action")
    params = action_plan.get("params", {})
    
    result = {}
    
    try:
        if action == "create_db":
            db_obj = logic.create_database(
                name=params.get("name"), 
                description=params.get("description")
            )
            # Collect properties for Flutter to create fields
            properties_list = []
            # Add properties if present
            if "properties" in params:
                for prop in params["properties"]:
                    # Default to 'text' if type not specified
                    prop_type = prop.get("type") or "text"
                    logic.add_property(
                        db_id=db_obj.id,
                        name=prop.get("name"),
                        type=prop_type,
                        options=prop.get("options")
                    )
                    # Add to list for Flutter response
                    properties_list.append({
                        "name": prop.get("name"),
                        "type": prop_type
                    })

            result = {
                "message": f"Database '{db_obj.name}' created.", 
                "db_id": str(db_obj.id), 
                "action_type": "create_database",
                "properties": properties_list  # Include properties for AppFlowy
            }

            
        elif action == "create_record":
            # We need to find db_id from name if name is provided
            db_name = params.get("db_name")
            if not db_name:
                # LLM might have put it in 'db'
                db_name = params.get("db")
            
            if not db_name:
                 raise ValueError("Database name is required")
                 
            # Resolve ID
            from agent.db.service import get_database_by_name
            db_obj = get_database_by_name(db, db_name)
            if not db_obj:
                 raise ValueError(f"Database '{db_name}' not found")
            
            data = params.get("data", {})
            record = logic.create_record(db_obj.id, data)
            result = {"message": "Record created", "record_id": str(record.id), "action_type": "insert_block"}
            
        elif action == "query_db" or action == "semantic_search":
            query = params.get("query")
            if not query:
                query = user_text
            
            hits = logic.semantic_search(query)
            result = {"matches": hits, "action_type": "display_results"}
            
        elif action == "apply_template":
            template_name = params.get("template")
            db_name = params.get("name")
            
            if not template_name:
                raise ValueError("Template name is required")
                
            db_obj = logic.apply_template(template_name, db_name)
            result = {"message": f"Template '{template_name}' applied.", "db_id": str(db_obj.id), "action_type": "create_database"}

        elif action == "list_templates":
            templates = logic.list_templates()
            result = {"templates": templates}

        else:
            result = {"status": "unknown_action", "action": action}

    except Exception as e:
        print(f"Execution Error: {e}")
        log_event(f"Error: {e}")
        raise e
        
    log_event(f"Success: {result}")
    return {"status": "success", "result": result}

@app.post("/run-prompt")
def run_prompt_endpoint(payload: PromptRequest, db: Session = Depends(get_db)):
    """
    Legacy natural language endpoint.
    """
    try:
        return process_prompt(payload.text, payload.context, db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/databases")
def get_databases(db: Session = Depends(get_db)):
    dbs = db_service.list_databases(db)
    return {"databases": [{"id": str(d.id), "name": d.name, "description": d.description} for d in dbs]}

@app.get("/logs")
def get_logs():
    return {"logs": list(LOGS_BUFFER)}

@app.post("/agent/execute")
async def execute_agent(payload: Dict[str, Any], db: Session = Depends(get_db)):
    """
    Stable entry point for Native AppFlowy Integration.
    """
    prompt = payload.get("prompt")
    context = payload.get("context", {})
    
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt is required")
        
    try:
        result_data = process_prompt(prompt, context, db)
        
        # Return structured actions
        return {
            "thought": "Processing request based on AppFlowy context...",
            "actions": [result_data.get("result", {})]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/context")
def get_context():
    ctx = context_resolver.detect_active_page(WORKSPACE_PATH)
    return ctx

# --- Projection Endpoints ---

@app.post("/projection/render_all")
def render_all(db: Session = Depends(get_db)):
    """
    Regenerates all markdown pages for all databases.
    """
    try:
        databases = db_service.list_databases(db)
        for d in databases:
            projection.write_db_page(db, d.id)
        return {"status": "success", "count": len(databases)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/projection/render_db/{db_id}")
def render_db(db_id: str, db: Session = Depends(get_db)):
    """
    Regenerates markdown for a specific database.
    """
    try:
        projection.write_db_page(db, db_id)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/apply_patch")
def apply_patch(payload: Dict[str, Any], db: Session = Depends(get_db)):
    """
    Applies a patch (changes detected in MD) to the SQL DB.
    """
    record_id = payload.get("record_id")
    patch = payload.get("patch")
    
    if not record_id or not patch:
        raise HTTPException(status_code=400, detail="record_id and patch are required")
        
    try:
        # Cast to UUID
        rec_uuid = uuid.UUID(record_id)
        # Resolve record
        record = db_service.get_record(db, rec_uuid)
        if not record:
            raise HTTPException(status_code=404, detail="Record not found")
            
        # Merge patch into existing data
        new_data = record.data.copy() if record.data else {}
        new_data.update(patch)
        
        # Update in SQL
        db_service.update_record(db, rec_uuid, new_data)
        
        # Re-project to keep MD in sync
        projection.write_record_page(db, rec_uuid)
        
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
