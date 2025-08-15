# Multi-stage build
FROM python:3.11-slim AS builder
WORKDIR /app

# Install build dependencies for cryptography and other packages
# Optimize for GitHub Actions build speed and reliability
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    build-essential \
    pkg-config \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

COPY requirements.txt .
# Upgrade pip and setuptools for better compatibility
RUN pip install --user --upgrade pip setuptools wheel
# Install Python packages with optimized settings
RUN pip install --user --no-cache-dir --prefer-binary -r requirements.txt

FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
RUN useradd -m appuser
COPY --from=builder --chown=appuser:appuser /root/.local /home/appuser/.local
ENV PATH="/home/appuser/.local/bin:$PATH"
COPY --chown=appuser:appuser . .
RUN mkdir -p /app/data && chown -R appuser:appuser /app
USER appuser
ENV APP_PORT=8000
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "app.server:app", "--host", "0.0.0.0", "--port", "8000"]
