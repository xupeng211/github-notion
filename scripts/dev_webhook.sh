#!/usr/bin/env bash
set -euo pipefail

# Load .env if exists
if [ -f .env ]; then
  set -a
  source .env
  set +a
fi

SECRET=${GITEE_WEBHOOK_SECRET:-}
if [ -z "$SECRET" ]; then
  echo "GITEE_WEBHOOK_SECRET is empty. Fill it in .env"
  exit 1
fi

EVENT_PAYLOAD='{
  "action": "open",
  "issue": {
    "number": 12345,
    "title": "Demo issue from dev_webhook.sh"
  }
}'

SIG=$(printf "%s" "$EVENT_PAYLOAD" | openssl dgst -sha256 -hmac "$SECRET" | awk '{print $2}')

curl -sS -X POST \
  -H "Content-Type: application/json" \
  -H "X-Gitee-Event: Issue Hook" \
  -H "X-Gitee-Token: $SIG" \
  --data "$EVENT_PAYLOAD" \
  http://localhost:${APP_PORT:-8000}/gitee_webhook | jq .
