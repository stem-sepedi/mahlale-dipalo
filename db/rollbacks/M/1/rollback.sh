#!/usr/bin/env bash
# Rollback migration 001_initial_schema.sql
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
MIGRATION_FILE="${SCRIPT_DIR}/../migrations/001_initial_schema.sql"

echo "Rolling back 001_initial_schema.sql..."

psql "${DATABASE_URL}" <<'SQL'
DROP TABLE IF EXISTS mqtt_jobs CASCADE;
DROP TABLE IF EXISTS version_snapshots CASCADE;
DROP TABLE IF EXISTS reviews CASCADE;
DROP TABLE IF EXISTS quiz_questions CASCADE;
DROP TABLE IF EXISTS explanations CASCADE;
DROP TABLE IF EXISTS translations CASCADE;
DROP TABLE IF EXISTS concepts CASCADE;
DROP TABLE IF EXISTS session_tokens CASCADE;
DROP TABLE IF EXISTS users CASCADE;

DROP TYPE IF EXISTS content_status CASCADE;
DROP TYPE IF EXISTS domain_type CASCADE;
DROP TYPE IF EXISTS user_role CASCADE;
SQL

echo "Rollback complete."
