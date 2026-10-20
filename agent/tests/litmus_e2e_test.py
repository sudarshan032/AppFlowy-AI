"""
End-to-End litmus test with LIVE Ollama LLM.
Tests every action type through the full pipeline:
  User text → LLM parse → handler → response

Orchestrator on :8088, AI Plugin on :8089
"""
import sys, os, json, uuid, requests, time

ORCH = "http://localhost:8088"
PLUGIN = "http://localhost:8089"
TIMEOUT = 180  # LLM can be slow

passed = 0
failed = 0

def ok(label):
    global passed
    passed += 1
    print(f"  ✅  {label}")

def fail(label, detail=""):
    global failed
    failed += 1
    print(f"  ❌  {label} — {detail}")

def assert_test(cond, label, detail=""):
    if cond: ok(label)
    else: fail(label, detail)

def orch_prompt(text, context=None):
    """Send prompt to orchestrator, return (status_code, json)."""
    payload = {"text": text}
    if context:
        payload["context"] = context
    r = requests.post(f"{ORCH}/run-prompt", json=payload, timeout=TIMEOUT)
    return r.status_code, r.json()

def plugin_prompt(text, context=None):
    """Send prompt to AI plugin, return (status_code, json)."""
    payload = {"text": text}
    if context:
        payload["context"] = context
    r = requests.post(f"{PLUGIN}/run-prompt", json=payload, timeout=TIMEOUT)
    return r.status_code, r.json()

print("\n" + "=" * 70)
print("  END-TO-END LITMUS TESTS (Live LLM)")
print("=" * 70)

# ════════════════════════════════════════════════════════════════════════
# 0. Verify servers
# ════════════════════════════════════════════════════════════════════════
print("\n── 0. Server Health ──")
try:
    r = requests.get(f"{ORCH}/", timeout=5)
    assert_test(r.status_code == 200, "Orchestrator running")
except Exception as e:
    fail("Orchestrator running", str(e))
    print("FATAL: Orchestrator not running, aborting")
    sys.exit(1)

try:
    r = requests.get(f"{PLUGIN}/", timeout=5)
    assert_test(r.status_code == 200, "AI Plugin running")
except Exception as e:
    fail("AI Plugin running", str(e))
    print("FATAL: AI Plugin not running, aborting")
    sys.exit(1)

try:
    r = requests.get("http://localhost:11434/api/tags", timeout=5)
    assert_test(r.status_code == 200, "Ollama running")
except Exception as e:
    fail("Ollama running", str(e))
    print("FATAL: Ollama not running, aborting")
    sys.exit(1)

# Pre-cleanup: remove any leftover E2ETestDB from prior runs
print("\n── Pre-cleanup ──")
for _ in range(3):  # up to 3 leftover copies
    r = requests.get(f"{ORCH}/databases", timeout=10).json()
    if "E2ETestDB" in [d["name"] for d in r.get("databases", [])]:
        try:
            orch_prompt("Delete the E2ETestDB database")
            print("  Cleaned up leftover E2ETestDB")
        except Exception:
            break
    else:
        break

# ════════════════════════════════════════════════════════════════════════
# 1. CREATE DATABASE (via orchestrator)
# ════════════════════════════════════════════════════════════════════════
print("\n── 1. Create Database (Orchestrator) ──")

code, data = orch_prompt("Create a database called E2ETestDB with columns: Name (text), Age (number), Active (checkbox)")
print(f"   Response: {json.dumps(data, indent=2)[:300]}")
assert_test(code == 200, f"create_db returns 200 (got {code})")
assert_test(data.get("status") == "success", f"create_db status=success")
result = data.get("result", {})
assert_test(result.get("action_type") == "create_database", f"action_type=create_database (got {result.get('action_type')})")
assert_test("E2ETestDB" in result.get("message", ""), "message contains db name")
db_id = result.get("db_id")
assert_test(db_id is not None, "db_id returned")
props = result.get("properties", [])
assert_test(len(props) >= 2, f"≥2 properties returned (got {len(props)})")

# Verify db appears in /databases
code2, data2 = requests.get(f"{ORCH}/databases", timeout=10).status_code, requests.get(f"{ORCH}/databases", timeout=10).json()
db_names = [d["name"] for d in data2.get("databases", [])]
assert_test("E2ETestDB" in db_names, "E2ETestDB visible in /databases")

# Check icon field exists
assert_test("icon" in result, "icon field present in response")

# ════════════════════════════════════════════════════════════════════════
# 2. CREATE RECORD
# ════════════════════════════════════════════════════════════════════════
print("\n── 2. Create Record ──")

code, data = orch_prompt("Add a record to E2ETestDB with Name: Alice, Age: 30, Active: true")
print(f"   Response: {json.dumps(data, indent=2)[:300]}")
assert_test(code == 200, f"create_record returns 200")
assert_test(data.get("status") == "success", "create_record status=success")
result = data.get("result", {})
assert_test(result.get("action_type") == "insert_block", f"action_type=insert_block (got {result.get('action_type')})")
record_id = result.get("record_id")
assert_test(record_id is not None, "record_id returned")

# ════════════════════════════════════════════════════════════════════════
# 3. ADD PROPERTY
# ════════════════════════════════════════════════════════════════════════
print("\n── 3. Add Property ──")

code, data = orch_prompt("Add a column called Email as text to E2ETestDB")
print(f"   Response: {json.dumps(data, indent=2)[:300]}")
assert_test(code == 200, "add_property returns 200")
result = data.get("result", {})
assert_test(result.get("action_type") == "add_field", f"action_type=add_field (got {result.get('action_type')})")
assert_test("field_name" in result, "field_name in response")
assert_test("db_name" in result, "db_name in response")

# ════════════════════════════════════════════════════════════════════════
# 4. LIST PROPERTIES
# ════════════════════════════════════════════════════════════════════════
print("\n── 4. List Properties ──")

code, data = orch_prompt("What columns does E2ETestDB have?")
print(f"   Response: {json.dumps(data, indent=2)[:300]}")
assert_test(code == 200, "list_properties returns 200")
result = data.get("result", {})
assert_test(result.get("action_type") == "list_fields", f"action_type=list_fields (got {result.get('action_type')})")
prop_list = result.get("properties", [])
assert_test(len(prop_list) >= 3, f"≥3 properties listed (got {len(prop_list)})")

# ════════════════════════════════════════════════════════════════════════
# 5. RENAME PROPERTY
# ════════════════════════════════════════════════════════════════════════
print("\n── 5. Rename Property ──")

code, data = orch_prompt("Rename the Email column to ContactEmail in E2ETestDB")
print(f"   Response: {json.dumps(data, indent=2)[:300]}")
assert_test(code == 200, "rename_property returns 200")
result = data.get("result", {})
assert_test(result.get("action_type") == "rename_field", f"action_type=rename_field (got {result.get('action_type')})")

# ════════════════════════════════════════════════════════════════════════
# 6. DROP PROPERTY
# ════════════════════════════════════════════════════════════════════════
print("\n── 6. Drop Property ──")

code, data = orch_prompt("Drop the ContactEmail column from E2ETestDB")
print(f"   Response: {json.dumps(data, indent=2)[:300]}")
assert_test(code == 200, "drop_property returns 200")
result = data.get("result", {})
assert_test(result.get("action_type") == "drop_field", f"action_type=drop_field (got {result.get('action_type')})")

# ════════════════════════════════════════════════════════════════════════
# 7. APPLY TEMPLATE
# ════════════════════════════════════════════════════════════════════════
print("\n── 7. Apply Template ──")

code, data = orch_prompt("Apply the meeting_notes template")
print(f"   Response: {json.dumps(data, indent=2)[:300]}")
assert_test(code == 200, "apply_template returns 200")
result = data.get("result", {})
assert_test(result.get("action_type") == "create_database", f"template creates database (got {result.get('action_type')})")
tmpl_db_id = result.get("db_id")
assert_test(tmpl_db_id is not None, "template db_id returned")

# ════════════════════════════════════════════════════════════════════════
# 8. LIST TEMPLATES
# ════════════════════════════════════════════════════════════════════════
print("\n── 8. List Templates ──")

code, data = orch_prompt("List all available templates")
print(f"   Response: {json.dumps(data, indent=2)[:300]}")
assert_test(code == 200, "list_templates returns 200")
result = data.get("result", {})
templates = result.get("templates", [])
assert_test(len(templates) >= 9, f"≥9 templates (got {len(templates)})")

# ════════════════════════════════════════════════════════════════════════
# 9. DELETE DATABASE
# ════════════════════════════════════════════════════════════════════════
print("\n── 9. Delete Database ──")

# Delete the template db (if it was created)
if tmpl_db_id:
    code, data = orch_prompt("Delete the Meeting Notes database")
    print(f"   Response: {json.dumps(data, indent=2)[:300]}")
    assert_test(code == 200, "delete_database returns 200")
    result = data.get("result", {})
    assert_test(result.get("action_type") == "delete_database", f"action_type=delete_database (got {result.get('action_type')})")
    assert_test("db_name" in result, "db_name in delete response")
else:
    # Template wasn't created - test delete on a fresh db
    orch_prompt("Create a database called DeleteTestDB with Name (text)")
    code, data = orch_prompt("Delete the DeleteTestDB database")
    print(f"   Response: {json.dumps(data, indent=2)[:300]}")
    assert_test(code == 200, "delete_database returns 200")
    result = data.get("result", {})
    assert_test(result.get("action_type") == "delete_database", f"action_type=delete_database (got {result.get('action_type')})")
    assert_test("db_name" in result, "db_name in delete response")

# ════════════════════════════════════════════════════════════════════════
# 10. WRITING ACTIONS (Summarize, Improve, Explain)
# ════════════════════════════════════════════════════════════════════════
print("\n── 10. Writing Actions ──")

code, data = orch_prompt("Summarize: Machine learning is a subset of artificial intelligence that enables systems to learn from data and improve their performance without being explicitly programmed.")
assert_test(code == 200, "summarize returns 200")
result = data.get("result", {})
assert_test(result.get("action_type") == "text_response", f"summarize action_type=text_response (got {result.get('action_type')})")
assert_test(len(result.get("response", "")) > 10, "summarize returns text")
print(f"   Summary: {result.get('response', '')[:150]}...")

code, data = orch_prompt("Explain this in simple terms: Machine learning uses gradient descent to minimize loss functions through iterative parameter updates")
assert_test(code == 200, "explain returns 200")
result = data.get("result", {})
assert_test(result.get("action_type") == "text_response", f"explain action_type=text_response (got {result.get('action_type')})")
assert_test(len(result.get("response", "")) > 10, "explain returns text")

# ════════════════════════════════════════════════════════════════════════
# 11. CREATE PAGE
# ════════════════════════════════════════════════════════════════════════
print("\n── 11. Create Page ──")

code, data = orch_prompt("Create a page called Q4 Planning Notes with meeting agenda and action items")
print(f"   Response: {json.dumps(data, indent=2)[:500]}")
assert_test(code == 200, "create_page returns 200")
result = data.get("result", {})
assert_test(result.get("action_type") == "create_page", f"action_type=create_page (got {result.get('action_type')})")
assert_test("title" in result, "title in response")
assert_test("icon" in result, "icon in response")
assert_test("content" in result, "content in response")
assert_test("page_id" in result, "page_id in response")
content = result.get("content", {})
blocks = content.get("blocks", [])
assert_test(len(blocks) >= 2, f"≥2 content blocks (got {len(blocks)})")

# Check page was projected to markdown
page_id = result.get("page_id")
title = result.get("title", "")
slug = title.replace(" ", "_").replace("/", "_")
page_path = f"/Users/siddh/Downloads/Projects/APPFlowy-notion Clone/agent_inbox_test/Agent Outputs/Pages/{slug}.md"
if os.path.exists(page_path):
    ok(f"page markdown projected to {slug}.md")
    with open(page_path) as f:
        page_md = f.read()
    assert_test("page_type: page" in page_md, "page markdown has frontmatter")
else:
    fail(f"page markdown not found at {page_path}")

# ════════════════════════════════════════════════════════════════════════
# 12. CONTINUE WRITING
# ════════════════════════════════════════════════════════════════════════
print("\n── 12. Continue Writing ──")

code, data = orch_prompt("Continue writing: The future of AI in healthcare is promising. Early diagnosis through machine learning models has shown remarkable results in")
assert_test(code == 200, "continue_writing returns 200")
result = data.get("result", {})
assert_test(result.get("action_type") == "text_response", f"continue_writing action_type=text_response (got {result.get('action_type')})")
response_text = result.get("response", "")
assert_test(len(response_text) > 30, f"continue_writing returns substantial text ({len(response_text)} chars)")

# ════════════════════════════════════════════════════════════════════════
# 13. NONE ACTION (off-topic)
# ════════════════════════════════════════════════════════════════════════
print("\n── 13. None / Ignored Action ──")

code, data = orch_prompt("Hello, how are you today?")
print(f"   Response: {json.dumps(data, indent=2)[:200]}")
assert_test(code == 200, "greeting returns 200")
assert_test(data.get("status") == "ignored", f"greeting status=ignored (got {data.get('status')})")

# ════════════════════════════════════════════════════════════════════════
# 14. AI PLUGIN BRIDGE (orchestrator-first routing)
# ════════════════════════════════════════════════════════════════════════
print("\n── 14. AI Plugin Bridge ──")

# 14.1 Database operation routed through plugin
code, data = plugin_prompt("What columns does E2ETestDB have?")
print(f"   Plugin→Orch: {json.dumps(data, indent=2)[:300]}")
assert_test(code == 200, "plugin forwards to orchestrator (200)")
result = data.get("result", {})
assert_test(result.get("action_type") == "list_fields", f"plugin routes db action correctly (got {result.get('action_type')})")

# 14.2 Off-topic routed through plugin → orchestrator (ignored) → generic AI
code, data = plugin_prompt("What is the capital of France?")
print(f"   Plugin→Generic: {json.dumps(data, indent=2)[:300]}")
assert_test(code == 200, "plugin fallback to generic AI (200)")
result = data.get("result", {})
# Should have a text response (either from orchestrator or generic fallback)
has_response = result.get("response") or result.get("action_type") == "text_response"
assert_test(has_response, "plugin returns text for off-topic")

# 14.3 Writing shortcut via plugin (fast path)
code, data = plugin_prompt("summarize: Artificial intelligence is transforming industries worldwide. From healthcare to finance, AI-powered solutions are automating complex tasks.")
print(f"   Plugin→Writing: {json.dumps(data, indent=2)[:300]}")
assert_test(code == 200, "plugin writing shortcut (200)")
result = data.get("result", {})
assert_test(result.get("action_type") == "text_response", f"plugin writing shortcut returns text_response (got {result.get('action_type')})")

# ════════════════════════════════════════════════════════════════════════
# 15. CLEANUP — Delete E2ETestDB
# ════════════════════════════════════════════════════════════════════════
print("\n── 15. Cleanup ──")

code, data = orch_prompt("Delete the E2ETestDB database")
assert_test(code == 200, "cleanup: delete E2ETestDB")
result = data.get("result", {})
assert_test(result.get("action_type") == "delete_database", "cleanup: action_type=delete_database")

# Verify gone
r3 = requests.get(f"{ORCH}/databases", timeout=10)
db_names3 = [d["name"] for d in r3.json().get("databases", [])]
assert_test("E2ETestDB" not in db_names3, "cleanup: E2ETestDB removed from /databases")

# ════════════════════════════════════════════════════════════════════════
# SUMMARY
# ════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print(f"  RESULTS: {passed} passed, {failed} failed, {passed + failed} total")
print("=" * 70)
if failed > 0:
    print(f"  ⚠️  {failed} TESTS FAILED")
    sys.exit(1)
else:
    print("  ALL E2E TESTS PASSED ✅")
    sys.exit(0)
