import os
import glob
import yaml
from typing import Dict, Any, Optional

def get_frontmatter(filepath: str) -> Dict[str, Any]:
    """
    Parses frontmatter from a markdown file.
    """
    try:
        with open(filepath, 'r') as f:
            content = f.read()
            if content.startswith("---"):
                parts = content.split("---")
                if len(parts) >= 3:
                    return yaml.safe_load(parts[1]) or {}
    except Exception as e:
        print(f"Error parsing frontmatter for {filepath}: {e}")
    return {}

def detect_active_page(workspace_root: str) -> Dict[str, Any]:
    """
    Detects the most recently modified markdown file in the workspace
    and extracts its metadata from frontmatter.
    """
    if not workspace_root or not os.path.exists(workspace_root):
        return {"status": "error", "message": "Workspace path invalid"}

    # Find all .md files recursively
    search_pattern = os.path.join(workspace_root, "**", "*.md")
    files = glob.glob(search_pattern, recursive=True)
    
    if not files:
        return {"status": "no_pages_found"}

    # Sort by modification time (heuristic for "active" page)
    latest_file = max(files, key=os.path.getmtime)
    
    metadata = get_frontmatter(latest_file)
    
    return {
        "status": "success",
        "page_path": latest_file,
        "page_name": os.path.basename(latest_file),
        "page_type": metadata.get("page_type"),
        "db_name": metadata.get("db_name"),
        "record_id": metadata.get("record_id"),
        "agent_managed": metadata.get("agent_managed", False),
        "last_synced": metadata.get("last_synced")
    }
