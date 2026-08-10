# CHANGELOG.md

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added — Milestone 10: Question triage to LLM via Forgejo/Gitea issues

- `src/services/forgejo_client.py` — Forgejo/Gitea issue + label + comment client.
- `src/services/question_triage.py` — triage decision (new / similar / answered).
- `src/services/question_engine.py` — LLM Sepedi answer generation for questions.
- `src/services/question_worker.py` — MQTT worker for `question.answer.request`.
- `src/api/routes/questions.py` — `/questions` CRUD + dispatch/verify/reject + moderation queue.
- `db/migrations/003_question_triage.sql` + `db/rollbacks/M/10/rollback.sh`.
- MQTT topics `question.answer.request` / `question.answer.completed`.
- `.env` — `FORGEJO_URL`, `FORGEJO_TOKEN` (falls back to `GITEA_TOKEN`),
  `FORGEJO_OWNER`, `FORGEJO_REPO`.
- `docs/QUESTION_TRIAGE.md` — workflow + Forgejo label guide.
- `API_REFERENCE.md` — Question Triage Endpoints section.
- Unit tests for the triage decision driven by a mocked Forgejo API.

### Added (Initial Planning)

- GOAL.md - Project goal objectives success metrics design principles
- README.md - Sepedi language context and translation reference
- AGENTS.md - Agent definitions for all AI workers
- ARCHITECTURE.md - System architecture diagram and tech stack
- TODO.md - Phased feature development plan
- CHANGELOG.md - This file
