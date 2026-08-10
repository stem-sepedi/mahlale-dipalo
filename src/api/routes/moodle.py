"""Moodle integration routes — /moodle/*.

Content source API for Moodle LMS integration.
Auth: API key via X-Moodle-Key header (separate key space from AI workers).
Rate limit: 60 RPM per Moodle instance (IP-based).
"""

import hashlib
import hmac
import os
import xml.etree.ElementTree as ET
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel
import asyncpg

from src.middleware.api_key import verify_api_key

router = APIRouter(prefix="/moodle", tags=["moodle"])


async def _get_pool() -> asyncpg.Pool:
    dsn = os.getenv("DATABASE_URL", "postgresql://localhost/polelo")
    return await asyncpg.create_pool(dsn, min_size=1, max_size=5)


# ------------------------------------------------------------------
# Auth dependency — Moodle instances authenticate via X-Moodle-Key
# ------------------------------------------------------------------

_moodle_key_header = "X-Moodle-Key"


async def _require_moodle_key(request: Request) -> str:
    """Validate the Moodle API key. Returns the key on success."""
    key = request.headers.get(_moodle_key_header)
    if not key:
        raise HTTPException(status_code=401, detail="Missing X-Moodle-Key header")
    allowed = [k.strip() for k in os.getenv("MOODLE_API_KEYS", "").split(",") if k.strip()]
    if not allowed or key not in allowed:
        raise HTTPException(status_code=403, detail="Invalid Moodle API key")
    return key


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _jsonld_concept(row: dict, translations: list[dict], explanations: list[dict]) -> dict:
    """Build a JSON-LD compatible concept payload."""
    best_translation = translations[0] if translations else None
    sepedi_term = best_translation["sepedi_term"] if best_translation else None

    jsonld = {
        "@context": "https://schema.org",
        "@type": "DefinedTerm",
        "name": sepedi_term or row["name_en"],
        "alternateName": row["name_en"],
        "description": row.get("definition_en", ""),
        "inDefinedTermSet": {
            "@type": "DefinedTermSet",
            "name": "Polelo STEM Sepedi",
        },
    }
    if row.get("domain"):
        jsonld["additionalType"] = f"https://polelo.taip.co.za/domain/{row['domain'].lower().replace(' ', '-')}"

    return jsonld


def _moodle_quiz_xml(questions: list[dict], category: str = "Polelo") -> str:
    """Generate Moodle XML import format from quiz questions."""
    quiz = ET.Element("quiz")
    cat_el = ET.SubElement(quiz, "question")
    cat_el.set("type", "category")
    cat_text = ET.SubElement(cat_el, "category")
    cat_text.text = f"$course$/{category}"

    for q in questions:
        q_type = q.get("question_type", "multiple_choice")
        if q_type == "multiple_choice":
            q_el = ET.SubElement(quiz, "question")
            q_el.set("type", "multichoice")
            name_el = ET.SubElement(q_el, "name")
            name_text = ET.SubElement(name_el, "text")
            name_text.text = q.get("question_sep", "")[:80]
            question_text = ET.SubElement(q_el, "questiontext")
            question_text.set("format", "html")
            qt_text = ET.SubElement(question_text, "text")
            qt_text.text = q.get("question_sep", "")
            defaultgrade = ET.SubElement(q_el, "defaultgrade")
            defaultgrade.text = "1"
            single = ET.SubElement(q_el, "single")
            single.text = "true"
            shuffleanswers = ET.SubElement(q_el, "shuffleanswers")
            shuffleanswers.text = "1"
            options = q.get("options", [])
            correct = q.get("correct_answer", "")
            for opt in options:
                ans = ET.SubElement(q_el, "answer")
                fraction = "100" if opt == correct else "0"
                ans.set("fraction", fraction)
                ans_text = ET.SubElement(ans, "text")
                ans_text.text = opt
        elif q_type == "fill_in_blank":
            q_el = ET.SubElement(quiz, "question")
            q_el.set("type", "shortanswer")
            name_el = ET.SubElement(q_el, "name")
            name_text = ET.SubElement(name_el, "text")
            name_text.text = q.get("question_sep", "")[:80]
            question_text = ET.SubElement(q_el, "questiontext")
            question_text.set("format", "html")
            qt_text = ET.SubElement(question_text, "text")
            qt_text.text = q.get("question_sep", "")
            ans = ET.SubElement(q_el, "answer")
            ans.set("fraction", "100")
            ans_text = ET.SubElement(ans, "text")
            ans_text.text = q.get("correct_answer", "")
        else:
            q_el = ET.SubElement(quiz, "question")
            q_el.set("type", "shortanswer")
            name_el = ET.SubElement(q_el, "name")
            name_text = ET.SubElement(name_el, "text")
            name_text.text = q.get("question_sep", "")[:80]
            question_text = ET.SubElement(q_el, "questiontext")
            question_text.set("format", "html")
            qt_text = ET.SubElement(question_text, "text")
            qt_text.text = q.get("question_sep", "")
            ans = ET.SubElement(q_el, "answer")
            ans.set("fraction", "100")
            ans_text = ET.SubElement(ans, "text")
            ans_text.text = q.get("correct_answer", "")

    ET.indent(quiz, space="  ")
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(quiz, encoding="unicode", xml_declaration=False)


# ------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------

@router.get("/concepts")
async def moodle_concepts(
    request: Request,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    domain: str | None = None,
    grade: int | None = None,
    since: str | None = Query(None, description="ISO timestamp — only return concepts updated after this time"),
    format: str = Query("plain", description="plain or jsonld"),
    _key: str = Depends(_require_moodle_key),
):
    pool = await _get_pool()
    conditions = ["c.status = 'published'"]
    params: list = []
    idx = 1

    if domain:
        conditions.append(f"c.domain = ${idx}")
        params.append(domain)
        idx += 1

    if grade is not None:
        conditions.append(f"${idx} = ANY(c.grade_levels)")
        params.append(grade)
        idx += 1

    if since:
        conditions.append(f"c.updated_at > ${idx}")
        params.append(since)
        idx += 1

    where = " AND ".join(conditions)
    offset = (page - 1) * limit

    count_row = await pool.fetchrow(f"SELECT count(*) as total FROM concepts c WHERE {where}", *params)
    total = count_row["total"]

    rows = await pool.fetch(
        f"SELECT c.* FROM concepts c WHERE {where} ORDER BY c.updated_at DESC LIMIT ${idx} OFFSET ${idx + 1}",
        *params, limit, offset,
    )

    items = []
    for r in rows:
        cid = str(r["id"])
        translations = [dict(t) for t in await pool.fetch(
            "SELECT * FROM translations WHERE concept_id = $1 AND status = 'approved' ORDER BY created_at DESC LIMIT 5", cid
        )]
        explanations = [dict(e) for e in await pool.fetch(
            "SELECT * FROM explanations WHERE concept_id = $1 AND status = 'approved' ORDER BY grade_level", cid
        )]

        best_translation = translations[0] if translations else None
        best_explanation = next((e for e in explanations if e["grade_level"] == 8), explanations[0] if explanations else None)

        item = {
            "concept_id": cid,
            "name_en": r["name_en"],
            "definition_en": r.get("definition_en", ""),
            "domain": r["domain"],
            "grade_levels": list(r["grade_levels"]),
            "sepedi_term": best_translation["sepedi_term"] if best_translation else None,
            "confidence_score": best_translation["confidence_score"] if best_translation else None,
            "explanation_sep": best_explanation["content_sep"] if best_explanation else None,
            "explanation_grade": best_explanation["grade_level"] if best_explanation else None,
            "updated_at": r["updated_at"].isoformat() if r["updated_at"] else None,
        }

        if format == "jsonld":
            item["@context"] = "https://schema.org"
            item["@type"] = "DefinedTerm"
            item["name"] = item["sepedi_term"] or item["name_en"]
            item["alternateName"] = item["name_en"]

        items.append(item)

    return {
        "concepts": items,
        "total": total,
        "page": page,
        "limit": limit,
        "has_next": offset + limit < total,
    }


@router.get("/concepts/{concept_id}")
async def moodle_concept_detail(
    concept_id: str,
    format: str = Query("plain", description="plain or jsonld"),
    _key: str = Depends(_require_moodle_key),
):
    pool = await _get_pool()
    row = await pool.fetchrow("SELECT * FROM concepts WHERE id = $1", concept_id)
    if not row:
        raise HTTPException(status_code=404, detail="Concept not found")
    if row["status"] != "published":
        raise HTTPException(status_code=404, detail="Concept not published")

    translations = [dict(t) for t in await pool.fetch(
        "SELECT * FROM translations WHERE concept_id = $1 AND status = 'approved' ORDER BY created_at DESC", concept_id
    )]
    explanations = [dict(e) for e in await pool.fetch(
        "SELECT * FROM explanations WHERE concept_id = $1 AND status = 'approved' ORDER BY grade_level", concept_id
    )]

    best_translation = translations[0] if translations else None
    best_explanation = next((e for e in explanations if e["grade_level"] == 8), explanations[0] if explanations else None)

    result = {
        "concept_id": concept_id,
        "name_en": row["name_en"],
        "definition_en": row.get("definition_en", ""),
        "domain": row["domain"],
        "grade_levels": list(row["grade_levels"]),
        "translations": [{"sepedi_term": t["sepedi_term"], "confidence_score": t["confidence_score"], "status": t["status"]} for t in translations],
        "explanations": [{"grade_level": e["grade_level"], "content_sep": e["content_sep"], "examples_sep": e["examples_sep"]} for e in explanations],
        "sepedi_term": best_translation["sepedi_term"] if best_translation else None,
        "explanation_sep": best_explanation["content_sep"] if best_explanation else None,
        "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
    }

    if format == "jsonld":
        result = _jsonld_concept(dict(row), translations, explanations)

    return result


@router.get("/quizzes")
async def moodle_quiz_bank(
    request: Request,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    domain: str | None = None,
    grade: int | None = None,
    format: str = Query("json", description="json or moodle_xml"),
    _key: str = Depends(_require_moodle_key),
):
    pool = await _get_pool()
    conditions = ["q.concept_id IN (SELECT id FROM concepts WHERE status = 'published')"]
    params: list = []
    idx = 1

    if domain:
        conditions.append(f"q.concept_id IN (SELECT id FROM concepts WHERE domain = ${idx})")
        params.append(domain)
        idx += 1

    if grade is not None:
        conditions.append(f"q.grade_level = ${idx}")
        params.append(grade)
        idx += 1

    where = " AND ".join(conditions)
    offset = (page - 1) * limit

    count_row = await pool.fetchrow(f"SELECT count(*) as total FROM quiz_questions q WHERE {where}", *params)
    total = count_row["total"]

    rows = await pool.fetch(
        f"""SELECT q.*, c.name_en, c.domain
            FROM quiz_questions q
            JOIN concepts c ON c.id = q.concept_id
            WHERE {where}
            ORDER BY q.created_at DESC
            LIMIT ${idx} OFFSET ${idx + 1}""",
        *params, limit, offset,
    )

    questions = []
    for r in rows:
        questions.append({
            "id": str(r["id"]),
            "concept_id": str(r["concept_id"]),
            "concept_name": r["name_en"],
            "domain": r["domain"],
            "grade_level": r["grade_level"],
            "question_type": r["question_type"],
            "question_sep": r["question_sep"],
            "options": r["options"],
            "correct_answer": r["correct_answer"],
        })

    if format == "moodle_xml":
        xml_content = _moodle_quiz_xml(questions, category="Polelo STEM")
        return Response(content=xml_content, media_type="application/xml", headers={
            "Content-Disposition": "attachment; filename=polelo_quiz_bank.xml",
        })

    return {
        "questions": questions,
        "total": total,
        "page": page,
        "limit": limit,
        "has_next": offset + limit < total,
    }


@router.get("/quizzes/{concept_id}")
async def moodle_concept_quizzes(
    concept_id: str,
    grade_level: int = Query(8, ge=0, le=12),
    format: str = Query("json", description="json or moodle_xml"),
    _key: str = Depends(_require_moodle_key),
):
    pool = await _get_pool()
    concept = await pool.fetchrow("SELECT * FROM concepts WHERE id = $1 AND status = 'published'", concept_id)
    if not concept:
        raise HTTPException(status_code=404, detail="Concept not found or not published")

    rows = await pool.fetch(
        "SELECT * FROM quiz_questions WHERE concept_id = $1 AND grade_level = $2 ORDER BY created_at",
        concept_id, grade_level,
    )

    questions = [{
        "id": str(r["id"]),
        "question_type": r["question_type"],
        "question_sep": r["question_sep"],
        "options": r["options"],
        "correct_answer": r["correct_answer"],
    } for r in rows]

    if format == "moodle_xml":
        xml_content = _moodle_quiz_xml(questions, category=f"Polelo / {concept['name_en']}")
        return Response(content=xml_content, media_type="application/xml", headers={
            "Content-Disposition": f"attachment; filename=polelo_quiz_{concept_id}.xml",
        })

    return {
        "concept_id": concept_id,
        "concept_name": concept["name_en"],
        "grade_level": grade_level,
        "questions": questions,
        "total": len(questions),
    }


@router.get("/courses/{course_id}/sync")
async def moodle_course_sync(
    course_id: str,
    since: str | None = Query(None, description="ISO timestamp — only return changes after this time"),
    _key: str = Depends(_require_moodle_key),
):
    """Pull all published concepts and quizzes for a Moodle course.
    course_id is the Moodle course ID — we map it to grade_levels via convention.
    """
    pool = await _get_pool()

    # Fetch all published concepts
    conditions = ["c.status = 'published'"]
    params: list = []
    idx = 1
    if since:
        conditions.append(f"c.updated_at > ${idx}")
        params.append(since)
        idx += 1

    where = " AND ".join(conditions)
    concept_rows = await pool.fetch(
        f"SELECT c.* FROM concepts c WHERE {where} ORDER BY c.updated_at DESC", *params
    )

    concepts = []
    total_questions = 0
    for r in concept_rows:
        cid = str(r["id"])
        translations = [dict(t) for t in await pool.fetch(
            "SELECT * FROM translations WHERE concept_id = $1 AND status = 'approved' ORDER BY created_at DESC LIMIT 3", cid
        )]
        explanations = [dict(e) for e in await pool.fetch(
            "SELECT * FROM explanations WHERE concept_id = $1 AND status = 'approved' ORDER BY grade_level", cid
        )]
        quiz_rows = await pool.fetch(
            "SELECT * FROM quiz_questions WHERE concept_id = $1 ORDER BY grade_level", cid
        )

        best_translation = translations[0] if translations else None
        best_explanation = next((e for e in explanations if e["grade_level"] == 8), explanations[0] if explanations else None)

        concepts.append({
            "concept_id": cid,
            "name_en": r["name_en"],
            "definition_en": r.get("definition_en", ""),
            "domain": r["domain"],
            "grade_levels": list(r["grade_levels"]),
            "sepedi_term": best_translation["sepedi_term"] if best_translation else None,
            "explanation_sep": best_explanation["content_sep"] if best_explanation else None,
            "quizzes_count": len(quiz_rows),
            "updated_at": r["updated_at"].isoformat() if r["updated_at"] else None,
        })
        total_questions += len(quiz_rows)

    return {
        "course_id": course_id,
        "concepts": concepts,
        "total_concepts": len(concepts),
        "total_quizzes": total_questions,
        "synced_at": datetime.utcnow().isoformat(),
    }


@router.post("/courses/{course_id}/sync")
async def moodle_course_push(
    course_id: str,
    body: dict,
    _key: str = Depends(_require_moodle_key),
):
    """Moodle pushes completion/mastery data back to Polelo.
    Body: { concept_id: str, user_moodle_id: int, score_pct: float, completed_at: str }
    """
    pool = await _get_pool()
    concept_id = body.get("concept_id")
    user_moodle_id = body.get("user_moodle_id")
    score_pct = body.get("score_pct", 0.0)
    completed_at = body.get("completed_at")

    if not concept_id or user_moodle_id is None:
        raise HTTPException(status_code=422, detail="concept_id and user_moodle_id are required")

    # Store in mqtt_jobs as a sync record (reuse existing table)
    await pool.fetchrow(
        """INSERT INTO mqtt_jobs (topic, payload, status)
           VALUES ($1, $2, 'completed')
           RETURNING id""",
        f"moodle.sync.{course_id}",
        {
            "concept_id": concept_id,
            "user_moodle_id": user_moodle_id,
            "score_pct": score_pct,
            "completed_at": completed_at,
            "course_id": course_id,
        },
    )

    return {"status": "received", "course_id": course_id, "concept_id": concept_id}
