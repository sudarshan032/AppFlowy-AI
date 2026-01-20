import yaml
import datetime
from typing import Dict, Any, Optional, List

def generate_frontmatter(
    page_type: str,
    db_name: Optional[str] = None,
    db_id: Optional[str] = None,
    record_id: Optional[str] = None
) -> str:
    """
    Generates standardization frontmatter for AppFlowy pages.
    """
    data = {
        "agent_managed": True,
        "page_type": page_type,
        "last_synced": datetime.datetime.now().isoformat()
    }
    
    if db_name:
        data["db_name"] = db_name
    if db_id:
        data["db_id"] = db_id
    if record_id:
        data["record_id"] = record_id
        
    # Use yaml.dump but ensure it looks like frontmatter
    yaml_str = yaml.dump(data, default_flow_style=False, sort_keys=False)
    return f"---\n{yaml_str}---\n"

def generate_database_page(db_name: str, properties: List[Dict[str, Any]], db_id: Optional[str] = None) -> str:
    """
    Generates a markdown page for a Database.
    """
    frontmatter = generate_frontmatter(page_type="database", db_name=db_name, db_id=db_id)
    
    content = f"# {db_name}\n\n"
    content += f"**Description**: Database for {db_name}\n\n"
    content += "## Properties\n"
    for prop in properties:
        content += f"- **{prop['name']}** ({prop['type']})\n"
        
    return frontmatter + content

def generate_record_page(db_name: str, record_id: str, data: Dict[str, Any], db_id: Optional[str] = None) -> str:
    """
    Generates a markdown page for a Record.
    """
    frontmatter = generate_frontmatter(page_type="record", db_name=db_name, db_id=db_id, record_id=record_id)
    
    # Heuristic for title
    title = data.get("Name") or data.get("Title") or f"Record {record_id}"
    
    content = f"# {title}\n\n"
    for k, v in data.items():
        content += f"**{k}**: {v}\n\n"
        
    return frontmatter + content
