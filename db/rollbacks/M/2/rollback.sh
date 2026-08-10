#!/usr/bin/env bash
# Rollback migration 002_moodle_schema.sql
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Rolling back 002_moodle_schema.sql..."

psql "${DATABASE_URL}" <<'SQL'
DROP TABLE IF EXISTS moodle_webhook_logs CASCADE;
DROP TABLE IF EXISTS moodle_sync_state CASCADE;
DROP TABLE IF EXISTS moodle_courses CASCADE;
DROP TABLE IF EXISTS moodle_instances CASCADE;

DROP TYPE IF EXISTS moodle_sync_status CASCADE;
SQL

echo "Rollback complete."