"""Embedding service for text → vector conversion.

Supports:
- OpenAI text-embedding-3-small (cloud, 1536 dims)
- Ollama nomic-embed-text (local, 768 dims)
"""

import logging
from typing import Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Convert text chunks into dense embedding vectors."""

    def __init__(self, provider: Optional[str] = None):
        self.provider = (provider or settings.EMBEDDING_PROVIDER).lower()
        self.timeout = 30.0

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts. Returns list of embedding vectors."""
        if not texts:
            return []
        if self.provider == "openai":
            return await self._embed_openai(texts)
        if self.provider == "ollama":
            return await self._embed_ollama(texts)
        raise ValueError(f"Unsupported embedding provider: {self.provider}")

    async def embed_single(self, text: str) -> list[float]:
        """Embed a single text string."""
        results = await self.embed([text])
        return results[0] if results else []

    async def _embed_openai(self, texts: list[str]) -> list[list[float]]:
        if not settings.OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY not configured for embeddings")

        url = "https://api.openai.com/v1/embeddings"
        headers = {
            "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
            "Content-Type": "application/json",
        }

        # OpenAI accepts up to 2048 inputs per request
        batch_size = 2048
        all_embeddings: list[list[float]] = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            payload = {
                "model": settings.OPENAI_EMBEDDING_MODEL,
                "input": batch,
                "encoding_format": "float",
                "dimensions": settings.EMBEDDING_DIMENSIONS,
            }
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(url, headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()
                # Sort by index to preserve order
                sorted_data = sorted(data["data"], key=lambda x: x["index"])
                all_embeddings.extend([d["embedding"] for d in sorted_data])

        return all_embeddings

    async def _embed_ollama(self, texts: list[str]) -> list[list[float]]:
        url = f"{settings.OLLAMA_BASE_URL}/api/embed"
        all_embeddings: list[list[float]] = []

        for text in texts:
            payload = {
                "model": settings.OLLAMA_EMBEDDING_MODEL,
                "input": text,
            }
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                all_embeddings.append(data["embeddings"][0])

        return all_embeddings


def get_embedding_service() -> EmbeddingService:
    """Factory: return an EmbeddingService instance."""
    return EmbeddingService()
