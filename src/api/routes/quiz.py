"""Quiz routes — /concepts/{id}/quiz, /quiz/validate."""

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from src.middleware.jwt import TokenPayload, get_current_user
from src.services.grade_config import validate_grade
from src.services.translation_engine import TranslationEngine

router = APIRouter(tags=["quiz"])


async def _get_pool() -> asyncpg.Pool:
    import os
    dsn = os.getenv("DATABASE_URL", "postgresql://localhost/polelo")
    return await asyncpg.create_pool(dsn, min_size=1, max_size=5)


class QuizValidateRequest(BaseModel):
    concept_id: str
    grade_level: int
    answers: list[dict]


@router.get("/concepts/{concept_id}/quiz")
async def get_quiz(
    concept_id: str,
    grade_level: int = Query(8),
    count: int = Query(5, ge=1, le=20),
    type: str = Query("all", description="all, fill_in_blank, multiple_choice, short_answer"),
    user: TokenPayload = Depends(get_current_user),
):
    try:
        grade_level = validate_grade(grade_level)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None

    pool = await _get_pool()
    concept = await pool.fetchrow("SELECT * FROM concepts WHERE id = $1", concept_id)
    if not concept:
        raise HTTPException(status_code=404, detail="Concept not found")

    engine = TranslationEngine()
    questions = await engine.quiz(concept["name_en"], concept["domain"], grade_level, count)

    # Filter by type if requested
    if type != "all":
        questions = [q for q in questions if q.get("question_type") == type]

    # Store questions in DB
    stored = []
    for q in questions:
        row = await pool.fetchrow(
            """INSERT INTO quiz_questions
               (concept_id, grade_level, question_type, question_sep, options, correct_answer)
               VALUES ($1, $2, $3, $4, $5, $6)
               RETURNING id, question_sep, question_type, options""",
            concept_id,
            grade_level,
            q.get("question_type", "multiple_choice"),
            q.get("question_sep", ""),
            q.get("options", []),
            q.get("correct_answer", ""),
        )
        stored.append({
            "id": str(row["id"]),
            "question_sep": row["question_sep"],
            "question_type": row["question_type"],
            "options": row["options"],
        })

    return {"questions": stored, "concept_id": concept_id, "grade_level": grade_level}


@router.post("/quiz/validate")
async def validate_quiz(
    req: QuizValidateRequest,
    user: TokenPayload = Depends(get_current_user),
):
    try:
        req.grade_level = validate_grade(req.grade_level)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None

    pool = await _get_pool()
    results = []
    correct_count = 0

    for answer in req.answers:
        qid = answer.get("question_id")
        response = answer.get("response_sep", "")
        row = await pool.fetchrow("SELECT * FROM quiz_questions WHERE id = $1", qid)
        if not row:
            results.append({"question_id": qid, "correct": False, "score_pct": 0.0})
            continue

        is_correct = response.strip().lower() == row["correct_answer"].strip().lower()
        score = 1.0 if is_correct else 0.0
        if is_correct:
            correct_count += 1
        results.append({
            "question_id": qid,
            "correct": is_correct,
            "score_pct": score,
        })

    total = len(req.answers) or 1
    return {
        "results": results,
        "total_score_pct": round(correct_count / total, 2),
    }
