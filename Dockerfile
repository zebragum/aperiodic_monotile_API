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
COPY scripts /app/scripts
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

COPY --chown=spectre:spectre <<'EOF' /app/entrypoint.sh
#!/bin/sh
set -eu

bootstrap_atlas() {
  if [ "${SPECTRE_PATCH_BOOTSTRAP_ATLAS:-false}" = "true" ]; then
    python /app/scripts/bootstrap_atlas.py
  fi
}

run_api() {
  UVICORN_LOG_LEVEL="$(printf '%s' "${SPECTRE_PATCH_LOG_LEVEL:-info}" | tr '[:upper:]' '[:lower:]')"
  exec uvicorn spectre_patch.api.main:app \
    --host 0.0.0.0 \
    --port "${SPECTRE_PATCH_API_PORT:-8000}" \
    --workers "${UVICORN_WORKERS:-1}" \
    --proxy-headers \
    --forwarded-allow-ips '*' \
    --log-level "$UVICORN_LOG_LEVEL"
}

case "${1:-api}" in
  api)
    bootstrap_atlas
    run_api
    ;;
  worker)
    exec spectre-patch-worker
    ;;
  api-worker)
    bootstrap_atlas
    WORKER_COUNT="${SPECTRE_PATCH_WORKER_COUNT:-1}"
    echo "[entrypoint] launching ${WORKER_COUNT} worker supervisor(s) at $(date -u +%FT%TZ)"
    # Worker auto-respawn: a single bad job should not take the API offline.
    # Render restarts the container if the API exits, but workers are child
    # processes; keep them alive and let operators raise WORKER_COUNT for spikes.
    worker_pids=""
    i=1
    while [ "$i" -le "$WORKER_COUNT" ] 2>/dev/null; do
      (
        while true; do
          rc=0
          echo "[worker-supervisor-$i] starting spectre-patch-worker at $(date -u +%FT%TZ)"
          SPECTRE_PATCH_WORKER_ID="${SPECTRE_PATCH_WORKER_ID:-worker}-$i" spectre-patch-worker 2>&1 || rc=$?
          echo "[worker-supervisor-$i] spectre-patch-worker exited rc=${rc}; respawning in 5s" 1>&2
          sleep 5
        done
      ) &
      worker_pids="${worker_pids} $!"
      i=$((i + 1))
    done
    UVICORN_LOG_LEVEL="$(printf '%s' "${SPECTRE_PATCH_LOG_LEVEL:-info}" | tr '[:upper:]' '[:lower:]')"
    uvicorn spectre_patch.api.main:app \
      --host 0.0.0.0 \
      --port "${SPECTRE_PATCH_API_PORT:-8000}" \
      --workers "${UVICORN_WORKERS:-1}" \
      --proxy-headers \
      --forwarded-allow-ips '*' \
      --log-level "$UVICORN_LOG_LEVEL" &
    api_pid="$!"

    GC_INTERVAL_SEC="${SPECTRE_PATCH_GC_INTERVAL_SEC:-21600}"
    GC_OLDER_THAN_HOURS="${SPECTRE_PATCH_GC_OLDER_THAN_HOURS:-24}"
    if [ "${GC_INTERVAL_SEC}" -gt 0 ] 2>/dev/null; then
      (
        # First pass sleeps so we don't double-up at boot if a deploy restarts
        # the container near the previous GC window. After that, run every
        # SPECTRE_PATCH_GC_INTERVAL_SEC seconds. Failures are non-fatal so a
        # transient disk error never takes down API or worker.
        sleep "${SPECTRE_PATCH_GC_FIRST_DELAY_SEC:-300}"
        while true; do
          spectre-patch-gc --older-than-hours "${GC_OLDER_THAN_HOURS}" || true
          sleep "${GC_INTERVAL_SEC}"
        done
      ) &
      gc_pid="$!"
    else
      gc_pid=""
    fi

    terminate() {
      kill "$api_pid" $worker_pids ${gc_pid:-} 2>/dev/null || true
      wait "$api_pid" $worker_pids ${gc_pid:-} 2>/dev/null || true
    }
    trap 'terminate; exit 0' INT TERM

    # We monitor the API process specifically: if the worker supervisor dies
    # (e.g., signal during shutdown) we still want to keep serving. Render
    # restarts the container if and only if Uvicorn exits.
    while kill -0 "$api_pid" 2>/dev/null; do
      sleep 2
    done

    terminate
    exit 1
    ;;
  *)
    exec "$@"
    ;;
esac
EOF
RUN chmod +x /app/entrypoint.sh

# tini reaps zombies cleanly when uvicorn or the worker get SIGTERM'd.
ENTRYPOINT ["/usr/bin/tini", "--", "/app/entrypoint.sh"]
CMD ["api"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -fsS "http://127.0.0.1:${SPECTRE_PATCH_API_PORT:-8000}/healthz" >/dev/null || exit 1
