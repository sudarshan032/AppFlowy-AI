"""
AI Plugin FastAPI Application

Standalone API service for AI capabilities.
Includes all Phase 1-7 feature routes.
"""

import os
import time
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import database, writing, providers, agents, qa


def create_app() -> FastAPI:
    """Create and configure the FastAPI application with all routes."""
    app = FastAPI(
        title="AppFlowy AI Plugin",
        description="Modular AI capabilities for AppFlowy — Notion AI Clone",
        version="2.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS for AppFlowy integration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # =========================================================================
    # CORE ROUTES (Phase 1-2)
    # =========================================================================
    app.include_router(database.router)
    app.include_router(writing.router)
    app.include_router(providers.router)
    app.include_router(agents.router)
    app.include_router(qa.router)

    # =========================================================================
    # PHASE 3-7 ROUTES (Loaded dynamically to handle missing dependencies)
    # =========================================================================
    try:
        from .routes import meeting
        app.include_router(meeting.router)
    except ImportError:
        pass

    try:
        from .routes import connectors
        app.include_router(connectors.router)
    except ImportError:
        pass

    try:
        from .routes import translation
        app.include_router(translation.router)
    except ImportError:
        pass

    try:
        from .routes import sites
        app.include_router(sites.router)
    except ImportError:
        pass

    # =========================================================================
    # ROOT & HEALTH ENDPOINTS
    # =========================================================================

    @app.get("/")
    async def root():
        return {
            "name": "AppFlowy AI Plugin",
            "version": "2.0.0",
            "status": "running",
            "endpoints": [
                "/ai/database/*",
                "/ai/writing/*",
                "/ai/providers/*",
                "/ai/agents/*",
                "/ai/qa/*",
                "/ai/meeting/*",
                "/ai/connectors/*",
                "/ai/translation/*",
                "/ai/sites/*",
            ]
        }

    @app.get("/health")
    async def health():
        """Comprehensive health check for all services."""
        health_status = {
            "status": "healthy",
            "timestamp": time.time(),
            "services": {}
        }

        # Check AI Engine
        try:
            from ..core import get_engine
            engine = get_engine()
            engine_health = await engine.health_check()
            health_status["services"]["ai_engine"] = engine_health
        except Exception as e:
            health_status["services"]["ai_engine"] = {"healthy": False, "error": str(e)}

        # Check Qdrant
        try:
            from agent.db.vector_store import VectorStore
            vs = VectorStore()
            qdrant_ok = vs.health_check()
            health_status["services"]["qdrant"] = {"healthy": qdrant_ok}
        except Exception as e:
            health_status["services"]["qdrant"] = {"healthy": False, "error": str(e)}

        # Check Redis
        try:
            import redis
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            r = redis.from_url(redis_url, socket_timeout=3)
            r.ping()
            health_status["services"]["redis"] = {"healthy": True}
        except Exception as e:
            health_status["services"]["redis"] = {"healthy": False, "error": str(e)}

        # Check Database
        try:
            from agent.db.database import SessionLocal
            db = SessionLocal()
            db.execute("SELECT 1" if hasattr(db, 'execute') else None)
            db.close()
            health_status["services"]["database"] = {"healthy": True}
        except Exception as e:
            health_status["services"]["database"] = {"healthy": False, "error": str(e)}

        # Overall status
        any_unhealthy = any(
            not svc.get("healthy", False)
            for svc in health_status["services"].values()
        )
        if any_unhealthy:
            health_status["status"] = "degraded"

        return health_status

    # =========================================================================
    # BRIDGE ENDPOINT (Flutter AiAgentClient compatibility)
    # =========================================================================
    from pydantic import BaseModel
    from typing import Any

    class PromptRequest(BaseModel):
        text: str
        context: Any = None
        scope: str = "page"

    @app.post("/run-prompt")
    async def run_prompt(request: PromptRequest):
        """
        Bridge endpoint for Flutter's AiAgentClient.
        Orchestrator-first: forward everything to orchestrator, fall back to generic AI.
        """
        import httpx

        prompt = request.text.lower().strip()
        context = request.context or {}

        # Fast path: writing shortcuts
        writing_shortcuts = {
            "summarize": "summarize",
            "improve": "improve_writing",
            "fix grammar": "fix_grammar",
            "fix spelling": "fix_grammar",
            "make shorter": "make_shorter",
            "shorter": "make_shorter",
            "make longer": "make_longer",
            "longer": "make_longer",
            "translate": "translate",
            "explain": "explain",
            "brainstorm": "brainstorm",
            "outline": "outline",
        }

        for keyword, method_name in writing_shortcuts.items():
            if prompt.startswith(keyword) or prompt == keyword:
                try:
                    from ..capabilities.writing import get_writing_ai
                    writing_ai = get_writing_ai()
                    text_to_process = context.get("selected_text", request.text)
                    if hasattr(writing_ai, method_name):
                        handler = getattr(writing_ai, method_name)
                        result = await handler(text=text_to_process)
                    else:
                        from ..core import get_engine
                        engine = get_engine()
                        result = await engine.generate(f"{method_name}: {text_to_process}")
                    return {"status": "success", "result": {"response": result, "action_type": "text_response"}}
                except Exception as e:
                    return {"status": "error", "error": str(e)}

        # Default path: forward to orchestrator
        orchestrator_url = os.getenv("ORCHESTRATOR_URL", "http://localhost:8000")
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{orchestrator_url}/run-prompt",
                    json={"text": request.text, "context": context}
                )
                if response.status_code == 200:
                    data = response.json()
                    if data.get("status") == "ignored":
                        from ..core import get_engine
                        engine = get_engine()
                        result = await engine.generate(request.text)
                        return {"status": "success", "result": {"response": result, "action_type": "text_response"}}
                    return data
                else:
                    from ..core import get_engine
                    engine = get_engine()
                    result = await engine.generate(request.text)
                    return {"status": "success", "result": {"response": result, "action_type": "text_response"}}
        except Exception:
            try:
                from ..core import get_engine
                engine = get_engine()
                result = await engine.generate(request.text)
                return {"status": "success", "result": {"response": result, "action_type": "text_response"}}
            except Exception as e:
                return {"status": "error", "error": str(e)}

    return app


# Create default app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
