#!/usr/bin/env python3
import os
import requests

TOKEN = os.getenv("DEADLETTER_REPLAY_TOKEN", "")
PORT = os.getenv("APP_PORT", "8000")
URL = f"http://127.0.0.1:{PORT}/replay-deadletters"


def main() -> int:
    if not TOKEN:
        print("DEADLETTER_REPLAY_TOKEN not set; abort")
        return 1
    resp = requests.post(URL, headers={"Authorization": f"Bearer {TOKEN}"})
    print(resp.status_code, resp.text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

