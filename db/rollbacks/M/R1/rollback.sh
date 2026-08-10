#!/usr/bin/env bash
# Rollback migration 004_grade_catalog.sql
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Rolling back 004_grade_catalog.sql..."

psql "${DATABASE_URL}" <<'SQL'
DROP TABLE IF EXISTS grade_catalog CASCADE;
SQL

echo "Rollback complete."
