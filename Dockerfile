
# =====================================
# Builder
# =====================================
FROM python:3.12-slim AS builder

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Build dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        cmake \
        ninja-build \
        libopenblas-dev \
        liblapack-dev \
        gfortran \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr-mirror.liara.ir/astral-sh/uv:0.9.5 /uv /uvx /bin/

# Install Python dependencies
COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-dev --no-install-project

# Runtime
FROM python:3.12-slim AS runtime

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/backend/src \
    DJANGO_SETTINGS_MODULE=config.settings.prod \
    PATH="/app/.venv/bin:$PATH"

# Runtime libraries
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libopenblas0 \
        liblapack3 \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment
COPY --from=builder /app/.venv /app/.venv

# Copy Django source
COPY backend/src /app/backend/src

# Entrypoint
COPY --chmod=755 <<'EOF' /usr/local/bin/entrypoint
#!/bin/sh
set -eu

python /app/backend/src/manage.py migrate --noinput

exec gunicorn config.wsgi:application \
    --chdir /app/backend/src \
    --bind 0.0.0.0:8000 \
    --workers "${GUNICORN_WORKERS:-3}" \
    --timeout "${GUNICORN_TIMEOUT:-120}"
EOF

EXPOSE 8000
CMD ["/usr/local/bin/entrypoint"]
