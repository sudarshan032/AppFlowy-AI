"""
Provider Management API Routes

Routes for managing and switching AI providers.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from ...providers import get_provider, ProviderConfig, list_available_providers
from ...providers.base import ProviderType
from ...core import get_engine


router = APIRouter(prefix="/ai/providers", tags=["Providers"])


class SwitchProviderRequest(BaseModel):
    """Request to switch providers."""
    provider: str  # ollama, openai, anthropic
    model: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response."""
    provider: str
    healthy: bool
    model: Optional[str] = None


@router.get("/list")
async def list_providers():
    """List available AI providers."""
    return {"providers": list_available_providers()}


@router.get("/current")
async def get_current_provider():
    """Get current provider info."""
    provider = get_provider()
    return {
        "name": provider.name,
        "type": provider.provider_type.value
    }


@router.post("/switch")
async def switch_provider(request: SwitchProviderRequest):
    """Switch to a different AI provider."""
    try:
        provider_type = ProviderType(request.provider.lower())
        engine = get_engine()
        engine.set_provider(provider_type.value, model_name=request.model)
        return {
            "success": True,
            "provider": request.provider,
            "model": request.model
        }
    except ValueError:
        raise HTTPException(
            status_code=400, 
            detail=f"Unknown provider: {request.provider}. Available: ollama, openai, anthropic"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Check current provider health."""
    try:
        engine = get_engine()
        health = await engine.health_check()
        return HealthResponse(**health)
    except Exception as e:
        return HealthResponse(provider="unknown", healthy=False)
