"""
OpenAI Provider Implementation

Wraps OpenAI API for cloud-based LLM inference.
"""

import os
from typing import List, Optional, AsyncIterator

from .base import AIProvider, ModelConfig, ChatMessage, ProviderType


class OpenAIProvider(AIProvider):
    """
    OpenAI provider for cloud LLM inference.
    
    Requires:
    - OPENAI_API_KEY environment variable or api_key parameter
    
    Default model: gpt-4o-mini
    """
    
    def __init__(
        self, 
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        base_url: Optional[str] = None
    ):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key required. Set OPENAI_API_KEY env var or pass api_key.")
        
        self.default_model = model_name or "gpt-4o-mini"
        self.base_url = base_url or "https://api.openai.com/v1"
        
        # Lazy import to avoid dependency if not using OpenAI
        try:
            from openai import AsyncOpenAI
            self.client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)
        except ImportError:
            raise ImportError("openai package required. Install with: pip install openai")
    
    @property
    def name(self) -> str:
        return "openai"
    
    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.OPENAI
    
    def _get_model_name(self, config: Optional[ModelConfig]) -> str:
        """Get model name from config or default."""
        return config.model_name if config else self.default_model
    
    async def generate(
        self, 
        prompt: str, 
        config: Optional[ModelConfig] = None
    ) -> str:
        """Generate text from a prompt using OpenAI."""
        model = self._get_model_name(config)
        temperature = config.temperature if config else 0.7
        max_tokens = config.max_tokens if config else 4096
        
        response = await self.client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content
    
    async def chat(
        self, 
        messages: List[ChatMessage], 
        config: Optional[ModelConfig] = None
    ) -> str:
        """Chat completion with message history."""
        model = self._get_model_name(config)
        temperature = config.temperature if config else 0.7
        max_tokens = config.max_tokens if config else 4096
        
        # Convert to OpenAI message format
        openai_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]
        
        response = await self.client.chat.completions.create(
            model=model,
            messages=openai_messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content
    
    async def stream_generate(
        self, 
        prompt: str, 
        config: Optional[ModelConfig] = None
    ) -> AsyncIterator[str]:
        """Stream text generation from OpenAI."""
        model = self._get_model_name(config)
        temperature = config.temperature if config else 0.7
        
        stream = await self.client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            stream=True,
        )
        
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    
    async def embed(self, text: str) -> List[float]:
        """Generate embeddings using OpenAI's embedding API."""
        response = await self.client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        return response.data[0].embedding
    
    async def health_check(self) -> bool:
        """Check if OpenAI API is accessible."""
        try:
            await self.client.models.list()
            return True
        except Exception:
            return False
