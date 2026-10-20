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
    },
    "meeting_notes": {
        "name": "Meeting Notes",
        "description": "Track meeting agendas and action items",
        "properties": [
            {"name": "Meeting Title", "type": "text"},
            {"name": "Date", "type": "date"},
            {"name": "Attendees", "type": "text"},
            {"name": "Agenda", "type": "text"},
            {"name": "Action Items", "type": "text"},
            {"name": "Status", "type": "select", "options": ["Scheduled", "Completed", "Cancelled"]}
        ]
    },
    "journal": {
        "name": "Journal",
        "description": "Daily journal entries",
        "properties": [
            {"name": "Date", "type": "date"},
            {"name": "Mood", "type": "select", "options": ["Great", "Good", "Okay", "Bad"]},
            {"name": "Entry", "type": "text"},
            {"name": "Gratitude", "type": "text"},
            {"name": "Goals", "type": "text"}
        ]
    },
    "contacts": {
        "name": "Contacts",
        "description": "Contact directory",
        "properties": [
            {"name": "Name", "type": "text"},
            {"name": "Email", "type": "text"},
            {"name": "Phone", "type": "text"},
            {"name": "Company", "type": "text"},
            {"name": "Role", "type": "text"},
            {"name": "Last Contact", "type": "date"},
            {"name": "Notes", "type": "text"}
        ]
    },
    "inventory": {
        "name": "Inventory",
        "description": "Track inventory items and stock levels",
        "properties": [
            {"name": "Item Name", "type": "text"},
            {"name": "SKU", "type": "text"},
            {"name": "Quantity", "type": "number"},
            {"name": "Price", "type": "number"},
            {"name": "Category", "type": "select", "options": ["Electronics", "Office", "Materials", "Other"]},
            {"name": "Reorder", "type": "checkbox"}
        ]
    },
    "reading_list": {
        "name": "Reading List",
        "description": "Track books and articles to read",
        "properties": [
            {"name": "Title", "type": "text"},
            {"name": "Author", "type": "text"},
            {"name": "URL", "type": "url"},
            {"name": "Status", "type": "select", "options": ["To Read", "Reading", "Finished"]},
            {"name": "Rating", "type": "number"},
            {"name": "Notes", "type": "text"}
        ]
    },
    "wiki": {
        "name": "Wiki",
        "description": "Team knowledge base",
        "properties": [
            {"name": "Title", "type": "text"},
            {"name": "Category", "type": "select", "options": ["Engineering", "Product", "Design", "Operations"]},
            {"name": "Content", "type": "text"},
            {"name": "Last Updated", "type": "date"},
            {"name": "Author", "type": "text"}
        ]
    }
}

def get_template(name: str) -> Dict[str, Any]:
    return TEMPLATES.get(name.lower())

def list_templates() -> List[str]:
    return list(TEMPLATES.keys())
