#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")"/.. && pwd)
cd "$ROOT_DIR"

echo "[1/4] Lint (flake8)..."
python3 -m pip install -q --upgrade pip >/dev/null 2>&1 || true
python3 -m pip install -q flake8 >/dev/null 2>&1 || true
flake8

echo "[2/4] Tests (minimal)..."
python3 -m pip install -q -r requirements.txt >/dev/null 2>&1 || true
PYTHONPATH="$ROOT_DIR" DISABLE_METRICS=1 pytest -q tests/test_mapping.py tests/test_service_flow.py

echo "[3/4] Docker build..."
docker build -f Dockerfile -t gitee-notion:ci-local .

echo "[4/4] Container smoke..."
docker rm -f ci-local-app >/dev/null 2>&1 || true
docker run -d --name ci-local-app -p 8000:8000 \
  -e APP_PORT=8000 \
  -e LOG_LEVEL=INFO \
  -e GITEE_WEBHOOK_SECRET=ci-secret \
  -e DB_URL=sqlite:///data/sync.db \
  gitee-notion:ci-local

sleep 2
curl -fsS http://127.0.0.1:8000/health >/dev/null
code=$(curl -sS -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/metrics/)
if [[ "$code" != "200" ]]; then
  echo "metrics failed $code" >&2
  docker logs --tail 200 ci-local-app || true
  docker rm -f ci-local-app >/dev/null 2>&1 || true
  exit 1
fi

BODY='{"issue":{"id":9002,"number":9002,"title":"ci-local"}}'
SIG=$(python3 - <<'PY'
import hmac,hashlib
sec=b"ci-secret"; body=b'{"issue":{"id":9002,"number":9002,"title":"ci-local"}}'
print(hmac.new(sec, body, hashlib.sha256).hexdigest())
PY
)
curl -fsS -H "X-Gitee-Token: $SIG" -H "X-Gitee-Event: Issue Hook" -H "Content-Type: application/json" -d "$BODY" http://127.0.0.1:8000/gitee_webhook >/dev/null
docker logs --tail 50 ci-local-app | tail -n 50
docker rm -f ci-local-app >/dev/null 2>&1 || true
echo "All good."


