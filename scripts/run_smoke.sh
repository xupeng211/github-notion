#!/usr/bin/env bash
set -euo pipefail

# Smoke test the service locally or against a running container on localhost.
# Steps:
#  1) Health and metrics check
#  2) Send a signed webhook with a random issue id

ENV_FILE=".env"
BASE_URL="http://127.0.0.1:8000"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --env-file) ENV_FILE="$2"; shift 2 ;;
    --base-url) BASE_URL="$2"; shift 2 ;;
    *) echo "Unknown arg: $1" >&2; exit 1 ;;
  esac
done

if [[ -f "$ENV_FILE" ]]; then
  # shellcheck disable=SC1090
  set -a; . "$ENV_FILE"; set +a
fi

echo "[1/3] Health check..." >&2
curl -fsS "$BASE_URL/health" >/dev/null
echo "OK" >&2

echo "[2/3] Metrics check..." >&2
code=$(curl -sS -o /dev/null -w "%{http_code}" "$BASE_URL/metrics/")
if [[ "$code" != "200" ]]; then
  echo "Metrics endpoint failed with code $code" >&2; exit 3
fi
echo "OK" >&2

echo "[3/3] Webhook demo..." >&2
"$(dirname "$0")/send_webhook.sh" --env-file "$ENV_FILE" --url "$BASE_URL/gitee_webhook"
echo "Done" >&2


