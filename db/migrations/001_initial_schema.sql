-- Polelo STEM Sepedi Translation Layer — Initial Schema
-- Target: TimescaleDB (PostgreSQL 15+)
-- Migration: 001_initial_schema.sql

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- ============================================================
-- ENUMS
-- ============================================================

CREATE TYPE user_role AS ENUM ('learner', 'translator', 'reviewer', 'teacher', 'admin');
CREATE TYPE content_status AS ENUM ('draft', 'pending_review', 'approved', 'published', 'rejected');
CREATE TYPE domain_type AS ENUM ('Biology', 'Physics', 'Chemistry', 'Mathematics', 'Geography', 'Computer Science', 'General');

-- ============================================================
-- USERS
-- ============================================================

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(64) NOT NULL UNIQUE,
    password_hash VARCHAR(256) NOT NULL,
    role user_role NOT NULL DEFAULT 'learner',
    active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_users_username ON users (username);
CREATE INDEX idx_users_role ON users (role);

-- ============================================================
-- SESSION TOKENS (JWT revocation)
-- ============================================================

CREATE TABLE session_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    jti VARCHAR(64) NOT NULL UNIQUE,
    token_type VARCHAR(16) NOT NULL DEFAULT 'access',
    revoked BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX idx_session_tokens_jti ON session_tokens (jti);
CREATE INDEX idx_session_tokens_user ON session_tokens (user_id);

-- ============================================================
-- CONCEPTS
-- ============================================================

CREATE TABLE concepts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name_en VARCHAR(256) NOT NULL,
    definition_en TEXT,
    domain domain_type NOT NULL DEFAULT 'General',
    grade_levels SMALLINT[] NOT NULL DEFAULT '{}',
    status content_status NOT NULL DEFAULT 'draft',
    current_version INTEGER NOT NULL DEFAULT 1,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_concepts_name ON concepts USING gin (name_en gin_trgm_ops);
CREATE INDEX idx_concepts_domain ON concepts (domain);
CREATE INDEX idx_concepts_status ON concepts (status);

-- ============================================================
-- TRANSLATIONS
-- ============================================================

CREATE TABLE translations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    concept_id UUID NOT NULL REFERENCES concepts(id) ON DELETE CASCADE,
    sepedi_term VARCHAR(256) NOT NULL,
    confidence_score REAL,
    alternative_forms JSONB DEFAULT '[]',
    status content_status NOT NULL DEFAULT 'draft',
    generated_by VARCHAR(64) NOT NULL DEFAULT 'AI Agent',
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_translations_concept ON translations (concept_id);
CREATE INDEX idx_translations_sepedi ON translations USING gin (sepedi_term gin_trgm_ops);
CREATE INDEX idx_translations_status ON translations (status);

-- ============================================================
-- EXPLANATIONS
-- ============================================================

CREATE TABLE explanations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    concept_id UUID NOT NULL REFERENCES concepts(id) ON DELETE CASCADE,
    grade_level SMALLINT NOT NULL,
    content_sep TEXT NOT NULL,
    examples_sep JSONB DEFAULT '[]',
    status content_status NOT NULL DEFAULT 'draft',
    generated_by VARCHAR(64) NOT NULL DEFAULT 'AI Agent',
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_explanations_concept ON explanations (concept_id);
CREATE INDEX idx_explanations_grade ON explanations (grade_level);

-- ============================================================
-- QUIZ QUESTIONS
-- ============================================================

CREATE TABLE quiz_questions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    concept_id UUID NOT NULL REFERENCES concepts(id) ON DELETE CASCADE,
    grade_level SMALLINT NOT NULL,
    question_type VARCHAR(32) NOT NULL DEFAULT 'multiple_choice',
    question_sep TEXT NOT NULL,
    options JSONB DEFAULT '[]',
    correct_answer TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_quiz_concept ON quiz_questions (concept_id);
CREATE INDEX idx_quiz_grade ON quiz_questions (grade_level);

-- ============================================================
-- REVIEWS
-- ============================================================

CREATE TABLE reviews (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    concept_id UUID NOT NULL REFERENCES concepts(id) ON DELETE CASCADE,
    reviewer_id UUID NOT NULL REFERENCES users(id),
    action VARCHAR(16) NOT NULL CHECK (action IN ('approved', 'rejected')),
    comments TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_reviews_concept ON reviews (concept_id);
CREATE INDEX idx_reviews_reviewer ON reviews (reviewer_id);

-- ============================================================
-- VERSION SNAPSHOTS
-- ============================================================

CREATE TABLE version_snapshots (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    concept_id UUID NOT NULL REFERENCES concepts(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    snapshot_data JSONB NOT NULL,
    diff_to_prev TEXT,
    archived_by VARCHAR(64) NOT NULL DEFAULT 'system',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (concept_id, version_number)
);

CREATE INDEX idx_versions_concept ON version_snapshots (concept_id);

-- ============================================================
-- MQTT JOB TRACKING
-- ============================================================

CREATE TABLE mqtt_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    topic VARCHAR(256) NOT NULL,
    payload JSONB NOT NULL,
    status VARCHAR(16) NOT NULL DEFAULT 'pending',
    retry_count INTEGER NOT NULL DEFAULT 0,
    max_retries INTEGER NOT NULL DEFAULT 3,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_mqtt_jobs_status ON mqtt_jobs (status);
CREATE INDEX idx_mqtt_jobs_topic ON mqtt_jobs (topic);
