"""User management routes — /users."""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
import asyncpg

from src.middleware.jwt import TokenPayload, get_current_user, require_role, hash_password

router = APIRouter(prefix="/users", tags=["users"])


async def _get_pool() -> asyncpg.Pool:
    import os
    dsn = os.getenv("DATABASE_URL", "postgresql://localhost/polelo")
    return await asyncpg.create_pool(dsn, min_size=1, max_size=5)


class UserCreate(BaseModel):
    username: str
    password: str
    role: str = "learner"


class UserUpdate(BaseModel):
    role: str | None = None
    active: bool | None = None


@router.get("/me")
async def get_me(user: TokenPayload = Depends(get_current_user)):
    pool = await _get_pool()
    row = await pool.fetchrow("SELECT id, username, role, active, created_at FROM users WHERE id = $1", user.sub)
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    return dict(row)


@router.get("")
async def list_users(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user: TokenPayload = Depends(require_role("admin")),
):
    pool = await _get_pool()
    offset = (page - 1) * limit
    count_row = await pool.fetchrow("SELECT count(*) as total FROM users")
    rows = await pool.fetch(
        "SELECT id, username, role, active, created_at FROM users ORDER BY created_at DESC LIMIT $1 OFFSET $2",
        limit, offset,
    )
    return {
        "items": [dict(r) for r in rows],
        "total": count_row["total"],
        "page": page,
        "limit": limit,
    }


@router.post("", status_code=201)
async def create_user(
    req: UserCreate,
    user: TokenPayload = Depends(require_role("admin")),
):
    pool = await _get_pool()
    existing = await pool.fetchrow("SELECT id FROM users WHERE username = $1", req.username)
    if existing:
        raise HTTPException(status_code=409, detail="Username already exists")
    hashed = hash_password(req.password)
    row = await pool.fetchrow(
        "INSERT INTO users (username, password_hash, role) VALUES ($1, $2, $3::user_role) "
        "RETURNING id, username, role, active, created_at",
        req.username, hashed, req.role,
    )
    return dict(row)


@router.patch("/{user_id}")
async def update_user(
    user_id: str,
    req: UserUpdate,
    user: TokenPayload = Depends(require_role("admin")),
):
    pool = await _get_pool()
    updates = {k: v for k, v in req.model_dump(exclude_unset=True).items()}
    if not updates:
        raise HTTPException(status_code=422, detail="No fields to update")

    set_parts = []
    params: list = []
    idx = 1
    for field, value in updates.items():
        set_parts.append(f"{field} = ${idx}")
        params.append(value)
        idx += 1
    params.append(user_id)

    row = await pool.fetchrow(
        f"UPDATE users SET {', '.join(set_parts)} WHERE id = ${idx} "
        "RETURNING id, username, role, active, created_at",
        *params,
    )
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    return dict(row)
