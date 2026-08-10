# Moodle Content Source API

The `/moodle/*` endpoints expose Polelo content to self-hosted Moodle instances as
a **content source**. They supersede the JWT-authenticated REST API for machine
clients; authentication is a dedicated API key presented in the `X-Moodle-Key`
header, separate from AI-worker keys.

Base URL: `https://<polelo-host>` (no `/api/v1` prefix).

## Authentication

All `/moodle/*` endpoints require:

```
X-Moodle-Key: <moodle-instance-key>
```

Keys are issued per Moodle instance on the Polelo server via `MOODLE_API_KEYS`
(comma-separated). Invalid or missing keys return `401`/`403`.

## Rate limiting

Moodle instances are rate-limited to **60 requests/minute** (IP-based, via the
existing rate-limit middleware). Optional `since` params let clients implement
incremental sync to stay well under the limit.

## Endpoints

| Method | Path                          | Purpose                                  | Formats          |
|--------|-------------------------------|------------------------------------------|------------------|
| GET    | `/moodle/concepts`            | Paginated published concept feed         | plain, jsonld    |
| GET    | `/moodle/concepts/{id}`       | Single concept: translation + explanation| plain, jsonld    |
| GET    | `/moodle/quizzes`             | Quiz bank export                         | json, moodle_xml |
| GET    | `/moodle/quizzes/{concept_id}`| Quiz questions for one concept           | json, moodle_xml |
| GET    | `/moodle/courses/{id}/sync`   | Pull all concepts + quizzes for a course | json             |
| POST   | `/moodle/courses/{id}/sync`   | Push mastery/completion back to Polelo   | json             |

### GET `/moodle/concepts`

Query parameters:

| Param  | Type        | Default | Description                                    |
|--------|-------------|---------|------------------------------------------------|
| page   | integer     | 1       | 1-indexed page                                 |
| limit  | integer     | 50      | max 200                                        |
| domain | enum        | —       | Biology, Physics, Chemistry, Mathematics, Geography, Computer Science, General |
| grade  | int         | —       | Concept must contain this grade level          |
| since  | ISO-8601    | —       | Return only concepts updated after this time   |
| format | plain\|jsonld | plain | JSON-LD (`@context: schema.org`, `DefinedTerm`)|

Response:

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
      "updated_at": "2026-07-24T10:00:00+00:00"
    }
  ],
  "total": 1247,
  "page": 1,
  "limit": 50,
  "has_next": true
}
```

`format=jsonld` adds `"@context"`, `"@type": "DefinedTerm"`, `"name"`,
`"alternateName"`.

### GET `/moodle/concepts/{concept_id}`

Returns the single published concept including the full `translations[]` and
`explanations[]` history (approved only). `format=jsonld` swaps the payload for a
compact JSON-LD `DefinedTerm`.

### GET `/moodle/quizzes`

Quiz bank export. Params: `page`, `limit`, `domain`, `grade`, `format` (`json` |
`moodle_xml`). With `format=moodle_xml` the response is an `application/xml`
download (`polelo_quiz_bank.xml`) in Moodle XML import format (multichoice +
shortanswer).

### GET `/moodle/quizzes/{concept_id}`

Quiz questions for one published concept. Params: `grade_level` (default 8),
`format`. Each question includes `id`, `question_type`, `question_sep`, `options`,
`correct_answer`.

### GET `/moodle/courses/{course_id}/sync`

Incremental pull for a course. Params: `since` (ISO-8601). Returns all published
concepts with their best Sepedi term/explanation and `quizzes_count`.

```json
{
  "course_id": "42",
  "concepts": [ ... ],
  "total_concepts": 10,
  "total_quizzes": 31,
  "synced_at": "..."
}
```

### POST `/moodle/courses/{course_id}/sync`

Moodle pushes completion/mastery data back to Polelo. Body:

```json
{
  "concept_id": "<uuid>",
  "user_moodle_id": 1004,
  "score_pct": 82.5,
  "completed_at": "2026-07-24T10:00:00Z"
}
```

Stored as a completed sync record (topic `moodle.sync.<course>`).

---

## Webhooks (Moodle → Polelo push)

Event ingestion uses HMAC-SHA256 signed webhooks, distinct from the key-header
endpoints above. See `docs/MOODLE_WIDGETS.md` section "Webhooks".

| Endpoint                              | Event            | Purpose                         |
|---------------------------------------|------------------|---------------------------------|
| `POST /moodle/webhooks/enrolment`     | enrolment        | Course enrolment → bulk translation |
| `POST /moodle/webhooks/activity`      | activity         | Activity completion → mastery   |
| `POST /moodle/webhooks/quiz-submission`| quiz-submission | Quiz attempt → store results    |

All webhooks require `X-Moodle-Signature` (HMAC-SHA256 of
`<timestamp>.<raw-body>`) and `X-Moodle-Timestamp` (Unix, ±300 s window).
Responses return `{"status":"queued","log_id":"<uuid>"}`.