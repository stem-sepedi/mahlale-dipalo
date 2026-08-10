"""Moodle webhook routes — /moodle/webhooks/*.

Moodle → Polelo event ingestion with HMAC-SHA256 signature verification.
Events are queued via MQTT for async processing by the sync engine.
"""

import hashlib
import hmac
import json
import os
import time
from typing import Any

import asyncpg
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel

router = APIRouter(prefix="/moodle/webhooks", tags=["moodle"])


async def _get_pool() -> asyncpg.Pool:
    dsn = os.getenv("DATABASE_URL", "postgresql://localhost/polelo")
    return await asyncpg.create_pool(dsn, min_size=1, max_size=5)


# ------------------------------------------------------------------
# Signature verification — HMAC-SHA256
# ------------------------------------------------------------------

SECRET_HEADER = "X-Moodle-Signature"
TIMESTAMP_HEADER = "X-Moodle-Timestamp"


def _compute_signature(raw_body: bytes, secret: str, timestamp: str) -> str:
    message = f"{timestamp}.{raw_body.decode('utf-8', errors='replace')}"
    return hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()


def _valid_secrets() -> list[str]:
    return [s.strip() for s in os.getenv("MoodleWebhookSecret", "").split(",") if s.strip()]


async def _verify_signature(
    request: Request,
    x_moodle_signature: str | None = Header(default=None),
    x_moodle_timestamp: str | None = Header(default=None),
) -> bytes:
    """Verify HMAC signature and replay window. Returns the raw body."""
    raw_body = await request.body()
    if not x_moodle_signature or not x_moodle_timestamp:
        raise HTTPException(status_code=401, detail="Missing signature headers")

    try:
        ts = int(x_moodle_timestamp)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid timestamp header") from None

    if abs(int(time.time()) - ts) > 300:
        raise HTTPException(status_code=401, detail="Webhook timestamp outside allowed window")

    secrets = _valid_secrets()
    if not secrets:
        raise HTTPException(status_code=503, detail="Webhook secret not configured")

    valid = any(
        hmac.compare_digest(
            _compute_signature(raw_body, secret, x_moodle_timestamp),
            x_moodle_signature,
        )
        for secret in secrets
    )
    if not valid:
        raise HTTPException(status_code=403, detail="Invalid webhook signature")
    if request.headers.get("content-type", "").startswith("application/json"):
        pass
    return raw_body


class EnrolmentEvent(BaseModel):
    event_type: str = "enrolment"
    course_id: int
    user_id: int
    instance_url: str
    timestamp: str | None = None


class ActivityEvent(BaseModel):
    event_type: str = "activity"
    concept_id: str
    course_id: int
    user_id: int
    completed: bool
    instance_url: str
    timestamp: str | None = None


class QuizSubmissionEvent(BaseModel):
    event_type: str = "quiz-submission"
    concept_id: str
    course_id: int
    user_id: int
    score_pct: float
    questions_total: int = 0
    record_template: str | None = None
    record_template_moodle: str | None = None
    instance_url: str
    timestamp: str | None = None


async def _queue_event(pool: asyncpg.Pool, instance_url: str, event_type: str, payload: dict) -> str:
    """Persist event to moodle_webhook_logs then enqueue to MQTT for async processing."""
    instance = await pool.fetchrow(
        "SELECT id FROM moodle_instances WHERE base_url = $1 AND active = true", instance_url
    )
    instance_id = str(instance["id"]) if instance else None

    log = await pool.fetchrow(
        """INSERT INTO moodle_webhook_logs (instance_id, event_type, payload, signature_valid, processed, process_status)
           VALUES ($1, $2, $3, true, false, 'queued')
           RETURNING id""",
        instance_id, event_type, json.dumps(payload),
    )

    try:
        from src.services.mqtt_worker import MQTTProducer
        producer = MQTTProducer()
        producer.connect()
        producer._client.publish("moodle.webhook", json.dumps({
            "event_type": event_type,
            "payload": payload,
            "log_id": str(log["id"]),
        }), qos=1)
        producer.disconnect()
    except Exception:
        await pool.execute(
            "UPDATE moodle_webhook_logs SET process_status = 'mqtt_failed' WHERE id = $1", log["id"]
        )

    return str(log["id"])


@router.post("/enrolment")
async def webhook_enrolment(
    request: Request,
    raw_body: bytes = Depends(_verify_signature),
):
    """Course enrolment event → trigger bulk translation for the course."""
    body = _parse_body(raw_body)
    if not isinstance(body, dict):
        raise HTTPException(status_code=422, detail="Expected JSON object")

    enrollment = EnrolmentEvent(**{k: v for k, v in body.items() if k in EnrolmentEvent.model_fields})
    pool = await _get_pool()

    log_id = await _queue_event(
        pool, enrollment.instance_url, "enrolment", enrollment.model_dump()
    )
    return {"status": "queued", "log_id": log_id, "event": enrollment.model_dump()}


@router.post("/activity")
async def webhook_activity(
    request: Request,
    raw_body: bytes = Depends(_verify_signature),
):
    """Activity completion → update concept mastery."""
    body = _parse_body(raw_body)
    if not isinstance(body, dict):
        raise HTTPException(status_code=422, detail="Expected JSON object")

    event = ActivityEvent(**{k: v for k, v in body.items() if k in ActivityEvent.model_fields})
    pool = await _get_pool()

    log_id = await _queue_event(pool, event.instance_url, "activity", event.model_dump())
    return {"status": "queued", "log_id": log_id, "event": event.model_dump()}


@router.post("/quiz-submission")
async def webhook_quiz_submission(
    request: Request,
    raw_body: bytes = Depends(_verify_signature),
):
    """Quiz attempt → store results in Polelo."""
    body = _parse_body(raw_body)
    if not isinstance(body, dict):
        raise HTTPException(status_code=422, detail="Expected JSON object")

    event = QuizSubmissionEvent(**{k: v for k, v in body.items() if k in QuizSubmissionEvent.model_fields})
    pool = await _get_pool()

    log_id = await _queue_event(pool, event.instance_url, "quiz-submission", event.model_dump())
    return {"status": "queued", "log_id": log_id, "event": event.model_dump()}


def _parse_body(raw_body: bytes) -> Any:
    try:
        return json.loads(raw_body.decode())
    except json.JSONDecodeError:
        raise HTTPException(status_code=422, detail="Invalid JSON body") from None
