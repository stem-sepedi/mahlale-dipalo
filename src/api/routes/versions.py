"""Version snapshot routes — /concepts/{id}/versions, version diffs."""

import difflib
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
import asyncpg

from src.middleware.jwt import TokenPayload, get_current_user, require_role

router = APIRouter(tags=["versions"])


async def _get_pool() -> asyncpg.Pool:
    import os
    dsn = os.getenv("DATABASE_URL", "postgresql://localhost/polelo")
    return await asyncpg.create_pool(dsn, min_size=1, max_size=5)


async def create_version_snapshot(
    pool: asyncpg.Pool, concept_id: str, *, archived_by: str = "system",
) -> dict:
    """Capture a snapshot of the concept's current state and store it."""
    concept = await pool.fetchrow("SELECT * FROM concepts WHERE id = $1", concept_id)
    if not concept:
        raise ValueError(f"Concept {concept_id} not found")

    translations = await pool.fetch(
        "SELECT * FROM translations WHERE concept_id = $1 ORDER BY created_at", concept_id
    )
    explanations = await pool.fetch(
        "SELECT * FROM explanations WHERE concept_id = $1 ORDER BY grade_level", concept_id
    )

    snapshot_data = {
        "concept": dict(concept),
        "translations": [dict(t) for t in translations],
        "explanations": [dict(e) for e in explanations],
    }

    # Get previous version for diff
    prev = await pool.fetchrow(
        "SELECT version_number, snapshot_data FROM version_snapshots "
        "WHERE concept_id = $1 ORDER BY version_number DESC LIMIT 1",
        concept_id,
    )

    diff_to_prev = None
    if prev:
        old_text = json.dumps(dict(prev["snapshot_data"]), indent=2, default=str)
        new_text = json.dumps(snapshot_data, indent=2, default=str)
        diff_lines = list(difflib.unified_diff(
            old_text.splitlines(), new_text.splitlines(),
            fromfile=f"v{prev['version_number']}", tofile=f"v{concept['current_version']}",
            lineterm="",
        ))
        diff_to_prev = "\n".join(diff_lines)

    version_number = (prev["version_number"] + 1) if prev else 1

    await pool.execute(
        """INSERT INTO version_snapshots (concept_id, version_number, snapshot_data, diff_to_prev, archived_by)
           VALUES ($1, $2, $3, $4, $5)""",
        concept_id, version_number, json.dumps(snapshot_data, default=str), diff_to_prev, archived_by,
    )

    await pool.execute(
        "UPDATE concepts SET current_version = $1, updated_at = $2 WHERE id = $3",
        version_number, datetime.now(timezone.utc), concept_id,
    )

    return {
        "version_number": version_number,
        "diff_to_prev": diff_to_prev,
        "archived_by": archived_by,
    }


@router.get("/concepts/{concept_id}/versions")
async def list_versions(
    concept_id: str,
    user: TokenPayload = Depends(get_current_user),
):
    pool = await _get_pool()
    rows = await pool.fetch(
        "SELECT version_number, archived_by, created_at, diff_to_prev "
        "FROM version_snapshots WHERE concept_id = $1 ORDER BY version_number DESC",
        concept_id,
    )
    return {
        "versions": [
            {
                "version_number": r["version_number"],
                "archived_by": r["archived_by"],
                "timestamp": r["created_at"].isoformat() if r["created_at"] else None,
                "diff_to_prev": r["diff_to_prev"],
            }
            for r in rows
        ]
    }


@router.get("/concepts/{concept_id}/versions/{version_number}")
async def get_version(
    concept_id: str,
    version_number: int,
    user: TokenPayload = Depends(get_current_user),
):
    pool = await _get_pool()
    row = await pool.fetchrow(
        "SELECT * FROM version_snapshots WHERE concept_id = $1 AND version_number = $2",
        concept_id, version_number,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Version not found")
    return {
        "version_number": row["version_number"],
        "snapshot_data": json.loads(row["snapshot_data"]) if isinstance(row["snapshot_data"], str) else row["snapshot_data"],
        "archived_by": row["archived_by"],
        "timestamp": row["created_at"].isoformat() if row["created_at"] else None,
    }


@router.post("/concepts/{concept_id}/revert/{version_number}")
async def revert_to_version(
    concept_id: str,
    version_number: int,
    user: TokenPayload = Depends(require_role("admin", "teacher")),
):
    pool = await _get_pool()
    row = await pool.fetchrow(
        "SELECT * FROM version_snapshots WHERE concept_id = $1 AND version_number = $2",
        concept_id, version_number,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Version not found")

    snapshot = json.loads(row["snapshot_data"]) if isinstance(row["snapshot_data"], str) else row["snapshot_data"]
    concept_data = snapshot.get("concept", {})

    await pool.execute(
        """UPDATE concepts SET name_en = $1, definition_en = $2, domain = $3,
           grade_levels = $4, status = 'draft', updated_at = now() WHERE id = $5""",
        concept_data.get("name_en"),
        concept_data.get("definition_en"),
        concept_data.get("domain"),
        concept_data.get("grade_levels", []),
        concept_id,
    )

    await create_version_snapshot(pool, concept_id, archived_by=user.username)
    return {"status": "reverted", "version_number": version_number}
