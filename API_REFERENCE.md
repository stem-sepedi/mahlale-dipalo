# API_REFERENCE.md

STEM Sepedi Translation Layer - Complete API Reference

Version: 0.1

---

## Base URL

`http://<host:port>/api/v1`

All responses return `Content-Type: application/json`.  
Status codes follow RFC 9110 conventions.

---

## Authentication

Every endpoint except `/auth/login` and `/auth/refresh` requires a JWT in the `Authorization` header using Bearer scheme.

```
Authorization: Bearer <jwt_token>
```

JWT payload shape:
```json
{
  "sub": "<user_id>",
  "username": "alice",
  "role": "teacher",
  "iat": 1710000000,
  "exp": 1710086400,
  "jti": "<uuid>"
}
```

Token lifetime: `exp - iat` defaults to 24 hours. Refresh tokens last 30 days.

---

## Errors

Standard error envelope:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "grade_levels is required.",
    "details": [
      { "field": "grade_levels", "issue": "must be a non-empty array of integers" }
    ]
  }
}
```

| Error Code | HTTP Status | Meaning |
|------------|-------------|---------|
| UNAUTHORIZED | 401 | Missing or expired token, invalid signature, revoked jti |
| FORBIDDEN | 403 | Valid user but role insufficient for this action |
| NOT_FOUND | 404 | Entity does not exist |
| VALIDATION_ERROR | 422 | Malformed request body or query parameters |
| CONFLICT | 409 | Duplicate username, version mismatch |
| INTERNAL_ERROR | 500 | Unexpected server-side failure |

---

## Auth Endpoints

### POST /auth/login

Authenticates a user. Returns access token + refresh token pair.

**Request:**
```json
{ "username": "alice", "password": "secret" }
```

**Response (200):**
```json
{
  "access_token": "<jwt>",
  "refresh_token": "<opaque>",
  "expires_in": 86400,
  "token_type": "Bearer"
}
```

### POST /auth/refresh

Rotates access tokens without re-authentication.

**Request:**
```json
{ "refresh_token": "<opaque>" }
```

**Response (200):** New token pair. Old refresh token becomes invalid on rotation.

### POST /auth/logout

Revokes the current access and refresh tokens. Adds their JWT's `jti` to the session_tokens table.

---

## Concept Endpoints

### GET /concepts

List concepts with filtering and pagination.

**Query Parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| page | integer | 1 | Page number (1-indexed) |
| limit | integer | 20 | Items per page (max 100) |
| search | string | "" | Full-text fuzzy match against name_en, definition_en, sepedi_term |
| domain | enum | all | Filters by domain |
| grade | smallint | all | Filters concepts containing this grade_level in their array |
| status | enum | published | Only 'published' is meaningful for learners; higher roles may search draft/pending/approved too. Options: {draft,published,all} |

**Success Response (200):**
```json
{
  "items": [ /* Concept objects */, ... ],
  "total": 1247,
  "page": 1,
  "limit": 20,
  "_links": {
    "self": "/api/v1/concepts?page=1&limit=20",
    "next": "/api/v1/concepts?page=2&limit=20",
    "prev": null
  }
}
```

**Response shape for each Concept:**
```json
{
  "id": "<uuid>",
  "name_en": "Photosynthesis",
  "domain": " Biology",
  "grade_levels": [5, 8, 10],
  "status": "published",
  "current_version": 3,
  "_links": {
    "self": "/api/v1/concept/<uuid>",
    "translations": "/api/v1/concept/<uuid>/translations",
    "explanations": "/api/v1/concept/<uuid>/explanations"
  }
}
```

### POST /concepts

Creates a new concept. Auth: teacher or admin.

**Request:**
```json
{
  "name_en": "Mitosis",
  "definition_en": "A type of cell division that results in two daughter cells each having the same number and kind of chromosomes as the parent nucleus.",
  "domain": "Biology",
  "grade_levels": [10, 11, 12],
  "_links": {}
}
```

**Response (201):**
```json
{
  "concept": {
    "id": "<uuid>",
    "name_en": "Mitosis",
    "domain": "Biology",
    "grade_levels": [10, 11],
    "status": "draft"
  }
}
```

### GET /concepts/{id}

Returns a full concept object with all attached translations and explanations. Auth: any authenticated user.

**Response (200):**
```json
{
  "id": "<uuid>",
  "name_en": "Photosynthesis",
  "definition_en": "...",
  "domain": "Biology",
  "grade_levels": [5, 8],
  "status": "published",
  "current_version": 3,
  "translations": [ /* Translation objects */ ],
  "explanations": [ /* Explanation objects */ ],
  "_links": {
    "versions": "/api/v1/concept/<uuid>/versions",
    "reviews": "/api/v1/concept/<uuid>/reviews"
  }
}
```

### GET /concepts/{id}/translations

Returns version history for a concept's translations. Same response array as above but limited to translation objects only.

### GET /concepts/{id}/explanations

Returns version history for a concept's explanations.

---

## Translation Endpoints

### POST /translate

Generates Sepedi translations for an English STEM term using Ollama. Translations enter the workflow at `draft` status and must be reviewed. Auth: translator or AI agent.

**Request:**
```json
{
  "term": "Photosynthesis",
  "domain": "Biology",
  "grade_levels": [5, 8],
  "context_sep": "Dikologo tša mateti ya tlhago (optional hint for context)"
}
```

**Response (201):**
```json
{
  "translations": [
    {
      "id": "<uuid>",
      "sepedi_term": "Go belaela ga dimela",
      "confidence_score": 0.87,
      "alternative_forms": [
        { "form": "Photosynthesis (borrowed)", "register": "informal" }
      ],
      "status": "draft",
      "generated_by": "AI Agent",
      "_links": {
        "self": "/api/v1/translation/<uuid>"
      }
    },
    // ... up to 4 more alternatives
  ]
}
```

### PATCH /translations/{id}

A translator can edit their own draft translation before submitting for review. Auth: creator.

**Request:**
```json
{ "sepedi_term": "Go belaela ga dimela (revised)" }
```

### POST /translations/{id}/submit

Submits a translation for human review. Transitions status: `draft` → `pending`.

---

## Explanation Endpoints

### POST /explain

Generates a Sepedi explanation for a concept at a specified grade level using Ollama. Auth: teacher or AI agent.

**Request:**
```json
{
  "concept_id": "<uuid>",
  "grade_level": 8
}
```

**Response (201):**
```json
{
  "explanation": {
    "id": "<uuid>",
    "concept_id": "<uuid>",
    "grade_level": 8,
    "content_sep": "... full explanation body ...",
    "examples_sep": [...],
    "status": "draft",
    "generated_by": "AI Agent",
    "_links": {}
  }
}
```

### POST /explanations/{id}/submit

Transitions an explanation to `pending` for human review.

---

## Quiz Endpoints

### GET /concepts/{id}/quiz

Generates a quiz for a concept at the specified grade level using Ollama. Auth: teacher or AI agent.

**Query params:**
- `grade_level`: int — target difficulty (0–12, 99)
- `count`: int — number of questions to generate (default 5, max 20)
- `type`: enum — all / fill_in_blank / multiple_choice / short_answer

**Response (200):** Returns array of QuizQuestion objects in JSON. Questions are created as rows in the database and also returned inline.

### POST /quiz/validate

Client sends answers back for auto-grading.

**Request:**
```json
{
  "concept_id": "<uuid>",
  "grade_level": 8,
  "answers": [
    { "question_id": "<uuid>", "response_sep": "Karabo ya mofuta A" }
  ]
}
```

**Response (200):**
```json
{
  "results": [
    { "question_id": "<uuid>", "correct": true, "score_pct": 1.0 },
    { "question_id": "<uuid>", "correct": false, "score_pct": 0.6 }
  ],
  "total_score_pct": 0.80
}
```

---

## Review Endpoints

### POST /review

Moves an entity through the approval pipeline. Auth: reviewer or admin.

**Request:**
```json
{
  "concept_id": "<uuid>",
  "action": "approved",
  "comments": "Mantshi a nepagetše — terminology e dumelana le ditaba tša thuto."
}
```

Valid `action` values: `{ approved, rejected }`. If the entity being reviewed is at final status (`published`) the action transitions it; if not it advances to the next stage. On rejection comments are mandatory and required to be non-empty. Entity returns to `draft` for revision.

### GET /reviews

Lists all reviews for a concept or user across time, filtered by `?concept_id=<uuid>&action=approved`.

---

## Search Endpoint

### GET /search

Full-text search with faceting over concepts and translations. Auth: any authenticated user; learners can only see published entities.

**Query Parameters:**

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| q | string | Yes | Search query in Sepedi or English terms |
| domain | enum | No | Narrow search to a domain |
| grade | smallint | No | Only include entities applicable to this grade level |
| include_translations | boolean | No — false | Also scan translation table for matching sepedi_term values |
| page | integer | No — 1 | Page number |
| limit | integer | No — 20 | Items per page (max 100) |

**Response (200):**
```json
{
  "results": [
    {
      "type": "concept",
      "score": 0.94,
      "entity": { "id": "<uuid>", "name_en": "Photosynthesis" }
    },
    {
      "type": "translation",
      "score": 0.78,
      "entity": { "sepedi_term": "Go belaela ga dimela" }
    }
  ],
  "facets": {
    "domain": { "Biology": 142, "Physics": 89, ... },
    "grade": { 5: 67, 8: 103, 10: 45 }
  },
  "total": 156,
  "_links": {}
}
```

---

## Version Endpoints

### GET /concepts/{id}/versions

Lists all immutable snapshots of a concept's translations and explanations across published versions.

**Response (200):**
```json
[
  {
    "version_number": 3,
    "snapshot_key": "s3://polelo-snapshots/concept/<uuid>/v3.json",
    "diff_to_prev": "@@ -1,4 +1,6 @@ ...",
    "timestamp": "2025-07-25T14:00:00Z",
    "archived_by": "system"
  },
  // ... v2, v1, ...
]
```

### GET /concepts/{id}/versions/{version_number}

Returns the full entity state at that version snapshot, fetched from S3.

### POST /concepts/{id}/revert/{version_number}

Restores a concept to a previous version. Creates a new draft based on the reverted state and triggers review. Auth: admin or teacher.

---

## User Endpoints

### GET /users

Returns paginated list of users for admin use. Auth: admin only. Password hashes are never returned in any response.

### PATCH /users/{id}

Edit a user's role or disable account with admin privileges. Auth: admin only.

**Request:**
```json
{ "role": "teacher", "active": true }
```

### POST /users

Create a new user. Auth: admin only.

**Request:**
```json
{
  "username": "bosco",
  "password": "temp-pass-123",
  "role": "translator"
}
```

### GET /users/me

Returns the currently authenticated user's own profile (with password_hash redacted). Auth: any.

---

## Queue Management

These endpoints allow admin inspection of the MQTT queue state but do not publish messages — that is reserved for internal workers.

### GET /queue/stats

**Response (200):**
```json
{
  "active_workers": 4,
  "pending_jobs": {
    "translation.request": 12,
    "review.pending": 3
  },
  "dead_letter_count": 1
}
```

### GET /queue/dead-letter

Lists messages that have exhausted their retry count. Auth: admin only.

---

## Health & Monitoring

### GET /health

**Response (200):**
```json
{
  "status": "ok",
  "version": "0.1.0",
  "uptime_seconds": 36012
}
```

### GET /metrics

Prometheus-format metrics for integration with Prometheus/Grafana. No auth required.

**Response (200):**
```
# HELP polelo_uptime_seconds Application uptime in seconds
# TYPE polelo_uptime_seconds gauge
polelo_uptime_seconds 36012.0
# HELP polelo_info Application info
# TYPE polelo_info gauge
polelo_info{version="0.1.0"} 1
```

---

## Translation Endpoints

### POST /translate

Generates Sepedi translations for an English STEM term using Ollama. Auth: translator or AI agent.

**Request:**
```json
{
  "term": "Photosynthesis",
  "domain": "Biology",
  "grade_levels": [5, 8],
  "context_sep": "Dikologo tša mateti ya tlhago (optional)"
}
```

**Response (201):**
```json
{
  "translation": {
    "id": "<uuid>",
    "concept_id": "<uuid>",
    "sepedi_term": "Go belaela ga dimela",
    "confidence_score": 0.87,
    "alternative_forms": [{"form": "Photosynthesis (borrowed)", "register": "informal"}],
    "status": "draft",
    "generated_by": "AI Agent"
  }
}
```

### PATCH /translations/{id}

Edit a draft translation before submitting. Auth: creator.

### POST /translations/{id}/submit

Submit a translation for human review. Status: `draft` → `pending_review`.

---

## Explanation Endpoints

### POST /explain

Generates a Sepedi explanation for a concept at a specified grade level. Auth: teacher or admin.

**Request:**
```json
{
  "concept_id": "<uuid>",
  "grade_level": 8
}
```

**Response (201):**
```json
{
  "explanation": {
    "id": "<uuid>",
    "concept_id": "<uuid>",
    "grade_level": 8,
    "content_sep": "...",
    "examples_sep": ["..."],
    "status": "draft",
    "generated_by": "AI Agent"
  }
}
```

### POST /explanations/{id}/submit

Submit an explanation for review. Status: `draft` → `pending_review`.

---

## Quiz Endpoints

### GET /concepts/{id}/quiz

Generates a quiz for a concept at the specified grade level using Ollama.

**Query params:**
- `grade_level`: int (0–12)
- `count`: int (default 5, max 20)
- `type`: all / fill_in_blank / multiple_choice / short_answer

**Response (200):**
```json
{
  "questions": [
    {
      "id": "<uuid>",
      "question_sep": "...",
      "question_type": "multiple_choice",
      "options": ["A", "B", "C", "D"]
    }
  ],
  "concept_id": "<uuid>",
  "grade_level": 8
}
```

### POST /quiz/validate

Auto-grade quiz answers.

**Request:**
```json
{
  "concept_id": "<uuid>",
  "grade_level": 8,
  "answers": [
    {"question_id": "<uuid>", "response_sep": "Karabo"}
  ]
}
```

**Response (200):**
```json
{
  "results": [
    {"question_id": "<uuid>", "correct": true, "score_pct": 1.0}
  ],
  "total_score_pct": 0.80
}
```

---

## Archive Endpoints

### POST /archive/releases

Batch-archive published concepts to S3. Auth: admin.

**Request:**
```json
{
  "concept_ids": ["<uuid>"],
  "archive_all_published": false
}
```

---

## Screenshot Endpoints

### GET /screenshots/health

Returns the status of the Playwright browser backend.

**Response (200):**
```json
{
  "status": "not_started",
  "browser": "chromium"
}
```

| Status | Meaning |
|--------|---------|
| not_started | Browser has not been launched yet; will auto-start on first capture |
| ok | Browser is running and ready |

### POST /screenshots/capture

Takes a screenshot of the given URL using headless Chromium.

**Request:**
```json
{
  "url": "https://example.com",
  "full_page": true
}
```

**Response (200):**
```json
{
  "path": "screenshots/1785034467.png"
}
```

**Response (502):** Screenshot failed after retries.
```json
{
  "detail": "Failed after 3 attempts: <error>"
}
```

---

## Question Triage Endpoints (M10)

Student questions are mirrored to a Forgejo/Gitea issue and answered by the LLM
engine after a triage pass. Labels on the issue track the lifecycle:
`LLM_BACKLOG` → `LLM_WIP` → `LLM_DONE` + `HUMAN_BACKLOG` → (`HUMAN_VERIFIED` | `REJECTED`).
See `docs/QUESTION_TRIAGE.md`.

| Method | Path                        | Auth               | Purpose                              |
|--------|-----------------------------|--------------------|--------------------------------------|
| POST   | `/questions`                | learner/teacher/admin | Submit a question (creates issue + triages) |
| GET    | `/questions`                | learner/teacher/admin | List questions; `status=human_backlog` = moderation queue |
| GET    | `/questions/{id}`           | learner/teacher/admin | Single question with answers |
| POST   | `/questions/{id}/answer`    | teacher/admin      | Dispatch to LLM (queued via MQTT)    |
| POST   | `/questions/{id}/verify`    | teacher/admin      | Confirm an answer (→ `HUMAN_VERIFIED`) |
| POST   | `/questions/{id}/reject`    | teacher/admin      | Reject an answer (→ `REJECTED`, back to `LLM_BACKLOG`) |

### POST /questions

**Request:**
```json
{
  "question_text": "What is photosynthesis?",
  "grade": 8,
  "subject": "Biology",
  "student_ref": "learner-042"
}
```

**Response (201):**
```json
{
  "question": {
    "id": "<uuid>",
    "question_text": "What is photosynthesis?",
    "grade": 8,
    "subject": "Biology",
    "student_ref": "learner-042",
    "forgejo_issue_number": 12,
    "triage_status": "new"
  },
  "triage": {
    "decision": "new",
    "matching_issue_number": null,
    "answer": null
  }
}
```

`triage.decision` is `new` (proceed to LLM), `similar` (an unanswered issue with
the same topic exists — labelled `LLM_SIMILAR`), or `answered` (an existing
answer is reused — returned in `triage.answer`, no LLM call).

### GET /questions?status=human_backlog

Returns the teacher/parent moderation queue — questions whose latest answer is
`llm_done` and awaiting verification. Other status values: `new`, `similar`,
`dispatched`, `answered`, `verified`, `rejected`.

### POST /questions/{id}/answer

Dispatches the question to the LLM. Adds `LLM_WIP` (removing `LLM_BACKLOG`),
records an `mqtt_jobs` row, and publishes `question.answer.request` on MQTT. The
`question_worker` generates the answer, stores it in `question_answers` (status
`llm_done`), adds `LLM_DONE` + `HUMAN_BACKLOG`, posts the answer back to the
issue, and broadcasts `question.answer.completed`.

**Response (202):**
```json
{
  "status": "dispatched",
  "question_id": "<uuid>",
  "forgejo_issue_number": 12
}
```

### POST /questions/{id}/verify

Teacher/parent confirms an answer. Adds `HUMAN_VERIFIED` (keeping `LLM_DONE`).
**Body (optional):** `{"review_comment": "..."}`

### POST /questions/{id}/reject

Rejects an answer. Reopens the issue with `REJECTED` and returns it to
`LLM_BACKLOG` for regeneration. **Body (optional):** `{"review_comment": "..."}`

---

## Grade Catalog Endpoints (R1)

Per-grade/phase configuration (Grade R–12 + University) driving every
grade-sensitive behaviour. Backed by the `grade_catalog` table; see
`ROADMAP_GRADES_R12.md`.

| Method | Path           | Auth  | Purpose                                  |
|--------|----------------|-------|------------------------------------------|
| GET    | `/grades`      | admin | Full catalog (R–12 + University)         |
| GET    | `/grades/{grade}` | any authenticated user | One grade's config + CAPS reference |

### GET /grades

**Response (200):**
```json
{
  "grades": [
    {
      "grade": 8,
      "phase": "senior",
      "band": "senior",
      "name_en": "Grade 8",
      "name_sep": "Mphato wa 8",
      "age_min": 13,
      "age_max": 14,
      "vocab_level": 4,
      "curriculum_ref": "CAPS Natural Sciences / Mathematics"
    }
  ]
}
```

### GET /grades/{grade}

Same shape for one grade. Invalid grades (`13`, `-1`, `100`…) return `422`;
grades `0–12` and `99` are accepted.

**Grade bounds:** all grade-bearing endpoints (`/concepts`, `/explain`,
`/concepts/{id}/quiz`, `/quiz/validate`, `/questions`, `/translate`) now reject
grades outside `0–12`/`99` with `422` via a central validator
(`src/services/grade_config.py`).

**Per-instance overrides:** `GRADE_CONFIG_OVERRIDES` env var
(e.g. `{"8":{"vocab_level":5}}`) merges onto the seeded catalog without a DB
change.

---

## Rate Limiting

| Role | Requests per minute |
|------|---------------------|
| Learner | 60 |
| Translator/Reviewer/Teacher | 120 |
| Admin | 300 |
| AI Worker (internal) | No limit |

Excess requests return `429 Too Many Requests` with a `Retry-After` header.

---

## OpenAPI Spec

A full OpenAPI 3.x specification (`openapi.yaml`) is auto-generated from Pydantic models at runtime and served at `/docs`. Browsing the URL in-browser activates Swagger UI for interactive API exploration.

---

## Moodle Content Source API

The `/moodle/*` endpoints expose published content to self-hosted Moodle LMS
instances. Auth uses a dedicated `X-Moodle-Key` header (separate key space from
AI workers and JWT users).

**Auth header:**
```
X-Moodle-Key: <moodle-instance-key>
```

**Rate limit:** 60 requests/minute per Moodle instance (IP-based).

| Method | Path                           | Purpose                                   |
|--------|--------------------------------|-------------------------------------------|
| GET    | `/moodle/concepts`             | Paginated published concept feed          |
| GET    | `/moodle/concepts/{id}`        | Single concept (translation + explanation)|
| GET    | `/moodle/quizzes`              | Quiz bank export (json or Moodle XML)     |
| GET    | `/moodle/quizzes/{concept_id}` | Quiz questions for one concept            |
| GET    | `/moodle/courses/{id}/sync`    | Pull concepts + quizzes for a course      |
| POST   | `/moodle/courses/{id}/sync`    | Push completion/mastery back              |

Full reference: see `docs/MOODLE_API.md`.

### Example — GET /moodle/concepts

**Query params:** `page`, `limit` (≤200), `domain`, `grade`, `since` (ISO-8601),
`format` (`plain`|`jsonld`).

**Response (200):**
```json
{
  "concepts": [
    {
      "concept_id": "<uuid>",
      "name_en": "Photosynthesis",
      "definition_en": "...",
      "domain": "Biology",
      "grade_levels": [5, 8, 10],
      "sepedi_term": "Go belaela ga dimela",
      "confidence_score": 0.87,
      "explanation_sep": "...",
      "explanation_grade": 8,
      "updated_at": "2026-07-24T10:00:00Z"
    }
  ],
  "total": 1247,
  "page": 1,
  "limit": 50,
  "has_next": true
}
```

### Example — GET /moodle/quizzes?format=moodle_xml

Returns an `application/xml` attachment (`polelo_quiz_bank.xml`) in Moodle quiz
XML import format.

## Moodle Webhooks

Signed (HMAC-SHA256) event ingestion from Moodle → Polelo. Immediate responses
return `{"status":"queued","log_id":"<uuid>"}`; processing is async via MQTT.

| Method | Path                                      | Event            |
|--------|-------------------------------------------|------------------|
| POST   | `/moodle/webhooks/enrolment`              | Course enrolment |
| POST   | `/moodle/webhooks/activity`               | Activity completion |
| POST   | `/moodle/webhooks/quiz-submission`        | Quiz attempt     |

**Signing headers:** `X-Moodle-Signature` =
`HMAC_SHA256(<X-Moodle-Timestamp>.<raw-body>)` with the `MoodleWebhookSecret`.
Timestamp must be within ±300 seconds.

Errors: missing/invalid signature → `401`/`403`; expired window → `401`.

## Embed Widget API

Public (unauthenticated, learner-rate-limited) endpoints used by the embeddable
JS widgets:

| Method | Path                                  | Purpose                       |
|--------|---------------------------------------|-------------------------------|
| GET    | `/embed/translate`                    | Standalone iframe translation page |
| GET    | `/embed/quiz`                         | Standalone iframe quiz page   |
| GET    | `/embed/api/translate/{concept_id}`   | Widget data for translation   |
| GET    | `/embed/api/quiz/{concept_id}`        | Widget data for quiz          |
| GET    | `/widgets/translation-widget.js`      | Widget script (static)        |
| GET    | `/widgets/quiz-widget.js`             | Widget script (static)        |
| GET    | `/widgets/polelo-embed.js`            | Shortcode loader (static)     |

Embed pages send CSP `frame-ancestors` headers controlled by
`EMBED_ALLOWED_ORIGINS`; widget API responses include CORS headers per
`CORS_ORIGINS`. Only **published** concepts and **approved** translations/
explanations are exposed. See `docs/MOODLE_WIDGETS.md`.
