"""Grade catalog routes — /grades (R1).

Read-only endpoints exposing the per-grade/phase configuration and CAPS reference.
"""

import asyncpg
from fastapi import APIRouter, Depends, HTTPException

from src.middleware.jwt import TokenPayload, get_current_user, require_role
from src.services import grade_config

router = APIRouter(prefix="/grades", tags=["grades"])


async def _get_pool() -> asyncpg.Pool:
    import os
    dsn = os.getenv("DATABASE_URL", "postgresql://localhost/polelo")
    return await asyncpg.create_pool(dsn, min_size=1, max_size=5)


@router.get("")
async def list_grades(
    user: TokenPayload = Depends(require_role("admin")),
):
    """List the full grade catalog (R–12 + University). Admin only."""
    pool = await _get_pool()
    return {"grades": await grade_config.list_grades(pool)}


@router.get("/{grade}")
async def get_grade(
    grade: int,
    user: TokenPayload = Depends(get_current_user),
):
    """Return config + CAPS reference for one grade."""
    try:
        validated = grade_config.validate_grade(grade)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None

    pool = await _get_pool()
    try:
        config = await grade_config.get_grade_config(validated, pool)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None

    return {"grade": config}
