"""Review workflow routes — /review, /reviews."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import asyncpg

from src.middleware.jwt import TokenPayload, require_role
from src.services.status_engine import transition_status

router = APIRouter(tags=["reviews"])


async def _get_pool() -> asyncpg.Pool:
    import os
    dsn = os.getenv("DATABASE_URL", "postgresql://localhost/polelo")
    return await asyncpg.create_pool(dsn, min_size=1, max_size=5)


class ReviewRequest(BaseModel):
    concept_id: str
    action: str  # "approved" | "rejected"
    comments: str = ""


@router.post("/review")
async def submit_review(
    req: ReviewRequest,
    user: TokenPayload = Depends(require_role("reviewer", "admin")),
):
    if req.action not in ("approved", "rejected"):
        raise HTTPException(status_code=422, detail="action must be 'approved' or 'rejected'")
    if req.action == "rejected" and not req.comments.strip():
        raise HTTPException(status_code=422, detail="Comments are required when rejecting")

    pool = await _get_pool()
    new_status = "approved" if req.action == "approved" else "rejected"
    try:
        updated = await transition_status(
            pool, "concepts", req.concept_id, new_status,
            reviewer_id=user.sub, comments=req.comments,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return {"concept_id": req.concept_id, "status": updated["status"]}


@router.get("/reviews")
async def list_reviews(
    concept_id: str | None = None,
    action: str | None = None,
    user: TokenPayload = Depends(require_role("reviewer", "admin")),
):
    pool = await _get_pool()
    conditions = []
    params: list = []
    idx = 1
    if concept_id:
        conditions.append(f"r.concept_id = ${idx}")
        params.append(concept_id)
        idx += 1
    if action:
        conditions.append(f"r.action = ${idx}")
        params.append(action)
        idx += 1

    where = " AND ".join(conditions) if conditions else "true"
    rows = await pool.fetch(
        f"SELECT r.*, u.username as reviewer_name FROM reviews r LEFT JOIN users u ON r.reviewer_id = u.id "
        f"WHERE {where} ORDER BY r.created_at DESC LIMIT 50",
        *params,
    )
    return {"reviews": [dict(r) for r in rows]}
