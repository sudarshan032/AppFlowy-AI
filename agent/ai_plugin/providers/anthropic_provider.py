"""
Anthropic Provider Implementation

Wraps Anthropic's Claude API for cloud-based LLM inference.
"""

import os
from typing import List, Optional, AsyncIterator

from .base import AIProvider, ModelConfig, ChatMessage, ProviderType


class AnthropicProvider(AIProvider):
    """
    Anthropic provider for Claude models.
    
    Requires:
    - ANTHROPIC_API_KEY environment variable or api_key parameter
    
    Default model: claude-3-5-sonnet-20241022
    """
    
    def __init__(
        self, 
        api_key: Optional[str] = None,
        model_name: Optional[str] = None
    ):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("Anthropic API key required. Set ANTHROPIC_API_KEY env var or pass api_key.")
        
        self.default_model = model_name or "claude-3-5-sonnet-20241022"
        
        # Lazy import
        try:
            from anthropic import AsyncAnthropic
            self.client = AsyncAnthropic(api_key=self.api_key)
        except ImportError:
            raise ImportError("anthropic package required. Install with: pip install anthropic")
    
    @property
    def name(self) -> str:
        return "anthropic"
    
    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.ANTHROPIC
    
    def _get_model_name(self, config: Optional[ModelConfig]) -> str:
        """Get model name from config or default."""
        return config.model_name if config else self.default_model
    
    async def generate(
        self, 
        prompt: str, 
        config: Optional[ModelConfig] = None
    ) -> str:
        """Generate text from a prompt using Claude."""
        model = self._get_model_name(config)
        temperature = config.temperature if config else 0.7
        max_tokens = config.max_tokens if config else 4096
        
        response = await self.client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
        )
        return response.content[0].text
    
    async def chat(
        self, 
        messages: List[ChatMessage], 
        config: Optional[ModelConfig] = None
    ) -> str:
        """Chat completion with message history."""
        model = self._get_model_name(config)
        temperature = config.temperature if config else 0.7
        max_tokens = config.max_tokens if config else 4096
        
        # Extract system message if present
        system_msg = None
        chat_messages = []
        
        for msg in messages:
            if msg.role == "system":
                system_msg = msg.content
            else:
                chat_messages.append({
                    "role": msg.role,
                    "content": msg.content
                })
        
        kwargs = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": chat_messages,
            "temperature": temperature,
        }
        
        if system_msg:
            kwargs["system"] = system_msg
        
        response = await self.client.messages.create(**kwargs)
        return response.content[0].text
    
    async def stream_generate(
        self, 
        prompt: str, 
        config: Optional[ModelConfig] = None
    ) -> AsyncIterator[str]:
        """Stream text generation from Claude."""
        model = self._get_model_name(config)
        temperature = config.temperature if config else 0.7
        max_tokens = config.max_tokens if config else 4096
        
        async with self.client.messages.stream(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
        ) as stream:
            async for text in stream.text_stream:
                yield text
    
    async def health_check(self) -> bool:
        """Check if Anthropic API is accessible."""
        try:
            # Simple test with minimal tokens
            await self.client.messages.create(
                model=self.default_model,
                max_tokens=1,
                messages=[{"role": "user", "content": "hi"}],
            )
            return True
        except Exception:
            return False
