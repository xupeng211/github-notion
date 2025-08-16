#!/usr/bin/env bash
set -euo pipefail

: "${MINIO_ENDPOINT:=http://minio:9000}"
: "${MINIO_ROOT_USER:=minioadmin}"
: "${MINIO_ROOT_PASSWORD:=minioadmin}"
: "${MINIO_BUCKET:=dev-bucket}"

# wait for minio
for i in $(seq 1 60); do
  if curl -fsS "$MINIO_ENDPOINT/minio/health/ready" >/dev/null; then
    break
  fi
  sleep 2
  if [ $i -eq 60 ]; then echo "MinIO not ready" >&2; exit 1; fi
done

pip install --quiet minio
python - <<'PY'
import os
from minio import Minio
endpoint = os.getenv('MINIO_ENDPOINT','http://minio:9000').replace('http://','').replace('https://','')
client = Minio(endpoint, access_key=os.getenv('MINIO_ROOT_USER','minioadmin'), secret_key=os.getenv('MINIO_ROOT_PASSWORD','minioadmin'), secure=False)
bucket = os.getenv('MINIO_BUCKET','dev-bucket')
if not client.bucket_exists(bucket):
    client.make_bucket(bucket)
    print(f"Created bucket: {bucket}")
else:
    print(f"Bucket exists: {bucket}")
PY
