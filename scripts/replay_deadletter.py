#!/usr/bin/env python3
import os
import requests

TOKEN = os.getenv("DEADLETTER_REPLAY_TOKEN", "")
PORT = os.getenv("APP_PORT", "8000")
URL = f"http://127.0.0.1:{PORT}/replay-deadletters"

if not TOKEN:
    print("DEADLETTER_REPLAY_TOKEN not set; abort")
    raise SystemExit(1)

resp = requests.post(URL, headers={"Authorization": f"Bearer {TOKEN}"})
print(resp.status_code, resp.text)

