-- Polelo STEM Sepedi Translation Layer — Moodle Integration Schema
-- Target: TimescaleDB (PostgreSQL 15+)
-- Migration: 002_moodle_schema.sql

-- ============================================================
-- ENUMS
-- ============================================================

CREATE TYPE moodle_sync_status AS ENUM ('pending', 'syncing', 'synced', 'failed');

-- ============================================================
-- MOODLE INSTANCES
-- ============================================================

CREATE TABLE moodle_instances (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(128) NOT NULL,
    base_url VARCHAR(256) NOT NULL UNIQUE,
    api_key_hash VARCHAR(256) NOT NULL,
    webhook_secret_hash VARCHAR(256),
    lti_client_id VARCHAR(256),
    lti_secret_hash VARCHAR(256),
    active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_moodle_instances_active ON moodle_instances (active);

-- ============================================================
-- MOODLE COURSES
-- ============================================================

CREATE TABLE moodle_courses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    instance_id UUID NOT NULL REFERENCES moodle_instances(id) ON DELETE CASCADE,
    moodle_course_id BIGINT NOT NULL,
    name VARCHAR(256) NOT NULL,
    grade_level SMALLINT,
    status moodle_sync_status NOT NULL DEFAULT 'pending',
    last_sync_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (instance_id, moodle_course_id)
);

CREATE INDEX idx_moodle_courses_instance ON moodle_courses (instance_id);
CREATE INDEX idx_moodle_courses_status ON moodle_courses (status);

-- ============================================================
-- MOODLE SYNC STATE
-- ============================================================

CREATE TABLE moodle_sync_state (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    course_id UUID NOT NULL REFERENCES moodle_courses(id) ON DELETE CASCADE,
    last_sync TIMESTAMPTZ,
    status moodle_sync_status NOT NULL DEFAULT 'pending',
    concepts_pulled INTEGER NOT NULL DEFAULT 0,
    quizzes_pulled INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    next_sync_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_moodle_sync_course ON moodle_sync_state (course_id);
CREATE INDEX idx_moodle_sync_status ON moodle_sync_state (status);
CREATE INDEX idx_moodle_sync_next ON moodle_sync_state (next_sync_at);

-- ============================================================
-- MOODLE WEBHOOK LOGS
-- ============================================================

CREATE TABLE moodle_webhook_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    instance_id UUID REFERENCES moodle_instances(id) ON DELETE SET NULL,
    event_type VARCHAR(64) NOT NULL,
    payload JSONB DEFAULT '{}',
    signature_valid BOOLEAN NOT NULL DEFAULT true,
    processed BOOLEAN NOT NULL DEFAULT false,
    process_status VARCHAR(32),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_moodle_webhook_logs_instance ON moodle_webhook_logs (instance_id);
CREATE INDEX idx_moodle_webhook_logs_created ON moodle_webhook_logs (created_at DESC);
CREATE INDEX idx_moodle_webhook_logs_processed ON moodle_webhook_logs (processed);