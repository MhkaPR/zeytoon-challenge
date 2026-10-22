FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

WORKDIR /app

# psycopg[binary] and Pillow-free stack: only build tools needed are minimal.
COPY pyproject.toml uv.lock* ./
RUN pip install --no-cache-dir uv \
    && uv pip install --system --no-cache -r pyproject.toml

COPY backend/ ./backend/

WORKDIR /app/backend/src

EXPOSE 8000

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]
