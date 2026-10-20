"""
Ollama Provider Implementation

Wraps the Ollama local LLM server for the AI plugin.
Uses direct HTTP calls for reliability and no deprecated dependencies.
"""

import os
import json
from typing import List, Optional, AsyncIterator
import httpx

from .base import AIProvider, ModelConfig, ChatMessage, ProviderType


class OllamaProvider(AIProvider):
    """
    Ollama provider for local LLM inference.
    
    Default model and URL can be configured via environment variables:
    - OLLAMA_MODEL: Model name (default: gpt-oss:20b)
    - OLLAMA_BASE_URL: Server URL (default: http://localhost:11434)
    """
    
    def __init__(
        self, 
        model_name: Optional[str] = None,
        base_url: Optional[str] = None
    ):
        self.default_model = model_name or os.getenv("OLLAMA_MODEL", "gpt-oss:20b")
        self.base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        
    @property
    def name(self) -> str:
        return "ollama"
    
    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.OLLAMA
    
    def _get_model_name(self, config: Optional[ModelConfig]) -> str:
        """Get model name from config or default."""
        return config.model_name if config else self.default_model
    
    async def generate(
        self, 
        prompt: str, 
        config: Optional[ModelConfig] = None
    ) -> str:
        """Generate text from a prompt using Ollama."""
        model_name = self._get_model_name(config)
        temperature = config.temperature if config else 0.7
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": temperature}
                },
                timeout=120.0
            )
            response.raise_for_status()
            data = response.json()
            return data.get("response", "")
    
    async def chat(
        self, 
        messages: List[ChatMessage], 
        config: Optional[ModelConfig] = None
    ) -> str:
        """Chat completion with message history."""
        model_name = self._get_model_name(config)
        temperature = config.temperature if config else 0.7
        
        # Convert to Ollama message format
        ollama_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": model_name,
                    "messages": ollama_messages,
                    "stream": False,
                    "options": {"temperature": temperature}
                },
                timeout=120.0
            )
            response.raise_for_status()
            data = response.json()
            return data.get("message", {}).get("content", "")
    
    async def stream_generate(
        self, 
        prompt: str, 
        config: Optional[ModelConfig] = None
    ) -> AsyncIterator[str]:
        """Stream text generation from Ollama."""
        model_name = self._get_model_name(config)
        temperature = config.temperature if config else 0.7
        
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/generate",
                json={
                    "model": model_name,
                    "prompt": prompt,
                    "stream": True,
                    "options": {"temperature": temperature}
                },
                timeout=120.0
            ) as response:
                async for line in response.aiter_lines():
                    if line:
                        data = json.loads(line)
                        if "response" in data:
                            yield data["response"]
    
    async def embed(self, text: str) -> List[float]:
        """Generate embeddings using Ollama's embedding API."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/embeddings",
                json={
                    "model": self.default_model,
                    "prompt": text
                },
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()
            return data.get("embedding", [])
    
    async def health_check(self) -> bool:
        """Check if Ollama server is running."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/tags",
                    timeout=5.0
                )
                return response.status_code == 200
        except Exception:
            return False
