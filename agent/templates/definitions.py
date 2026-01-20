from typing import Dict, Any, List

TEMPLATES: Dict[str, Dict[str, Any]] = {
    "crm": {
        "name": "CRM",
        "description": "Customer Relationship Management system",
        "properties": [
            {"name": "Client Name", "type": "text"},
            {"name": "Email", "type": "text"},
            {"name": "Status", "type": "select", "options": ["Lead", "Active", "Closed"]},
            {"name": "Value", "type": "number"},
            {"name": "Last Contact", "type": "date"}
        ]
    },
    "tracker": {
        "name": "Project Tracker",
        "description": "Task and project tracking",
        "properties": [
            {"name": "Task Name", "type": "text"},
            {"name": "Assignee", "type": "text"},
            {"name": "Priority", "type": "select", "options": ["Low", "Medium", "High", "Critical"]},
            {"name": "Due Date", "type": "date"},
            {"name": "Status", "type": "select", "options": ["Backlog", "In Progress", "Review", "Done"]}
        ]
    },
    "notes": {
        "name": "Notes",
        "description": "Simple notes database",
        "properties": [
            {"name": "Title", "type": "text"},
            {"name": "Tags", "type": "multi_select", "options": ["Personal", "Work", "Ideas"]},
            {"name": "Created", "type": "date"}
        ]
    }
}

def get_template(name: str) -> Dict[str, Any]:
    return TEMPLATES.get(name.lower())

def list_templates() -> List[str]:
    return list(TEMPLATES.keys())
