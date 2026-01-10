#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="/backup/mariadb"
TS="$(date +'%Y%m%d_%H%M%S')"
OUT="${BACKUP_DIR}/notesdb_${TS}.sql.gz"

mkdir -p "$BACKUP_DIR"

# Uses /etc/notesapp.cnf so password is not stored in this script
mysqldump --defaults-extra-file=/etc/notesapp.cnf notesdb | gzip > "$OUT"

# Keep the last 14 days
find "$BACKUP_DIR" -type f -name "notesdb_*.sql.gz" -mtime +14 -delete
