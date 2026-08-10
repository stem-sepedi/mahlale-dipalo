"""Question triage routes — /questions.

M10 — student questions are mirrored to Forgejo/Gitea issues and answered by the
LLM engine after a triage pass (reuse answered / flag similar). Teachers and
parents verify answers; rejected answers are regenerated.
"""

import logging
from datetime import datetime, timezone

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from src.middleware.jwt import TokenPayload, require_role
from src.services.question_triage import triage_question

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/questions", tags=["questions"])


async def _get_pool() -> asyncpg.Pool:
    import os
    dsn = os.getenv("DATABASE_URL", "postgresql://localhost/polelo")
    return await asyncpg.create_pool(dsn, min_size=1, max_size=5)


def _forgejo():
    from src.services.forgejo_client import ForgejoClient
    return ForgejoClient()


class QuestionCreate(BaseModel):
    question_text: str
    grade: int | None = None
    subject: str | None = None
    student_ref: str | None = None


class ReviewRequest(BaseModel):
    review_comment: str | None = None


def _issue_body(question_text: str, grade: int | None, subject: str | None, student_ref: str | None) -> str:
    now = datetime.now(timezone.utc).isoformat()
    lines = [
        "## Polelo learner question",
        "",
        f"**Question:** {question_text}",
        f"**Grade:** {grade if grade is not None else 'unspecified'}",
        f"**Subject:** {subject or 'unspecified'}",
        f"**Student ref:** {student_ref or 'anonymous'}",
        f"**Submitted:** {now}",
    ]
    return "\n".join(lines)


@router.post("", status_code=201)
async def create_question(
    req: QuestionCreate,
    user: TokenPayload = Depends(require_role("learner", "teacher", "admin")),
):
    """Accept a student question, mirror it to a Forgejo issue, and triage it."""
    if not req.question_text.strip():
        raise HTTPException(status_code=422, detail="question_text is required")

    pool = await _get_pool()
    client = _forgejo()

    issue_number = None
    issue_url = None
    if client.is_configured:
        try:
            label_map = await client.ensure_labels()
            title = req.question_text.strip()[:80] or "Learner question"
            issue = await client.create_issue(
                title,
                _issue_body(req.question_text, req.grade, req.subject, req.student_ref),
                labels=[label_map["LLM_BACKLOG"]],
            )
            issue_number = int(issue.get("number", 0))
            issue_url = issue.get("html_url")
        except Exception as exc:
            logger.warning("Forgejo issue creation failed, continuing without issue: %s", exc)

    row = await pool.fetchrow(
        """INSERT INTO questions
           (question_text, grade, subject, student_ref, submitted_by, forgejo_issue_number, forgejo_issue_url, triage_status)
           VALUES ($1, $2, $3, $4, $5, $6, $7, 'new')
           RETURNING *""",
        req.question_text, req.grade, req.subject, req.student_ref, user.sub, issue_number, issue_url,
    )
    question = dict(row)
    question_id = str(row["id"])

    triage = {"decision": "new", "matching_issue_number": None, "answer": None}
    if client.is_configured and issue_number:
        try:
            label_map = await client.ensure_labels()
            triage = await triage_question(client, issue_number, req.question_text)

            if triage["decision"] == "answered":
                await client.replace_labels(
                    issue_number,
                    {"LLM_SIMILAR", "LLM_DONE", "HUMAN_VERIFIED"},
                    label_map,
                )
                reused = triage.get("answer") or ""
                await client.post_comment(
                    issue_number,
                    f"Reused answer from issue #{triage['matching_issue_number']}:\n\n{reused}",
                )
                answer_row = await pool.fetchrow(
                    """INSERT INTO question_answers
                       (question_id, answer_sep, confidence_score, status, generated_by)
                       VALUES ($1, $2, 1.0, 'human_verified', $3)
                       RETURNING *""",
                    question_id,
                    reused,
                    f"reuse:issue-{triage['matching_issue_number']}",
                )
                await pool.execute(
                    """UPDATE questions
                       SET triage_status = 'verified', matching_issue_number = $2, updated_at = now()
                       WHERE id = $1""",
                    question_id, triage["matching_issue_number"],
                )
                question["triage_status"] = "verified"
                question["matching_issue_number"] = triage["matching_issue_number"]
                question["answer"] = dict(answer_row)
            elif triage["decision"] == "similar":
                await client.add_labels(issue_number, [label_map["LLM_SIMILAR"]])
                await pool.execute(
                    "UPDATE questions SET matching_issue_number = $2, updated_at = now() WHERE id = $1",
                    question_id, triage["matching_issue_number"],
                )
                question["matching_issue_number"] = triage["matching_issue_number"]
        except Exception as exc:
            logger.warning("Forgejo triage failed for %s: %s", question_id, exc)
            triage = {"decision": "new", "matching_issue_number": None, "answer": None}

    return {"question": question, "triage": triage}


@router.get("")
async def list_questions(
    user: TokenPayload = Depends(require_role("learner", "teacher", "admin")),
    status: str = Query("all", description="all, new, similar, dispatched, answered, verified, rejected, human_backlog"),
    grade: int | None = None,
    subject: str | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    """List questions. `status=human_backlog` is the teacher/parent moderation queue."""
    pool = await _get_pool()

    conditions = []
    params: list = []
    idx = 1

    if status == "human_backlog":
        conditions.append(
            "EXISTS (SELECT 1 FROM question_answers a WHERE a.question_id = q.id AND a.status = 'llm_done')"
        )
    elif status != "all":
        conditions.append(f"q.triage_status = ${idx}")
        params.append(status)
        idx += 1

    if grade is not None:
        conditions.append(f"q.grade = ${idx}")
        params.append(grade)
        idx += 1

    if subject:
        conditions.append(f"q.subject = ${idx}")
        params.append(subject)
        idx += 1

    where = " AND ".join(conditions) if conditions else "true"
    offset = (page - 1) * limit

    count_row = await pool.fetchrow(f"SELECT count(*) as total FROM questions q WHERE {where}", *params)
    total = count_row["total"]

    rows = await pool.fetch(
        f"""SELECT q.* FROM questions q
            WHERE {where}
            ORDER BY q.created_at DESC
            LIMIT ${idx} OFFSET ${idx + 1}""",
        *params, limit, offset,
    )

    items = []
    for r in rows:
        qid = str(r["id"])
        answers = [dict(a) for a in await pool.fetch(
            "SELECT * FROM question_answers WHERE question_id = $1 ORDER BY created_at DESC", qid
        )]
        item = dict(r)
        item["latest_answer"] = answers[0] if answers else None
        items.append(item)

    return {
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
        "_links": {
            "self": f"/api/v1/questions?page={page}&limit={limit}&status={status}",
            "next": f"/api/v1/questions?page={page + 1}&limit={limit}&status={status}" if offset + limit < total else None,
            "prev": f"/api/v1/questions?page={page - 1}&limit={limit}&status={status}" if page > 1 else None,
        },
    }


@router.get("/{question_id}")
async def get_question(
    question_id: str,
    user: TokenPayload = Depends(require_role("learner", "teacher", "admin")),
):
    pool = await _get_pool()
    row = await pool.fetchrow("SELECT * FROM questions WHERE id = $1", question_id)
    if not row:
        raise HTTPException(status_code=404, detail="Question not found")

    answers = [dict(a) for a in await pool.fetch(
        "SELECT * FROM question_answers WHERE question_id = $1 ORDER BY created_at DESC", question_id
    )]
    question = dict(row)
    question["answers"] = answers
    return question


@router.post("/{question_id}/answer", status_code=202)
async def dispatch_answer(
    question_id: str,
    user: TokenPayload = Depends(require_role("teacher", "admin")),
):
    """Dispatch a question to the LLM. Queued via MQTT like the translation pipeline."""
    pool = await _get_pool()
    question = await pool.fetchrow("SELECT * FROM questions WHERE id = $1", question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    if question["triage_status"] in ("answered", "verified"):
        raise HTTPException(status_code=400, detail="Question already answered")

    if question["triage_status"] == "dispatched":
        raise HTTPException(status_code=409, detail="Question already dispatched")

    client = _forgejo()
    if client.is_configured and question["forgejo_issue_number"]:
        try:
            label_map = await client.ensure_labels()
            await client.replace_labels(
                int(question["forgejo_issue_number"]),
                {"LLM_WIP"},
                label_map,
            )
        except Exception as exc:
            logger.warning("Forgejo dispatch labels failed: %s", exc)

    # Queue the job and broadcast the request over MQTT.
    from src.services.mqtt_worker import MQTTProducer
    try:
        producer = MQTTProducer()
        producer.connect()
        producer.publish_question_answer_request(question_id)
        producer.disconnect()
    except Exception as exc:
        logger.warning("MQTT publish failed, job still recorded: %s", exc)

    await pool.execute(
        """INSERT INTO mqtt_jobs (topic, payload, status)
           VALUES ('question.answer.request', $1, 'pending')""",
        {"question_id": question_id},
    )
    await pool.execute(
        "UPDATE questions SET triage_status = 'dispatched', updated_at = now() WHERE id = $1",
        question_id,
    )

    return {
        "status": "dispatched",
        "question_id": question_id,
        "forgejo_issue_number": question["forgejo_issue_number"],
    }


@router.post("/{question_id}/verify")
async def verify_answer(
    question_id: str,
    req: ReviewRequest | None = None,
    user: TokenPayload = Depends(require_role("teacher", "admin")),
):
    """Teacher/parent confirms an answer — adds HUMAN_VERIFIED alongside LLM_DONE."""
    pool = await _get_pool()
    question = await pool.fetchrow("SELECT * FROM questions WHERE id = $1", question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    answer = await pool.fetchrow(
        "SELECT * FROM question_answers WHERE question_id = $1 ORDER BY created_at DESC LIMIT 1",
        question_id,
    )
    if not answer:
        raise HTTPException(status_code=404, detail="No answer to verify")
    if answer["status"] == "human_verified":
        raise HTTPException(status_code=409, detail="Answer already verified")
    if answer["status"] == "rejected":
        raise HTTPException(status_code=409, detail="Answer was rejected — dispatch a new answer first")

    comment = req.review_comment if req else None
    await pool.execute(
        """UPDATE question_answers
           SET status = 'human_verified', reviewed_by = $2, review_comment = COALESCE($3, review_comment),
               updated_at = now()
           WHERE id = $1""",
        answer["id"], user.sub, comment,
    )
    await pool.execute(
        "UPDATE questions SET triage_status = 'verified', updated_at = now() WHERE id = $1",
        question_id,
    )

    client = _forgejo()
    if client.is_configured and question["forgejo_issue_number"]:
        try:
            label_map = await client.ensure_labels()
            await client.replace_labels(
                int(question["forgejo_issue_number"]),
                {"LLM_DONE", "HUMAN_VERIFIED"},
                label_map,
            )
        except Exception as exc:
            logger.warning("Forgejo verify labels failed: %s", exc)

    updated = await pool.fetchrow(
        "SELECT * FROM question_answers WHERE id = $1", answer["id"]
    )
    return {"status": "verified", "answer": dict(updated)}


@router.post("/{question_id}/reject")
async def reject_answer(
    question_id: str,
    req: ReviewRequest | None = None,
    user: TokenPayload = Depends(require_role("teacher", "admin")),
):
    """Reject an answer — issue reopened with REJECTED and sent back to LLM_BACKLOG."""
    pool = await _get_pool()
    question = await pool.fetchrow("SELECT * FROM questions WHERE id = $1", question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    answer = await pool.fetchrow(
        "SELECT * FROM question_answers WHERE question_id = $1 ORDER BY created_at DESC LIMIT 1",
        question_id,
    )
    if not answer:
        raise HTTPException(status_code=404, detail="No answer to reject")
    if answer["status"] == "rejected":
        raise HTTPException(status_code=409, detail="Answer already rejected")

    comment = (req.review_comment if req else None) or ""
    await pool.execute(
        """UPDATE question_answers
           SET status = 'rejected', reviewed_by = $2, review_comment = COALESCE($3, review_comment),
               updated_at = now()
           WHERE id = $1""",
        answer["id"], user.sub, comment,
    )
    await pool.execute(
        "UPDATE questions SET triage_status = 'rejected', updated_at = now() WHERE id = $1",
        question_id,
    )

    client = _forgejo()
    if client.is_configured and question["forgejo_issue_number"]:
        try:
            label_map = await client.ensure_labels()
            await client.reopen_issue(int(question["forgejo_issue_number"]))
            await client.replace_labels(
                int(question["forgejo_issue_number"]),
                {"REJECTED", "LLM_BACKLOG"},
                label_map,
            )
        except Exception as exc:
            logger.warning("Forgejo reject labels failed: %s", exc)

    updated = await pool.fetchrow(
        "SELECT * FROM question_answers WHERE id = $1", answer["id"]
    )
    return {"status": "rejected", "answer": dict(updated)}
