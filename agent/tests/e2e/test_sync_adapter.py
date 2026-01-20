import os
import time
import shutil
import pytest
import threading
from uvicorn import Config, Server

from agent.sync_adapter.watch import start_watcher
from agent.orchestrator.main import app

# Constants for test paths
TEST_WORKSPACE = "./test_workspace"
TEST_INBOX = os.path.join(TEST_WORKSPACE, "inbox.txt")
TEST_OUTPUT_DIR = os.path.join(TEST_WORKSPACE, "AgentOutputs")

@pytest.fixture(scope="module")
def server():
    # Start server in thread
    config = Config(app=app, host="localhost", port=8001, log_level="info")
    server = Server(config)
    t = threading.Thread(target=server.run)
    t.start()
    time.sleep(3) # Wait for server to start
    yield
    server.should_exit = True
    t.join()

@pytest.fixture
def workspace():
    if os.path.exists(TEST_WORKSPACE):
        shutil.rmtree(TEST_WORKSPACE)
    os.makedirs(TEST_WORKSPACE)
    os.makedirs(TEST_OUTPUT_DIR)
    yield TEST_WORKSPACE
    # Cleanup
    if os.path.exists(TEST_WORKSPACE):
        shutil.rmtree(TEST_WORKSPACE)

# Using a mocked watcher loop or running watcher in thread is tricky.
# We will test the handler logic directly or run watcher in thread.
# Let's run watcher in thread for 10 seconds.

def test_e2e_sync_flow(server, workspace):
    # Start watcher in thread
    # We need to stop it, so we might need a flag or just let it die
    # For simplicity, we can instantiate handler and call methods directly
    # to avoid file system race conditions in CI/test env.
    
    from agent.sync_adapter.watch import AppFlowyInboxHandler
    
    # 1. Instantiate Handler pointing to our test server
    # New signature takes workspace_root
    handler = AppFlowyInboxHandler(agent_url="http://localhost:8001", workspace_root=workspace)
    
    # 2. Create Agent Inbox directory and command file
    inbox_dir = os.path.join(workspace, "Agent Inbox")
    os.makedirs(inbox_dir, exist_ok=True)
    test_inbox_file = os.path.join(inbox_dir, "inbox.txt")

    cmd_content = """
    @agent
    Create a database named TestProject with properties Name (text) and Status (select)
    """
    with open(test_inbox_file, 'w') as f:
        f.write(cmd_content)
        
    # 3. Trigger handler manually
    print(f"Processing {test_inbox_file}")
    handler.process_file(test_inbox_file)
    
    # 4. Check outputs
    # We expect Agent Outputs/Databases/TestProject.md
    expected_file = os.path.join(workspace, "Agent Outputs", "Databases", "TestProject.md")
    
    # Debug: Check if any file was created
    db_out_dir = os.path.join(workspace, "Agent Outputs", "Databases")
    if os.path.exists(db_out_dir):
        print(f"Files in {db_out_dir}: {os.listdir(db_out_dir)}")
    else:
        print(f"Dir not found: {db_out_dir}")
    
    # Wait a bit just in case (though process_file is synchronous here)
    if not os.path.exists(expected_file):
        print("FAIL: Expected output file not found.")
    
    assert os.path.exists(expected_file)
    
    with open(expected_file, 'r') as f:
        content = f.read()
        assert "db_name: TestProject" in content
        assert "db_id:" in content
        assert "agent_managed: true" in content
