.PHONY: env check-env dev up logs

ENV_FILE := .env
ENV_EXAMPLE := .env.example

env:
	@if [ ! -f $(ENV_FILE) ]; then \
		cp $(ENV_EXAMPLE) $(ENV_FILE); \
		echo "Created $(ENV_FILE) from $(ENV_EXAMPLE). Please fill in required values."; \
	else \
		echo "$(ENV_FILE) already exists. Skipping."; \
	fi

check-env:
	python3 scripts/check_env.py

dev:
	uvicorn app.server:app --reload --port $${APP_PORT:-8000}

up:
	docker compose up -d --build

logs:
	docker compose logs -f app

