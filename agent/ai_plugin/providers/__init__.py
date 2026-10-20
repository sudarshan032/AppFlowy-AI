"""
AI Provider Abstraction Layer

Pluggable model providers supporting Ollama, OpenAI, Anthropic, and custom providers.
"""

from .base import AIProvider, ModelConfig, ProviderType, ChatMessage
from .ollama_provider import OllamaProvider
from .config import ProviderConfig, get_provider, list_available_providers, set_provider

__all__ = [
    'AIProvider',
    'ModelConfig',
    'ProviderType',
    'ChatMessage',
    'OllamaProvider',
    'ProviderConfig',
    'get_provider',
    'set_provider',
    'list_available_providers',
]
