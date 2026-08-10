"""Ollama HTTP client for Polelo — wraps local Ollama API for LLM inference."""

import os
import logging

import httpx

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL") or os.getenv("OLLAMA_HOST", "http://localhost:11434")


class OllamaClient:
    """Async client for Ollama API."""

    def __init__(self, base_url: str = OLLAMA_BASE_URL):
        self._base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(base_url=self._base_url, timeout=120.0)

    async def close(self):
        await self._client.aclose()

    def ping(self) -> bool:
        """Synchronous health check — returns True if Ollama is reachable."""
        try:
            resp = httpx.get(f"{self._base_url}/api/tags", timeout=5.0)
            return resp.status_code == 200
        except Exception:
            return False

    async def generate(
        self,
        prompt: str,
        model: str = "llama3.2",
        system: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        """Send a prompt to Ollama and return the generated text."""
        payload: dict = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        if system:
            payload["system"] = system

        try:
            resp = await self._client.post("/api/generate", json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data.get("response", "")
        except httpx.HTTPStatusError as exc:
            logger.error("Ollama HTTP error %s: %s", exc.response.status_code, exc.response.text[:200])
            raise
        except httpx.RequestError as exc:
            logger.error("Ollama connection error: %s", exc)
            raise

    async def chat(
        self,
        messages: list[dict],
        model: str = "llama3.2",
        temperature: float = 0.7,
    ) -> str:
        """Multi-turn chat completion via Ollama."""
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature},
        }
        try:
            resp = await self._client.post("/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data.get("message", {}).get("content", "")
        except httpx.HTTPStatusError as exc:
            logger.error("Ollama chat error %s: %s", exc.response.status_code, exc.response.text[:200])
            raise
        except httpx.RequestError as exc:
            logger.error("Ollama connection error: %s", exc)
            raise
