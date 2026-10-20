"""
Comprehensive litmus test for all service, logic, and projection layers.
Runs against a fresh in-memory SQLite database (no LLM, no server needed).
"""
import sys, os, uuid, json, shutil, tempfile

# Setup path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from agent.db.models import Base, Database, Property, Record, Embedding, Page
from agent.db import service as svc
from agent.orchestrator import projection

# ── Helpers ──────────────────────────────────────────────────────────────
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

def assert_test(condition, label, detail=""):
    if condition:
        ok(label)
    else:
        fail(label, detail)

# ── Setup fresh in-memory DB ────────────────────────────────────────────
engine = create_engine("sqlite:///:memory:")
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

# Temp dir for projections
tmp_dir = tempfile.mkdtemp(prefix="litmus_proj_")
projection.APPFLOWY_DB_FOLDER = os.path.join(tmp_dir, "Databases")
projection.APPFLOWY_PAGES_FOLDER = os.path.join(tmp_dir, "Pages")

print("\n" + "=" * 60)
print("  LITMUS UNIT TESTS")
print("=" * 60)

# ════════════════════════════════════════════════════════════════════════
# 1. DATABASE SERVICE CRUD
# ════════════════════════════════════════════════════════════════════════
print("\n── 1. Database Service CRUD ──")

# 1.1 create_database
db1 = svc.create_database(session, "TestDB", "A test database")
assert_test(db1 is not None, "create_database returns object")
assert_test(db1.name == "TestDB", "create_database name correct")
assert_test(db1.description == "A test database", "create_database description correct")
assert_test(isinstance(db1.id, uuid.UUID), "create_database id is UUID")

# 1.2 get_database
fetched = svc.get_database(session, db1.id)
assert_test(fetched is not None, "get_database by id")
assert_test(fetched.name == "TestDB", "get_database name matches")

# 1.3 get_database_by_name
fetched2 = svc.get_database_by_name(session, "TestDB")
assert_test(fetched2 is not None, "get_database_by_name")
assert_test(fetched2.id == db1.id, "get_database_by_name id matches")

# 1.4 get_database_by_name — nonexistent
assert_test(svc.get_database_by_name(session, "NoSuchDB") is None, "get_database_by_name returns None for missing")

# 1.5 list_databases
db2 = svc.create_database(session, "AnotherDB")
dbs = svc.list_databases(session)
assert_test(len(dbs) >= 2, f"list_databases returns ≥2 (got {len(dbs)})")

# 1.6 create_database with empty description
db_no_desc = svc.create_database(session, "NullDescDB")
assert_test(db_no_desc.description is None, "create_database with null description")


# ════════════════════════════════════════════════════════════════════════
# 2. PROPERTY SERVICE CRUD
# ════════════════════════════════════════════════════════════════════════
print("\n── 2. Property Service CRUD ──")

p1 = svc.add_property(session, db1.id, "Name", "text")
assert_test(p1 is not None, "add_property returns object")
assert_test(p1.name == "Name", "add_property name correct")
assert_test(p1.type == "text", "add_property type correct")

p2 = svc.add_property(session, db1.id, "Age", "number")
p3 = svc.add_property(session, db1.id, "Email", "text")

# list_properties
props = svc.list_properties(session, db1.id)
assert_test(len(props) == 3, f"list_properties returns 3 (got {len(props)})")

# get_property_by_name
found = svc.get_property_by_name(session, db1.id, "Age")
assert_test(found is not None, "get_property_by_name found")
assert_test(found.type == "number", "get_property_by_name type correct")

# get_property_by_name — missing
assert_test(svc.get_property_by_name(session, db1.id, "Nope") is None, "get_property_by_name returns None for missing")

# rename_property
renamed = svc.rename_property(session, db1.id, "Age", "Years")
assert_test(renamed is not None, "rename_property returns object")
assert_test(renamed.name == "Years", "rename_property name updated")

# rename_property — nonexistent
assert_test(svc.rename_property(session, db1.id, "Ghost", "NewName") is None, "rename_property returns None for missing")

# delete_property
assert_test(svc.delete_property(session, db1.id, "Email") is True, "delete_property returns True")
assert_test(svc.get_property_by_name(session, db1.id, "Email") is None, "delete_property actually removed")
assert_test(svc.delete_property(session, db1.id, "Email") is False, "delete_property returns False for missing")

# add_property with options
p_sel = svc.add_property(session, db1.id, "Status", "select", options=["Active", "Closed"])
assert_test(p_sel.options == ["Active", "Closed"], "add_property with options")

# ════════════════════════════════════════════════════════════════════════
# 3. RECORD SERVICE CRUD
# ════════════════════════════════════════════════════════════════════════
print("\n── 3. Record Service CRUD ──")

r1 = svc.create_record(session, db1.id, {"Name": "Alice", "Years": 30})
assert_test(r1 is not None, "create_record returns object")
assert_test(r1.data["Name"] == "Alice", "create_record data correct")

r2 = svc.create_record(session, db1.id, {"Name": "Bob", "Years": 25})

# get_record
fetched_r = svc.get_record(session, r1.id)
assert_test(fetched_r is not None, "get_record by id")
assert_test(fetched_r.data["Name"] == "Alice", "get_record data matches")

# get_record — nonexistent
assert_test(svc.get_record(session, uuid.uuid4()) is None, "get_record returns None for missing")

# list_records
recs = svc.list_records(session, db1.id)
assert_test(len(recs) == 2, f"list_records returns 2 (got {len(recs)})")

# update_record
updated = svc.update_record(session, r1.id, {"Name": "Alice Updated", "Years": 31})
assert_test(updated is not None, "update_record returns object")
assert_test(updated.data["Name"] == "Alice Updated", "update_record data changed")

# update_record — nonexistent
assert_test(svc.update_record(session, uuid.uuid4(), {"x": 1}) is None, "update_record returns None for missing")

# delete_record
assert_test(svc.delete_record(session, r2.id) is True, "delete_record returns True")
assert_test(svc.get_record(session, r2.id) is None, "delete_record actually removed")
assert_test(svc.delete_record(session, r2.id) is False, "delete_record returns False for already-deleted")

# ════════════════════════════════════════════════════════════════════════
# 4. DELETE DATABASE (CASCADE)
# ════════════════════════════════════════════════════════════════════════
print("\n── 4. Delete Database (Cascade) ──")

del_db = svc.create_database(session, "ToDelete")
svc.add_property(session, del_db.id, "Col1", "text")
svc.add_property(session, del_db.id, "Col2", "number")
del_rec = svc.create_record(session, del_db.id, {"Col1": "val"})
svc.create_embedding(session, del_rec.id, "test text")

assert_test(svc.delete_database(session, del_db.id) is True, "delete_database returns True")
assert_test(svc.get_database(session, del_db.id) is None, "delete_database removed db")
assert_test(len(svc.list_properties(session, del_db.id)) == 0, "delete_database cascaded properties")
assert_test(len(svc.list_records(session, del_db.id)) == 0, "delete_database cascaded records")
assert_test(svc.delete_database(session, uuid.uuid4()) is False, "delete_database returns False for missing")


# ════════════════════════════════════════════════════════════════════════
# 5. PAGE SERVICE CRUD
# ════════════════════════════════════════════════════════════════════════
print("\n── 5. Page Service CRUD ──")

page1 = svc.create_page(session, title="Meeting Notes", icon="📝",
                         content={"blocks": [{"type": "heading", "level": 1, "text": "Meeting"}]})
assert_test(page1 is not None, "create_page returns object")
assert_test(page1.title == "Meeting Notes", "create_page title correct")
assert_test(page1.icon == "📝", "create_page icon correct")
assert_test(isinstance(page1.content, dict), "create_page content is dict")
assert_test(len(page1.content["blocks"]) == 1, "create_page content has 1 block")
assert_test(isinstance(page1.id, uuid.UUID), "create_page id is UUID")

# get_page
fetched_p = svc.get_page(session, page1.id)
assert_test(fetched_p is not None, "get_page by id")
assert_test(fetched_p.title == "Meeting Notes", "get_page title matches")

# get_page — nonexistent
assert_test(svc.get_page(session, uuid.uuid4()) is None, "get_page returns None for missing")

# create child page
child = svc.create_page(session, title="Sub Page", parent_id=page1.id)
assert_test(child.parent_id == page1.id, "create_page with parent_id")

# list_pages (only root pages)
page2 = svc.create_page(session, title="Journal Entry")
pages = svc.list_pages(session)
root_titles = [p.title for p in pages]
assert_test("Meeting Notes" in root_titles, "list_pages includes root page")
assert_test("Journal Entry" in root_titles, "list_pages includes second root page")
assert_test("Sub Page" not in root_titles, "list_pages excludes child page")

# update_page
updated_p = svc.update_page(session, page1.id, title="Updated Meeting Notes", icon="🗓️")
assert_test(updated_p is not None, "update_page returns object")
assert_test(updated_p.title == "Updated Meeting Notes", "update_page title changed")
assert_test(updated_p.icon == "🗓️", "update_page icon changed")

# update_page — nonexistent
assert_test(svc.update_page(session, uuid.uuid4(), title="X") is None, "update_page returns None for missing")

# delete_page
assert_test(svc.delete_page(session, page2.id) is True, "delete_page returns True")
assert_test(svc.get_page(session, page2.id) is None, "delete_page actually removed")
assert_test(svc.delete_page(session, page2.id) is False, "delete_page returns False for missing")

# create_page with no icon (nullable)
page_no_icon = svc.create_page(session, title="No Icon Page")
assert_test(page_no_icon.icon is None, "create_page icon is None when omitted")

# create_page with empty content
page_empty = svc.create_page(session, title="Empty Page", content=None)
assert_test(page_empty.content is None, "create_page content is None when omitted")

# ════════════════════════════════════════════════════════════════════════
# 6. PROJECTION — Database
# ════════════════════════════════════════════════════════════════════════
print("\n── 6. Projection — Database ──")

proj_db = svc.create_database(session, "ProjectionTest", "Projection test db")
svc.add_property(session, proj_db.id, "Title", "text")
svc.add_property(session, proj_db.id, "Priority", "select")
svc.create_record(session, proj_db.id, {"Title": "Task 1", "Priority": "High"})
svc.create_record(session, proj_db.id, {"Title": "Task 2", "Priority": "Low"})

projection.write_db_page(session, proj_db.id)

index_path = os.path.join(projection.APPFLOWY_DB_FOLDER, "ProjectionTest", "index.md")
assert_test(os.path.exists(index_path), "write_db_page creates index.md")

with open(index_path, 'r') as f:
    content = f.read()

assert_test("agent_managed: true" in content, "index.md has agent_managed frontmatter")
assert_test("page_type: database" in content, "index.md has page_type frontmatter")
assert_test("# ProjectionTest" in content, "index.md has database title")
assert_test("| Title | Priority |" in content, "index.md has table headers")
assert_test("Task 1" in content, "index.md has record data")
assert_test("Task 2" in content, "index.md has second record data")

# Check record pages exist
recs = svc.list_records(session, proj_db.id)
for r in recs:
    rec_path = os.path.join(projection.APPFLOWY_DB_FOLDER, "ProjectionTest", f"{r.id}.md")
    assert_test(os.path.exists(rec_path), f"record page exists: {r.id}")

# Empty database projection
empty_db = svc.create_database(session, "EmptyDB")
svc.add_property(session, empty_db.id, "Col", "text")
projection.write_db_page(session, empty_db.id)
empty_idx = os.path.join(projection.APPFLOWY_DB_FOLDER, "EmptyDB", "index.md")
assert_test(os.path.exists(empty_idx), "empty db projection creates index.md")
with open(empty_idx) as f:
    empty_content = f.read()
assert_test("| Col |" in empty_content, "empty db projection has headers")

# Database with no properties
bare_db = svc.create_database(session, "BareDB")
projection.write_db_page(session, bare_db.id)
bare_idx = os.path.join(projection.APPFLOWY_DB_FOLDER, "BareDB", "index.md")
assert_test(os.path.exists(bare_idx), "bare db (no props) projection creates index.md")

# ════════════════════════════════════════════════════════════════════════
# 7. PROJECTION — Page
# ════════════════════════════════════════════════════════════════════════
print("\n── 7. Projection — Page ──")

proj_page = svc.create_page(session, title="Test Page", icon="🧪",
    content={"blocks": [
        {"type": "heading", "level": 1, "text": "Test Page"},
        {"type": "paragraph", "text": "This is a test paragraph."},
        {"type": "bullet_list", "items": ["Item A", "Item B", "Item C"]},
        {"type": "todo", "text": "Buy milk", "checked": False},
        {"type": "todo", "text": "Done task", "checked": True},
        {"type": "heading", "level": 2, "text": "Section Two"},
    ]})

projection.write_page(session, proj_page.id)

page_path = os.path.join(projection.APPFLOWY_PAGES_FOLDER, "Test_Page.md")
assert_test(os.path.exists(page_path), "write_page creates markdown file")

with open(page_path, 'r') as f:
    pcontent = f.read()

assert_test("page_type: page" in pcontent, "page md has page_type frontmatter")
assert_test("icon:" in pcontent, "page md has icon frontmatter")
assert_test("# Test Page" in pcontent, "page md has title heading")
assert_test("This is a test paragraph." in pcontent, "page md has paragraph")
assert_test("- Item A" in pcontent, "page md has bullet list items")
assert_test("- [ ] Buy milk" in pcontent, "page md has unchecked todo")
assert_test("- [x] Done task" in pcontent, "page md has checked todo")
assert_test("## Section Two" in pcontent, "page md has h2 heading")

# Page with empty content
empty_page = svc.create_page(session, title="Empty Page Proj", icon="", content={"blocks": []})
projection.write_page(session, empty_page.id)
ep_path = os.path.join(projection.APPFLOWY_PAGES_FOLDER, "Empty_Page_Proj.md")
assert_test(os.path.exists(ep_path), "empty page projection creates file")

# Page with None content
none_page = svc.create_page(session, title="None Content", content=None)
projection.write_page(session, none_page.id)
nc_path = os.path.join(projection.APPFLOWY_PAGES_FOLDER, "None_Content.md")
assert_test(os.path.exists(nc_path), "None content page projection creates file")

# ════════════════════════════════════════════════════════════════════════
# 8. EMBEDDING SERVICE
# ════════════════════════════════════════════════════════════════════════
print("\n── 8. Embedding Service ──")

emb_rec = svc.create_record(session, proj_db.id, {"Title": "EmbedTest"})
emb = svc.create_embedding(session, emb_rec.id, "test embedding text")
assert_test(emb is not None, "create_embedding returns object")
assert_test(emb.text == "test embedding text", "create_embedding text correct")
assert_test(emb.record_id == emb_rec.id, "create_embedding record_id matches")

# ════════════════════════════════════════════════════════════════════════
# 9. TEMPLATES
# ════════════════════════════════════════════════════════════════════════
print("\n── 9. Templates ──")

from agent.templates.definitions import get_template, list_templates

templates = list_templates()
expected = ["crm", "tracker", "notes", "meeting_notes", "journal", "contacts", "inventory", "reading_list", "wiki"]
assert_test(len(templates) == 9, f"list_templates returns 9 (got {len(templates)})")
for t in expected:
    assert_test(t in templates, f"template '{t}' exists")

for t_name in expected:
    tmpl = get_template(t_name)
    assert_test(tmpl is not None, f"get_template('{t_name}') returns object")
    assert_test("name" in tmpl, f"template '{t_name}' has name")
    assert_test("properties" in tmpl, f"template '{t_name}' has properties")
    assert_test(len(tmpl["properties"]) > 0, f"template '{t_name}' has ≥1 property")

# Case insensitive
assert_test(get_template("CRM") is not None, "get_template case-insensitive")
assert_test(get_template("nonexistent") is None, "get_template returns None for missing")

# ════════════════════════════════════════════════════════════════════════
# 10. SPECIAL CHARACTERS / EDGE CASES
# ════════════════════════════════════════════════════════════════════════
print("\n── 10. Edge Cases ──")

# Database with special characters in name
special_db = svc.create_database(session, "My DB (Test) #1")
assert_test(special_db.name == "My DB (Test) #1", "db with special chars in name")

# Record with pipe characters (markdown table safety)
pipe_rec = svc.create_record(session, proj_db.id, {"Title": "Has | pipe", "Priority": "A|B"})
assert_test(pipe_rec.data["Title"] == "Has | pipe", "record with pipe chars stored")

# Projection with pipe chars
projection.write_db_page(session, proj_db.id)
with open(index_path, 'r') as f:
    pipe_content = f.read()
# escape_markdown should handle pipes
assert_test("Has" in pipe_content, "projection renders record with pipe chars")

# Record with empty data
empty_rec = svc.create_record(session, proj_db.id, {})
assert_test(empty_rec is not None, "create_record with empty data")
assert_test(empty_rec.data == {}, "create_record empty data is empty dict")

# Unicode in data
unicode_rec = svc.create_record(session, proj_db.id, {"Title": "日本語テスト 🎉", "Priority": "高"})
assert_test(unicode_rec.data["Title"] == "日本語テスト 🎉", "record with unicode data")

# Very long field value
long_val = "x" * 10000
long_rec = svc.create_record(session, proj_db.id, {"Title": long_val})
assert_test(len(long_rec.data["Title"]) == 10000, "record with 10k char value")

# Page with special characters in title
special_page = svc.create_page(session, title="Meeting: Q4/Q1 Review & Planning")
assert_test(special_page.title == "Meeting: Q4/Q1 Review & Planning", "page with special chars in title")

# Page with deeply nested content
deep_content = {"blocks": [{"type": "paragraph", "text": f"Block {i}"} for i in range(100)]}
deep_page = svc.create_page(session, title="Deep Page", content=deep_content)
assert_test(len(deep_page.content["blocks"]) == 100, "page with 100 content blocks")

# ════════════════════════════════════════════════════════════════════════
# CLEANUP & SUMMARY
# ════════════════════════════════════════════════════════════════════════
session.close()
shutil.rmtree(tmp_dir, ignore_errors=True)

print("\n" + "=" * 60)
print(f"  RESULTS: {passed} passed, {failed} failed, {passed + failed} total")
print("=" * 60)

if failed > 0:
    sys.exit(1)
else:
    print("  ALL TESTS PASSED ✅")
    sys.exit(0)
