"""Status transition engine — manages content lifecycle (draft → pending_review → approved → published)."""

import logging
from datetime import datetime, timezone

import asyncpg

logger = logging.getLogger(__name__)

VALID_TRANSITIONS = {
    "draft": ["pending_review"],
    "pending_review": ["approved", "rejected"],
    "rejected": ["draft"],
    "approved": ["published"],
    "published": [],
}


class StatusError(Exception):
    """Invalid status transition."""


def validate_transition(current: str, target: str) -> None:
    """Raise StatusError if the transition is not allowed."""
    allowed = VALID_TRANSITIONS.get(current, [])
    if target not in allowed:
        raise StatusError(
            f"Cannot transition from '{current}' to '{target}'. "
            f"Allowed: {allowed or 'none (terminal state)'}"
        )


async def transition_status(
    pool: asyncpg.Pool,
    table: str,
    record_id: str,
    new_status: str,
    *,
    reviewer_id: str | None = None,
    comments: str | None = None,
) -> asyncpg.Record:
    """Transition a record's status, validating the move and logging the review if applicable."""
    row = await pool.fetchrow(f"SELECT id, status FROM {table} WHERE id = $1", record_id)
    if not row:
        raise ValueError(f"Record {record_id} not found in {table}")

    validate_transition(row["status"], new_status)

    await pool.execute(
        f"UPDATE {table} SET status = $1, updated_at = $2 WHERE id = $3",
        new_status, datetime.now(timezone.utc), record_id,
    )

    if new_status in ("approved", "rejected") and reviewer_id:
        await pool.execute(
            "INSERT INTO reviews (concept_id, reviewer_id, action, comments) VALUES ($1, $2, $3, $4)",
            record_id, reviewer_id, new_status, comments,
        )

    logger.info("%s %s: %s → %s", table, record_id, row["status"], new_status)
    updated = await pool.fetchrow(f"SELECT * FROM {table} WHERE id = $1", record_id)
    return updated
