import os
import tempfile
import json
from datetime import datetime
from agent.db import service as db_service
from agent.utils.markdown import yaml_frontmatter, escape_markdown

# Default folder if not set via ENV
APPFLOWY_DB_FOLDER = os.getenv("APPFLOWY_DB_FOLDER", "/Users/siddh/.gemini/antigravity/playground/volatile-belt/agent_inbox_test/Agent Outputs/Databases")

def _atomic_write(path: str, content: str):
    """
    Writes content to a file atomically using a temporary file.
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=os.path.dirname(path))
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(content)
        os.replace(tmp_path, path)
    except Exception as e:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise e

def render_db_as_markdown(db_obj, records, view="table") -> str:
    """
    Renders a database index page in markdown.
    """
    fm = {
        "agent_managed": True,
        "page_type": "database",
        "db_id": str(db_obj.id),
        "last_synced": datetime.utcnow().isoformat() + "Z",
        "view": view
    }
    
    # Headers from properties
    headers = [p.name for p in db_obj.properties]
    
    md = yaml_frontmatter(fm)
    md += f"# {db_obj.name}\n\n"
    
    if view == "table":
        # Table Header
        md += "| " + " | ".join(headers) + " |\n"
        md += "| " + " | ".join(["---"] * len(headers)) + " |\n"
        
        # Table Rows
        for r in records:
            row_data = r.data if isinstance(r.data, dict) else {}
            row = [escape_markdown(str(row_data.get(h, ""))) for h in headers]
            md += "| " + " | ".join(row) + " |\n"
        md += "\n"
    
    # Links to record pages
    md += "## Records\n"
    for r in records:
        row_data = r.data if isinstance(r.data, dict) else {}
        name = row_data.get(headers[0]) if headers else "Record"
        slug = f"{r.id}.md"
        md += f"- [{name}]({slug})\n"
        
    return md

def render_record_as_markdown(record_obj, db_obj) -> str:
    """
    Renders a single record page in markdown.
    """
    fm = {
        "agent_managed": True,
        "page_type": "record",
        "db_id": str(db_obj.id),
        "record_id": str(record_obj.id),
        "last_synced": datetime.utcnow().isoformat() + "Z",
    }
    
    md = yaml_frontmatter(fm)
    md += f"# Record {record_obj.id}\n\n"
    
    data = record_obj.data if isinstance(record_obj.data, dict) else {}
    for k, v in data.items():
        md += f"**{k}:** {escape_markdown(str(v))}\n\n"
        
    return md

def write_db_page(db_session, db_id: str, view="table"):
    """
    Orchestrates writing the index and all record pages for a DB.
    """
    db_obj = db_service.get_database(db_session, db_id)
    if not db_obj:
        return
        
    records = db_service.list_records(db_session, db_id)
    folder = os.path.join(APPFLOWY_DB_FOLDER, db_obj.name)
    
    # 1. Write Index
    index_path = os.path.join(folder, "index.md")
    index_content = render_db_as_markdown(db_obj, records, view=view)
    _atomic_write(index_path, index_content)
    
    # 2. Write Records
    for r in records:
        path = os.path.join(folder, f"{r.id}.md")
        content = render_record_as_markdown(r, db_obj)
        _atomic_write(path, content)

def write_record_page(db_session, record_id: str):
    """
    Writes a single record page and updates the parent index.
    """
    record_obj = db_service.get_record(db_session, record_id)
    if not record_obj:
        return
        
    db_obj = db_service.get_database(db_session, record_obj.db_id)
    if not db_obj:
        return

    folder = os.path.join(APPFLOWY_DB_FOLDER, db_obj.name)
    
    # Write record page
    path = os.path.join(folder, f"{record_obj.id}.md")
    content = render_record_as_markdown(record_obj, db_obj)
    _atomic_write(path, content)
    
    # Update index page to reflect changes
    write_db_page(db_session, db_obj.id)
