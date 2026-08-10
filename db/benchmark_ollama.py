#!/usr/bin/env python3
"""Benchmark Ollama — measures latency, throughput, and quality of LLM responses."""

import asyncio
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.ollama_client import OllamaClient


async def benchmark(count: int = 5):
    """Run benchmark: measure response time for translation prompts."""
    ollama = OllamaClient()
    results = []

    prompts = [
        ("translate", "Translate 'Photosynthesis' into Sepedi for grade 8. Return JSON."),
        ("explain", "Explain 'Gravity' in Sepedi for grade 10. Return JSON."),
        ("quiz", "Generate 3 quiz questions about 'Mitosis' in Sepedi. Return JSON."),
    ]

    for name, prompt in prompts:
        times = []
        for i in range(count):
            start = time.monotonic()
            try:
                raw = await ollama.generate(prompt, temperature=0.3)
                elapsed = time.monotonic() - start
                times.append(elapsed)
                print(f"  {name} #{i+1}: {elapsed:.2f}s ({len(raw)} chars)")
            except Exception as exc:
                elapsed = time.monotonic() - start
                print(f"  {name} #{i+1}: FAILED after {elapsed:.2f}s — {exc}")

        if times:
            results.append({
                "prompt": name,
                "runs": len(times),
                "avg_seconds": round(sum(times) / len(times), 2),
                "min_seconds": round(min(times), 2),
                "max_seconds": round(max(times), 2),
                "total_seconds": round(sum(times), 2),
            })

    await ollama.close()
    return {"benchmark_results": results}


if __name__ == "__main__":
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    result = asyncio.run(benchmark(count))
    print(json.dumps(result, indent=2))
