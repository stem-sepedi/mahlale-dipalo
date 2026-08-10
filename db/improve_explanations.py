#!/usr/bin/env python3
"""Improve explanations — batch-reprocess low-quality explanations via Ollama."""

import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.ollama_client import OllamaClient
from src.services.prompts.templates import explain_prompt


async def improve_explanations(min_words: int = 50, max_improve: int = 20):
    """Find explanations that are too short and regenerate them."""
    import asyncpg

    dsn = os.getenv("DATABASE_URL", "postgresql://localhost/polelo")
    pool = await asyncpg.create_pool(dsn, min_size=1, max_size=2)
    ollama = OllamaClient()

    # Find short explanations
    rows = await pool.fetch(
        """SELECT e.*, c.name_en, c.domain
           FROM explanations e
           JOIN concepts c ON e.concept_id = c.id
           WHERE length(e.content_sep) < $1 * 5
           ORDER BY e.created_at ASC
           LIMIT $2""",
        min_words, max_improve,
    )

    improved = 0
    for row in rows:
        prompt = explain_prompt(row["name_en"], row["domain"], row["grade_level"])
        try:
            raw = await ollama.generate(prompt, temperature=0.5)
            data = json.loads(raw.strip().strip("`").removeprefix("json\n"))
            new_content = data.get("content_sep", "")
            new_examples = data.get("examples_sep", [])

            if len(new_content) > len(row["content_sep"]):
                await pool.execute(
                    "UPDATE explanations SET content_sep = $1, examples_sep = $2, updated_at = now() WHERE id = $3",
                    new_content, json.dumps(new_examples), row["id"],
                )
                improved += 1
                print(f"Improved: {row['name_en']} grade {row['grade_level']}")
        except Exception as exc:
            print(f"Failed to improve {row['name_en']}: {exc}")

    await ollama.close()
    await pool.close()
    return {"attempted": len(rows), "improved": improved}


if __name__ == "__main__":
    result = asyncio.run(improve_explanations())
    print(json.dumps(result, indent=2))
