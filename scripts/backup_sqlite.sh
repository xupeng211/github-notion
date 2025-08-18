#!/usr/bin/env bash
set -euo pipefail

DB_PATH=${DB_PATH:-data/sync.db}
BACKUP_DIR=${BACKUP_DIR:-backups}
RETENTION_DAYS=${RETENTION_DAYS:-7}

mkdir -p "${BACKUP_DIR}"
TS=$(date +%Y%m%d-%H%M%S)
OUT="${BACKUP_DIR}/sync-${TS}.db.gz"

if [ ! -f "${DB_PATH}" ]; then
  echo "DB not found: ${DB_PATH}" >&2
  exit 0
fi

gzip -c "${DB_PATH}" > "${OUT}"
echo "Backup created: ${OUT}"

# retention
find "${BACKUP_DIR}" -name 'sync-*.db.gz' -mtime +${RETENTION_DAYS} -delete || true

# optional OSS/S3
if [ -n "${OSS_BUCKET:-}" ]; then
  if command -v ossutil64 >/dev/null 2>&1; then
    echo "Uploading to OSS..."
    ossutil64 cp -f "${OUT}" "oss://${OSS_BUCKET}/sqlite/" || true
  elif command -v aws >/dev/null 2>&1; then
    echo "Uploading to S3..."
    aws s3 cp "${OUT}" "s3://${OSS_BUCKET}/sqlite/" || true
  else
    echo "No ossutil64/aws cli installed, skip upload"
  fi
fi
