"""Search routes — /search with pg_trgm fuzzy matching and faceted filters."""

from fastapi import APIRouter, Depends, Query
import asyncpg

from src.middleware.jwt import TokenPayload, get_current_user

router = APIRouter(prefix="/search", tags=["search"])


async def _get_pool() -> asyncpg.Pool:
    import os
    dsn = os.getenv("DATABASE_URL", "postgresql://localhost/polelo")
    return await asyncpg.create_pool(dsn, min_size=1, max_size=5)


@router.get("")
async def search(
    q: str = Query(..., min_length=1, description="Search query in Sepedi or English"),
    domain: str | None = None,
    grade: int | None = None,
    include_translations: bool = False,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user: TokenPayload = Depends(get_current_user),
):
    pool = await _get_pool()
    results = []
    facets_domain: dict[str, int] = {}
    facets_grade: dict[int, int] = {}

    # Search concepts
    concept_sql = """
        SELECT c.id, c.name_en, c.domain, c.grade_levels, c.status,
               similarity(c.name_en, $1) as score
        FROM concepts c
        WHERE c.name_en % $1 AND c.status = 'published'
    """
    params: list = [q]
    idx = 2
    if domain:
        concept_sql += f" AND c.domain = ${idx}"
        params.append(domain)
        idx += 1
    if grade is not None:
        concept_sql += f" AND ${idx} = ANY(c.grade_levels)"
        params.append(grade)
        idx += 1

    concept_sql += f" ORDER BY score DESC LIMIT ${idx} OFFSET ${idx + 1}"
    params.extend([limit, (page - 1) * limit])

    concept_rows = await pool.fetch(concept_sql, *params)
    for row in concept_rows:
        results.append({
            "type": "concept",
            "score": round(row["score"], 4),
            "entity": {
                "id": str(row["id"]),
                "name_en": row["name_en"],
                "domain": row["domain"],
                "grade_levels": row["grade_levels"],
            },
        })

    # Search translations if requested
    if include_translations:
        trans_sql = """
            SELECT t.id, t.sepedi_term, t.concept_id, t.status,
                   similarity(t.sepedi_term, $1) as score
            FROM translations t
            WHERE t.sepedi_term % $1 AND t.status = 'published'
            ORDER BY score DESC
            LIMIT $2 OFFSET $3
        """
        trans_rows = await pool.fetch(trans_sql, q, limit, (page - 1) * limit)
        for row in trans_rows:
            results.append({
                "type": "translation",
                "score": round(row["score"], 4),
                "entity": {
                    "id": str(row["id"]),
                    "sepedi_term": row["sepedi_term"],
                    "concept_id": str(row["concept_id"]),
                },
            })

    # Build facets from concept results
    facet_rows = await pool.fetch(
        "SELECT domain, grade_levels FROM concepts WHERE name_en % $1 AND status = 'published'",
        q,
    )
    for row in facet_rows:
        d = row["domain"]
        facets_domain[d] = facets_domain.get(d, 0) + 1
        for g in row["grade_levels"]:
            facets_grade[g] = facets_grade.get(g, 0) + 1

    # Total count
    count_row = await pool.fetchrow(
        "SELECT count(*) as total FROM concepts WHERE name_en % $1 AND status = 'published'", q,
    )
    total = count_row["total"]

    return {
        "results": results,
        "facets": {
            "domain": facets_domain,
            "grade": facets_grade,
        },
        "total": total,
        "_links": {},
    }
