#!/usr/bin/env python3
import os
import re
import sys
from pathlib import Path

REQUIRED_VARS = [
    "NOTION_TOKEN",
    "GITEE_WEBHOOK_SECRET",
    "GITEE_TOKEN",
    "SOURCE_OF_TRUTH",
    "DB_URL",
    "APP_PORT",
    "LOG_LEVEL",
]

OPTIONAL_VARS = [
    "NOTION_DATABASE_ID",
    "DEADLETTER_REPLAY_TOKEN",
    "DEADLETTER_REPLAY_INTERVAL_MINUTES",
    "DOMAIN_NAME",
    "EMAIL_FOR_SSL",
    "OSS_ENDPOINT",
    "OSS_BUCKET",
    "OSS_ACCESS_KEY_ID",
    "OSS_ACCESS_KEY_SECRET",
]

DB_URL_REGEX = re.compile(r"^[a-zA-Z0-9_+.-]+:\/\/\/?.+")


def fail(msg: str) -> None:
    print(f"[ENV CHECK] ERROR: {msg}")


def check_required_vars() -> bool:
    ok = True
    for var in REQUIRED_VARS:
        val = os.getenv(var)
        if not val:
            fail(f"Missing required env var: {var}")
            ok = False
    return ok


def check_db_url() -> bool:
    val = os.getenv("DB_URL", "")
    if not val:
        fail("DB_URL is empty")
        return False
    if not DB_URL_REGEX.match(val):
        fail(f"DB_URL format invalid: {val}")
        print("Hint: e.g. sqlite:///data/sync.db or postgresql://user:pass@host:5432/dbname")
        return False
    return True


def check_app_port() -> bool:
    val = os.getenv("APP_PORT", "")
    try:
        port = int(val)
    except ValueError:
        fail(f"APP_PORT must be an integer: {val!r}")
        return False
    if not (1 <= port <= 65535):
        fail("APP_PORT must be between 1 and 65535")
        return False
    return True


def check_source_of_truth() -> bool:
    val = os.getenv("SOURCE_OF_TRUTH", "").lower()
    if val not in {"gitee", "notion"}:
        fail("SOURCE_OF_TRUTH must be either 'gitee' or 'notion'")
        return False
    return True


def check_domain_email() -> bool:
    domain = os.getenv("DOMAIN_NAME", "")
    email = os.getenv("EMAIL_FOR_SSL", "")
    ok = True
    if domain and "://" in domain:
        fail("DOMAIN_NAME should be a hostname like example.com (no scheme)")
        ok = False
    if email and "@" not in email:
        fail("EMAIL_FOR_SSL looks invalid (expect an email address)")
        ok = False
    return ok


def main() -> int:
    env_file = Path(".env")
    if env_file.exists():
        try:
            from dotenv import load_dotenv  # type: ignore
            load_dotenv(env_file)
        except Exception:
            pass

    ok = True
    ok &= check_required_vars()
    ok &= check_db_url()
    ok &= check_app_port()
    ok &= check_source_of_truth()
    ok &= check_domain_email()

    if ok:
        print("[ENV CHECK] OK: all checks passed")
        return 0
    else:
        print("[ENV CHECK] FAILED: see errors above")
        return 1


if __name__ == "__main__":
    sys.exit(main())
