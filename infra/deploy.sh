#!/usr/bin/env bash
set -euo pipefail

REGISTRY_HOST=${REGISTRY_HOST:-}
IMAGE_REF=${IMAGE_REF:-${REGISTRY_HOST}:latest}
AWS_REGION=${AWS_REGION:-}

if ! command -v docker >/dev/null 2>&1; then
  echo "docker not installed" >&2
  exit 1
fi

mkdir -p /opt/gitee-notion-sync
cd /opt/gitee-notion-sync

# ECR 登录（如果 REGISTRY_HOST 指向 ECR）
if echo "$REGISTRY_HOST" | grep -q ".amazonaws.com"; then
  if command -v aws >/dev/null 2>&1; then
    aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "$(echo "$REGISTRY_HOST" | awk -F/ '{print $1}')"
  else
    echo "aws cli not found; please install if using ECR" >&2
  fi
fi

set +e
PREV_IMAGE=$(docker compose -f docker-compose.prod.yml images --quiet app 2>/dev/null)
set -e

export IMAGE_REF

# Pull and up
sed -i "s|image: .*|image: ${IMAGE_REF}|" docker-compose.prod.yml

docker compose -f docker-compose.prod.yml pull || true
if docker compose -f docker-compose.prod.yml up -d; then
  echo "Deploy success"
else
  echo "Deploy failed, rollback..."
  if [ -n "${PREV_IMAGE:-}" ]; then
    IMAGE_REF="$PREV_IMAGE" ./infra/rollback.sh
  else
    ./infra/rollback.sh || true
  fi
fi

# Health check
for i in {1..20}; do
  if curl -fsS http://127.0.0.1:8000/health >/dev/null; then
    echo "Health OK"
    exit 0
  fi
  sleep 2
  echo "Waiting health..."
done

echo "Health check failed"
exit 1
