#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <project-name>" >&2
  exit 1
fi

PROJECT="$1"

mkdir -p "$PROJECT" \
  "$PROJECT/apps" \
  "$PROJECT/apps/api" \
  "$PROJECT/data_pipeline" \
  "$PROJECT/models" \
  "$PROJECT/infra/deploy" \
  "$PROJECT/scripts" \
  "$PROJECT/tests" \
  "$PROJECT/docs" \
  "$PROJECT/.github/workflows" \
  "$PROJECT/.githooks"

# .editorconfig
cat >"$PROJECT/.editorconfig" <<'EOF'
root = true

[*]
charset = utf-8
end_of_line = lf
insert_final_newline = true
indent_style = space
indent_size = 4
trim_trailing_whitespace = true

[*.md]
trim_trailing_whitespace = false
EOF

# .gitignore
cat >"$PROJECT/.gitignore" <<'EOF'
# Python
__pycache__/
*.pyc
*.pyo
*.pyd
.venv/
venv/
env/
.mypy_cache/
.pytest_cache/
.ruff_cache/

# Env & secrets
.env
.env.*

# Logs & data
logs/
*.log
artifacts/
data/tmp/
.coverage
coverage.xml

# Build
build/
dist/

# OS junk
.DS_Store
Thumbs.db
EOF

# requirements.txt
cat >"$PROJECT/requirements.txt" <<'EOF'
fastapi>=0.111.0
uvicorn>=0.23.0
psycopg2-binary>=2.9.9
prefect>=2.14.0
xgboost>=2.0.0
EOF

# requirements-dev.txt
cat >"$PROJECT/requirements-dev.txt" <<'EOF'
ruff>=0.5.7
mypy>=1.10.0
pytest>=7.4.0
coverage[toml]>=7.5.0
pytest-cov>=4.1.0
pre-commit>=3.7.0
detect-secrets>=1.4.0
yamllint>=1.35.1
shellcheck-py>=0.10.0.1
httpx>=0.27.0
EOF

# Makefile
cat >"$PROJECT/Makefile" <<'EOF'
.PHONY: setup fix lint type test cov prepush ci

setup:
	pip install -r requirements.txt -r requirements-dev.txt
	pre-commit install
	pre-commit install --hook-type commit-msg --hook-type pre-push

fix:
	ruff format . || true
	ruff --fix . || true

lint:
	ruff check .

type:
	mypy . || true

test:
	pytest -q

cov:
	mkdir -p artifacts
	coverage run -m pytest -q
	coverage report -m --fail-under=60 | tee artifacts/coverage.txt

prepush: fix lint type test

ci:
	mkdir -p artifacts
	$(MAKE) lint type cov
	echo "# AI Run Log\n\n- $(shell date -u) CI completed." > artifacts/ai-runlog.md
EOF

# pyproject.toml
cat >"$PROJECT/pyproject.toml" <<'EOF'
[tool.ruff]
line-length = 100
src = ["."]
select = ["E","W","F","I","B","PL","UP","RUF"]
ignore = []

[tool.mypy]
python_version = "3.11"
ignore_missing_imports = true
warn_unused_ignores = false
warn_redundant_casts = false

[tool.pytest.ini_options]
minversion = "7.0"
addopts = "-ra -q"
testpaths = ["tests"]

[tool.coverage.run]
branch = true
source = ["."]

[tool.coverage.report]
show_missing = true
fail_under = 60
EOF

# .pre-commit-config.yaml
cat >"$PROJECT/.pre-commit-config.yaml" <<'EOF'
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.5.7
    hooks:
      - id: ruff
      - id: ruff-format
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.6.0
    hooks:
      - id: end-of-file-fixer
      - id: trailing-whitespace
      - id: check-merge-conflict
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets
  - repo: https://github.com/adrienverge/yamllint
    rev: v1.35.1
    hooks:
      - id: yamllint
  - repo: https://github.com/shellcheck-py/shellcheck-py
    rev: v0.10.0.1
    hooks:
      - id: shellcheck
EOF

# .githooks/pre-push
cat >"$PROJECT/.githooks/pre-push" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
make prepush
EOF
chmod +x "$PROJECT/.githooks/pre-push"

# .github/workflows/ci.yml
cat >"$PROJECT/.github/workflows/ci.yml" <<'EOF'
name: CI
on:
  pull_request:
  push:
    branches: [ main ]
jobs:
  ci:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install deps
        run: |
          pip install -r requirements.txt -r requirements-dev.txt
      - name: Run CI (lint+type+cov & write runlog)
        run: make ci
      - name: Upload runlog
        uses: actions/upload-artifact@v4
        with:
          name: ai-runlog
          path: artifacts/ai-runlog.md
          if-no-files-found: error
EOF

# .github/workflows/policy.yml
cat >"$PROJECT/.github/workflows/policy.yml" <<'EOF'
name: Policy
on:
  pull_request:
  push:
    branches: [ main ]
jobs:
  policy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Check forbidden files (.env)
        run: |
          if git ls-files | grep -E '(^|/)(\.env(\..*)?)$' ; then
            echo "Forbidden .env file detected" >&2; exit 1; fi
      - name: Validate .project_rules.yml
        run: |
          test -f .project_rules.yml || { echo 'missing .project_rules.yml' >&2; exit 1; }
          grep -q 'runlog_required: true' .project_rules.yml || { echo 'runlog_required not true' >&2; exit 1; }
      - name: Detect obvious secrets
        run: |
          if git grep -nE "(AWS_SECRET_ACCESS_KEY|AWS_ACCESS_KEY_ID|-----BEGIN (RSA|OPENSSH|EC) PRIVATE KEY-----|password=|SECRET_KEY=)" -- . ':!*.png' ':!*.jpg' ':!*.jpeg' ':!*.svg' ; then
            echo "Potential secrets detected" >&2; exit 1; fi
      - name: Generate runlog
        run: |
          mkdir -p artifacts
          echo "Policy check OK $(date -u)" > artifacts/ai-runlog.md
      - name: Upload runlog
        uses: actions/upload-artifact@v4
        with:
          name: ai-runlog
          path: artifacts/ai-runlog.md
EOF

# .project_rules.yml
cat >"$PROJECT/.project_rules.yml" <<'EOF'
required_commands:
  - make prepush
  - make ci
forbidden_files:
  - .env
  - .env.*
branch_policy:
  protected:
    - main
  require_reviews: 1
  ci_required: true
  runlog_required: true
EOF

# infra/deploy/healthcheck.sh
cat >"$PROJECT/infra/deploy/healthcheck.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
URL=${1:-http://localhost:8000/health}
for i in $(seq 1 20); do
  if curl -fsS "$URL" >/dev/null; then echo "healthy"; exit 0; fi
  sleep 1
done
echo "unhealthy" >&2; exit 1
EOF
chmod +x "$PROJECT/infra/deploy/healthcheck.sh"

# docs/AI_WORKFLOW.md
cat >"$PROJECT/docs/AI_WORKFLOW.md" <<'EOF'
# AI 协作 SOP

1. git pull --rebase
2. 新建特性分支 feature/<topic>
3. 本地 make fix；提交前 make prepush
4. 提交 commit 并 push 分支
5. 提交 PR，触发 CI；禁止直推 main
EOF

# pyproject pytest addopts already set; add simple app test
cat >"$PROJECT/tests/test_health.py" <<'EOF'
from fastapi.testclient import TestClient
from apps.api.main import app

def test_health():
    client = TestClient(app)
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json().get("status") == "ok"
EOF

# docs/CD_README.md
cat >"$PROJECT/docs/CD_README.md" <<'EOF'
# 发布与合并策略
- main 分支受保护，禁止直推
- CI 必须通过
- 至少 1 位 reviewer 通过后才能合并
EOF

# PULL_REQUEST_TEMPLATE.md
cat >"$PROJECT/PULL_REQUEST_TEMPLATE.md" <<'EOF'
## 变更内容

## 自检清单
- [ ] 本地 `make prepush` 通过
- [ ] 测试已更新或不需要
- [ ] DB 迁移（如有）已演练
EOF

# CODEOWNERS
cat >"$PROJECT/CODEOWNERS" <<'EOF'
* @your-account
EOF

# Minimal FastAPI app
cat >"$PROJECT/apps/api/main.py" <<'EOF'
from fastapi import FastAPI

app = FastAPI(title="Demo API")

@app.get("/health")
def health():
    return {"status": "ok"}
EOF

# Local run script
cat >"$PROJECT/scripts/run_dev.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
exec uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 --reload
EOF
chmod +x "$PROJECT/scripts/run_dev.sh"

# tests/test_smoke.py
cat >"$PROJECT/tests/test_smoke.py" <<'EOF'
def test_smoke():
    assert True
EOF

# docs/ placeholder required file created above

# scripts/ placeholder (empty for now)

# Final next steps
cat <<EOF

Next steps:

  cd $PROJECT
  git config core.hooksPath .githooks
  pip install -r requirements.txt -r requirements-dev.txt
  pre-commit install && pre-commit install --hook-type commit-msg --hook-type pre-push
  make setup
  make prepush

EOF
