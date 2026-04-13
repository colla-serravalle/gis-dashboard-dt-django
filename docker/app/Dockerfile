FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install uv from official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# System deps: psycopg build tools + SSL for truststore
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libpq-dev \
        gcc \
        libssl-dev \
        ca-certificates && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Non-root user
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid 1000 --no-create-home appuser

WORKDIR /app

# ── Dependency layer (cached unless pyproject.toml/uv.lock change) ──
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# ── Application code ──
COPY . .
RUN uv sync --frozen --no-dev

COPY docker/app/gunicorn.conf.py /etc/gunicorn/gunicorn.conf.py

# collectstatic requires SECRET_KEY; dummy value is safe — only used at build time
ARG SECRET_KEY=build-time-dummy-not-used-in-production
RUN SECRET_KEY=${SECRET_KEY} uv run python manage.py collectstatic --noinput

# Log dir — all three log files land here (mounted as app-logs volume)
RUN mkdir -p /app/logs && \
    chown -R appuser:appuser /app/logs /app/staticfiles

USER appuser
EXPOSE 8000

CMD ["uv", "run", "gunicorn", "--config", "/etc/gunicorn/gunicorn.conf.py", "config.wsgi:application"]
