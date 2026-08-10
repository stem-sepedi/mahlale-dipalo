#!/usr/bin/env bash
# Rollback migration 003_question_triage.sql
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Rolling back 003_question_triage.sql..."

psql "${DATABASE_URL}" <<'SQL'
DROP TABLE IF EXISTS question_answers CASCADE;
DROP TABLE IF EXISTS questions CASCADE;
SQL

echo "Rollback complete."
