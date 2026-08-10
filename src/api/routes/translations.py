"""Translate routes — /translate, /translations/{id}, /translations/{id}/submit."""

import asyncpg
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.middleware.jwt import TokenPayload, get_current_user, require_role
from src.services.grade_config import validate_grade_levels
from src.services.translation_engine import TranslationEngine

router = APIRouter(tags=["translations"])


async def _get_pool() -> asyncpg.Pool:
    import os
    dsn = os.getenv("DATABASE_URL", "postgresql://localhost/polelo")
    return await asyncpg.create_pool(dsn, min_size=1, max_size=5)


class TranslateRequest(BaseModel):
    term: str
    domain: str = "General"
    grade_levels: list[int] = [8]
    context_sep: str = ""


class TranslationUpdate(BaseModel):
    sepedi_term: str | None = None


@router.post("/translate", status_code=201)
async def translate(
    req: TranslateRequest,
    user: TokenPayload = Depends(require_role("translator", "teacher", "admin")),
):
    try:
        grade_levels = validate_grade_levels(req.grade_levels)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None

    engine = TranslationEngine()
    pool = await _get_pool()

    # Find or create the concept
    concept = await pool.fetchrow(
        "SELECT id FROM concepts WHERE name_en = $1", req.term,
    )
    if not concept:
        concept = await pool.fetchrow(
            """INSERT INTO concepts (name_en, domain, grade_levels, status, created_by)
               VALUES ($1, $2, $3, 'draft', $4) RETURNING id""",
            req.term, req.domain, grade_levels, user.sub,
        )

    # Generate translations via Ollama
    result = await engine.translate(req.term, req.domain, req.grade_levels, req.context_sep)

    # Store in DB
    row = await pool.fetchrow(
        """INSERT INTO translations
           (concept_id, sepedi_term, confidence_score, alternative_forms, status, generated_by, created_by)
           VALUES ($1, $2, $3, $4, 'draft', 'AI Agent', $5)
           RETURNING *""",
        concept["id"],
        result.get("sepedi_term", req.term),
        result.get("confidence_score", 0.0),
        result.get("alternative_forms", []),
        user.sub,
    )

    return {
        "translation": {
            "id": str(row["id"]),
            "concept_id": str(concept["id"]),
            "sepedi_term": row["sepedi_term"],
            "confidence_score": row["confidence_score"],
            "alternative_forms": row["alternative_forms"],
            "status": row["status"],
            "generated_by": row["generated_by"],
        }
    }


@router.patch("/translations/{translation_id}")
async def update_translation(
    translation_id: str,
    req: TranslationUpdate,
    user: TokenPayload = Depends(get_current_user),
):
    pool = await _get_pool()
    row = await pool.fetchrow("SELECT * FROM translations WHERE id = $1", translation_id)
    if not row:
        raise HTTPException(status_code=404, detail="Translation not found")
    if str(row["created_by"]) != user.sub and user.role not in ("admin", "reviewer"):
        raise HTTPException(status_code=403, detail="Not your translation")

    if req.sepedi_term is not None:
        await pool.execute(
            "UPDATE translations SET sepedi_term = $1, updated_at = now() WHERE id = $2",
            req.sepedi_term, translation_id,
        )

    updated = await pool.fetchrow("SELECT * FROM translations WHERE id = $1", translation_id)
    return dict(updated)


@router.post("/translations/{translation_id}/submit")
async def submit_translation(
    translation_id: str,
    user: TokenPayload = Depends(get_current_user),
):
    pool = await _get_pool()
    row = await pool.fetchrow("SELECT * FROM translations WHERE id = $1", translation_id)
    if not row:
        raise HTTPException(status_code=404, detail="Translation not found")
    if row["status"] != "draft":
        raise HTTPException(status_code=400, detail=f"Cannot submit from status '{row['status']}'")

    await pool.execute(
        "UPDATE translations SET status = 'pending_review', updated_at = now() WHERE id = $1",
        translation_id,
    )
    return {"status": "pending_review", "translation_id": translation_id}
