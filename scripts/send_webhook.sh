#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   scripts/send_webhook.sh [--env-file .env] [--url http://127.0.0.1:8000/gitee_webhook] [--body-json '{"issue":{...}}']
# If --body-json not provided, a sample payload is used.

ENV_FILE=".env"
URL="http://127.0.0.1:8000/gitee_webhook"
BODY_JSON=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --env-file)
      ENV_FILE="$2"; shift 2 ;;
    --url)
      URL="$2"; shift 2 ;;
    --body-json)
      BODY_JSON="$2"; shift 2 ;;
    *)
      echo "Unknown arg: $1" >&2; exit 1 ;;
  esac
done

if [[ -f "$ENV_FILE" ]]; then
  # shellcheck disable=SC1090
  set -a; . "$ENV_FILE"; set +a
fi

if [[ -z "${GITEE_WEBHOOK_SECRET:-}" ]]; then
  echo "GITEE_WEBHOOK_SECRET is required (set in $ENV_FILE)" >&2
  exit 2
fi

if [[ -z "$BODY_JSON" ]]; then
  ISSUE_ID=$(( (RANDOM % 9000) + 1000 ))
  BODY_JSON="{\"issue\":{\"id\":$ISSUE_ID,\"number\":$ISSUE_ID,\"title\":\"demo-$ISSUE_ID\"}}"
fi

export BODY="$BODY_JSON"
SIG=$(python3 - <<'PY'
import hmac, hashlib, os
sec=os.getenv("GITEE_WEBHOOK_SECRET","changeme").encode()
body=os.environ["BODY"].encode()
print(hmac.new(sec, body, hashlib.sha256).hexdigest())
PY
)

curl -sS \
  -H "X-Gitee-Token: $SIG" \
  -H "X-Gitee-Event: Issue Hook" \
  -H "Content-Type: application/json" \
  -d "$BODY_JSON" \
  "$URL"
echo


