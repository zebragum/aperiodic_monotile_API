# syntax=docker/dockerfile:1.6
# ==========================================================================
# Spectre Patch API + Worker  (single image, two entrypoints)
#
# Build:
#   docker build -t spectre-patch:latest .
#
# Run API:
#   docker run --rm -p 8000:8000 \
#     -e SPECTRE_PATCH_API_SECRET=$(openssl rand -hex 32) \
#     -e SPECTRE_PATCH_REQUIRE_API_KEY=true \
#     -e SPECTRE_PATCH_VALID_API_KEYS=$(uuidgen) \
#     -v $PWD/data:/app/data \
#     spectre-patch:latest api
#
# Run Worker (in a sibling container, sharing the same volume):
#   docker run --rm \
#     -v $PWD/data:/app/data \
#     spectre-patch:latest worker
# ==========================================================================

# -- builder ---------------------------------------------------------------
FROM python:3.12-slim AS builder
ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /build
RUN apt-get update -qq \
    && apt-get install -y --no-install-recommends \
        build-essential libgeos-dev libcairo2-dev pkg-config curl \
    && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml README.md ./
COPY src ./src
RUN python -m pip install --upgrade pip wheel \
    && python -m pip install -e ".[png,gltf,worker]"

# -- runtime ---------------------------------------------------------------
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    SPECTRE_PATCH_DB_PATH=/app/data/monotile.db \
    SPECTRE_PATCH_STORAGE_DIR=/app/data/jobs \
    SPECTRE_PATCH_ATLAS_DIR=/app/data/atlas \
    SPECTRE_PATCH_LOG_LEVEL=INFO

WORKDIR /app

RUN apt-get update -qq \
    && apt-get install -y --no-install-recommends \
        libgeos-c1v5 libcairo2 curl tini \
    && rm -rf /var/lib/apt/lists/*

# Bring over the installed environment.
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY src /app/src
COPY README.md /app/README.md

# Run as a non-root account.
RUN groupadd -r spectre && useradd -r -g spectre spectre \
    && mkdir -p /app/data/jobs /app/data/atlas \
    && chown -R spectre:spectre /app
USER spectre

# /app/data persisted by the orchestrator (compose volume / k8s PVC).
VOLUME ["/app/data"]

# 8000 is the default uvicorn port. The worker doesn't bind a socket.
EXPOSE 8000

# tini reaps zombies cleanly when uvicorn or the worker get SIGTERM'd.
ENTRYPOINT ["/usr/bin/tini", "--", "/app/entrypoint.sh"]
CMD ["api"]

COPY --chown=spectre:spectre <<'EOF' /app/entrypoint.sh
#!/bin/sh
set -eu

case "${1:-api}" in
  api)
    exec uvicorn spectre_patch.api.main:app \
      --host 0.0.0.0 \
      --port "${SPECTRE_PATCH_API_PORT:-8000}" \
      --workers "${UVICORN_WORKERS:-1}" \
      --proxy-headers \
      --forwarded-allow-ips '*' \
      --log-level "${SPECTRE_PATCH_LOG_LEVEL:-info}"
    ;;
  worker)
    exec spectre-patch-worker
    ;;
  *)
    exec "$@"
    ;;
esac
EOF
RUN chmod +x /app/entrypoint.sh

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -fsS "http://127.0.0.1:${SPECTRE_PATCH_API_PORT:-8000}/healthz" >/dev/null || exit 1
