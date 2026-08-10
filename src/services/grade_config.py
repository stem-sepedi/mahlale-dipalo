"""Grade catalog provider — R1 per-grade/phase configuration.

Loads the `grade_catalog` table once and caches it in-memory so per-request lookups
(`get_grade_config`) avoid a DB round-trip. Supports per-instance overrides via the
`GRADE_CONFIG_OVERRIDES` JSON env var, merged on top of the seeded catalog.
"""

import json
import logging
import os

logger = logging.getLogger(__name__)

# Accepted grades: 0 (Grade R) … 12 plus 99 (University tier).
VALID_GRADES = frozenset(range(0, 13)) | {99}

_catalog_cache: dict[int, dict] = {}
_catalog_loaded = False
_overrides_cache: dict | None = None


def validate_grade(grade: int) -> int:
    """Validate a grade number (0–12 or 99). Returns it on success, else raises ValueError."""
    grade = int(grade)
    if grade not in VALID_GRADES:
        raise ValueError(f"Invalid grade '{grade}': must be 0–12 or 99")
    return grade


def validate_grade_levels(grades: list[int]) -> list[int]:
    """Validate every entry in a grade list; raises on the first invalid value."""
    return [validate_grade(g) for g in grades]


def _load_overrides() -> dict:
    global _overrides_cache
    if _overrides_cache is None:
        raw = os.getenv("GRADE_CONFIG_OVERRIDES", "").strip()
        try:
            _overrides_cache = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            logger.warning("GRADE_CONFIG_OVERRIDES is not valid JSON; ignoring")
            _overrides_cache = {}
    return _overrides_cache


def _overrides_for(grade: int) -> dict:
    raw = _load_overrides()
    return raw.get(str(grade)) or {}


def _dsn() -> str:
    return os.getenv("DATABASE_URL", "postgresql://localhost/polelo")


async def load_catalog(pool=None) -> dict[int, dict]:
    """Load the grade catalog from the database into the cache (once)."""
    global _catalog_cache, _catalog_loaded
    if _catalog_loaded:
        return _catalog_cache

    own_pool = pool is None
    if own_pool:
        import asyncpg
        pool = await asyncpg.create_pool(_dsn(), min_size=1, max_size=5)

    try:
        rows = await pool.fetch("SELECT * FROM grade_catalog ORDER BY grade")
        for r in rows:
            _catalog_cache[int(r["grade"])] = {
                "grade": int(r["grade"]),
                "phase": r["phase"],
                "band": r["band"],
                "name_en": r["name_en"],
                "name_sep": r["name_sep"],
                "age_min": int(r["age_min"]),
                "age_max": int(r["age_max"]),
                "vocab_level": int(r["vocab_level"]),
                "curriculum_ref": r["curriculum_ref"],
            }
        _catalog_loaded = True
        logger.info("Loaded %d grades into catalog cache", len(_catalog_cache))
    finally:
        if own_pool:
            await pool.close()

    return _catalog_cache


async def list_grades(pool=None) -> list[dict]:
    """Return every catalog entry, sorted by grade, with overrides merged."""
    catalog = await load_catalog(pool)
    return [
        {**catalog[g], **_overrides_for(g)}
        for g in sorted(catalog)
    ]


async def get_grade_config(grade: int, pool=None) -> dict:
    """Return config for a single grade without a DB round-trip after first load."""
    grade = validate_grade(grade)
    catalog = await load_catalog(pool)
    if grade not in catalog:
        raise KeyError(f"Grade {grade} not present in the catalog")
    return {**catalog[grade], **_overrides_for(grade)}


def reset_cache() -> None:
    """Clear the cached catalog (used by tests)."""
    global _catalog_cache, _catalog_loaded, _overrides_cache
    _catalog_cache = {}
    _catalog_loaded = False
    _overrides_cache = None
