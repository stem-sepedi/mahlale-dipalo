# TODO.md

> **All milestones complete.** 46 API endpoints, 9 service modules, full test suite, Docker deployment.
> Last updated: Milestone 10 — question triage to LLM via Forgejo/Gitea issues shipped.

## Roadmaps (planning documents, not yet scheduled for implementation)

- [ ] **Grade R–12 configuration** — see `ROADMAP_GRADES_R12.md`
  - [x] **R1 Grade catalog & per-grade configuration** — `grade_catalog` seeded R–12 + 99, central validator (0–12, 99), `GET /grades`, `GRADE_CONFIG_OVERRIDES` (migration 004)
  - [ ] R2 Curriculum-aligned per-grade prompting (vocab levels 1–6, phase registers)
  - [ ] R3 CAPS content coverage per grade (import, MQTT bulk, coverage dashboard)
  - [ ] R4 Per-grade UX + operator/admin configuration, widget & Moodle grade mapping
  - [ ] R5 Quiz & assessment alignment (CAPS verbs, difficulty ladder, XML grade binding)
  - [ ] R6 Per-phase rollout & quality (complexity benchmark, pilot packs, PWA grade cache)
- [ ] **University tier (grade 99, TVET 100)** — see `ROADMAP_UNIVERSITY.md`
  - [ ] U1 University tier foundation (uni_tier, extended domains, tier validator/config API)
  - [ ] U2 Academic Sepedi register (academic prompts, glossary authority feed, citation, curation)
  - [ ] U3 Subject coverage expansion (engineering, stats, biochemistry; per-subject prompt packs)
  - [ ] U4 Lecture/tutorial/assessment assets (worked examples, Bloom-ladder question sets, exam export)
  - [ ] U5 University LMS integration (tier-aware Moodle plugin, LTI Advantage depth, university sync)
  - [ ] U6 Academic governance (academic reviewer role, glossary contributions, provenance)
  - [ ] U7 University pilot & foundation launch (one subject end-to-end at uni-foundation)

## Milestone 10 — Question Triage to LLM via Forgejo/Gitea Issues ✓

Questions asked by students are triaged through a Forgejo/Gitea issue pipeline before and after
the LLM engine answers them. Labels track lifecycle; teachers/parents verify.

### M10.1 Ingest — new question → issue ✓

- [x] `src/api/routes/questions.py` — `POST /questions` accepts a student question (text, grade, subject, student ref)
- [x] Forgejo client `src/services/forgejo_client.py` — create issue in configured project/repo on submit
- [x] New issue created with label `LLM_BACKLOG` (all NEW questions awaiting an LLM answer)
- [x] Issue body includes original question text, grade, subject, student/anonymous ref, timestamps

### M10.2 Triage — before calling the LLM ✓

- [x] Lookup existing questions (in Forgejo, by search/issues API) before invoking the engine
- [x] If **already answered** → reuse existing answer; no new LLM call
- [x] If **similar** question already exists → add label `LLM_SIMILAR` to the new issue as well
- [x] Triage result recorded on the issue (matching issue ref / similarity notes)

### M10.3 Dispatch — hand the job to the LLM ✓

- [x] On dispatch, remove `LLM_BACKLOG` label and add `LLM_WIP` label (replace per spec)
- [x] `POST /questions/{id}/answer` (or worker) triggers TranslationEngine/LLM answer against Ollama
- [x] Answer generation queued via MQTT (`question.answer.request` / `question.answer.completed`) like the translation pipeline

### M10.4 Completion — answer stored + human review queue ✓

- [x] On answer completion, update issue labels: add `LLM_DONE` **and** `HUMAN_BACKLOG` (labelled alongside, not replacing)
- [x] Answer persisted to DB (`question_answers` table) with issue ref + LLM confidence
- [x] Answer posted back to the issue for the requester teacher/parent visibility

### M10.5 Moderation — teacher/parent verification ✓

- [x] `POST /questions/{id}/verify` — teacher/parent role confirms an answer
- [x] On confirmation add label `HUMAN_VERIFIED`, keeping `LLM_DONE` alongside
- [x] `POST /questions/{id}/reject` — reject answer → issue reopened with `REJECTED` label + sent back to `LLM_BACKLOG` for regeneration
- [x] Moderation queue surfaced in UI (team UI filter by `HUMAN_BACKLOG` label)

### M10.6 Config & docs ✓

- [x] `.env` additions: `FORGEJO_URL`, `FORGEJO_TOKEN` (backed by existing `GITEA_TOKEN`), `FORGEJO_OWNER+REPO`, API keys
- [x] Label idempotency — labels applied via unique set, replaced cleanly, never duplicated
- [x] Docs: `docs/QUESTION_TRIAGE.md` — workflow + Forgejo label guide
- [x] Tests for triage decision (new / answered / similar) driven by mocked Forgejo API
- [x] Update this TODO.md — mark complete when shipped

## Milestone 9 — Moodle Integration (Self-Hosted) ✓

### M9.1 REST API — Content Source for Moodle ✓
- [x] `/moodle/concepts` — paginated concept feed (JSON-LD + plain) for Moodle enrolment
- [x] `/moodle/concepts/{id}` — single concept with translation + explanation
- [x] `/moodle/quizzes` — quiz bank export (Moodle XML / JSON import format)
- [x] `/moodle/quizzes/{concept_id}` — quiz questions for a specific concept
- [x] `/moodle/courses/{id}/sync` — pull all concepts/quizzes for a course ID
- [x] API key auth for Moodle server (X-Moodle-Key header, separate from worker keys)
- [x] Rate limit: 60 RPM per Moodle instance (IP-based via existing rate limiter)

### M9.2 Moodle Plugin — local_polelo (LTI Tool Provider) ✓
- [x] `moodle/local/polelo/version.php` — plugin metadata
- [x] `moodle/local/polelo/db/access.php` — capability definitions
- [x] `moodle/local/polelo/settings.php` — admin settings (Polelo URL, API key, MQTT broker)
- [x] `moodle/local/polelo/lib.php` — hook callbacks (course_module, moodle_page)
- [x] `moodle/local/polelo/lti/` — LTI 1.3 tool provider implementation
  - [x] `tool_provider.php` — OIDC login initiation + launch response
  - [x] `jwt_grant.php` — JWT signing for LTI advantage services
  - [x] `grades.php` — assignment grade passback
- [x] `moodle/local/polelo/classes/` — PHP class files
  - [x] `polelo_api_client.php` — HTTP client for Polelo REST API
  - [x] `polelo_mqtt_bridge.php` — MQTT publish for real-time translation requests
  - [x] `polelo_widgets.php` — widget markup builders (data-attr + iframe)
- [x] `moodle/local/polelo/lang/en/local_polelo.php` — language strings
- [x] `moodle/local/polelo/db/install.xml` — XMLDB table definitions
- [x] `moodle/local/polelo/tests/` — PHPUnit tests for plugin
- [x] `moodle/local/polelo/index.php` — sync landing page
- [x] `moodle/local/polelo/amd/src/init.js` — AMD JS module for widget loading

### M9.3 Embeddable Widgets — iframe-based Translation/Quiz ✓
- [x] `src/web/widgets/translation-widget.js` — lightweight JS widget (fetch + render)
- [x] `src/web/widgets/quiz-widget.js` — interactive quiz widget (questions + scoring)
- [x] `src/web/widgets/polelo-embed.js` — auto-detect `[polelo-translate]` shortcodes in Moodle HTML
- [x] `/embed/translate` — standalone translation page (iframe target)
- [x] `/embed/quiz` — standalone quiz page (iframe target)
- [x] `/embed/api/translate/{concept_id}` + `/embed/api/quiz/{concept_id}` — public widget data API
- [x] Widget config: theme colors, default grade level, Sepedi/English toggle
- [x] CSP headers + CORS for cross-origin iframe embedding

### M9.4 Webhook-Based Sync — Moodle → Polelo ✓
- [x] `/moodle/webhooks/enrolment` — course enrolment event → trigger bulk translation
- [x] `/moodle/webhooks/activity` — activity completion → update concept mastery
- [x] `/moodle/webhooks/quiz-submission` — quiz attempt → store results in Polelo
- [x] Webhook signature verification (HMAC-SHA256)
- [x] Webhook queue: async processing via MQTT
- [x] `src/services/moodle_sync.py` — sync engine (poll + push hybrid)
- [x] Sync state table: `moodle_sync_state` (last_sync, course_id, status)

### M9.5 Database & Config ✓
- [x] `db/migrations/002_moodle_schema.sql` — moodle_instances, moodle_courses, moodle_sync_state, moodle_webhook_logs
- [x] `db/migrations/001b_moodle_db.sql` — Docker init for the Moodle database
- [x] `db/rollbacks/M/2/rollback.sh`
- [x] `.env` additions: `MoodleLtiSecret`, `MoodleWebhookSecret`, `MoodleApiKey`, `EMBED_BASE_URL`, `EMBED_ALLOWED_ORIGINS`

### M9.6 Docker Compose — Add Moodle Container ✓
- [x] Add `moodle` service to docker-compose.yml (bitnami/moodle)
- [x] Moodle DB config pointed at same PostgreSQL
- [x] Moodle cron container for background tasks
- [x] Volume mount for Moodle data + plugin source

### M9.7 Documentation ✓
- [x] `docs/MOODLE_INSTALL.md` — step-by-step Moodle plugin install
- [x] `docs/MOODLE_API.md` — content source API reference
- [x] `docs/MOODLE_WIDGETS.md` — widget embed guide
- [x] Update `API_REFERENCE.md` with /moodle/* endpoints
- [x] Update `TODO.md` with completion summary

## Milestone 8 — Production Hardening ✓

- [x] M8.1 Rate limiting middleware (per-role RPM limits)
- [x] M8.2 Config management — .env loader, settings class
- [x] M8.3 CORS + trusted host middleware
- [x] M8.4 Structured logging (JSON logs, request ID middleware)
- [x] M8.5 Translation request endpoint (`/translate`)
- [x] M8.6 Explanation endpoint (`/explain`)
- [x] Quiz endpoint (`/concepts/{id}/quiz`, `/quiz/validate`)
- [x] M8.8 Prometheus metrics endpoint (`/metrics`)
- [x] M8.9 API key auth for AI workers
- [x] M8.10 Update API_REFERENCE.md + TODO.md + push

## Docker Deployment ✓

- [x] Multi-stage Dockerfile (builder + runtime, Playwright Chromium, non-root user)
- [x] docker-compose.yml — full dev stack (app, PostgreSQL, MinIO, Mosquitto, Ollama)
- [x] docker-compose.prod.yml — production overrides (resource limits, restart, log rotation)
- [x] .dockerignore
- [x] deploy/mosquitto.conf — MQTT broker config

## Phase 2 — AI-Assisted Screenshot Service ✓

- [x] M2.1 Embed Playwright screenshot service into existing FastAPI stack
- [x] M2.2 Add healthcheck for screenshot service
- [x] M2.3 Test with real URLs
- [x] M2.4 Add to API_REFERENCE.md

## Phase 1 — Foundation Infrastructure ✓

### Config & Scaffold
- [x] pyproject.toml with FastAPI, uvicorn, playwright deps
- [x] .editorconfig + ruff.toml config
- [x] src/api/main.py — FastAPI app factory
- [x] src/api/routes/__init__.py
- [x] src/services/__init__.py
- [x] src/tests/integration/conftest.py

### Database
- [x] db/migrations/001_initial_schema.sql (TimescaleDB tables)
- [x] rollbacks/M/1/rollback.sh
- [x] Seed admin user + test concept

### Core API
- [x] /health endpoint
- [x] src/api/routes/auth.py — JWT login/register
- [x] src/api/routes/concepts.py — full CRUD
- [x] src/middleware/jwt.py — auth middleware

### AI Integration
- [x] src/services/ollama_client.py — Ollama HTTP client
- [x] src/services/translation_engine.py — concept → Sepedi translation
- [x] prompt templates for translate/explain per grade level

### Translation Pipeline
- [x] MQTT worker producer (publishes to translation.request)
- [x] MQTT consumer + DB write (translation.completed)
- [x] Status transitions: draft → pending_review

### Search
- [x] src/api/routes/search.py — pg_trgm fuzzy search
- [x] Faceted filter support

### UI
- [x] php/login.php — login page calling auth API
- [x] php/search.php — basic search UI

## Phase 3 — Governance ✓
- [x] Review workflow engine (Draft → PendingReview → Approved → Published)
- [x] Version snapshots + diff_to_prev
- [x] Translation history with unified_diff
- [x] Community contributions UI
- [x] Moderation bulk endpoints

## Phase 4 — Storage & Reliability ✓
- [x] S3 archive worker (MinIO)
- [x] Snapshot admin endpoint
- [x] Disaster recovery script
- [x] Backup validation pipeline

## Phase 5 — Accessibility & Deployment ✓
- [x] Responsive mobile UI
- [x] PWA support + manifest.json
- [x] Offline cache layer
- [x] RPi ARM64 deployment guide

## Continuous Tasks ✓
- [x] Update documentation
- [x] Run automated tests
- [x] Verify translations
- [x] Improve explanations
- [x] Benchmark Ollama
- [x] Monitor MQTT queues
- [x] Archive approved releases
