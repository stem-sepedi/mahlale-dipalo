# IMPLEMENTATION_PLAN.md

STEM Sepedi Translation Layer - Milestone Implementation Plan

Version: 0.1

---

## Roadmaps

Scope expansion is tracked separately:
- `ROADMAP_GRADES_R12.md` — per-grade configuration (Grade R → 12, CAPS-aligned).
- `ROADMAP_UNIVERSITY.md` — university tier (grade 99) and TVET (grade 100).

Both are planning documents; schedule the milestones here once scoped.

---

## Overview

This plan decomposes development into milestone-based phases. Each milestone is a coherent deliverable submitted as a Gitea PR for human review before merging to main. Per AGENTS.md rules: every feature lives on its own branch, no broken code, atomic commits, tests required.

---

## Milestone 1 — Foundation Infrastructure (Phase 1)

**Goal:** Running Docker Compose stack with authenticated API, concept CRUD, translation from Ollama, search, and login page.

| # | Task | Scope | Acceptance Criterion |
|---|------|-------|---------------------|
| 1.1 | Repo scaffold & config files | `.editorconfig`, `pyproject.toml`, ruff/black config | Repository lints clean, no errors from any config tool |
| 1.2 | Docker Compose manifest | `docker-compose.yml` with 7 services: web-api, database, mqtt-broker, ollama, minio, php-app, worker | `docker compose up` starts all; `docker compose ps` shows all running |
| 1.3 | TimescaleDB migrations | `db/migrations/001_initial_schema.sql`, seed admin user | Integration test creates tables, inserts seed user, validates constraints |
| 1.4 | FastAPI scaffold + routing | `src/api/main.py`, route modules matching SPEC.md API table | `/health` returns status "ok" with all deps as "connected" in healthy state |
| 1.5 | JWT auth system | Auth routes + middleware per SPEC.md AUTH section | POST /auth/login validates hash, rotates refresh tokens; middleware rejects missing/expired Bearer tokens |
| 1.6 | Concept CRUD endpoints | GET/POST/GET-by-id PATCH/DELETE per API_REFERENCE.md concept endpoint specs | E2E test: create → fetch → update → delete — each step verified via pytest httpx against running stack |
| 1.7 | Ollama integration service | Pydantic models + HTTP client for Ollama; prompt templates for translate/explain | Service returns ≥2 translation alternatives with confidence_score when called via test API endpoint |
| 1.8 | Translation engine wiring | POST /translate routes concept → Ollama worker queue | Worker publishes translation.request on MQTT; consumer stores results to DB; status transitions draft→pending_review on submit |
| 1.9 | Full-text search | GET /search with pg_trgm fuzzy matching, faceted structure per spec | Search for "Photosynthesis" returns concept row scored above threshold; pagination works as specified |
| 1.10 | PHP login page | Basic HTML/PHP UI calling POST /api/v1/auth/login on FastAPI | Login flow accepts seed admin credentials, redirects to search page on success, shows error on wrong password |

**PR branch:** `milestone/1-foundation`
**Estimated effort:** ~20–25 developer-days

---

## Milestone 2 — AI-Assisted Features (Phase 2)

| # | Task | Scope | Acceptance Criterion |
|---|------|-------|---------------------|
| 2.1 | Explanation engine | Prompt templates per grade level; content_sep stored in explanations table | POST /explain on every concept at all 6 levels produces distinct output verified by comparison test (vocab complexity metric) |
| 2.2 | Example generator | Cultural context examples as Sepedi examples_sep entries in explanation model | Each explanation includes ≥1 example relevant to target grade level experience |
| 2.3 | Grade-level enum | Database schema extension for grade_level constraints per SPEC.md levels table | Querying by grade_level filters correctly; invalid levels rejected at schema layer |
| 2.4 | Image media support | Upload endpoint, MinIO storage, concept.media column reference | POST accepts image upload; stores to S3-compatible bucket; GET /media/{key} fetches it |
| 2.5 | Quiz generator | Auto-generate quiz_questions table rows per Ollama with types aligned to spec | Generated questions have all fields populated; auto-grade validates scores |
| 2.6 | Voice API stub | Route accepting audio, returning TTS placeholder endpoint for future integration | Endpoint exists, accepts multipart form, returns {status: "future-tts"} in Phase-2 scope |

**PR branch:** `milestone/2-ai-assisted`
**Can start after:** Milestone 1 merged (needs translation engine first)

---

## Milestone 3 — Human Review & Governance (Phase 3)

| # | Task | Scope | Acceptance Criterion |
|---|------|-------|---------------------|
| 3.1 | Review workflow engine | State machine: Draft→PendingReview→Approved→Published per SPEC.md review_agent + review section status transitions | All 4 transitions work; rejected items return to draft with comment field enforced; audit_log records every transition |
| 3.2 | Version control on concepts | Immutable version_snapshots + diff_to_prev via unified diff of serialized entity states | GET /concepts/{id}/versions returns history; revert endpoint restores previous state as new draft; S3 snapshot_key valid |
| 3.3 | Translation history | Versioned rows on translations table with per-concept_id+sepedi_term pair diff capability | User can view any historical translation state with unified_diff relative to its predecessor row |
| 3.4 | Community contributions UI | Public form for non-auth users to submit new concepts or translations | Non-approved submissions enter draft; translator/reviewer role fetches via GET with filter=pending_review; admin approves |
| 3.5 | Moderation tools | Admin-only bulk-approve / bulk-reject endpoints with audit trail | Bulk action requires confirmation POST /moderation/bulk{action + reason}; audit_log records each individual decision under admin user id |

**PR branch:** `milestone/3-governance`
**Can start after:** Milestone 1 merged (needs concepts + translations APIs)

---

## Milestone 4 — Storage & Reliability (Phase 4)

| # | Task | Scope | Acceptance Criterion |
|---|------|-------|---------------------|
| 4.1 | S3 archive worker | MQTT consumer for archive.store topic; writes concept states to MinIO bucket as immutable JSON per object_key = s3://polelo-snapshots/concept/{id}/v{number}.json | Successful archive produces row in version_snapshots table; re-fetching key returns identical payload (sha256 verified) |
| 4.2 | Snapshot admin endpoint | GET /snapshots listing, retrieving, downloading all snapshots | All entries have corresponding objects in storage; downloading any by ID produces valid JSON matching DB metadata; cannot modify/delete |
| 4.3 | Disaster recovery script | Bash/Python restoring full app from single S3 snapshot + pg_dump per --recovery-point argument arg | Post-recovery state exactly matches recovered snapshot; test deploys fresh stack, loads snapshot, asserts all rows present unmodified vs original hash file |
| 4.4 | Backup validation pipeline | Cron verifying backup integrity via sha256 comparison of db table rows to snapshots every hour | Every snapshot's sha256 matches corresponding PostgreSQL content for last {concept_id, version_number} pair; /health returns degraded if mismatch; alert webhook on failure |

**PR branch:** `milestone/4-storage-reliability`
**Can start after:** Milestone 3 (needs snapshots)

---

## Milestone 5 — Accessibility & Deployment (Phase 5)

| # | Task | Scope | Acceptance Criterion |
|---|------|-------|---------------------|
| 5.1 | Responsive mobile UI | PHP CSS + HTML supporting viewports from 320px to 1920px; touch-friendly navigation | Renders on Chrome DevTools device emulator covering iPhone SE through Pixel 7 sizes; no horizontal scroll at any width; WCAG 2.1 AA contrast via axe-core scan passes |
| 5.2 | PWA support | Service worker with fetch caching strategy for API responses and assets; manifest.json | Installable on Android Chrome as standalone app; works offline after initial cache population via network-first-strategy; update prompt when new manifest detected |
| 5.3 | Offline cache layer | IndexedDB-backed client-side cache storing recently-visited concept rows + translations for instant render sans server roundtrips | Cached data persists across browser reloads; stale entries auto-evict on LRU policy with configurable max_entries limit; user-facing "Clear Cache" button in Settings via mobile header icon-button at bottom-left corner position using inline SVG icon |
| 5.4 | RPi ARM64 deployment guide + container images | All service container images buildable for linux/arm64 with documented setup steps README.md section covering hardware prerequisites and docker compose deploy commands | `docker compose up` runs on actual Raspberry Pi 4 (4GB variant minimum specs) using only packages from Debian bookworm repos and native arm64 dockr hub images without any amd64-only dependencies present in the compose file; system resource usage remains under 80% of CPU/memory limits during normal search/browse operations |

**PR branch:** `milestone/5-access-deployment`
**Can start after:** Milestones 1, 2, 3 merged (UI consumes APIs)

---

## Milestones 6 + 7 — Curriculum & Domain Expansion (Data Seeding)

These run in parallel and can begin immediately after Milestone 1 scaffold exists since they are data-seeding tasks not code development.

### Milestone 6: Grade-level curriculum mapping

Populate seed concepts for all South African STEM curricula matching every grade level from TODO.md Phase 6: Grade R, Foundation Phase, Intermediate Phase, Senior Phase, FET (TVET), University STEM.

### Milestone 7: Domain expansion

Add translation entries covering all domains per TODO.md Phase 7: Physics, Chemistry, Biology, Mathematics, Engineering, Computer Science, Robotics, Astronomy, Agriculture, Environmental science — plus GeneralSTEM seeded earlier.

**PR branch:** `milestone/6-7-curriculum-domains`
**Can start:** immediately after Milestone 1

---

## Dependency Graph & Parallelization

```
M1 ──▶ M2 ──▶ M4
              │
         (parallel)
            /    \
           v      v
          M3     M5
           \     /
             v
          (merged to main)

M6 + M7 ◄─── can start after any single milestone completes, ideally early
```

| Milestone | Depends on | Can parallelize? |
|-----------|------------|------------------|
| M2 (AI features) | M1 — translation engine must exist first | No |
| M3 (Review) | M1 (concepts + translations APIs) | Yes, after M1 PR merged; works alongside M2 |
| M4 (Storage)   | M3 (needs versioned entities from review) | Can start early with basic snapshotting added incrementally |
| M5 (Mobile) | M1, M2, M3 | Yes, can begin as soon as API contracts (M1 + M2 partials) are available |
| M6+M7  (Data seeding) | None — requires only data model from M1 seed scripts | Fully parallel with any development milestone |

---

## Milestone Completion Criteria (All Milestones)

Before creating a Gitea PR, verify all of:
- All task rows in the milestone table checked off with corresponding commit SHAs listed under "Commits" section in PR description
- Integration + unit-test coverage ≥ 80% on modified code areas verified via coverage.py xml output
- No linting or type-checker warnings (ruff check passes clean; mypy reports zero errors)
- Database schema migrations have tested rollback paths in db/rollbacks/ alongside each forward migration file
- CHANGELOG.md updated with milestone section and link to PR
- Full-text search verified against dataset seeded for this phase's scope — search endpoint returns expected results at latency targets from SPEC.md performance section
- API_REFERENCE.md updated for any new endpoints or parameter changes introduced in the milestone

---

## Rollback per Milestone (AGENTS.md Rule: Every feature requires rollback instructions)

Each milestone PR must include a rollback script at `rollbacks/<milestone-number>/rollback.sh`:

```bash
#!/bin/bash
# rollbacks/M/N/rollback.sh — reverses M<N> changes safely
set -euo pipefail

docker compose down                   # stop running services
psql polelo_db -c "DROP SCHEMA IF EXISTS polelo CASCADE;"  # revert schema migration
docker compose up -d                 # restart services
```

All rollback scripts tested on staging branch before PR submission.

---

## Gitea PR Naming Convention (per milestone)

| Milestone | Branch name | PR title |
|-----------|-------------|----------|
| M1 | `milestone/1-foundation` | `feat: milestone 1 — foundation infrastructure` |
| M2 | `milestone/2-ai-assisted` | `feat: milestone 2 — AI-assisted explanation, quizzes, media` |
| M3 | `milestone/3-governance` | `feat: milestone 3 — human review workflow, version control, community governance` |
| M4 | `milestone/4-storage-reliability` | `feat: milestone 4 — immutability archive and disaster recovery` |
| M5 | `milestone/5-access-deployment` | `feat: milestone 5 — mobile UI, PWA, offline cache, Raspberry Pi deployment` |
| M6+M7 | `milestone/6-7-curriculum-domains` | `feat: milestones 6 & 7 — full curriculum + domain coverage expansion` |
