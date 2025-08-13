# Changelog

## Unreleased
- Migrate FastAPI startup to lifespan; graceful scheduler shutdown.
- Health response unified to include status/timestamp/environment/notion_api/app_info.
- Invalid signature now returns 403.
- Optional in-process rate limiter via `RATE_LIMIT_PER_MINUTE` (default off).
- Tests: add `tests/conftest.py`, skip integration/performance unless env set.
- Scripts: `replay_deadletter.py` switched to main-guarded entry.
- Dependencies: remove Flask stack, keep FastAPI-only.
- Compose: dev uses `build` only; prod uses image in `docker-compose.prod.yml`.
- Documentation updated (`README.md`, `API.md`), add `.env.example`. 