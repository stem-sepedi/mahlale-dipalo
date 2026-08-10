#!/bin/bash
# Polelo — Raspberry Pi ARM64 Deployment Guide
# Run this script on a fresh Raspberry Pi OS (Bookworm) to set up Polelo.
set -euo pipefail

echo "=== Polelo RPi Deployment ==="

# System deps
sudo apt-get update && sudo apt-get install -y \
    python3 python3-pip python3-venv \
    postgresql postgresql-client \
    nodejs npm \
    chromium-browser \
    libnss3 libatk-bridge2.0-0 libdrm2 libxcomposite1 libxdamage1 libxrandr2

# PostgreSQL
sudo systemctl enable postgresql
sudo -u postgres createdb polelo || true
sudo -u postgres psql -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;" polelo || true
sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'polelo';" || true

# Python venv
python3 -m venv /opt/polelo/venv
source /opt/polelo/venv/bin/activate
pip install --upgrade pip
pip install -r /opt/polelo/requirements.txt 2>/dev/null || pip install \
    fastapi uvicorn pydantic python-jose passlib asyncpg httpx \
    paho-mqtt playwright python-multipart

# Playwright browsers
playwright install chromium

# App setup
mkdir -p /opt/polelo/screenshots
cp -r /home/pi/polelo/* /opt/polelo/ 2>/dev/null || true

# Systemd service
cat > /etc/systemd/system/polelo.service << 'EOF'
[Unit]
Description=Polelo STEM Translation API
After=postgresql.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/polelo
ExecStart=/opt/polelo/venv/bin/uvicorn src.api.main:app --host 0.0.0.0 --port 8000
Restart=always
Environment=DATABASE_URL=postgresql://postgres:polelo@localhost/polelo
Environment=OLLAMA_BASE_URL=http://localhost:11434

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable polelo
sudo systemctl start polelo

echo "=== Polelo deployed at http://$(hostname -I | awk '{print $1}'):8000 ==="
echo "=== Docs at http://$(hostname -I | awk '{print $1}'):8000/docs ==="
