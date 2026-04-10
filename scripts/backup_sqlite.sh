#!/usr/bin/env bash
# Aletheia Core — SQLite backup with 7-day retention.
#
# Usage: ./scripts/backup_sqlite.sh [backup_dir]
# Cron:  0 * * * * /app/scripts/backup_sqlite.sh /backups
#
# For continuous replication, use litestream instead:
#   litestream replicate data/aletheia_decisions.sqlite3 s3://bucket/aletheia/
set -euo pipefail

DB_PATH="${ALETHEIA_DB_PATH:-data/aletheia_decisions.sqlite3}"
BACKUP_DIR="${1:-/backups}"
RETENTION_DAYS="${ALETHEIA_BACKUP_RETENTION_DAYS:-7}"

if [ ! -f "$DB_PATH" ]; then
    echo "WARN: Database not found at $DB_PATH — skipping backup" >&2
    exit 0
fi

mkdir -p "$BACKUP_DIR"
TIMESTAMP=$(date -u +%Y%m%dT%H%M%SZ)
DEST="$BACKUP_DIR/aletheia_$(echo "$TIMESTAMP").sqlite3"

# Use SQLite online backup API (safe with concurrent writers)
sqlite3 "$DB_PATH" ".backup '$DEST'"

# Verify backup integrity
sqlite3 "$DEST" "PRAGMA integrity_check;" > /dev/null 2>&1 || {
    echo "ERROR: Backup integrity check failed for $DEST" >&2
    rm -f "$DEST"
    exit 1
}

# Compress
gzip "$DEST"

# Prune old backups
find "$BACKUP_DIR" -name "aletheia_*.sqlite3.gz" -mtime "+$RETENTION_DAYS" -delete

echo "OK: Backup created at ${DEST}.gz"
