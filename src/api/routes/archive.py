"""Archive releases routes — /archive/approve to batch-archive published concepts to S3."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import asyncpg

from src.middleware.jwt import TokenPayload, require_role
from src.api.routes.versions import create_version_snapshot
from src.services.s3_archive import S3ArchiveWorker

router = APIRouter(prefix="/archive", tags=["archive"])


async def _get_pool() -> asyncpg.Pool:
    import os
    dsn = os.getenv("DATABASE_URL", "postgresql://localhost/polelo")
    return await asyncpg.create_pool(dsn, min_size=1, max_size=5)


class ArchiveReleaseRequest(BaseModel):
    concept_ids: list[str] = []
    archive_all_published: bool = False


@router.post("/releases")
async def archive_approved_releases(
    req: ArchiveReleaseRequest,
    user: TokenPayload = Depends(require_role("admin")),
):
    pool = await _get_pool()

    if req.archive_all_published:
        rows = await pool.fetch("SELECT id FROM concepts WHERE status = 'published'")
        concept_ids = [str(r["id"]) for r in rows]
    else:
        concept_ids = req.concept_ids

    if not concept_ids:
        raise HTTPException(status_code=422, detail="No concepts to archive")

    worker = S3ArchiveWorker()
    results = {"archived": 0, "errors": []}

    try:
        await worker.ensure_bucket()
        for cid in concept_ids:
            try:
                snap = await create_version_snapshot(pool, cid, archived_by=user.username)
                concept = await pool.fetchrow("SELECT * FROM concepts WHERE id = $1", cid)
                import json
                snapshot_data = json.loads(
                    (await pool.fetchrow(
                        "SELECT snapshot_data FROM version_snapshots WHERE concept_id = $1 ORDER BY version_number DESC LIMIT 1",
                        cid,
                    ))["snapshot_data"]
                )
                s3_key = await worker.archive_snapshot(cid, snap["version_number"], snapshot_data)
                results["archived"] += 1
            except Exception as exc:
                results["errors"].append({"concept_id": cid, "error": str(exc)})
    finally:
        await worker.close()

    return results
