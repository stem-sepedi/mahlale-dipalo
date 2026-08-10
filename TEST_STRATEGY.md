# TEST_STRATEGY.md

STEM Sepedi Translation Layer - Testing Strategy

Version: 0.1

---

## Philosophy

Tests are a first-class deliverable. Every new feature requires tests and every bug fix must include a regression test. No merged code without passing tests — not in CI, not locally, not ever.

The project uses **pytest** for the Python backend, and separate browser/end-to-end test harnesses for the frontend.

---

## Test Categories (Pyramid)

### 1. Unit Tests (~70% of tests)

Fast, isolated, mocked-external-dependency tests targeting individual functions and classes. No network calls, no database connections, no Ollama invocations.

**Tools:** pytest, unittest.mock, hypothesis (property-based testing for edge cases)

```python
# Example: test_translation_engine.py
async def test_confidence_score_within_range():
    result = await translate_term("Gravity", "Physics")
    assert 0.0 <= result["confidence_score"] <= 1.0
    assert isinstance(result["alternative_forms"], list)
    assert len(result["translations"]) >= 2

@pytest.mark.parametrize("term,expected_min_confidence", [
    ("Photosynthesis", 0.5),
    ("mitosis", 0.6),
])
async def test_known_terms_higher_confidence(term, expected_min_confidence):
    result = await translate_term(term)
    assert result["confidence_score"] >= expected_min_confidence
```

**Coverage target: ≥80% for all production code.**

### 2. Integration Tests (~25% of tests)

Tests that exercise the interaction between components: API route → database → cache, or worker → oMQTT broker → consumer. Uses test containers to spin up real TimescaleDB and MQTT broker during CI runs.

**Tools:** pytest-docker, httpx (async), PostgreSQL testcontainers, paho-mqtt

```python
# Example: test_concept_crud.py
@pytest.mark.asyncio
async def test_create_and_retrieve_concept(test_app):
    resp = await test_app.post("/api/v1/concepts", json={...})
    assert resp.status_code == 201
    concept_id = resp.json()["id"]
    get_resp = await test_app.get(f"/api/v1/concepts/{concept_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["name_en"] == "Photosynthesis"
```

### 3. End-to-End Tests (~5% of tests)

Full-system flows tested against a live stack deployed in ephemeral CI environments. These are the most fragile but highest-value. Run only on main branch merges and before every tagged release.

**Tools:** Playwright (browser automation), Docker Compose (CI environment spin-up)

```python
# Example: test_full_translation_workflow.py
async def test_complete_review_pipeline(playwright):
    # 1. Login as teacher
    # 2. Create a new concept
    # 3. Submit for translation (AI generates drafts)
    # 4. Reviewer logs in and approves
    # 5. Admin publishes
    # 6. Learner searches and verifies the published result
```

---

## Test Directory Structure

```
tests/
├── conftest.py           # Shared fixtures (test db, test app client, mock ollama server)
├── unit/
│   ├── test_translation.py
│   ├── test_authentication.py
│   ├── test_permissions.py
│   └── test_search.py
├── integration/
│   ├── test_concept_crud.py
│   ├── test_translation_flow.py
│   ├── test_auth_jwt.py
│   └── test_queue_consumption.py
├── e2e/
│   ├── conftest.py       # Playwright fixtures, compose service config
│   ├── test_login_flow.py
│   ├── test_publish_pipeline.py
│   └── test_full_translation_workflow.py
├── fixtures/
│   ├── sample_concepts.json      # Seed data for integration tests
│   └── translated_terms.json     # Golden-set translations for comparison assertions
└── conftest.py               # pytest hooks: setup, teardown, markers
```

---

## Test Fixtures and Seed Data

Golden set of approved Sepedi translations (used in assertion-based tests):

```json
[
  { "en": "Photosynthesis", "sep_golds": ["Go belaela ga dimela", "Go dirisiša mašwa a letsatsi go gola"] },
  { "en": "Mitosis", "sep_golds": ["Pogolo ya sele", "Go arogana ga sele"] }
]
```

Tests can assert that translations align with human-approved ground truth within a reasonable string-similarity threshold using `jaccard` or `Levenshtein` distance.

---

## CI Pipeline

**GitHub Actions workflow triggers:** PR, push to main, and scheduled daily at midnight for long-running E2E jobs.

```yaml
steps:
  - Checkout code
  - Install Python dependencies (Poetry install)
  - Start services via docker compose (-f docker-compose.test.yml — includes test database & mock Ollama service)
  - Wait for TimescaleDB ready check (pg_isready with retries)
  - Run unit tests: pytest -q tests/unit/
  - Run integration tests: pytest -q tests/integration/ --timeout=60
  - Run linter: ruff check . && mypy src/ && black --check .
  - (main only, nightly) Deploy full stack in e2e environment → run Playwright suite → collect artifact screenshots on failure
```

### Test markers

| Marker | Use case | Runs in CI? |
|--------|---------|-------------|
| @pytest.mark.unit | Fast function/class test | Always |
| @pytest.mark.integration | Needs real database or MQTT broker | On PR to main; skipped on feature branches |
| @pytest.mark.e2e | Full deploy + browser | Nightly and tagged releases only |
| @pytest.mark.slow (>5s per case) | Ollama generation simulation | Feature branch testing — CI skips if --run-slow flag not passed |

Run subset:
```bash
pytest -m "unit and not slow"        # Fast loop
pytest -m "integration"               # CI on feature branches
pytest                                # All markers (main branch)
```

---

## Mocking Strategy

| Dependency | Mock approach | Rationale |
|-----------|---------------|-----------|
| Ollama LLM | `unittest.mock.patch("httpx.AsyncClient.request")` — return canned responses based on input term | Ollama is the heaviest external dependency; slow, non-deterministic. Use golden JSON set for deterministic assertions. |
| MQTT Broker | `paho-mqtt` test client publishes to in-memory broker or mock listener | Real broker needed integration-level testing but unit tests use published-message assertions. |
| S3 Object Storage | moto library — local MinIO-compatible mock that supports bucket/object CRUD | No real AWS or object storage required during CI. |
| Database queries | real PostgreSQL container (testcontainers) | ORM-level correctness is critical; mocking the DB would hide integration bugs. |

---

## Coverage Requirements

| Area | Minimum coverage | Tool |
|------|-----------------|------|
| `src/api/` routes layer | ≥90% | coverage.py with xml output for codecov/github |
| `src/services/` (Ollama integration, translate logic, etc) | ≥85% | same |
| `src/models/` | ≥70% (schemas auto-covered by ORM) | same |
| `tests/unit/` | must cover all business logic paths | same |
| **Overall project** | **≥80%** | same |

Missing coverage blocks merge if the missing area is new code created in that branch.

---

## Test Data Guidelines

1. No real user passwords (use bcrypt-hashed stubs: `$2b$12$...`).
2. No production credentials of any kind.
3. All UUID IDs are generated in `conftest.py` via `uuid4()` fixtures, never hardcoded across test files to avoid shared state coupling.
4. Test concepts use domain terms from all 10 domains to ensure broad coverage across the domain enum constraint.

---

## Regression Testing for Translations

Because translations are semi-deterministic (Ollama can return different phrasing on repeated calls), this test category uses **assertion via metrics** not exact string match:

```python
async def test_translation_preserves_scientific_meaning():
    original_en = "Photosynthesis"
    result = await translate_term(original_en)
    # Verify scientific key-words appear in Sepedi output
    sep_texts = [t["sepedi_term"] for t in result["translations"]]
    has_light_reference = any("letsatsi" or "mašwa" in sep.lower() for sep in sep_texts)
    assert has_light_reference, f"Translation should reference light; got: {sep_texts}"
```

Golden-set comparison (exact string match for known good translations) is used separately and listed as golden translations.

---

## Rollback Testing Policy

Per AGENTS.md rule "Every feature requires rollback instructions", every new API endpoint or database migration includes at least one test that verifies rollback:

1. Run the migration forward
2. Verify entity exists
3. Run rollback migration
4. Verify entity is gone / table is back to original state

---

## Performance Tests (Optional, Phase 3+)

Post-MVP benchmarks run against staged data sets using `pytest-benchmark`:

```bash
pytest --benchmark-only tests/unit/test_search_performance.py
```

**Targets:**
- Search query for 100k concepts: p95 < 2 seconds
- Translation generation (Ollama): p50 < 3 seconds
- Concurrency test: 100 simultaneous requests via `locust` should hold under HTTP 200 for ≥99% of requests

These run on nightly CI with a seeded staging database.
