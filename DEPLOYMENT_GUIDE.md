# DEPLOYMENT_GUIDE.md

STEM Sepedi Translation Layer - Deployment Guide

Version: 0.1

---

## Quick Start

All services run via a single `docker compose up` command. No external dependencies beyond Docker.

```bash
git clone https://github.com/stem-sepedi/mahlale-dipalo.git && cd polelo
cp .env.example .env   # fill in secrets
docker compose up -d
```

---

## Services

| Service | Image | Port | Purpose |
|---------|-------|------|---------|
| web-api | python:3.12-slim (built from Dockerfile) | 8000 | FastAPI backend |
| database | timescale/timescaledb-ha:pg16 | 5432 | TimescaleDB (PostgreSQL extension) |
| mqtt-broker | eclipse-mosquitto:2 | 1883 | Message queue for workers |
| ollama | ollama/ollama:latest | 11434 | Local LLM inference server |
| minio | minio/minio:latest | 9000, 9001 | S3-compatible object storage |
| php-app | php:8.2-fpm-nginx | 80 | PHP + Nginx frontend |
| worker | python:3.12-slim (built from Dockerfile) | n/a | MQTT consumer pool |

---

## Environment Variables (.env)

```bash
# Auth
API_SECRET_KEY=<openssl rand -hex 32>
JWT_EXPIRY=86400
REFRESH_EXPIRY=2592000

# Database
POSTGRES_USER=polelo_admin
POSTGRES_PASSWORD=<openssl rand -hex 32>
POSTGRES_DB=polelo_db
DATABASE_URL=postgresql+asyncpg://polelo_admin:${POSTGRES_PASSWORD}@database:5432/polelo_db

# MinIO
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=<openssl rand -hex 32>

# Ollama
OLLAMA_MODEL=qwen3:latest
OLLAMA_HOST=ollama:11434

# MQTT
MQTT_BROKER_HOST=mqtt-broker
MQTT_BROKER_PORT=1883

# App
APP_ENV=development   # production strips stack traces
```

Never commit `.env`. It is in `.gitignore`.

---

## x86_64 Deployment (Standard)

### Step 1: Install prerequisites

```bash
# Ubuntu/Debian
apt-get update && apt-get install -y software-properties-common curl gnupg
curl -fsSL https://get.docker.com | sh
usermod -aG docker $USER
newgrp docker
docker compose --version   # should be >= 2.20
```

### Step 2: Generate secrets

```bash
openssl rand -hex 32 > .env.POSTGRES_PASSWORD
openssl rand -hex 32 > .env.MINIO_ROOT_PASSWORD  
openssl rand -hex 32 > .env.API_SECRET_KEY
cat .env.* >> .env   # append to main env file (remove .POSTGRES_PASSWORD etc from filenames first)
```

### Step 3: Pull Ollama model (internet required once)

```bash
docker compose run --rm ollama ollama pull qwen3:latest
```

### Step 4: Start stack

```bash
docker compose up -d
```

### Step 5: Verify

```bash
curl http://localhost:8000/health   # expect {"status":"ok","services":{"database":"connected",...}}
docker compose ps                   # all services should show "Up"
```

### Step 6: Seed admin user

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"changeme-admin","role":"admin"}'
# Login with these credentials to get JWT token
```

### Step 7: Run migrations

```bash
docker compose exec web-api python -m alembic upgrade head
```

---

## ARM64 Deployment (Raspberry Pi)

Same as x86_64 above with two changes:

1. Use smaller LLM model to fit RPi memory constraints:

```bash
ollama pull llama3.2:latest   # ~2GB vs qwen3 which may be larger
```

2. Minimum hardware: Raspberry Pi 4 (4GB RAM minimum). Tested on Pi 4 with 8GB. Pi 3 will struggle with Ollama + PostgreSQL in same container host.

---

## LAN Deployment (Offline)

After initial setup (which requires internet for first pull), the stack works fully offline. All dependencies are local Docker images. No cloud APIs, no external services.

For LAN exposure:

```yaml
# docker-compose.yml snippet - expose ports to network
services:
  web-api:
    ports: ["0.0.0.0:8000:8000"]   # API available to other LAN machines
  php-app:
    ports: ["0.0.0.0:80:80"]         # Frontend on port 80
```

Access from any LAN device: `http://<host-ip>/` for PHP UI, `http://<host-ip>:8000/docs` for OpenAPI spec (Swagger UI).

---

## HTTPS / TLS (Production)

For externally-facing deployments, terminate TLS at Nginx in php-app or add a reverse proxy (Traefik/caddy) before the stack. The backend FastAPI should use `proxy_read_header X-Forwarded-Proto` to know if requests came over HTTPS.

```yaml
services:
  traefik:
    image: traefik:v3.0
    ports: ["443:443"]
    command: ["--api.insecure=true", "--providers.docker=true"]
  # php-app and web-api no longer expose ports
  # Traefik routes traffic to them via Docker labels
```

---

## Maintenance

### Health check all services

```bash
docker compose ps
curl http://localhost:8000/health
```

### Restart stack (after code changes)

```bash
docker compose down && docker compose up -d
```

### View logs

```bash
docker compose logs -f web-api   # follow API logs
docker compose logs database     # one-shot DB logs
```

### Backup database

```bash
docker compose exec database pg_dump -U polelo_admin polelo_db > backup-$(date +%F).sql
```

### Restore from backup

```bash
docker compose exec -T database psql -U polelo_admin polelo_db < backup-2026-01-01.sql
```

---

## Dockerfile Reference (web-api)

The web-api service builds from this Dockerfile:

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml poetry.lock ./
RUN pip install --no-cache-dir poetry && poetry install --no-interaction --only main
COPY . .
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `database is not ready yet` on startup | Wait 30s, then retry: `docker compose exec web-api pg_isready -h database` |
| Ollama returns empty translations | Verify model was pulled: `curl http://ollama:11434/api/tags` |
| MQTT connection refused | Ensure mqtt-broker is up: `docker compose ps mqtt-broker` |
| MinIO bucket not found on deploy | Run init script: `mc mb --ignore-existing minio/polelo-snapshots` |
| PostgreSQL authentication failed | Verify POSTGRES_PASSWORD matches .env value used in DATABASE_URL |
