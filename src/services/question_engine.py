"""Question answer engine — answers learner questions via the Ollama LLM.

Used by the M10 triage pipeline to generate Sepedi answers. Kept separate from
the translation engine because it answers free-form learner questions rather
than translating individual STEM terms.
"""

import json
import logging

from src.services.ollama_client import OllamaClient
from src.services.prompts.templates import question_answer_prompt

logger = logging.getLogger(__name__)


class QuestionAnswerEngine:
    """Orchestrates LLM calls that answer learner questions in Sepedi."""

    def __init__(self, ollama: OllamaClient | None = None):
        self._ollama = ollama or OllamaClient()

    async def answer(
        self,
        question: str,
        grade: int | None = None,
        subject: str | None = None,
    ) -> dict:
        """Generate a Sepedi answer for a learner question. Returns parsed JSON."""
        prompt = question_answer_prompt(question, grade, subject)
        raw = await self._ollama.generate(prompt, temperature=0.3)
        return _parse_json(raw, fallback={
            "answer_sep": "",
            "confidence_score": 0.0,
        })


def _parse_json(raw: str, fallback: dict) -> dict:
    """Extract JSON from LLM output, handling markdown fences and noise."""
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [line for line in lines if not line.strip().startswith("```")]
        text = "\n".join(lines)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        logger.warning("Failed to parse LLM output as JSON: %s", text[:200])
        return fallback
