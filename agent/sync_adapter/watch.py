import time
import os
import requests
import json
import uuid
import yaml
import re
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

class AppFlowyInboxHandler(FileSystemEventHandler):
    def __init__(self, agent_url: str, workspace_root: str):
        self.agent_url = agent_url
        self.workspace_root = workspace_root
        
    def on_modified(self, event):
        if event.is_directory:
            return
        self.process_file(event.src_path)
        
    def process_file(self, filepath: str):
        if not filepath.endswith(".md"):
            return
            
        # 1. Handle Inbox (Commands)
        if "Agent Inbox" in filepath:
            self.handle_inbox(filepath)
            
        # 2. Handle Outputs (Two-Way Sync)
        elif "Agent Outputs" in filepath:
            self.handle_output_edit(filepath)

    def handle_inbox(self, filepath: str):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"Error reading inbox file: {e}")
            return

        if "## CMD:" in content or "@agent" in content or content.startswith("@agent"):
            print(f"Found command in {os.path.basename(filepath)}, sending to agent...")
            try:
                payload = {"text": content}
                response = requests.post(f"{self.agent_url}/run-prompt", json=payload)
                print(f"Agent Response: {response.status_code}")
            except Exception as e:
                print(f"Error calling agent: {e}")

    def handle_output_edit(self, filepath: str):
        """
        Detects edits in AppFlowy and patches the database.
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                raw_content = f.read()
                
            # Parse Frontmatter
            parts = raw_content.split('---')
            if len(parts) < 3:
                return
                
            try:
                fm = yaml.safe_load(parts[1])
            except yaml.YAMLError:
                return

            if not fm or fm.get("agent_managed") is not True:
                return
                
            if fm.get("page_type") == "record":
                record_id = fm.get("record_id")
                # Body is everything after the second ---
                body = parts[2]
                self.patch_record(record_id, body)
                
        except Exception as e:
            print(f"Error handling output edit: {e}")

    def patch_record(self, record_id: str, content: str):
        """
        Parses the markdown body and sends a patch to the orchestrator.
        """
        lines = content.split('\n')
        patch = {}
        for line in lines:
            # Match **Key:** Value
            match = re.match(r"\*\*(.*?)\:\*\*\s*(.*)", line.strip())
            if match:
                key = match.group(1)
                value = match.group(2)
                patch[key] = value
                
        if patch:
            print(f"Detected record patch for {record_id}: {patch}")
            try:
                response = requests.post(
                    f"{self.agent_url}/apply_patch", 
                    json={"record_id": record_id, "patch": patch}
                )
                if response.status_code == 200:
                    print(f"Successfully patched record {record_id}")
                else:
                    print(f"Failed to patch record: {response.text}")
            except Exception as e:
                print(f"Error patching record: {e}")

def start_watcher(workspace_root: str, agent_url: str = "http://localhost:8000"):
    print(f"Watching '{workspace_root}' (Inbox & Outputs) for AppFlowy sync...")
    
    event_handler = AppFlowyInboxHandler(agent_url, workspace_root)
    observer = Observer()
    observer.schedule(event_handler, workspace_root, recursive=True)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    from dotenv import load_dotenv
    env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    load_dotenv(env_path)
    
    workspace_path = os.getenv("AGENT_WORKSPACE_PATH")
    if not workspace_path or not os.path.exists(workspace_path):
        workspace_path = os.path.abspath("./agent_inbox_test")
        os.makedirs(workspace_path, exist_ok=True)
        
    start_watcher(workspace_path)
