# DATABASE_SCHEMA.md

STEM Sepedi Translation Layer - Database Schema

Version: 0.1

---

## Overview

All data stored in **TimescaleDB** (PostgreSQL extension for time-series with relational capabilities).  
Schema namespaced as `polelo`. Migration files at: `db/migrations/`

---

## Tables

### concepts

Primary concept entity. Each STEM topic is one row.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, default gen_random_uuid() | Unique identifier |
| name_en | varchar(255) | NOT NULL | English term (e.g. "Photosynthesis") |
| definition_en | text | NOT NULL | English definition |
| domain | varchar(30) | NOT NULL DEFAULT 'GeneralSTEM' | Physics, Chemistry, Biology, Mathematics, Engineering, ComputerScience, Robotics, Astronomy, Agriculture, EnvironmentalScience |
| grade_levels | smallint[] | NOT NULL DEFAULT '{}' | Applicable grades (0=Grade R, 1-12, 99=University) |
| status | varchar(16) | NOT NULL DEFAULT 'draft' | draft / pending_review / approved / published |
| review_status | varchar(32) | NOT NULL DEFAULT 'awaiting_review' | awaiting_review / reviewed / approved / published / rejected_need_revision |
| current_version | integer | NOT NULL DEFAULT 1 | Incremented on each publish |
| created_by | UUID | FK → users.id | Creator user ID |
| created_at | timestamptz | NOT NULL DEFAULT now() | Creation timestamp |
| updated_at | timestamptz | NOT NULL DEFAULT now() | Last modification timestamp |
| published_at | timestamptz | NULL until published | When status reached 'published' |

**Indexes:**
- `idx_concepts_status` ON (status) WHERE status = 'published'
- `idx_concepts_domain` ON (domain)
- `idx_concepts_grade` ON (grade_levels) USING GIN
- `idx_concepts_name_en` ON (name_en) gin_trgm_ops (for fuzzy search)
- `idx_concepts_created_at` ON (created_at DESC)

**Checks:**
- domain ∈ {'Physics','Chemistry','Biology','Mathematics','Engineering','ComputerScience','Robotics','Astronomy','Agriculture','EnvironmentalScience','GeneralSTEM'}
- status ∈ {'draft','pending_review','approved','published'}
- review_status ∈ {'awaiting_review','reviewed','approved','published','rejected_need_revision'}

---

### translations

Stores every Sepedi translation ever proposed. Multiple per concept over time.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, default gen_random_uuid() | Unique identifier |
| concept_id | UUID | FK → concepts.id ON DELETE CASCADE | Parent concept |
| sepedi_term | varchar(255) | NOT NULL | Sepedi translation of the concept name |
| definition_sep | text | NULL | Full Sepedi definition (may differ from literal name translation) |
| confidence_score | numeric(3,2) | CHECK ≥ 0 AND ≤ 1 | AI-confidence indicator |
| alternative_forms | jsonb | NOT NULL DEFAULT '[]' | [{ "form": "variant", "register": "formal/informal/register_note" }] |
| status | varchar(16) | NOT NULL DEFAULT 'draft' | draft / pending / approved / published |
| version | integer | NOT NULL DEFAULT 1 | Per-translation sequence number |
| generated_by | varchar(32) | NOT NULL AI Translator | Origin: human translator or AI agent label |
| source_concept_id | UUID | FK → concepts.id nullable | Optional hint referencing an English concept for context |
| created_at | timestamptz | NOT NULL DEFAULT now() | Creation timestamp |

**Indexes:**
- `idx_translations_concept` ON (concept_id)
- `idx_translations_status` ON (status) WHERE status = 'published'
- `idx_translations_sep_term` ON (sepedi_term) gin_trgm_ops (fuzzy search support)
- `idx_translations_generated_by` ON (generated_by)

---

### explanations

Learner-friendly Sepedi explanations at specified grade levels.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, default gen_random_uuid() | Unique identifier |
| concept_id | UUID | FK → concepts.id ON DELETE CASCADE | Parent concept |
| grade_level | smallint | NOT NULL | 0=Grade R through 12 + 99=University |
| content_sep | text | NOT NULL | Sepedi explanation body |
| examples_sep | jsonb[] | NOT NULL DEFAULT '[]' | [{ "sep": "...", "en_context": "..." }] |
| status | varchar(16) | NOT NULL DEFAULT 'draft' | draft / pending / approved / published |
| version | integer | NOT NULL DEFAULT 1 | Per-explanation sequence number |
| generated_by | varchar(32) | NOT NULL | AI Agent or human translator label |
| created_at | timestamptz | NOT NULL DEFAULT now() | Creation timestamp |

**Indexes:**
- `idx_explanations_concept` ON (concept_id)
- `idx_explanations_grade` ON (grade_level)
- `idx_explanations_status` ON (status) WHERE status = 'published'

---

### quiz_questions

Auto-generated or manually authored quiz questions per concept.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | Unique identifier |
| concept_id | UUID | FK → concepts.id ON DELETE CASCADE | Parent concept |
| type | varchar(24) | NOT NULL | fill_in_blank / multiple_choice / short_answer |
| question_sep | text | NOT NULL | Sepedi-language question text |
| question_en | text | NOT NULL | English parallel for translator reference |
| options | jsonb | NULL for non-MC | [{ "label": "A", "text_sep": "...", "text_en": "...", "is_correct": true }] |
| answer_sep | text | NOT NULL | Correct answer in Sepedi |
| explanation_sep | text | nullable | Why the answer is correct (in Sepedi) |
| difficulty | smallint | CHECK BETWEEN 1 AND 6 | Maps to grade levels when possible |
| source | varchar(32) | NOT NULL DEFAULT 'ai' | ai / human |
| created_at | timestamptz | NOT NULL DEFAULT now() | Creation timestamp |

**Indexes:**
- `idx_quiz_concept` ON (concept_id)
- `idx_quiz_type` ON (type)
- `idx_quiz_difficulty` ON (difficulty)

---

### teacher_notes

Classroom guidance generated alongside explanations.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | Unique identifier |
| concept_id | UUID | FK → concepts.id ON DELETE CASCADE | Parent concept |
| grade_level | smallint | NOT NULL | Target grade level |
| content_sep | text | NOT NULL | Sepedi-language teacher notes |
| extension_activities | jsonb[] | nullable | [{ "title": "...", "instructions_sep": "..." }] |
| suggested_demo | text | nullable | Suggested practical demonstration description in Sepedi |
| source | varchar(32) | NOT NULL DEFAULT 'ai' | AI or human label |
| created_at | timestamptz | NOT NULL DEFAULT now() | Creation timestamp |

---

### users

Authenticates all human actors.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, default gen_random_uuid() | Unique identifier |
| username | varchar(64) | NOT NULL, unique | Login identifier |
| password_hash | varchar(255) | NOT NULL | bcrypt hash (never plaintext) |
| role | varchar(16) | NOT NULL DEFAULT 'learner' | admin / teacher / translator / reviewer / learner |
| active | boolean | NOT NULL DEFAULT true | Accounts can be soft-disabled |
| created_at | timestamptz | NOT NULL DEFAULT now() | Creation timestamp |

**Indexes:**
- `idx_users_username` ON (username) unique

---

### audit_log

Immutable trail of every data mutation.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, default gen_random_uuid() | Unique identifier |
| user_id | UUID | FK → users.id nullable | Actor; NULL if generated by AI Worker role |
| timestamp | timestamptz | NOT NULL DEFAULT now() | Event time |
| entity_type | varchar(32) | NOT NULL | Concept / Translation / Explanation / QuizQuestion |
| entity_id | UUID | nullable | Affected resource. May be NULL for auth events |
| action | varchar(24) | NOT NULL | create, update, delete, publish, approve, reject, revert, archive |
| old_values | jsonb | nullable | State before mutation or null on create |
| new_values | jsonb | nullable | State after mutation or null on delete |

**Tablespaces:** Use timescaledb_data for performance. This table should grow monotonically — never updated. Periodic archive to cold storage recommended.

**Indexes:**
- `idx_audit_user` ON (user_id)
- `idx_audit_timestamp` ON (timestamp DESC)
- `idx_audit_entity` ON (entity_type, entity_id)

---

### version_snapshots

Immutable snapshot of a concept at each published version.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, default gen_random_uuid() | Unique identifier |
| concept_id | UUID | FK → concepts.id ON DELETE CASCADE | Parent concept |
| version_number | integer | NOT NULL | Version number for this concept |
| snapshot_key | varchar(255) | NOT NULL | S3-compatible object key where the full immutable JSON payload resides |
| diff_to_prev | text | nullable | Unified diff relative to previous version; null on first version |
| timestamp | timestamptz | NOT NULL DEFAULT now() | When snapshot was captured |
| archived_by | varchar(32) | NOT NULL DEFAULT 'system' | Origin label (system / admin) |

**Indexes:**
- `idx_snapshots_concept_version` ON (concept_id, version_number) unique
- `idx_snapshots_timestamp` ON (timestamp DESC)

---

### session_tokens

JWT black-out list for token revocation.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK | Unique identifier |
| jti | uuid | NOT NULL | JWT ID claim (unique per token) |
| user_id | UUID | FK → users.id ON DELETE CASCADE | Owner |
| expires_at | timestamptz | NOT NULL | When this revocation entry expires |
| created_at | timestamptz | NOT NULL DEFAULT now() | Recording timestamp |

**Indexes:**
- `idx_session_jti` ON (jti) unique
- `idx_session_expires` ON (expires_at) WHERE expires_at > now() (partial index, prunes old entries automatically)

---

## Seed Data (First Run)

```sql
-- Default admin user: username='admin' password='changeme-admin'
INSERT INTO users (username, password_hash, role, active)
VALUES ('admin', '$2b$12$<hashed>', 'admin', true);
```

---

## TimescaleDB Hypertables (time-series tables)

For audit_log and performance telemetry:

```sql
SELECT create_hypertable('audit_log', 'timestamp');
SELECT create_hypertable('session_tokens', 'created_at');
```

---

## Data Retention Policies

| Table | Retention Action | Criteria |
|-------|-----------------|----------|
| audit_log | Do not delete (immutable) | N/A — managed through S3 cold storage |
| session_tokens | Delete expired entries | Every 1h via cron job |
| version_snapshots | Keep all snapshots indefinitely | Each concept's full history is permanent |

---

## Migration Strategy

All migrations live in `db/migrations/` as numbered SQL files:

```
001_initial_schema.sql
002_add_quiz_questions.sql
003_add_teacher_notes.sql
...
```

Run with:  
`psql -f db/migrations/NNN_name.sql polelo_db`

Rollback is a matter of reverting the git commit and re-applying. Since TimescaleDB supports DDL in transactions, each migration must be idempotent (use `CREATE TABLE IF NOT EXISTS`, `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`, etc.).
