# Continuous Delivery Plan (Auto Build -> Push -> Deploy -> Rollback)

This repository uses a two-pipeline strategy:

- CI: .github/workflows/ci.yml (quality checks, tests, docker build, container smoke test)
- CD: .github/workflows/cd.yml (main branch: build+push to GHCR, deploy to server, health-check, auto-rollback to :stable)

## Required GitHub Secrets

For cd.yml:
- PROD_HOST: SSH host of production server (IP or domain)
- PROD_USER: SSH username (e.g., ubuntu)
- PROD_SSH_KEY: PEM private key content
- GITEE_WEBHOOK_SECRET: runtime secret
- GITHUB_WEBHOOK_SECRET: runtime secret
- DEADLETTER_REPLAY_TOKEN: runtime admin token
- (Optional) NOTION_TOKEN, NOTION_DATABASE_ID

## Server Requirements
- Docker installed (script will auto-install if missing)
- Docker Compose v2 (preferred) or docker-compose; script falls back to docker-compose

## Deploy Flow (cd.yml)
1. Build and push image to GHCR with tags: latest, stable, sha-<commit>
2. SSH to server, login GHCR, update .env, bring up compose
3. Health check /health up to 60s
4. If fail, rollback to :stable and re-check

## Local Pre-flight
- scripts/ci_local.sh to lint, minimal tests, and docker build
- test-docker-build.sh to build and smoke test locally

## Compose Files
- Development: docker-compose.yml
- Production: docker-compose.production.yml
