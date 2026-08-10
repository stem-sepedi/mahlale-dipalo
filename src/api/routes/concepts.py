"""Concept CRUD routes — /concepts."""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
import asyncpg

from src.middleware.jwt import TokenPayload, get_current_user, require_role

router = APIRouter(prefix="/concepts", tags=["concepts"])


async def _get_pool() -> asyncpg.Pool:
    import os
    dsn = os.getenv("DATABASE_URL", "postgresql://localhost/polelo")
    return await asyncpg.create_pool(dsn, min_size=1, max_size=5)


class ConceptCreate(BaseModel):
    name_en: str
    definition_en: str = ""
    domain: str = "General"
    grade_levels: list[int] = []


class ConceptUpdate(BaseModel):
    name_en: str | None = None
    definition_en: str | None = None
    domain: str | None = None
    grade_levels: list[int] | None = None


def _concept_links(cid: str) -> dict:
    return {
        "self": f"/api/v1/concept/{cid}",
        "translations": f"/api/v1/concept/{cid}/translations",
        "explanations": f"/api/v1/concept/{cid}/explanations",
        "versions": f"/api/v1/concept/{cid}/versions",
        "reviews": f"/api/v1/concept/{cid}/reviews",
    }


@router.get("")
async def list_concepts(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: str = Query("", description="Fuzzy match against name_en"),
    domain: str | None = None,
    grade: int | None = None,
    status: str = Query("published"),
):
    pool = await _get_pool()
    conditions = []
    params: list = []
    idx = 1

    if status != "all":
        conditions.append(f"c.status = ${idx}")
        params.append(status)
        idx += 1

    if domain:
        conditions.append(f"c.domain = ${idx}")
        params.append(domain)
        idx += 1

    if grade is not None:
        conditions.append(f"${idx} = ANY(c.grade_levels)")
        params.append(grade)
        idx += 1

    if search:
        conditions.append(f"c.name_en % ${idx}")
        params.append(search)
        idx += 1

    where = " AND ".join(conditions) if conditions else "true"
    offset = (page - 1) * limit

    count_row = await pool.fetchrow(f"SELECT count(*) as total FROM concepts c WHERE {where}", *params)
    total = count_row["total"]

    rows = await pool.fetch(
        f"SELECT c.* FROM concepts c WHERE {where} ORDER BY c.created_at DESC LIMIT ${idx} OFFSET ${idx + 1}",
        *params, limit, offset,
    )

    items = [dict(r) | {"_links": _concept_links(str(r["id"]))} for r in rows]

    return {
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
        "_links": {
            "self": f"/api/v1/concepts?page={page}&limit={limit}",
            "next": f"/api/v1/concepts?page={page + 1}&limit={limit}" if offset + limit < total else None,
            "prev": f"/api/v1/concepts?page={page - 1}&limit={limit}" if page > 1 else None,
        },
    }


@router.post("", status_code=201)
async def create_concept(
    req: ConceptCreate,
    user: TokenPayload = Depends(require_role("teacher", "admin")),
):
    pool = await _get_pool()
    row = await pool.fetchrow(
        """INSERT INTO concepts (name_en, definition_en, domain, grade_levels, status, created_by)
           VALUES ($1, $2, $3, $4, 'draft', $5)
           RETURNING *""",
        req.name_en, req.definition_en, req.domain, req.grade_levels, user.sub,
    )
    concept = dict(row)
    concept["_links"] = _concept_links(str(row["id"]))
    return {"concept": concept}


@router.get("/{concept_id}")
async def get_concept(concept_id: str, user: TokenPayload = Depends(get_current_user)):
    pool = await _get_pool()
    row = await pool.fetchrow("SELECT * FROM concepts WHERE id = $1", concept_id)
    if not row:
        raise HTTPException(status_code=404, detail="Concept not found")
    concept = dict(row)

    translations = await pool.fetch(
        "SELECT * FROM translations WHERE concept_id = $1 ORDER BY created_at DESC", concept_id
    )
    explanations = await pool.fetch(
        "SELECT * FROM explanations WHERE concept_id = $1 ORDER BY grade_level", concept_id
    )

    concept["translations"] = [dict(t) for t in translations]
    concept["explanations"] = [dict(e) for e in explanations]
    concept["_links"] = _concept_links(concept_id)
    return concept


@router.patch("/{concept_id}")
async def update_concept(
    concept_id: str,
    req: ConceptUpdate,
    user: TokenPayload = Depends(require_role("teacher", "admin")),
):
    pool = await _get_pool()
    existing = await pool.fetchrow("SELECT * FROM concepts WHERE id = $1", concept_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Concept not found")

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
    set_parts.append(f"updated_at = now()")
    params.append(concept_id)

    row = await pool.fetchrow(
        f"UPDATE concepts SET {', '.join(set_parts)} WHERE id = ${idx} RETURNING *",
        *params,
    )
    concept = dict(row)
    concept["_links"] = _concept_links(concept_id)
    return concept


@router.delete("/{concept_id}", status_code=204)
async def delete_concept(
    concept_id: str,
    user: TokenPayload = Depends(require_role("admin")),
):
    pool = await _get_pool()
    result = await pool.execute("DELETE FROM concepts WHERE id = $1", concept_id)
    if result == "DELETE 0":
        raise HTTPException(status_code=404, detail="Concept not found")
    return None
