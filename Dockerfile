# ============================================================
# Polelo — Multi-stage Dockerfile
# ============================================================

# --- Stage 1: Build dependencies ---
FROM python:3.12-slim AS builder

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir --prefix=/install -r requirements.txt

# --- Stage 2: Runtime ---
FROM python:3.12-slim AS runtime

# System deps for Playwright Chromium
RUN apt-get update && apt-get install -y --no-install-recommends \
    libnss3 libatk-bridge2.0-0 libdrm2 libxcomposite1 \
    libxdamage1 libxrandr2 libgbm1 libpango-1.0-0 \
    libcairo2 libasound2 libxshmfence1 fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages
COPY --from=builder /install /usr/local

# Install Playwright browsers
RUN playwright install chromium

WORKDIR /app

# Copy application code
COPY src/ ./src/
COPY db/ ./db/
COPY php/ ./php/
COPY deploy/ ./deploy/
COPY .env.example ./

# Create screenshot directory and gotcha permissions
RUN mkdir -p /app/screenshots

# Non-root user
RUN groupadd -r polelo && useradd -r -g polelo -d /app polelo \
    && chown -R polelo:polelo /app
USER polelo

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health').raise_for_status()"

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
