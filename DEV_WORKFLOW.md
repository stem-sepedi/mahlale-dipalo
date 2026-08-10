# DEV_WORKFLOW.md

STEM Sepedi Translation Layer - Development Workflow

Version: 0.1

---

## Branch Strategy (GitFlow-light)

```
main ──▶ v1.0 ──▶ v2.0
  ▲       ▲        ▲
  │       │        └── tagged releases, immutable tags
  │       └────────── feature integration candidates
  ╰── always deployable trunk
```

| Branch | Purpose | Who Creates | Lifetime |
|--------|---------|-------------|----------|
| main | Stable code ready for production | Maintainer only | Continuous |
| feature/<name> | Single-feature development | Any contributor | Days to weeks |
| fix/<issue-id> | Hotfix for main | Anyone authorized | Hours to days |
| docs/<topic> | Documentation updates only | Writers, maintainers | Days to weeks |

### Naming conventions

- Branch: `feature/descriptive-name` or `fix/issue-number-short-desc` (e.g. `feature/explanation-engine`, `fix/12-search-timeout`)
- Commit messages: `<type>: <description>` using Conventional Commits spec
- PR title: same pattern as commit subject

### Git branches must have a single purpose — one feature, one fix. Never mix concerns across domains or features in the same branch.

---

## Commit Format (Conventional Commits)

```
<type>: <description> [scope]

<body if needed>

<Footer: related issues, rollback instructions>
```

| Type | When to use | Examples |
|------|-------------|---------|
| feat | New feature | `feat(concepts): add concept search endpoint` |
| fix | Bug fix | `fix(auth): reject revocation on expired token` |
| docs | Documentation changes only | `docs(architecture): update data flow diagram` |
| refactor | Code reshaping without behavior change | `refactor(db): normalize audit_log schema` |
| test | Adding or fixing tests | `test(e2e): add publish pipeline e2e test` |
| chore | Build/CI/tooling changes | `chore(ci): add coverage badge to README` |

Examples:
```
feat(search): implement fuzzy full-text search on concept names

Uses PostgreSQL pg_trgm for similarity scoring. Adds GET /search endpoint with faceted results via query params.

Closes #42
Rollback: drop_search_function.sql + git checkout feature/branch
```

---

## Pull Request Process

1. **Create PR from your branch to `main`** using the PR template at `.github/PULL_REQUEST_TEMPLATE.md`.
2. **CI passes** — all tests green, linter clean, coverage meets minimum thresholds.
3. **Reviewer approves** — one maintainer approval required for merge; two if the PR touches auth or database.
4. **Squash merge** to main with a single descriptive commit message (the full PR body becomes the long-form commit description).

### PR Checklist (copied from template)

- [ ] Tests added and passing
- [ ] Code covered by documentation updated
- [ ] CI pipeline green on fork
- [ ] No secret/credential leaks in code or logs
- [ ] Rollback instructions provided at the end of the PR description
- [ ] Each commit is atomic (revert-per-commit safe)
- [ ] Database migrations run and tested with rollback

### Auto-closing issues

PR descriptions referencing `Closes #issue_number` will auto-close the associated issue on merge. Link related but not-yet-resolved items with `Related to #123`.

---

## Code Review Standards

Reviewers focus on:
- Correctness — does it do what it says it does per the spec?
- Security — no hardcoded secrets, proper input validation, SQL injection free (use ORM), XSS prevention in PHP frontend (template escaping)
- Performance — N+1 query checks, index considerations, Ollama call batching
- Testing — coverage meets thresholds, no flaky patterns, golden-test alignment for translations
- Documentation — docstrings present for public APIs, CHANGELOG updated
- Git hygiene — atomic commits, descriptive messages

Reviewers reject PRs for:
- CI not passing on fork
- Missing rollback instructions
- Unresolved security concerns (secrets, injection, auth bypass)
- Tests only covering happy paths
- Commit history cluttered with "WIP", "fix", "nits" — request force-push before reviewing

---

## Development Environment

### Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Python 3.12+ | ≥3.12.0 | Backend language |
| Poetry | latest dependency management | Dependency management |
| Node.js 20+ | ≥20 | PHP frontend tooling (npm scripts) |
| Docker + Compose v2 | ≥24.0 | Service orchestration (all environments) |
| Ollama | latest | Local LLM serving |
| PostgreSQL client tools (psql, pg_isready) | compatible with server | Database migration and debug |

### Setup (first-time dev environment)

```bash
git clone <repo-url>
cd polelo
docker compose up -d database mqtt   # Start required services
poetry install
npm ci                               # PHP frontend dependencies
cp .env.example .env                 # Configure local secrets
o ollama pull qwen3:latest          # Pull default model for AI features
pytest -q tests/unit                # Verify environment works
```

### Virtual Environment

Always use Poetry venv inside project — never the system Python. Activate with:
```bash
poetry shell
```

or inline:
```bash
poetry run python src/main.py
```

---

## Database Migration Workflow

All schema changes go through migrations in `db/migrations/`:

1. Modify SQL migration file (e.g. `005_add_quiz_questions.sql`).
2. Include both forward and rollback scripts.
3. Run forward: `psql -f db/migrations/NNN_forward.sql polelo_db`
4. Test the resulting schema against integration tests.
5. Create rollback: `db/rollbacks/NNN_rollback.sql`.
6. PR must include both files plus a migration test verifying idempotency and rollback.

### Migration naming convention

```
NNN_description.sql       — forward migration (applied)
006_add_quiz_questions    — example, zero-padded 3-digit numbers ensure correct ordering
```

---

## Release Process

Releases are versioned according to Semantic Versioning: `MAJOR.MINOR.PATCH`.

| Bump triggers | Version bump |
|-----------------------------|--------------|
| Breaking API changes, schema incompatibility | MAJOR (1.0.0 → 2.0.0) |
| New backward-compatible endpoints, features | MINOR (1.0.0 → 1.1.0) |
| Bug fixes only — no new surface area | PATCH (1.x.0 → 1.x.1) |

Release checklist:
- [ ] CHANGELOG.md updated with release notes and contributors
- [ ] All phase-related TODO.md items marked as complete per the current release scope
- [ ] Database migration files included and tested
- [ ] Docker Compose versions pinned, no `latest` tags in production manifests
- [ ] Version bump committed separately: `chore(release): vX.Y.Z`
- [ ] Tagged with `git tag -a v1.0.0 -m "Release 1.0.0"` then pushed

---

## Branching Rules (from AGENTS.md enforced by convention)

| Rule | Enforcement mechanism |
|------|-----------------------|
| Every feature lives on its own branch | PR template checklist item — reviewer rejects merged PRs from main |
| Never commit broken code | CI pipeline gate at merge time on main |
| Atomic commits | Human-reviewed during code review |
| Document every new file | PR checklist: "code/documentation updated" |

---

## Continuous Tasks (from AGENTS.md)

These run automatically or require periodic manual attention:

### Automated (CI/CD runs)
- Run automated tests — pytest in CI on every push
- Benchmark Ollama — nightly performance suite on seeded staging data

### Periodic
- Update documentation — developer owns docs for their changes; merged via docs/ branch
- Verify translations — weekly review sweep by translator role users
- Improve explanations — scheduled per-domain backlog grooming sessions (bi-weekly)
- Monitor MQTT queues — admin dashboard health check; alert on dead-letter queue growth
- Archive approved releases — S3 snapshot after every published PR merge to main
- Maintain API compatibility — CHANGELOG notes any deprecations and sunset timelines
