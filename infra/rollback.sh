#!/usr/bin/env bash
set -euo pipefail

cd /opt/gitee-notion-sync

if [ -z "${IMAGE_REF:-}" ]; then
  echo "IMAGE_REF not set; try to use previous 'latest'"
  exit 1
fi

sed -i "s|image: .*|image: ${IMAGE_REF}|" docker-compose.prod.yml

docker compose -f docker-compose.prod.yml up -d

echo "Rollback to ${IMAGE_REF} done"
