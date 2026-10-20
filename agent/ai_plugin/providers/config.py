"""
Provider Configuration and Registry

Manages provider selection and switching at runtime.
"""

import os
from typing import Dict, Optional, Type
from enum import Enum

from .base import AIProvider, ProviderType, ModelConfig


# Provider Registry - maps type to class
_PROVIDER_REGISTRY: Dict[ProviderType, Type[AIProvider]] = {}


def register_provider(provider_type: ProviderType):
    """Decorator to register a provider class."""
    def decorator(cls: Type[AIProvider]):
        _PROVIDER_REGISTRY[provider_type] = cls
        return cls
    return decorator


# Register built-in providers
def _register_builtin_providers():
    """Register all built-in providers."""
    from .ollama_provider import OllamaProvider
    _PROVIDER_REGISTRY[ProviderType.OLLAMA] = OllamaProvider
    
    try:
        from .openai_provider import OpenAIProvider
        _PROVIDER_REGISTRY[ProviderType.OPENAI] = OpenAIProvider
    except (ImportError, ValueError):
        pass  # OpenAI not available
    
    try:
        from .anthropic_provider import AnthropicProvider
        _PROVIDER_REGISTRY[ProviderType.ANTHROPIC] = AnthropicProvider
    except (ImportError, ValueError):
        pass  # Anthropic not available


class ProviderConfig:
    """
    Configuration for AI providers.
    
    Environment variables:
    - AI_PROVIDER: Provider type (ollama, openai, anthropic)
    - AI_MODEL: Default model name
    - OLLAMA_BASE_URL: Ollama server URL
    - OPENAI_API_KEY: OpenAI API key
    - ANTHROPIC_API_KEY: Anthropic API key
    """
    
    def __init__(
        self,
        provider_type: Optional[ProviderType] = None,
        model_name: Optional[str] = None,
        **kwargs
    ):
        # Get provider type from env or default to Ollama
        provider_str = os.getenv("AI_PROVIDER", "ollama").lower()
        self.provider_type = provider_type or ProviderType(provider_str)
        
        # Model defaults per provider
        self.model_defaults = {
            ProviderType.OLLAMA: "gpt-oss:20b",
            ProviderType.OPENAI: "gpt-4o-mini",
            ProviderType.ANTHROPIC: "claude-3-5-sonnet-20241022",
        }
        
        self.model_name = model_name or os.getenv("AI_MODEL") or self.model_defaults.get(self.provider_type)
        self.extra_config = kwargs
    
    def get_model_config(self, **overrides) -> ModelConfig:
        """Get ModelConfig with optional overrides."""
        config = {
            "model_name": self.model_name,
            **self.extra_config,
            **overrides
        }
        return ModelConfig(**config)


# Global provider instance (singleton pattern)
_current_provider: Optional[AIProvider] = None
_current_config: Optional[ProviderConfig] = None


def get_provider(config: Optional[ProviderConfig] = None) -> AIProvider:
    """
    Get the current AI provider instance.
    
    Creates a new provider if:
    - No provider exists
    - Config has changed
    
    Args:
        config: Optional provider configuration
        
    Returns:
        AIProvider instance
    """
    global _current_provider, _current_config
    
    # Ensure providers are registered
    if not _PROVIDER_REGISTRY:
        _register_builtin_providers()
    
    # Use existing or create default config
    if config is None:
        if _current_config is None:
            config = ProviderConfig()
        else:
            config = _current_config
    
    # Check if we need a new provider
    needs_new_provider = (
        _current_provider is None or
        _current_config is None or
        config.provider_type != _current_config.provider_type
    )
    
    if needs_new_provider:
        # Get provider class
        provider_cls = _PROVIDER_REGISTRY.get(config.provider_type)
        if provider_cls is None:
            raise ValueError(f"Provider {config.provider_type} not available. "
                           f"Available: {list(_PROVIDER_REGISTRY.keys())}")
        
        # Create provider instance
        if config.provider_type == ProviderType.OLLAMA:
            _current_provider = provider_cls(model_name=config.model_name)
        elif config.provider_type == ProviderType.OPENAI:
            _current_provider = provider_cls(model_name=config.model_name)
        elif config.provider_type == ProviderType.ANTHROPIC:
            _current_provider = provider_cls(model_name=config.model_name)
        else:
            _current_provider = provider_cls()
        
        _current_config = config
    
    return _current_provider


def set_provider(provider_type: ProviderType, **kwargs) -> AIProvider:
    """
    Switch to a different provider.
    
    Args:
        provider_type: The provider type to switch to
        **kwargs: Additional provider-specific configuration
        
    Returns:
        The new AIProvider instance
    """
    config = ProviderConfig(provider_type=provider_type, **kwargs)
    return get_provider(config)


def list_available_providers() -> Dict[str, bool]:
    """
    List all providers and their availability.
    
    Returns:
        Dict mapping provider name to availability
    """
    if not _PROVIDER_REGISTRY:
        _register_builtin_providers()
    
    return {
        provider_type.value: provider_type in _PROVIDER_REGISTRY
        for provider_type in ProviderType
    }
