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
WORKSPACE_PATH = os.getenv("AGENT_WORKSPACE_PATH", "/Users/siddh/Downloads/Projects/APPFlowy-notion Clone/agent_inbox_test")

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

@app.get("/")
def root():
    """Root endpoint for health check and API info."""
    return {
        "name": "Agent Orchestrator",
        "version": "2.0.0",
        "status": "running",
        "endpoints": [
            "/health",
            "/run-prompt",
            "/agent/execute",
            "/databases",
            "/logs",
            "/context",
            "/projection/render_all",
            "/projection/render_db/{db_id}",
            "/apply_patch"
        ]
    }


@app.get("/health")
def health_check():
    """Health check endpoint for Docker and load balancers."""
    import time
    health = {
        "status": "healthy",
        "timestamp": time.time(),
        "service": "backend-orchestrator",
        "version": "2.0.0",
    }
    # Check database connectivity
    try:
        db = next(get_db())
        db.execute(db_service.select(db_service.Database).limit(1)) if hasattr(db_service, 'select') else None
        db.close()
        health["database"] = "connected"
    except Exception as e:
        health["database"] = f"error: {str(e)}"
        health["status"] = "degraded"

    # Check vector store
    try:
        vs_ok = vector_store_service.health_check()
        health["qdrant"] = "connected" if vs_ok else "unavailable"
    except Exception:
        health["qdrant"] = "unavailable"

    return health


def process_prompt(user_text: str, context: Any, db: Session):
    """
    Core logic for processing a prompt and executing actions.
    """
    print(f"Received prompt: {user_text}")
    log_event(f"Received prompt: {user_text}")

    # 0. Fast path: writing keywords bypass LLM parse entirely (avoids double LLM call)
    lower = user_text.lower().strip()
    writing_fast_paths = [
        ("explain this", "explain"),
        ("explain ", "explain"),
        ("summarize:", "summarize"),
        ("summarize this", "summarize"),
        ("summarise:", "summarize"),
        ("summarise this", "summarize"),
        ("improve writing", "improve_writing"),
        ("improve this", "improve_writing"),
        ("continue writing", "continue_writing"),
        ("continue this", "continue_writing"),
    ]
    for keyword, fast_action in writing_fast_paths:
        if lower.startswith(keyword):
            log_event(f"Fast-path writing action: '{keyword}' → {fast_action}")
            action_plan = {"action": fast_action, "params": {"text": user_text}}
            break
    else:
        # 1. Parse intent with context
        action_plan = llm_service.parse_action(user_text, context=context)
    print(f"Action Plan: {action_plan}")
    log_event(f"Action Plan: {action_plan}")

    # Safety net: if LLM returns "none" but the prompt clearly matches a writing action,
    # override with the correct action (LLM sometimes misclassifies these as general questions)
    if not action_plan or action_plan.get("action") == "none":
        lower = user_text.lower().strip()
        writing_overrides = [
            ("explain", "explain"),
            ("summarize", "summarize"),
            ("summarise", "summarize"),
            ("improve", "improve_writing"),
            ("rewrite", "improve_writing"),
            ("continue writing", "continue_writing"),
        ]
        for keyword, override_action in writing_overrides:
            if lower.startswith(keyword):
                action_plan = {"action": override_action, "params": {"text": user_text}}
                log_event(f"Override: LLM said none, keyword '{keyword}' matched → {override_action}")
                break

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
                "properties": properties_list,
                "icon": params.get("icon", ""),
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
            template_name = params.get("template") or params.get("template_name")
            db_name = params.get("db_name") or params.get("name")
            # If LLM put the template name under "name" and it matches a known template, use it
            if not template_name and db_name:
                from agent.templates.definitions import get_template
                if get_template(db_name):
                    template_name = db_name
                    db_name = None
            if not template_name:
                raise ValueError("Template name is required")

            db_obj = logic.apply_template(template_name, db_name)
            result = {"message": f"Template '{template_name}' applied.", "db_id": str(db_obj.id), "action_type": "create_database"}

        elif action == "list_templates":
            templates = logic.list_templates()
            result = {"templates": templates}

        # --- Writing Actions (use LLM directly) ---
        elif action == "summarize":
            text_to_summarize = params.get("text", user_text)
            summary = llm_service.generate_text(f"Summarize this concisely:\n\n{text_to_summarize}")
            result = {"response": summary, "action_type": "text_response"}

        elif action == "improve_writing":
            text_to_improve = params.get("text", user_text)
            improved = llm_service.generate_text(f"Improve this writing for clarity and professionalism:\n\n{text_to_improve}")
            result = {"response": improved, "action_type": "text_response"}

        elif action == "explain":
            text_to_explain = params.get("text", user_text)
            explanation = llm_service.generate_text(f"Explain this in simple terms:\n\n{text_to_explain}")
            result = {"response": explanation, "action_type": "text_response"}

        # --- Schema Modification Actions ---
        elif action == "drop_property":
            db_name = params.get("db_name")
            prop_name = params.get("property_name") or params.get("prop_name") or params.get("name")
            
            if not db_name:
                raise ValueError("Database name is required")
            if not prop_name:
                raise ValueError("Property name is required")
            
            db_obj = db_service.get_database_by_name(db, db_name)
            if not db_obj:
                raise ValueError(f"Database '{db_name}' not found")
            
            success = logic.drop_property(db_obj.id, prop_name)
            if success:
                result = {"message": f"Column '{prop_name}' dropped from '{db_name}'.", "action_type": "drop_field",
                          "field_name": prop_name, "db_name": db_name}
            else:
                result = {"message": f"Column '{prop_name}' not found in '{db_name}'.", "action_type": "error"}

        elif action == "rename_property":
            db_name = params.get("db_name")
            old_name = params.get("old_name")
            new_name = params.get("new_name")
            
            if not db_name:
                raise ValueError("Database name is required")
            if not old_name or not new_name:
                raise ValueError("Both old_name and new_name are required")
            
            db_obj = db_service.get_database_by_name(db, db_name)
            if not db_obj:
                raise ValueError(f"Database '{db_name}' not found")
            
            prop = logic.rename_property(db_obj.id, old_name, new_name)
            if prop:
                result = {"message": f"Column '{old_name}' renamed to '{new_name}' in '{db_name}'.", "action_type": "rename_field",
                          "old_name": old_name, "new_name": new_name, "db_name": db_name}
            else:
                result = {"message": f"Column '{old_name}' not found in '{db_name}'.", "action_type": "error"}

        elif action == "list_properties":
            db_name = params.get("db_name")
            
            if not db_name:
                raise ValueError("Database name is required")
            
            db_obj = db_service.get_database_by_name(db, db_name)
            if not db_obj:
                raise ValueError(f"Database '{db_name}' not found")
            
            props = logic.list_properties(db_obj.id)
            prop_list = [{"name": p.name, "type": p.type} for p in props]
            result = {"message": f"Database '{db_name}' has {len(prop_list)} columns.", "properties": prop_list, "action_type": "list_fields"}

        elif action == "add_property":
            # Handle add_property with alternative param names from LLM
            db_name = params.get("db_name")
            prop_name = params.get("property_name") or params.get("name")
            prop_type = params.get("property_type") or params.get("type") or "text"
            options = params.get("options")

            if not db_name:
                raise ValueError("Database name is required")
            if not prop_name:
                raise ValueError("Property name is required")

            db_obj = db_service.get_database_by_name(db, db_name)
            if not db_obj:
                raise ValueError(f"Database '{db_name}' not found")

            prop = logic.add_property(db_obj.id, prop_name, prop_type, options)
            result = {"message": f"Column '{prop_name}' ({prop_type}) added to '{db_name}'.", "action_type": "add_field",
                      "field_name": prop_name, "field_type": prop_type, "db_name": db_name}

        elif action == "edit_record":
            db_name = params.get("db_name")
            record_id = params.get("record_id")
            data = params.get("data", {})

            if not db_name:
                raise ValueError("Database name is required")
            if not record_id:
                raise ValueError("Record ID is required")

            db_obj = db_service.get_database_by_name(db, db_name)
            if not db_obj:
                raise ValueError(f"Database '{db_name}' not found")

            rec_uuid = uuid.UUID(record_id)
            logic.edit_record(rec_uuid, data)
            result = {"message": f"Record updated in '{db_name}'.", "action_type": "edit_record", "db_name": db_name}

        elif action == "delete_record":
            db_name = params.get("db_name")
            record_id = params.get("record_id")

            if not db_name:
                raise ValueError("Database name is required")
            if not record_id:
                raise ValueError("Record ID is required")

            db_obj = db_service.get_database_by_name(db, db_name)
            if not db_obj:
                raise ValueError(f"Database '{db_name}' not found")

            rec_uuid = uuid.UUID(record_id)
            success = logic.delete_record(db_obj.id, rec_uuid)
            if success:
                result = {"message": f"Record deleted from '{db_name}'.", "action_type": "delete_record", "db_name": db_name}
            else:
                result = {"message": f"Record not found in '{db_name}'.", "action_type": "error"}

        elif action == "delete_database":
            db_name = params.get("db_name") or params.get("name")

            if not db_name:
                raise ValueError("Database name is required")

            db_obj = db_service.get_database_by_name(db, db_name)
            if not db_obj:
                raise ValueError(f"Database '{db_name}' not found")

            success = logic.delete_database(db_obj.id)
            if success:
                result = {"message": f"Database '{db_name}' deleted.", "action_type": "delete_database", "db_name": db_name}
            else:
                result = {"message": f"Failed to delete '{db_name}'.", "action_type": "error"}

        elif action == "continue_writing":
            text = params.get("text", user_text)
            continued = llm_service.generate_text(f"Continue writing from where this text leaves off. Write 2-3 more paragraphs in the same style and tone:\n\n{text}")
            result = {"response": continued, "action_type": "text_response"}

        elif action == "create_page":
            title = params.get("title", "Untitled")
            description = params.get("description", "")
            icon = params.get("icon", "📄")

            content = llm_service.generate_page_content(title, description)

            # Store in SQL
            from agent.db.service import create_page
            page = create_page(db, title=title, icon=icon, content=content)

            # Project to markdown
            projection.write_page(db, page.id)

            result = {
                "message": f"Page '{title}' created.",
                "action_type": "create_page",
                "title": title,
                "icon": icon,
                "content": content,
                "page_id": str(page.id)
            }

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
        db_uuid = uuid.UUID(db_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid database ID format")
    try:
        projection.write_db_page(db, db_uuid)
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
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
