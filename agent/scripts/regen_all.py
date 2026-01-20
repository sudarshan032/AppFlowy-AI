import sys
import os
from sqlalchemy.orm import Session

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from agent.db.database import SessionLocal
from agent.db import service as db_service
from agent.orchestrator import projection

def main():
    db = SessionLocal()
    try:
        databases = db_service.list_databases(db)
        print(f"Regenerating {len(databases)} databases...")
        for d in databases:
            print(f"Processing '{d.name}' ({d.id})...")
            projection.write_db_page(db, d.id)
        print("Done!")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
