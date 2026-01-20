import shutil
import os
import datetime
import argparse
import sys

# Paths (relative to script execution from root)
DB_PATH = "agent/agent.db"
QDRANT_PATH = "agent_qdrant_db"
BACKUP_DIR = "backups"

def create_backup():
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
        
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"backup_{timestamp}"
    backup_path = os.path.join(BACKUP_DIR, backup_name)
    
    os.makedirs(backup_path)
    
    # 1. Backup SQLite
    if os.path.exists(DB_PATH):
        print(f"Backing up SQLite DB: {DB_PATH}")
        shutil.copy2(DB_PATH, os.path.join(backup_path, "agent.db"))
    else:
        print(f"Warning: SQLite DB not found at {DB_PATH}")

    # 2. Backup Qdrant
    if os.path.exists(QDRANT_PATH):
        print(f"Backing up Qdrant Data: {QDRANT_PATH}")
        shutil.copytree(QDRANT_PATH, os.path.join(backup_path, "agent_qdrant_db"))
    else:
        print(f"Warning: Qdrant data not found at {QDRANT_PATH}")
        
    # 3. Zip it
    shutil.make_archive(backup_path, 'zip', backup_path)
    
    # Clean up folder
    shutil.rmtree(backup_path)
    
    print(f"Backup created successfully: {backup_path}.zip")

def restore_backup(zip_path):
    if not os.path.exists(zip_path):
        print(f"Error: Zip file {zip_path} not found.")
        return
    
    confirm = input(f"WARNING: This will overwrite current data. Restore from {zip_path}? (y/n): ")
    if confirm.lower() != 'y':
        print("Restore cancelled.")
        return

    print("Restoring...")
    
    # Unzip to temp
    temp_dir = "temp_restore"
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    os.makedirs(temp_dir)
    
    shutil.unpack_archive(zip_path, temp_dir)
    
    # Restore SQLite
    src_db = os.path.join(temp_dir, "agent.db")
    if os.path.exists(src_db):
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
        shutil.copy2(src_db, DB_PATH)
        print("Restored SQLite DB.")
        
    # Restore Qdrant
    src_qdrant = os.path.join(temp_dir, "agent_qdrant_db")
    if os.path.exists(src_qdrant):
        if os.path.exists(QDRANT_PATH):
            shutil.rmtree(QDRANT_PATH)
        shutil.copytree(src_qdrant, QDRANT_PATH)
        print("Restored Qdrant Data.")
        
    shutil.rmtree(temp_dir)
    print("Restore complete.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backup and Restore Agent Data")
    parser.add_argument("action", choices=["backup", "restore"], help="Action to perform")
    parser.add_argument("--file", help="Path to zip file for restore")
    
    args = parser.parse_args()
    
    if args.action == "backup":
        create_backup()
    elif args.action == "restore":
        if not args.file:
            print("Error: --file argument required for restore")
        else:
            restore_backup(args.file)
