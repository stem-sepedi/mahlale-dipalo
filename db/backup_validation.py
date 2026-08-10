#!/usr/bin/env python3
"""Backup validation pipeline — exports database state to JSON for offline verification."""

import asyncio
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def export_backup(output_path: str = "backup"):
    """Export all tables to JSON files for backup verification."""
    import asyncpg

    dsn = os.getenv("DATABASE_URL", "postgresql://localhost/polelo")
    pool = await asyncpg.create_pool(dsn, min_size=1, max_size=2)

    os.makedirs(output_path, exist_ok=True)

    tables = ["users", "concepts", "translations", "explanations", "quiz_questions", "reviews", "version_snapshots"]

    for table in tables:
        rows = await pool.fetch(f"SELECT * FROM {table}")
        data = [dict(r) for r in rows]
        filepath = os.path.join(output_path, f"{table}.json")
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2, default=str)
        print(f"Exported {len(data)} rows to {filepath}")

    # Generate summary
    summary = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "tables": {},
    }
    for table in tables:
        count = await pool.fetchval(f"SELECT count(*) FROM {table}")
        summary["tables"][table] = count

    summary_path = os.path.join(output_path, "summary.json")
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

    await pool.close()
    print(f"Backup complete: {summary_path}")
    return summary


if __name__ == "__main__":
    output = sys.argv[1] if len(sys.argv) > 1 else "backup"
    asyncio.run(export_backup(output))
