# ghcr.io is filtered on this network; pull uv through the Liara ghcr mirror instead.
# BuildKit cannot expand ARGs in ``COPY --from``, so the mirror is used via its own stage.
ARG UV_IMAGE=ghcr-mirror.liara.ir/astral-sh/uv:0.9.5

FROM ${UV_IMAGE} AS uv

# Debian (glibc) rather than Alpine (musl): patchright/playwright only publish
# manylinux wheels, so a musl base cannot resolve them at all.
FROM python:3.14-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_HTTP_TIMEOUT=180
WORKDIR /app

# Debian's default mirrors are filtered on this network; use the Liara mirrors.
# Only ``implicit`` lacks a wheel here, so a C/C++ toolchain is enough to build it.
ARG DEBIAN_MIRROR=https://linux-mirror.liara.ir/repository/debian
ARG DEBIAN_SECURITY_MIRROR=https://linux-mirror.liara.ir/repository/debian-security
RUN set -eu; \
    for file in /etc/apt/sources.list /etc/apt/sources.list.d/debian.sources; do \
        [ -f "${file}" ] || continue; \
        sed -i \
            -e "s|https\?://deb.debian.org/debian-security|${DEBIAN_SECURITY_MIRROR}|g" \
            -e "s|https\?://security.debian.org/debian-security|${DEBIAN_SECURITY_MIRROR}|g" \
            -e "s|https\?://deb.debian.org/debian|${DEBIAN_MIRROR}|g" \
            "${file}"; \
    done; \
    for attempt in 1 2 3 4 5; do \
        if apt-get update \
            && apt-get install -y --no-install-recommends build-essential libffi-dev libssl-dev; then \
            rm -rf /var/lib/apt/lists/*; \
            exit 0; \
        fi; \
        echo "apt-get failed (attempt ${attempt}); retrying in 10s"; \
        sleep 10; \
    done; \
    exit 1
COPY --from=uv /uv /uvx /bin/
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

FROM python:3.14-slim AS runtime
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/backend/src \
    DJANGO_SETTINGS_MODULE=config.settings.prod \
    PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/usr/bin/chromium
WORKDIR /app

# Debian's default mirrors are filtered on this network; use the Liara mirrors.
# System Chromium is installed because Playwright's own browser CDN is blocked.
ARG DEBIAN_MIRROR=https://linux-mirror.liara.ir/repository/debian
ARG DEBIAN_SECURITY_MIRROR=https://linux-mirror.liara.ir/repository/debian-security
RUN set -eu; \
    for file in /etc/apt/sources.list /etc/apt/sources.list.d/debian.sources; do \
        [ -f "${file}" ] || continue; \
        sed -i \
            -e "s|https\?://deb.debian.org/debian-security|${DEBIAN_SECURITY_MIRROR}|g" \
            -e "s|https\?://security.debian.org/debian-security|${DEBIAN_SECURITY_MIRROR}|g" \
            -e "s|https\?://deb.debian.org/debian|${DEBIAN_MIRROR}|g" \
            "${file}"; \
    done; \
    for attempt in 1 2 3 4 5; do \
        if apt-get update \
            && apt-get install -y --no-install-recommends libffi8 openssl chromium chromium-driver; then \
            rm -rf /var/lib/apt/lists/*; \
            exit 0; \
        fi; \
        echo "apt-get failed (attempt ${attempt}); retrying in 10s"; \
        sleep 10; \
    done; \
    exit 1
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
