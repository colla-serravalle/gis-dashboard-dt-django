FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_CACHE_DIR=/tmp/uv-cache

# Install uv from official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# System deps: psycopg build tools + SSL for truststore
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libpq-dev \
        gcc \
        libssl-dev \
        ca-certificates \
        libcairo2-dev \
        pkg-config \
        python3-dev \
        libgirepository1.0-dev && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Non-root user
RUN groupadd --gid 1000 reports_user && \
    useradd --uid 1000 --gid 1000 --no-create-home reports_user

WORKDIR /app

# ── Dependency layer (cached unless pyproject.toml/uv.lock change) ──
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# ── Application code ──
COPY . .
RUN uv sync --frozen --no-dev

COPY docker/app/gunicorn.conf.py /etc/gunicorn/gunicorn.conf.py

# Log dir must exist before Django initialises logging (collectstatic triggers it)
RUN mkdir -p /app/logs /app/staticfiles

# collectstatic requires SECRET_KEY; dummy value is safe — only used at build time
ARG SECRET_KEY=build-time-dummy-not-used-in-production
RUN SECRET_KEY=${SECRET_KEY} uv run python manage.py collectstatic --noinput

RUN chown -R reports_user:reports_user /app/logs /app/staticfiles && \
    mkdir -p /tmp/uv-cache && chown -R reports_user:reports_user /tmp/uv-cache && \
    chmod 1777 /tmp

USER reports_user
EXPOSE 8000

CMD ["uv", "run", "gunicorn", "--config", "/etc/gunicorn/gunicorn.conf.py", "config.wsgi:application"]
