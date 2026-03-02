#!/usr/bin/env bash
# scripts/backup.sh — Budgie SQLite backup script
#
# Usage:
#   ./scripts/backup.sh [backup_dir]
#
# Defaults:
#   backup_dir = ./data/backups
#
# Recommended cron job (daily at 02:00):
#   0 2 * * * /path/to/budgetizer/scripts/backup.sh >> /path/to/budgetizer/data/backups/backup.log 2>&1
#
# Inside Docker (add to docker-compose.yml cron service, or run manually):
#   docker exec budgie /bin/bash /app/scripts/backup.sh /app/data/backups

set -euo pipefail

# ── Configuration ─────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

DB_PATH="${DB_PATH:-${PROJECT_DIR}/data/budgie.db}"
BACKUP_DIR="${1:-${PROJECT_DIR}/data/backups}"
KEEP_DAYS="${KEEP_DAYS:-7}"

# ── Validate source database ──────────────────────────────────────────────────
if [[ ! -f "$DB_PATH" ]]; then
    echo "[ERROR] Database not found: $DB_PATH" >&2
    exit 1
fi

# ── Create backup directory ───────────────────────────────────────────────────
mkdir -p "$BACKUP_DIR"

# ── Create timestamped backup ─────────────────────────────────────────────────
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/budgie_${TIMESTAMP}.db"

cp "$DB_PATH" "$BACKUP_FILE"
echo "[OK] Backup created: $BACKUP_FILE ($(du -h "$BACKUP_FILE" | cut -f1))"

# ── Prune old backups ─────────────────────────────────────────────────────────
PRUNED=$(find "$BACKUP_DIR" -name "budgie_*.db" -mtime +"$KEEP_DAYS" -print -delete | wc -l)
if [[ "$PRUNED" -gt 0 ]]; then
    echo "[OK] Pruned $PRUNED backup(s) older than ${KEEP_DAYS} days"
fi

# ── Summary ───────────────────────────────────────────────────────────────────
TOTAL=$(find "$BACKUP_DIR" -name "budgie_*.db" | wc -l)
echo "[OK] ${TOTAL} backup(s) kept in ${BACKUP_DIR}"
