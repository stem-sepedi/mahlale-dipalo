"""Embed routes — iframe targets and public widget endpoints.

/embed/translate and /embed/quiz are standalone pages designed to be placed in an
<iframe> on a Moodle course or any external site. The widget scripts are served
from /widgets and talk to the public /embed/api/* endpoints below.
"""

import os

import asyncpg
from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse

router = APIRouter(prefix="/embed", tags=["embed"])


async def _get_pool() -> asyncpg.Pool:
    dsn = os.getenv("DATABASE_URL", "postgresql://localhost/polelo")
    return await asyncpg.create_pool(dsn, min_size=1, max_size=5)


_ALLOWED_THEMES = {"light", "dark"}
_ALLOWED_LANGS = {"sepedi", "english"}


def _embed_form(
    title: str,
    body: str,
    scripts: list[str],
    theme: str = "light",
    grade: int = 8,
    lang: str = "sepedi",
) -> HTMLResponse:
    """Render an embeddable HTML page with theme variables and the widget scripts."""
    accent = "#2563eb" if theme == "light" else "#38bdf8"
    bg = "#ffffff" if theme == "light" else "#1e293b"
    fg = "#0f172a" if theme == "light" else "#e2e8f0"
    script_tags = "\n".join(
        f'<script src="{os.getenv("EMBED_BASE_URL", "")}{s}" defer></script>' for s in scripts
    )
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} — Polelo</title>
<style>
  body {{ margin:0; font-family:system-ui, -apple-system, sans-serif; background:{bg}; color:{fg}; }}
  body {{
    background: {bg};
    color: {fg};
    -webkit-font-smoothing: antialiased;
  }}
  .wrap {{ padding: 1rem; }}
  a {{ color: {accent}; }}
</style>
</head>
<body>
<script>
  window.POLELO_BASE_URL = {os.getenv("EMBED_BASE_URL", "")!r};
  window.POLELO_THEME = {theme!r};
  window.POLELO_GRADE = {grade};
  window.POLELO_LANG = {lang!r};
</script>
<div class="wrap">
{body}
</div>
{script_tags}
</body>
</html>"""
    return HTMLResponse(html)


# ------------------------------------------------------------------
# Embed pages (iframe targets)
# ------------------------------------------------------------------


@router.get("/translate", response_class=HTMLResponse)
async def embed_translate(
    request: Request,
    concept_id: str = Query("", description="Concept UUID to display"),
    grade: int = Query(8, ge=0, le=12),
    theme: str = Query("light"),
    lang: str = Query("sepedi"),
):
    html = f"""
<div id="polelo-translate" data-concept-id="{concept_id}" data-grade="{grade}"
     data-theme="{theme}" data-lang="{lang}"></div>
<noscript>Enable JavaScript to see the Polelo translation widget.</noscript>
"""
    resp = _embed_form("Translation", html, ["/widgets/translation-widget.js"], theme, grade, lang)
    return _with_embed_headers(resp, theme)


@router.get("/quiz", response_class=HTMLResponse)
async def embed_quiz(
    request: Request,
    concept_id: str = Query("", description="Concept UUID to quiz on"),
    grade: int = Query(8, ge=0, le=12),
    count: int = Query(5, ge=1, le=20),
    theme: str = Query("light"),
):
    html = f"""
<div id="polelo-quiz" data-concept-id="{concept_id}" data-grade="{grade}"
     data-count="{count}" data-theme="{theme}"></div>
<noscript>Enable JavaScript to see the Polelo quiz widget.</noscript>
"""
    resp = _embed_form("Quiz", html, ["/widgets/quiz-widget.js"], theme, grade)
    return _with_embed_headers(resp, theme)


def _with_embed_headers(resp, theme):
    # CSP: default-src self, inline styles/scripts allowed, frame-ancestors controls where the
    # embedded page itself can be framed (the hosting Moodle site).
    ancestors = _frame_ancestors()
    resp.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
        "connect-src 'self'; frame-ancestors " + ancestors + ";"
    )
    if ancestors != "*":
        resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["X-Content-Type-Options"] = "nosniff"
    return resp


def _frame_ancestors() -> str:
    origins = os.getenv("EMBED_ALLOWED_ORIGINS", "*").split(",")
    if any(o.strip() == "*" for o in origins):
        return "*"
    return " ".join(o.strip() for o in origins if o.strip())


# ------------------------------------------------------------------
# Public widget API — no API key required (rate limited as learner)
# ------------------------------------------------------------------


@router.get("/api/translate/{concept_id}")
async def embed_api_translate(concept_id: str, grade: int = Query(8, ge=0, le=12)):
    pool = await _get_pool()
    row = await pool.fetchrow(
        "SELECT * FROM concepts WHERE id = $1 AND status = 'published'", concept_id
    )
    if not row:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Concept not found or not published")

    translation = await pool.fetchrow(
        """SELECT sepedi_term FROM translations
           WHERE concept_id = $1 AND status = 'approved'
           ORDER BY created_at DESC LIMIT 1""",
        concept_id,
    )
    explanation = await pool.fetchrow(
        """SELECT content_sep AS explanation_sep FROM explanations
           WHERE concept_id = $1 AND status = 'approved' AND grade_level = $2
           LIMIT 1""",
        concept_id, grade,
    )
    explanation_en = await pool.fetchrow(
        """SELECT definition_en FROM concepts WHERE id = $1""", concept_id
    )
    return {
        "concept_id": concept_id,
        "name_en": row["name_en"],
        "definition_en": row["definition_en"],
        "domain": row["domain"],
        "grade_levels": list(row["grade_levels"]),
        "sepedi_term": translation["sepedi_term"] if translation else None,
        "explanation_sep": explanation["explanation_sep"] if explanation else None,
        "explanation_en": explanation_en["definition_en"] if explanation_en else None,
    }


@router.get("/api/quiz/{concept_id}")
async def embed_api_quiz(
    concept_id: str,
    grade_level: int = Query(8, ge=0, le=12),
    count: int = Query(5, ge=1, le=20),
):
    pool = await _get_pool()
    row = await pool.fetchrow(
        "SELECT name_en FROM concepts WHERE id = $1 AND status = 'published'", concept_id
    )
    if not row:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Concept not found or not published")

    questions = await pool.fetch(
        """SELECT id, question_type, question_sep, options, correct_answer
           FROM quiz_questions
           WHERE concept_id = $1 AND grade_level = $2
           ORDER BY created_at LIMIT $3""",
        concept_id, grade_level, count,
    )
    items = [{
        "id": str(q["id"]),
        "question_type": q["question_type"],
        "question_sep": q["question_sep"],
        "options": q["options"],
        "correct_answer": q["correct_answer"],
    } for q in questions]

    return {
        "concept_id": concept_id,
        "concept_name": row["name_en"],
        "grade_level": grade_level,
        "questions": items,
        "total": len(items),
    }
