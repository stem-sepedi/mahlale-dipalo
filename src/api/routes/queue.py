"""Queue management routes — /queue/stats, /queue/dead-letter."""

from fastapi import APIRouter, Depends
import asyncpg

from src.middleware.jwt import TokenPayload, require_role

router = APIRouter(prefix="/queue", tags=["queue"])


async def _get_pool() -> asyncpg.Pool:
    import os
    dsn = os.getenv("DATABASE_URL", "postgresql://localhost/polelo")
    return await asyncpg.create_pool(dsn, min_size=1, max_size=5)


@router.get("/stats")
async def queue_stats(user: TokenPayload = Depends(require_role("admin"))):
    pool = await _get_pool()

    pending = await pool.fetchrow(
        "SELECT count(*) as c FROM mqtt_jobs WHERE status = 'pending'"
    )
    completed = await pool.fetchrow(
        "SELECT count(*) as c FROM mqtt_jobs WHERE status = 'completed'"
    )
    failed = await pool.fetchrow(
        "SELECT count(*) as c FROM mqtt_jobs WHERE status = 'failed'"
    )

    topic_counts = await pool.fetch(
        "SELECT topic, count(*) as c FROM mqtt_jobs WHERE status = 'pending' GROUP BY topic"
    )

    return {
        "pending_jobs": {r["topic"]: r["c"] for r in topic_counts},
        "pending_total": pending["c"],
        "completed_total": completed["c"],
        "failed_total": failed["c"],
    }


@router.get("/dead-letter")
async def dead_letter(user: TokenPayload = Depends(require_role("admin"))):
    pool = await _get_pool()
    rows = await pool.fetch(
        "SELECT * FROM mqtt_jobs WHERE status = 'failed' ORDER BY updated_at DESC LIMIT 50"
    )
    return {"dead_letters": [dict(r) for r in rows]}
