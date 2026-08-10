"""Auth routes — /auth/login, /auth/register, /auth/refresh, /auth/logout."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import asyncpg

from src.middleware.jwt import (
    TokenPayload,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
    get_current_user,
)

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str
    role: str = "learner"


class RefreshRequest(BaseModel):
    refresh_token: str


async def _get_pool() -> asyncpg.Pool:
    """Get or create the database connection pool."""
    import os
    dsn = os.getenv("DATABASE_URL", "postgresql://localhost/polelo")
    return await asyncpg.create_pool(dsn, min_size=1, max_size=5)


async def _get_user(pool: asyncpg.Pool, username: str) -> asyncpg.Record | None:
    return await pool.fetchrow("SELECT * FROM users WHERE username = $1", username)


async def _create_user(pool: asyncpg.Pool, username: str, password_hash: str, role: str) -> asyncpg.Record:
    return await pool.fetchrow(
        "INSERT INTO users (username, password_hash, role) VALUES ($1, $2, $3::user_role) RETURNING id, username, role",
        username, password_hash, role,
    )


@router.post("/register")
async def register(req: RegisterRequest):
    pool = await _get_pool()
    existing = await _get_user(pool, req.username)
    if existing:
        raise HTTPException(status_code=409, detail="Username already exists")
    hashed = hash_password(req.password)
    user = await _create_user(pool, req.username, hashed, req.role)
    access_token, _ = create_access_token(str(user["id"]), user["username"], user["role"])
    refresh_token, _ = create_refresh_token(str(user["id"]))
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "Bearer",
        "expires_in": 86400,
    }


@router.post("/login")
async def login(req: LoginRequest):
    pool = await _get_pool()
    user = await _get_user(pool, req.username)
    if not user or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user["active"]:
        raise HTTPException(status_code=403, detail="Account disabled")
    access_token, _ = create_access_token(str(user["id"]), user["username"], user["role"])
    refresh_token, _ = create_refresh_token(str(user["id"]))
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "Bearer",
        "expires_in": 86400,
    }


@router.post("/refresh")
async def refresh(req: RefreshRequest):
    payload = decode_token(req.refresh_token)
    if getattr(payload, "type", None) != "refresh":
        raise HTTPException(status_code=401, detail="Not a refresh token")
    pool = await _get_pool()
    user = await pool.fetchrow("SELECT * FROM users WHERE id = $1", payload.sub)
    if not user or not user["active"]:
        raise HTTPException(status_code=401, detail="User not found or disabled")
    access_token, _ = create_access_token(str(user["id"]), user["username"], user["role"])
    refresh_token, _ = create_refresh_token(str(user["id"]))
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "Bearer",
        "expires_in": 86400,
    }


@router.post("/logout")
async def logout(user: TokenPayload = Depends(get_current_user)):
    return {"status": "logged_out"}
