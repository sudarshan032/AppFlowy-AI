import os
import ollama
from typing import List

class EmbeddingsService:
    def __init__(self, model: str = "nomic-embed-text"):
        self.model = model
        # base_url is picked up from OLLAMA_HOST env var if set, or defaults to localhost

    def embed_text(self, text: str) -> List[float]:
        """
        Generates embedding for a single text string using Ollama.
        """
        if not text:
            return []
        
        try:
            response = ollama.embeddings(model=self.model, prompt=text)
            return response['embedding']
        except Exception as e:
            print(f"Error generating embedding via Ollama: {e}")
            return []

    def embed_query(self, text: str) -> List[float]:
        """
        Generates embedding for a query (search).
        """
        # For nomic-embed-text, query vs doc might matter for headers, 
        # but via Ollama API it's usually just 'prompt'.
        return self.embed_text(text)
