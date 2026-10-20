"""
Abstract Base Class for AI Model Providers

This module defines the interface that all AI providers must implement.
Providers can be swapped without changing application code.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, AsyncIterator
from pydantic import BaseModel
from enum import Enum


class ProviderType(str, Enum):
    """Supported provider types."""
    OLLAMA = "ollama"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    CUSTOM = "custom"


class ModelConfig(BaseModel):
    """Configuration for model inference."""
    model_name: str
    temperature: float = 0.7
    max_tokens: int = 4096
    top_p: float = 0.9
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    
    class Config:
        extra = "allow"  # Allow additional provider-specific params


class ChatMessage(BaseModel):
    """A single chat message."""
    role: str  # "user", "assistant", "system"
    content: str


class AIProvider(ABC):
    """
    Abstract base class for all AI model providers.
    
    Implement this interface to add support for new LLM providers.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Return the provider name identifier."""
        pass
    
    @property
    @abstractmethod
    def provider_type(self) -> ProviderType:
        """Return the provider type."""
        pass
    
    @abstractmethod
    async def generate(
        self, 
        prompt: str, 
        config: Optional[ModelConfig] = None
    ) -> str:
        """
        Generate text from a prompt.
        
        Args:
            prompt: The input prompt text
            config: Optional model configuration
            
        Returns:
            Generated text response
        """
        pass
    
    @abstractmethod
    async def chat(
        self, 
        messages: List[ChatMessage], 
        config: Optional[ModelConfig] = None
    ) -> str:
        """
        Chat completion with message history.
        
        Args:
            messages: List of chat messages
            config: Optional model configuration
            
        Returns:
            Assistant's response text
        """
        pass
    
    @abstractmethod
    async def stream_generate(
        self, 
        prompt: str, 
        config: Optional[ModelConfig] = None
    ) -> AsyncIterator[str]:
        """
        Stream text generation token by token.
        
        Args:
            prompt: The input prompt text
            config: Optional model configuration
            
        Yields:
            Generated text chunks
        """
        pass
    
    async def embed(self, text: str) -> List[float]:
        """
        Generate embeddings for text.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector
            
        Raises:
            NotImplementedError if provider doesn't support embeddings
        """
        raise NotImplementedError(f"{self.name} does not support embeddings")
    
    async def health_check(self) -> bool:
        """
        Check if the provider is available.
        
        Returns:
            True if provider is healthy, False otherwise
        """
        try:
            await self.generate("test", ModelConfig(model_name="test", max_tokens=1))
            return True
        except Exception:
            return False
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}({self.name})>"
