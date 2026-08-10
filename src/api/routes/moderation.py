"""Moderation routes — /moderation/bulk for batch operations."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import asyncpg

from src.middleware.jwt import TokenPayload, require_role

router = APIRouter(prefix="/moderation", tags=["moderation"])


async def _get_pool() -> asyncpg.Pool:
    import os
    dsn = os.getenv("DATABASE_URL", "postgresql://localhost/polelo")
    return await asyncpg.create_pool(dsn, min_size=1, max_size=5)


class BulkAction(BaseModel):
    ids: list[str]
    action: str  # "approve" | "reject" | "delete"


@router.post("/bulk")
async def bulk_moderate(
    req: BulkAction,
    user: TokenPayload = Depends(require_role("admin")),
):
    if not req.ids:
        raise HTTPException(status_code=422, detail="ids list cannot be empty")
    if req.action not in ("approve", "reject", "delete"):
        raise HTTPException(status_code=422, detail="action must be approve, reject, or delete")

    pool = await _get_pool()
    results = {"processed": 0, "errors": []}

    for cid in req.ids:
        try:
            if req.action == "delete":
                await pool.execute("DELETE FROM concepts WHERE id = $1", cid)
            elif req.action == "approve":
                await pool.execute(
                    "UPDATE concepts SET status = 'approved', updated_at = now() WHERE id = $1", cid,
                )
            elif req.action == "reject":
                await pool.execute(
                    "UPDATE concepts SET status = 'rejected', updated_at = now() WHERE id = $1", cid,
                )
            results["processed"] += 1
        except Exception as exc:
            results["errors"].append({"id": cid, "error": str(exc)})

    return results
