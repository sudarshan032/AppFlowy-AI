"""
Comprehensive API Litmus Test for AppFlowy AI Backend

Tests all endpoints on both:
- Orchestrator API (port 8000)
- AI Plugin API (port 8001)
"""

import httpx
import asyncio
import json
from typing import Dict, Any, List, Tuple
import time

# API Base URLs
ORCHESTRATOR_URL = "http://localhost:8000"
AI_PLUGIN_URL = "http://localhost:8001"

# Test Results Storage
results: List[Dict[str, Any]] = []

def log_result(api: str, endpoint: str, method: str, status: str, response: Any, error: str = None, duration: float = 0):
    """Log a test result."""
    result = {
        "api": api,
        "endpoint": endpoint,
        "method": method,
        "status": status,
        "duration_ms": round(duration * 1000, 2),
        "error": error,
        "response_preview": str(response)[:200] if response else None
    }
    results.append(result)
    
    emoji = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
    print(f"{emoji} [{api}] {method} {endpoint} - {status} ({result['duration_ms']}ms)")
    if error:
        print(f"   Error: {error}")


async def test_endpoint(
    client: httpx.AsyncClient,
    api_name: str,
    base_url: str,
    method: str,
    endpoint: str,
    payload: Dict[str, Any] = None,
    expected_status: int = 200
) -> Tuple[bool, Any]:
    """Test a single endpoint."""
    url = f"{base_url}{endpoint}"
    start = time.time()
    
    try:
        if method == "GET":
            response = await client.get(url, timeout=30.0)
        elif method == "POST":
            response = await client.post(url, json=payload, timeout=60.0)
        elif method == "DELETE":
            response = await client.delete(url, timeout=30.0)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        duration = time.time() - start
        
        if response.status_code == expected_status:
            log_result(api_name, endpoint, method, "PASS", response.json() if response.content else None, duration=duration)
            return True, response.json() if response.content else None
        else:
            log_result(api_name, endpoint, method, "FAIL", None, 
                      f"Expected {expected_status}, got {response.status_code}: {response.text[:200]}", duration=duration)
            return False, None
            
    except httpx.ConnectError as e:
        duration = time.time() - start
        log_result(api_name, endpoint, method, "FAIL", None, f"Connection error: {str(e)}", duration=duration)
        return False, None
    except httpx.TimeoutException as e:
        duration = time.time() - start
        log_result(api_name, endpoint, method, "FAIL", None, f"Timeout: {str(e)}", duration=duration)
        return False, None
    except Exception as e:
        duration = time.time() - start
        log_result(api_name, endpoint, method, "FAIL", None, f"Error: {str(e)}", duration=duration)
        return False, None


async def run_orchestrator_tests(client: httpx.AsyncClient):
    """Test all Orchestrator API endpoints."""
    print("\n" + "="*60)
    print("TESTING ORCHESTRATOR API (Port 8000)")
    print("="*60 + "\n")
    
    api = "Orchestrator"
    base = ORCHESTRATOR_URL
    
    # 1. Health/Root Check
    await test_endpoint(client, api, base, "GET", "/")
    
    # 2. Get Logs
    await test_endpoint(client, api, base, "GET", "/logs")
    
    # 3. Get Context
    await test_endpoint(client, api, base, "GET", "/context")
    
    # 4. List Databases
    await test_endpoint(client, api, base, "GET", "/databases")
    
    # 5. Run Prompt - Create Database
    await test_endpoint(client, api, base, "POST", "/run-prompt", {
        "text": "Create a database named TestDB with name, email, and age properties",
        "context": None,
        "scope": "page"
    })
    
    # 6. Run Prompt - Query
    await test_endpoint(client, api, base, "POST", "/run-prompt", {
        "text": "Find all users",
        "context": None,
        "scope": "page"
    })
    
    # 7. Run Prompt - Summarize
    await test_endpoint(client, api, base, "POST", "/run-prompt", {
        "text": "Summarize: AppFlowy is a local-first productivity app",
        "context": None,
        "scope": "page"
    })
    
    # 8. Agent Execute
    await test_endpoint(client, api, base, "POST", "/agent/execute", {
        "prompt": "Create a CRM database with leads, contacts, and deals",
        "context": {}
    })
    
    # 9. Projection - Render All
    await test_endpoint(client, api, base, "POST", "/projection/render_all")


async def run_ai_plugin_tests(client: httpx.AsyncClient):
    """Test all AI Plugin API endpoints."""
    print("\n" + "="*60)
    print("TESTING AI PLUGIN API (Port 8001)")
    print("="*60 + "\n")
    
    api = "AI-Plugin"
    base = AI_PLUGIN_URL
    
    # === Root & Health ===
    print("\n--- Root & Health ---")
    await test_endpoint(client, api, base, "GET", "/")
    await test_endpoint(client, api, base, "GET", "/health")
    
    # === Provider Endpoints ===
    print("\n--- Provider Endpoints ---")
    await test_endpoint(client, api, base, "GET", "/ai/providers/list")
    await test_endpoint(client, api, base, "GET", "/ai/providers/current")
    await test_endpoint(client, api, base, "GET", "/ai/providers/health")
    
    # === Writing AI Endpoints ===
    print("\n--- Writing AI Endpoints ---")
    
    sample_text = "The quick brown fox jumps over the lazy dog. This is a sample text for testing AI writing capabilities."
    
    await test_endpoint(client, api, base, "POST", "/ai/writing/summarize", {
        "text": sample_text,
        "style": "concise",
        "max_sentences": 2
    })
    
    await test_endpoint(client, api, base, "POST", "/ai/writing/improve", {
        "text": "this text needs improvment and has some issues with grammer",
        "focus": "grammar"
    })
    
    await test_endpoint(client, api, base, "POST", "/ai/writing/fix-grammar", {
        "text": "Their going to the store tommorow"
    })
    
    await test_endpoint(client, api, base, "POST", "/ai/writing/change-tone", {
        "text": "Hey, what's up? Can you help me with this thing?",
        "tone": "professional"
    })
    
    await test_endpoint(client, api, base, "POST", "/ai/writing/translate", {
        "text": "Hello, how are you?",
        "target_language": "Spanish",
        "preserve_formatting": True
    })
    
    await test_endpoint(client, api, base, "POST", "/ai/writing/make-longer", {
        "text": "AI is transforming productivity.",
        "style": "expand"
    })
    
    await test_endpoint(client, api, base, "POST", "/ai/writing/make-shorter", {
        "text": "In conclusion, after careful consideration of all the various factors and elements that were presented throughout this extensive discussion, it becomes abundantly clear that the final determination must be made.",
        "aggressive": True
    })
    
    await test_endpoint(client, api, base, "POST", "/ai/writing/explain", {
        "text": "Machine learning algorithms optimize parameters through gradient descent on a loss function.",
        "audience": "beginner"
    })
    
    await test_endpoint(client, api, base, "POST", "/ai/writing/continue", {
        "text": "Once upon a time, in a land far away, there lived a brave knight who",
        "style": "narrative",
        "length": "paragraph"
    })
    
    await test_endpoint(client, api, base, "GET", "/ai/writing/tones")
    
    # === Database AI Endpoints ===
    print("\n--- Database AI Endpoints ---")
    
    await test_endpoint(client, api, base, "POST", "/ai/database/autofill", {
        "content": "John Smith is a software engineer at Google with 5 years of experience",
        "property_name": "job_title",
        "property_type": "text",
        "existing_values": ["Engineer", "Manager", "Designer"],
        "context": "Employee database"
    })
    
    await test_endpoint(client, api, base, "POST", "/ai/database/formula", {
        "description": "Calculate total price by multiplying quantity and unit price",
        "columns": [
            {"name": "quantity", "type": "number"},
            {"name": "unit_price", "type": "number"}
        ],
        "database_context": "Sales database"
    })
    
    await test_endpoint(client, api, base, "POST", "/ai/database/categorize", {
        "content": "Need help resetting my password for the admin portal",
        "categories": ["Technical Support", "Billing", "Sales", "General Inquiry"],
        "allow_new": False
    })
    
    await test_endpoint(client, api, base, "POST", "/ai/database/extract", {
        "content": "Contact: John Doe, Email: john@example.com, Phone: 555-1234, Company: Acme Corp",
        "fields": ["name", "email", "phone", "company"]
    })
    
    await test_endpoint(client, api, base, "POST", "/ai/database/summary", {
        "content": "The quarterly sales report shows a 15% increase in revenue compared to last quarter. Key drivers include new product launches in the enterprise segment and expansion into the Asian market. Customer retention rate improved to 92%.",
        "max_words": 30
    })
    
    # === Agent Endpoints ===
    print("\n--- Agent Endpoints ---")
    
    await test_endpoint(client, api, base, "GET", "/ai/agents/actions")
    
    await test_endpoint(client, api, base, "POST", "/ai/agents/simple", {
        "task": "Analyze the sentiment of this feedback: The product is amazing and exceeded my expectations!",
        "context": "Customer feedback analysis"
    })
    
    await test_endpoint(client, api, base, "POST", "/ai/agents/batch", {
        "items": [
            "Great product, love it!",
            "Terrible experience, would not recommend",
            "It's okay, nothing special"
        ],
        "action": "sentiment",
        "batch_size": 3
    })
    
    await test_endpoint(client, api, base, "POST", "/ai/agents/chain", {
        "input_text": "Machine learning is revolutionizing how we process data",
        "actions": ["summarize", "translate_spanish"]
    })
    
    await test_endpoint(client, api, base, "POST", "/ai/agents/workflow", {
        "steps": [
            {
                "action": "generate",
                "input_key": "input",
                "output_key": "summary",
                "params": {"prompt_template": "Summarize: {input}"}
            }
        ],
        "initial_context": {"input": "This is a test document about AI capabilities."}
    })
    
    # === Q&A Endpoints ===
    print("\n--- Q&A Endpoints ---")
    
    # Index a test document first
    success, doc_result = await test_endpoint(client, api, base, "POST", "/ai/qa/index", {
        "title": "Test Document",
        "content": "AppFlowy is an open-source alternative to Notion. It provides local-first data storage and AI capabilities.",
        "metadata": {"type": "documentation", "version": "1.0"}
    })
    
    await test_endpoint(client, api, base, "GET", "/ai/qa/documents")
    
    await test_endpoint(client, api, base, "POST", "/ai/qa/search", {
        "query": "What is AppFlowy?",
        "top_k": 3
    })
    
    await test_endpoint(client, api, base, "POST", "/ai/qa/ask", {
        "question": "What are the key features of AppFlowy?",
        "context_docs": None
    })
    
    await test_endpoint(client, api, base, "GET", "/ai/qa/summary")
    
    # Index batch documents
    await test_endpoint(client, api, base, "POST", "/ai/qa/index-batch", [
        {
            "title": "Document 1",
            "content": "This is the first test document.",
            "metadata": {}
        },
        {
            "title": "Document 2", 
            "content": "This is the second test document.",
            "metadata": {}
        }
    ])
    
    # === Run-Prompt Bridge ===
    print("\n--- Run-Prompt Bridge ---")
    
    await test_endpoint(client, api, base, "POST", "/run-prompt", {
        "text": "summarize",
        "context": {"selected_text": "This is a long document that needs summarization."},
        "scope": "page"
    })
    
    await test_endpoint(client, api, base, "POST", "/run-prompt", {
        "text": "improve writing",
        "context": {"selected_text": "this text need to be better written"},
        "scope": "page"
    })
    
    await test_endpoint(client, api, base, "POST", "/run-prompt", {
        "text": "explain this concept",
        "context": {"selected_text": "Quantum entanglement"},
        "scope": "page"
    })


async def run_all_tests():
    """Run all API tests."""
    print("\n" + "="*60)
    print("APPFLOWY AI BACKEND - COMPREHENSIVE LITMUS TEST")
    print("="*60)
    print(f"\nStarted at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Orchestrator API: {ORCHESTRATOR_URL}")
    print(f"AI Plugin API: {AI_PLUGIN_URL}")
    
    async with httpx.AsyncClient() as client:
        # Test Orchestrator API
        await run_orchestrator_tests(client)
        
        # Test AI Plugin API
        await run_ai_plugin_tests(client)
    
    # Print Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = [r for r in results if r["status"] == "PASS"]
    failed = [r for r in results if r["status"] == "FAIL"]
    
    print(f"\n✅ PASSED: {len(passed)}")
    print(f"❌ FAILED: {len(failed)}")
    print(f"📊 TOTAL:  {len(results)}")
    print(f"📈 Success Rate: {len(passed)/len(results)*100:.1f}%")
    
    # Group by API
    print("\n--- By API ---")
    for api in ["Orchestrator", "AI-Plugin"]:
        api_results = [r for r in results if r["api"] == api]
        api_passed = [r for r in api_results if r["status"] == "PASS"]
        print(f"  {api}: {len(api_passed)}/{len(api_results)} passed")
    
    # Show Failed Tests
    if failed:
        print("\n--- Failed Tests ---")
        for r in failed:
            print(f"  ❌ [{r['api']}] {r['method']} {r['endpoint']}")
            print(f"     Error: {r['error']}")
    
    # Average Response Time
    avg_time = sum(r["duration_ms"] for r in results) / len(results) if results else 0
    print(f"\n⏱️  Average Response Time: {avg_time:.2f}ms")
    
    print(f"\nCompleted at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    return results


if __name__ == "__main__":
    asyncio.run(run_all_tests())
