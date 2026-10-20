"""
Schema Operations Litmus Test for AppFlowy AI Agent

Tests drop_property, add_property, rename_property, and list_properties actions.
"""

import httpx
import json
import time

BASE_URL = "http://localhost:8000"

def test_prompt(prompt: str, expected_action_type: str = None) -> dict:
    """Test a single prompt and return the result."""
    print(f"\n{'='*60}")
    print(f"PROMPT: {prompt}")
    print(f"{'='*60}")
    
    start = time.time()
    response = httpx.post(
        f"{BASE_URL}/run-prompt",
        json={"text": prompt, "context": None},
        timeout=120.0
    )
    duration = time.time() - start
    
    result = response.json()
    print(f"STATUS: {result.get('status')}")
    print(f"DURATION: {duration:.2f}s")
    
    if "result" in result:
        r = result["result"]
        print(f"MESSAGE: {r.get('message', r.get('response', 'N/A')[:100])}")
        print(f"ACTION TYPE: {r.get('action_type')}")
        
        if "properties" in r:
            print(f"PROPERTIES: {[p['name'] for p in r['properties']]}")
        
        # Check expected action type if specified
        if expected_action_type and r.get("action_type") != expected_action_type:
            print(f"⚠️  EXPECTED: {expected_action_type}, GOT: {r.get('action_type')}")
            return {"passed": False, "result": result, "prompt": prompt}
    
    is_pass = result.get("status") == "success"
    print(f"RESULT: {'✅ PASS' if is_pass else '❌ FAIL'}")
    
    return {"passed": is_pass, "result": result, "prompt": prompt}


def run_litmus_test():
    """Run comprehensive schema operations litmus test."""
    print("\n" + "="*60)
    print("SCHEMA OPERATIONS LITMUS TEST")
    print("="*60)
    print(f"Started at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Target: {BASE_URL}")
    
    tests = []
    
    # Test 1: List current columns
    tests.append(test_prompt(
        "List all columns in CRM",
        expected_action_type="list_fields"
    ))
    
    # Test 2: Add a new column
    tests.append(test_prompt(
        "Add a column called test_column as text to CRM",
        expected_action_type="add_field"
    ))
    
    # Test 3: List columns again to verify
    tests.append(test_prompt(
        "What columns does CRM have?",
        expected_action_type="list_fields"
    ))
    
    # Test 4: Rename the column
    tests.append(test_prompt(
        "Rename test_column to renamed_column in CRM",
        expected_action_type="rename_field"
    ))
    
    # Test 5: List to verify rename
    tests.append(test_prompt(
        "Show me the columns in CRM database",
        expected_action_type="list_fields"
    ))
    
    # Test 6: Drop the column
    tests.append(test_prompt(
        "Drop renamed_column from CRM",
        expected_action_type="drop_field"
    ))
    
    # Test 7: Final list to verify drop
    tests.append(test_prompt(
        "List columns in CRM",
        expected_action_type="list_fields"
    ))
    
    # Summary
    print("\n" + "="*60)
    print("LITMUS TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for t in tests if t["passed"])
    failed = sum(1 for t in tests if not t["passed"])
    
    print(f"\n✅ PASSED: {passed}")
    print(f"❌ FAILED: {failed}")
    print(f"📊 TOTAL: {len(tests)}")
    print(f"📈 Success Rate: {passed/len(tests)*100:.1f}%")
    
    if failed > 0:
        print("\n--- Failed Tests ---")
        for t in tests:
            if not t["passed"]:
                print(f"  ❌ {t['prompt']}")
    
    print(f"\nCompleted at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    return passed == len(tests)


if __name__ == "__main__":
    success = run_litmus_test()
    exit(0 if success else 1)
