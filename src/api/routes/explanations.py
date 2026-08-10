"""Explain routes — /explain, /explanations/{id}/submit."""

import asyncpg
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.middleware.jwt import TokenPayload, get_current_user, require_role
from src.services.grade_config import validate_grade
from src.services.translation_engine import TranslationEngine

router = APIRouter(tags=["explanations"])


async def _get_pool() -> asyncpg.Pool:
    import os
    dsn = os.getenv("DATABASE_URL", "postgresql://localhost/polelo")
    return await asyncpg.create_pool(dsn, min_size=1, max_size=5)


class ExplainRequest(BaseModel):
    concept_id: str
    grade_level: int = 8


@router.post("/explain", status_code=201)
async def explain(
    req: ExplainRequest,
    user: TokenPayload = Depends(require_role("teacher", "admin")),
):
    try:
        grade_level = validate_grade(req.grade_level)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None

    pool = await _get_pool()
    concept = await pool.fetchrow("SELECT * FROM concepts WHERE id = $1", req.concept_id)
    if not concept:
        raise HTTPException(status_code=404, detail="Concept not found")

    engine = TranslationEngine()
    result = await engine.explain(concept["name_en"], concept["domain"], grade_level)

    row = await pool.fetchrow(
        """INSERT INTO explanations
           (concept_id, grade_level, content_sep, examples_sep, status, generated_by, created_by)
           VALUES ($1, $2, $3, $4, 'draft', 'AI Agent', $5)
           RETURNING *""",
        req.concept_id,
        grade_level,
        result.get("content_sep", ""),
        result.get("examples_sep", []),
        user.sub,
    )

    return {
        "explanation": {
            "id": str(row["id"]),
            "concept_id": str(req.concept_id),
            "grade_level": row["grade_level"],
            "content_sep": row["content_sep"],
            "examples_sep": row["examples_sep"],
            "status": row["status"],
            "generated_by": row["generated_by"],
        }
    }


@router.post("/explanations/{explanation_id}/submit")
async def submit_explanation(
    explanation_id: str,
    user: TokenPayload = Depends(get_current_user),
):
    pool = await _get_pool()
    row = await pool.fetchrow("SELECT * FROM explanations WHERE id = $1", explanation_id)
    if not row:
        raise HTTPException(status_code=404, detail="Explanation not found")
    if row["status"] != "draft":
        raise HTTPException(status_code=400, detail=f"Cannot submit from status '{row['status']}'")

    await pool.execute(
        "UPDATE explanations SET status = 'pending_review', updated_at = now() WHERE id = $1",
        explanation_id,
    )
    return {"status": "pending_review", "explanation_id": explanation_id}
