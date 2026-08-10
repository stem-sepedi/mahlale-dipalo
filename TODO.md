# TODO.md

> **All milestones complete.** 41 API endpoints, 8 service modules, full test suite, Docker deployment.
> Last updated: Milestone 9 — Moodle Integration (Self-Hosted)

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
