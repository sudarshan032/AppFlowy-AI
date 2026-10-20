"""
Google Gemini AI Provider implementation.

Provides integration with Google's Generative AI (Gemini) models.
"""

import os
import logging
from typing import Optional, AsyncIterator, List
from enum import Enum

from .base import AIProvider, ProviderType

logger = logging.getLogger(__name__)


class GoogleProvider(AIProvider):
    """
    Google Gemini AI Provider.

    Uses google-generativeai library to interact with Google's Gemini models.
    Requires GOOGLE_API_KEY environment variable.
    """

    name = "google"
    provider_type = ProviderType.CUSTOM

    def __init__(self):
        """Initialize Google Gemini provider."""
        self.api_key = os.getenv("GOOGLE_API_KEY")

        if not self.api_key:
            logger.warning(
                "GOOGLE_API_KEY not set. Google provider will not work. "
                "Set GOOGLE_API_KEY environment variable."
            )
            self.client = None
            return

        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self.genai = genai
            self.client = True
            logger.info("Google Gemini provider initialized")
        except ImportError:
            logger.error(
                "google-generativeai library not installed. "
                "Install with: pip install google-generativeai"
            )
            self.client = None
            self.genai = None

    async def health_check(self) -> bool:
        """
        Check if Google API is available.

        Returns:
            True if API is available and configured, False otherwise
        """
        if not self.client or not self.api_key:
            return False

        try:
            # Try a simple API call to verify connectivity
            model = self.genai.GenerativeModel("gemini-pro")
            response = model.generate_content("Test")
            return response is not None
        except Exception as e:
            logger.error(f"Google provider health check failed: {e}")
            return False

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> str:
        """
        Generate text completion using Google Gemini.

        Args:
            prompt: User prompt/question
            system_prompt: System instruction (not directly supported by Gemini, prepended to prompt)
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text completion

        Raises:
            RuntimeError: If provider not initialized or API call fails
        """
        if not self.client:
            raise RuntimeError("Google provider not initialized. Set GOOGLE_API_KEY.")

        try:
            # Combine system prompt with user prompt if provided
            full_prompt = prompt
            if system_prompt:
                full_prompt = f"{system_prompt}\n\n{prompt}"

            model = self.genai.GenerativeModel(
                "gemini-pro",
                generation_config=self.genai.types.GenerationConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                )
            )

            response = model.generate_content(full_prompt)

            if response and response.text:
                return response.text
            else:
                logger.warning("Empty response from Google Gemini")
                return ""

        except Exception as e:
            logger.error(f"Google Gemini generation failed: {e}")
            raise RuntimeError(f"Google Gemini API error: {str(e)}")

    async def stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7
    ) -> AsyncIterator[str]:
        """
        Stream text generation token by token.

        Args:
            prompt: User prompt/question
            system_prompt: System instruction
            temperature: Sampling temperature

        Yields:
            Text tokens as they are generated

        Raises:
            RuntimeError: If provider not initialized or API call fails
        """
        if not self.client:
            raise RuntimeError("Google provider not initialized. Set GOOGLE_API_KEY.")

        try:
            # Combine system prompt with user prompt if provided
            full_prompt = prompt
            if system_prompt:
                full_prompt = f"{system_prompt}\n\n{prompt}"

            model = self.genai.GenerativeModel(
                "gemini-pro",
                generation_config=self.genai.types.GenerationConfig(
                    temperature=temperature,
                )
            )

            response = model.generate_content(full_prompt, stream=True)

            for chunk in response:
                if chunk and chunk.text:
                    yield chunk.text

        except Exception as e:
            logger.error(f"Google Gemini streaming failed: {e}")
            raise RuntimeError(f"Google Gemini streaming error: {str(e)}")

    async def embed(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for texts using Google's embedding model.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors (each 768-dimensional)

        Raises:
            RuntimeError: If provider not initialized or API call fails
        """
        if not self.client:
            raise RuntimeError("Google provider not initialized. Set GOOGLE_API_KEY.")

        try:
            embeddings = []

            for text in texts:
                try:
                    # Use Google's embedding model
                    result = self.genai.embed_content(
                        model="models/embedding-001",
                        content=text
                    )
                    embeddings.append(result["embedding"])
                except Exception as e:
                    logger.error(f"Failed to embed text: {e}")
                    # Return zero vector on failure
                    embeddings.append([0.0] * 768)

            return embeddings

        except Exception as e:
            logger.error(f"Google embedding failed: {e}")
            raise RuntimeError(f"Google embedding API error: {str(e)}")

    async def chat(
        self,
        messages: List[dict],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> str:
        """
        Generate response in a multi-turn conversation.

        Args:
            messages: List of message dicts with 'role' and 'content'
            system_prompt: System instruction
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Response text

        Raises:
            RuntimeError: If provider not initialized or API call fails
        """
        if not self.client:
            raise RuntimeError("Google provider not initialized. Set GOOGLE_API_KEY.")

        try:
            model = self.genai.GenerativeModel(
                "gemini-pro",
                generation_config=self.genai.types.GenerationConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                ),
                system_instruction=system_prompt
            )

            # Convert messages to Google format
            chat_history = []
            for msg in messages[:-1]:  # All but last
                chat_history.append({
                    "role": "user" if msg["role"] == "user" else "model",
                    "parts": [msg["content"]]
                })

            chat = model.start_chat(history=chat_history)
            last_message = messages[-1]["content"] if messages else ""

            response = chat.send_message(last_message)

            if response and response.text:
                return response.text
            else:
                logger.warning("Empty chat response from Google Gemini")
                return ""

        except Exception as e:
            logger.error(f"Google Gemini chat failed: {e}")
            raise RuntimeError(f"Google Gemini chat error: {str(e)}")

    async def stream_chat(
        self,
        messages: List[dict],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7
    ) -> AsyncIterator[str]:
        """
        Stream response in a multi-turn conversation.

        Args:
            messages: List of message dicts with 'role' and 'content'
            system_prompt: System instruction
            temperature: Sampling temperature

        Yields:
            Response tokens as they are generated

        Raises:
            RuntimeError: If provider not initialized or API call fails
        """
        if not self.client:
            raise RuntimeError("Google provider not initialized. Set GOOGLE_API_KEY.")

        try:
            model = self.genai.GenerativeModel(
                "gemini-pro",
                generation_config=self.genai.types.GenerationConfig(
                    temperature=temperature,
                ),
                system_instruction=system_prompt
            )

            # Convert messages to Google format
            chat_history = []
            for msg in messages[:-1]:  # All but last
                chat_history.append({
                    "role": "user" if msg["role"] == "user" else "model",
                    "parts": [msg["content"]]
                })

            chat = model.start_chat(history=chat_history)
            last_message = messages[-1]["content"] if messages else ""

            response = chat.send_message(last_message, stream=True)

            for chunk in response:
                if chunk and chunk.text:
                    yield chunk.text

        except Exception as e:
            logger.error(f"Google Gemini chat streaming failed: {e}")
            raise RuntimeError(f"Google Gemini chat streaming error: {str(e)}")

    async def stream_generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7
    ) -> AsyncIterator[str]:
        """
        Stream text generation (alias for stream method).

        Args:
            prompt: User prompt/question
            system_prompt: System instruction
            temperature: Sampling temperature

        Yields:
            Text tokens as they are generated
        """
        async for chunk in self.stream(prompt, system_prompt, temperature):
            yield chunk

    @staticmethod
    def get_available_models() -> List[str]:
        """
        Get list of available Google Gemini models.

        Returns:
            List of model names
        """
        return [
            "gemini-pro",
            "gemini-pro-vision",
            "gemini-1.5-pro",
            "gemini-1.5-flash",
        ]

    @staticmethod
    def get_model_info(model: str) -> dict:
        """
        Get information about a specific model.

        Args:
            model: Model name

        Returns:
            Dictionary with model information
        """
        models_info = {
            "gemini-pro": {
                "name": "Gemini Pro",
                "type": "text",
                "context_window": 32000,
                "max_output_tokens": 8000,
            },
            "gemini-pro-vision": {
                "name": "Gemini Pro Vision",
                "type": "multimodal",
                "context_window": 32000,
                "max_output_tokens": 8000,
            },
            "gemini-1.5-pro": {
                "name": "Gemini 1.5 Pro",
                "type": "text",
                "context_window": 1000000,
                "max_output_tokens": 8000,
            },
            "gemini-1.5-flash": {
                "name": "Gemini 1.5 Flash",
                "type": "text",
                "context_window": 1000000,
                "max_output_tokens": 8000,
            },
        }
        return models_info.get(
            model,
            {
                "name": model,
                "type": "unknown",
                "context_window": 32000,
                "max_output_tokens": 8000,
            }
        )
