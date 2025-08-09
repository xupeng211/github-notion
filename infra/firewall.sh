#!/usr/bin/env bash
set -euo pipefail

sudo ufw allow 22/tcp || true
sudo ufw allow 443/tcp || true
sudo ufw deny 8000/tcp || true

sudo ufw enable || true
sudo ufw status verbose

