FROM python:3.14-alpine AS builder

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
WORKDIR /app

# Alpine's default CDN is filtered on this network; use the Liara mirror for apk.
ARG APK_MIRROR=https://linux-mirror.liara.ir/repository/alpine
RUN sed -i "s|https\?://dl-cdn.alpinelinux.org/alpine|${APK_MIRROR}|g" /etc/apk/repositories \
    && apk add --no-cache build-base linux-headers libffi-dev openssl-dev cargo rust
COPY --from=ghcr.io/astral-sh/uv:0.9.5 /uv /uvx /bin/
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

FROM python:3.14-alpine AS runtime
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/backend/src \
    DJANGO_SETTINGS_MODULE=config.settings.prod
WORKDIR /app

# Alpine's default CDN is filtered on this network; use the Liara mirror for apk.
ARG APK_MIRROR=https://linux-mirror.liara.ir/repository/alpine
RUN sed -i "s|https\?://dl-cdn.alpinelinux.org/alpine|${APK_MIRROR}|g" /etc/apk/repositories \
    && apk add --no-cache libstdc++ libffi openssl chromium chromium-chromedriver
COPY --from=builder /app/.venv /app/.venv
COPY backend/src /app/backend/src
COPY --chmod=755 <<'EOF' /usr/local/bin/entrypoint
#!/bin/sh
set -eu
python /app/backend/src/manage.py migrate --noinput
exec gunicorn config.wsgi:application --chdir /app/backend/src --bind 0.0.0.0:8000 --workers "${GUNICORN_WORKERS:-3}" --timeout "${GUNICORN_TIMEOUT:-120}"
EOF

EXPOSE 8000
CMD ["/usr/local/bin/entrypoint"]
