"""Tests for R1 grade catalog — validator, config provider, overrides.

The catalog is exercised with a fake async pool (no live PostgreSQL required);
grade validation is pure logic.
"""

import pytest

from src.services import grade_config
from src.services.grade_config import (
    get_grade_config,
    list_grades,
    validate_grade,
    validate_grade_levels,
)


class FakePool:
    """Minimal asyncpg.Pool stand-in returning fixed rows for grade_catalog."""

    def __init__(self, rows: list[dict]):
        self._rows = rows
        self.fetch_calls = 0
        self.closed = False

    async def fetch(self, query, *args):
        self.fetch_calls += 1
        return self._rows

    async def close(self):
        self.closed = True


def _seed_rows() -> list[dict]:
    return [
        {"grade": 8, "phase": "senior", "band": "senior", "name_en": "Grade 8",
         "name_sep": "Mphato wa 8", "age_min": 13, "age_max": 14, "vocab_level": 4,
         "curriculum_ref": "CAPS Natural Sciences / Mathematics"},
        {"grade": 0, "phase": "foundation", "band": "foundation-r", "name_en": "Grade R",
         "name_sep": "Mphato wa R", "age_min": 5, "age_max": 6, "vocab_level": 1,
         "curriculum_ref": "CAPS Life Skills – Beginning Knowledge (play-based)"},
        {"grade": 12, "phase": "fet", "band": "fet", "name_en": "Grade 12",
         "name_sep": "Mphato wa 12", "age_min": 17, "age_max": 18, "vocab_level": 6,
         "curriculum_ref": "CAPS Physical Sciences / Mathematics / Life Sciences / IT"},
        {"grade": 99, "phase": "university", "band": "university", "name_en": "University",
         "name_sep": "Mphato wa yunibesithi", "age_min": 18, "age_max": 99, "vocab_level": 6,
         "curriculum_ref": "HEQF university tier"},
    ]


@pytest.fixture(autouse=True)
def _reset_cache():
    grade_config.reset_cache()
    yield
    grade_config.reset_cache()


@pytest.fixture
def anyio_backend():
    return "asyncio"


def test_validate_grade_accepts_bounds():
    for g in range(0, 13):
        assert validate_grade(g) == g
    assert validate_grade(99) == 99


@pytest.mark.parametrize("bad", [-1, 13, 14, 100])
def test_validate_grade_rejects_out_of_bounds(bad):
    with pytest.raises(ValueError):
        validate_grade(bad)


def test_validate_grade_levels():
    assert validate_grade_levels([0, 8, 99]) == [0, 8, 99]
    with pytest.raises(ValueError):
        validate_grade_levels([8, 13])


@pytest.mark.asyncio
async def test_get_grade_config_grade8():
    config = await get_grade_config(8, pool=FakePool(_seed_rows()))
    assert config["band"] == "senior"
    assert config["vocab_level"] == 4
    assert config["phase"] == "senior"
    assert "CAPS" in config["curriculum_ref"]


@pytest.mark.asyncio
async def test_catalog_cached_no_second_query():
    pool = FakePool(_seed_rows())
    await get_grade_config(8, pool=pool)
    await get_grade_config(0, pool=pool)
    await get_grade_config(12, pool=pool)
    # All three lookups share the single initial load.
    assert pool.fetch_calls == 1


@pytest.mark.asyncio
async def test_list_grades_sorted(monkeypatch):
    rows = await list_grades(pool=FakePool(_seed_rows()))
    grades = [r["grade"] for r in rows]
    assert grades == [0, 8, 12, 99]


@pytest.mark.asyncio
async def test_overrides_merge(monkeypatch):
    monkeypatch.setenv("GRADE_CONFIG_OVERRIDES", '{"8": {"vocab_level": 5}}')
    grade_config.reset_cache()
    config = await get_grade_config(8, pool=FakePool(_seed_rows()))
    assert config["vocab_level"] == 5
    # Non-overridden grade unaffected
    config12 = await get_grade_config(12, pool=FakePool(_seed_rows()))
    assert config12["vocab_level"] == 6


@pytest.mark.asyncio
async def test_overrides_invalid_json_ignored(monkeypatch):
    monkeypatch.setenv("GRADE_CONFIG_OVERRIDES", "not-json{")
    grade_config.reset_cache()
    config = await get_grade_config(8, pool=FakePool(_seed_rows()))
    assert config["vocab_level"] == 4


def test_reset_cache_clears():
    grade_config._catalog_loaded = True
    grade_config._catalog_cache = {8: {"grade": 8}}
    grade_config.reset_cache()
    assert not grade_config._catalog_loaded
    assert grade_config._catalog_cache == {}
