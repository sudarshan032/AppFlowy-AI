"""
AI Plugin Core Engine

Central orchestrator for AI capabilities.
"""

from typing import Optional, Dict, Any, List
from ..providers import AIProvider, ModelConfig, get_provider, ProviderConfig


class AIEngine:
    """
    Core AI engine that coordinates providers and capabilities.
    
    Usage:
        engine = AIEngine()
        result = await engine.generate("Hello!")
        
        # Switch provider
        engine.set_provider("openai")
    """
    
    def __init__(self, config: Optional[ProviderConfig] = None):
        self._config = config
        self._provider: Optional[AIProvider] = None
    
    @property
    def provider(self) -> AIProvider:
        """Get current provider, initializing if needed."""
        if self._provider is None:
            self._provider = get_provider(self._config)
        return self._provider
    
    def set_provider(self, provider_type: str, **kwargs):
        """Switch to a different provider."""
        from ..providers.base import ProviderType
        self._config = ProviderConfig(
            provider_type=ProviderType(provider_type),
            **kwargs
        )
        self._provider = get_provider(self._config)
    
    async def generate(
        self, 
        prompt: str, 
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096
    ) -> str:
        """Generate text from prompt."""
        config = ModelConfig(
            model_name=model or self._config.model_name if self._config else "default",
            temperature=temperature,
            max_tokens=max_tokens
        )
        return await self.provider.generate(prompt, config)
    
    async def chat(
        self, 
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7
    ) -> str:
        """Chat completion."""
        from ..providers.base import ChatMessage
        chat_messages = [ChatMessage(**msg) for msg in messages]
        config = ModelConfig(
            model_name=model or self._config.model_name if self._config else "default",
            temperature=temperature
        )
        return await self.provider.chat(chat_messages, config)
    
    async def health_check(self) -> Dict[str, Any]:
        """Check provider health."""
        is_healthy = await self.provider.health_check()
        return {
            "provider": self.provider.name,
            "healthy": is_healthy,
            "model": self._config.model_name if self._config else "default"
        }


# Global engine instance
_engine: Optional[AIEngine] = None


def get_engine() -> AIEngine:
    """Get global AI engine instance."""
    global _engine
    if _engine is None:
        # Initialize with default Ollama config
        config = ProviderConfig(model_name="gpt-oss:20b")
        _engine = AIEngine(config)
    return _engine
