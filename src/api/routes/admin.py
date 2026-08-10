"""Snapshot admin routes — /admin/snapshots for managing archived snapshots."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import asyncpg

from src.middleware.jwt import TokenPayload, require_role
from src.services.s3_archive import S3ArchiveWorker

router = APIRouter(prefix="/admin", tags=["admin"])


async def _get_pool() -> asyncpg.Pool:
    import os
    dsn = os.getenv("DATABASE_URL", "postgresql://localhost/polelo")
    return await asyncpg.create_pool(dsn, min_size=1, max_size=5)


class ArchiveRequest(BaseModel):
    concept_id: str
    version_number: int


class RestoreRequest(BaseModel):
    concept_id: str
    version_number: int


@router.get("/snapshots")
async def list_snapshots(
    concept_id: str | None = None,
    user: TokenPayload = Depends(require_role("admin")),
):
    pool = await _get_pool()
    if concept_id:
        rows = await pool.fetch(
            "SELECT * FROM version_snapshots WHERE concept_id = $1 ORDER BY version_number DESC",
            concept_id,
        )
    else:
        rows = await pool.fetch(
            "SELECT * FROM version_snapshots ORDER BY created_at DESC LIMIT 100",
        )
    return {"snapshots": [dict(r) for r in rows]}


@router.post("/snapshots/archive")
async def archive_snapshot(
    req: ArchiveRequest,
    user: TokenPayload = Depends(require_role("admin")),
):
    pool = await _get_pool()
    row = await pool.fetchrow(
        "SELECT * FROM version_snapshots WHERE concept_id = $1 AND version_number = $2",
        req.concept_id, req.version_number,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Snapshot not found")

    import json
    snapshot_data = json.loads(row["snapshot_data"]) if isinstance(row["snapshot_data"], str) else row["snapshot_data"]

    worker = S3ArchiveWorker()
    try:
        await worker.ensure_bucket()
        s3_key = await worker.archive_snapshot(req.concept_id, req.version_number, snapshot_data)
        await pool.execute(
            "UPDATE version_snapshots SET archived_by = $1 WHERE concept_id = $2 AND version_number = $3",
            f"s3:{s3_key}", req.concept_id, req.version_number,
        )
        return {"archived_to": s3_key}
    finally:
        await worker.close()


@router.post("/snapshots/restore")
async def restore_snapshot(
    req: RestoreRequest,
    user: TokenPayload = Depends(require_role("admin")),
):
    pool = await _get_pool()
    row = await pool.fetchrow(
        "SELECT * FROM version_snapshots WHERE concept_id = $1 AND version_number = $2",
        req.concept_id, req.version_number,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Snapshot not found")

    import json
    snapshot_data = json.loads(row["snapshot_data"]) if isinstance(row["snapshot_data"], str) else row["snapshot_data"]
    concept_data = snapshot_data.get("concept", {})

    await pool.execute(
        """UPDATE concepts SET name_en = $1, definition_en = $2, domain = $3,
           grade_levels = $4, status = 'draft', updated_at = now() WHERE id = $5""",
        concept_data.get("name_en"),
        concept_data.get("definition_en"),
        concept_data.get("domain"),
        concept_data.get("grade_levels", []),
        req.concept_id,
    )

    return {"status": "restored", "version_number": req.version_number}
