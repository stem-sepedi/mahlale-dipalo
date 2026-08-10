#!/usr/bin/env python3
"""Disaster recovery script — validates backups and restores from S3 snapshots."""

import asyncio
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def validate_backups():
    """Check that all version snapshots have corresponding S3 archives."""
    import asyncpg
    from src.services.s3_archive import S3ArchiveWorker

    dsn = os.getenv("DATABASE_URL", "postgresql://localhost/polelo")
    pool = await asyncpg.create_pool(dsn, min_size=1, max_size=2)
    worker = S3ArchiveWorker()

    snapshots = await pool.fetch(
        "SELECT concept_id, version_number, archived_by FROM version_snapshots ORDER BY created_at DESC"
    )

    results = {"total": len(snapshots), "validated": 0, "missing_s3": 0, "errors": []}

    for snap in snapshots:
        if snap["archived_by"] and snap["archived_by"].startswith("s3:"):
            try:
                data = await worker.restore_snapshot(snap["concept_id"], snap["version_number"])
                if data:
                    results["validated"] += 1
                else:
                    results["missing_s3"] += 1
                    results["errors"].append(f"Empty snapshot: {snap['concept_id']}v{snap['version_number']}")
            except Exception as exc:
                results["missing_s3"] += 1
                results["errors"].append(f"{snap['concept_id']}v{snap['version_number']}: {exc}")
        else:
            results["missing_s3"] += 1

    await worker.close()
    await pool.close()
    return results


async def restore_all():
    """Restore all concepts from their latest version snapshots."""
    import asyncpg
    import json

    dsn = os.getenv("DATABASE_URL", "postgresql://localhost/polelo")
    pool = await asyncpg.create_pool(dsn, min_size=1, max_size=2)

    concepts = await pool.fetch("SELECT id FROM concepts")
    restored = 0

    for concept in concepts:
        cid = concept["id"]
        snap = await pool.fetchrow(
            "SELECT * FROM version_snapshots WHERE concept_id = $1 ORDER BY version_number DESC LIMIT 1",
            cid,
        )
        if snap:
            data = json.loads(snap["snapshot_data"]) if isinstance(snap["snapshot_data"], str) else snap["snapshot_data"]
            cd = data.get("concept", {})
            await pool.execute(
                """UPDATE concepts SET name_en = $1, definition_en = $2, domain = $3,
                   grade_levels = $4, current_version = $5 WHERE id = $6""",
                cd.get("name_en"), cd.get("definition_en"), cd.get("domain"),
                cd.get("grade_levels", []), snap["version_number"], cid,
            )
            restored += 1

    await pool.close()
    return {"concepts_restored": restored}


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else "validate"
    if command == "validate":
        result = asyncio.run(validate_backups())
    elif command == "restore":
        result = asyncio.run(restore_all())
    else:
        print(f"Unknown command: {command}")
        print("Usage: disaster_recovery.py [validate|restore]")
        sys.exit(1)

    print(json.dumps(result, indent=2, default=str))
