#!/usr/bin/env bash
set -euo pipefail
if ! command -v ufw >/dev/null 2>&1; then
  sudo apt-get update -y
  sudo apt-get install -y ufw
fi
sudo ufw --force reset
sudo ufw allow 22/tcp
sudo ufw allow 443/tcp
sudo ufw deny 80/tcp || true
sudo ufw deny 8000/tcp || true
echo "y" | sudo ufw enable
sudo ufw status verbose
