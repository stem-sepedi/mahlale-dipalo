"""Translation engine — bridges concepts to Ollama LLM for Sepedi translation/explanation."""

import json
import logging

from src.services.ollama_client import OllamaClient
from src.services.prompts.templates import translate_prompt, explain_prompt, quiz_prompt

logger = logging.getLogger(__name__)


class TranslationEngine:
    """Orchestrates LLM calls for translation, explanation, and quiz generation."""

    def __init__(self, ollama: OllamaClient | None = None):
        self._ollama = ollama or OllamaClient()

    async def translate(
        self,
        term: str,
        domain: str,
        grade_levels: list[int],
        context_sep: str = "",
    ) -> dict:
        """Translate a STEM term into Sepedi. Returns parsed JSON from LLM."""
        prompt = translate_prompt(term, domain, grade_levels, context_sep)
        raw = await self._ollama.generate(prompt, temperature=0.3)
        return _parse_json(raw, fallback={
            "sepedi_term": term,
            "confidence_score": 0.0,
            "alternative_forms": [],
        })

    async def explain(self, term: str, domain: str, grade_level: int) -> dict:
        """Generate a Sepedi explanation for a concept."""
        prompt = explain_prompt(term, domain, grade_level)
        raw = await self._ollama.generate(prompt, temperature=0.5)
        return _parse_json(raw, fallback={
            "content_sep": "",
            "examples_sep": [],
        })

    async def quiz(
        self, term: str, domain: str, grade_level: int, count: int = 5,
    ) -> list[dict]:
        """Generate quiz questions for a concept."""
        prompt = quiz_prompt(term, domain, grade_level, count)
        raw = await self._ollama.generate(prompt, temperature=0.4)
        data = _parse_json(raw, fallback={"questions": []})
        return data.get("questions", [])


def _parse_json(raw: str, fallback: dict) -> dict:
    """Extract JSON from LLM output, handling markdown fences and noise."""
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        logger.warning("Failed to parse LLM output as JSON: %s", text[:200])
        return fallback
