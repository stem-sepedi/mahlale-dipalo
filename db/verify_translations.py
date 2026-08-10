#!/usr/bin/env python3
"""Verify translations — checks quality of translations against source concepts."""

import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def verify_translations(limit: int = 50):
    """Check translations for quality issues: empty terms, low confidence, missing alternatives."""
    import asyncpg

    dsn = os.getenv("DATABASE_URL", "postgresql://localhost/polelo")
    pool = await asyncpg.create_pool(dsn, min_size=1, max_size=2)

    rows = await pool.fetch(
        "SELECT t.*, c.name_en, c.domain FROM translations t "
        "JOIN concepts c ON t.concept_id = c.id "
        "ORDER BY t.created_at DESC LIMIT $1",
        limit,
    )

    issues = []
    verified = 0

    for row in rows:
        row_issues = []
        if not row["sepedi_term"] or row["sepedi_term"].strip() == "":
            row_issues.append("empty_sepedi_term")
        if row["confidence_score"] is not None and row["confidence_score"] < 0.3:
            row_issues.append(f"low_confidence ({row['confidence_score']})")
        alts = row["alternative_forms"]
        if isinstance(alts, str):
            alts = json.loads(alts)
        if len(alts) < 1:
            row_issues.append("no_alternative_forms")
        if row["status"] not in ("draft", "pending_review", "approved", "published", "rejected"):
            row_issues.append(f"invalid_status ({row['status']})")

        if row_issues:
            issues.append({
                "translation_id": str(row["id"]),
                "concept": row["name_en"],
                "sepedi_term": row["sepedi_term"],
                "issues": row_issues,
            })
        else:
            verified += 1

    await pool.close()
    return {"total_checked": len(rows), "verified": verified, "issues": issues}


if __name__ == "__main__":
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    result = asyncio.run(verify_translations(limit))
    print(json.dumps(result, indent=2, default=str))
    if result["issues"]:
        sys.exit(1)
