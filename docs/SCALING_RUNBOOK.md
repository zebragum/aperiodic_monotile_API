# Scaling runbook

This service is designed to survive a launch spike by queueing jobs instead of
doing expensive geometry work in the HTTP request path.

## Current launch shape

- FastAPI accepts jobs and stores them in `patch_jobs`.
- `spectre-patch-worker` drains queued jobs from the same database.
- Jobs are tagged with a queue lane: `small`, `standard`, or `heavy`.
- The worker favors `small` jobs first, then `standard`, then `heavy`, so a few
  large GLB/STL_ZIP/OBJ_ZIP requests do not block all raster previews.
- `/v1/jobs/{job_id}` includes queue metadata with lane, position, and estimated
  wait seconds.
- `/metrics` includes total queue depth and per-lane queued/running counts.

## First lever: worker count

Increase `SPECTRE_PATCH_WORKER_COUNT` when queue time is growing and CPU/memory
headroom exists. On Render this can be changed as an environment variable.

Good starting points:

- `1`: conservative default for tiny launch traffic.
- `2`: launch default on the current single-service Render setup.
- `4`: short-term spike setting if jobs are mostly raster/SVG/CSV/JSON.

Do not blindly raise workers for large 3D traffic. More workers can make memory
pressure worse if several GLB/STL_ZIP/OBJ_ZIP jobs run at once.

## Backpressure limits

The API rejects overload before the queue becomes hostile:

- `SPECTRE_PATCH_QUEUE_MAX_ACTIVE_JOBS`: total queued/running jobs.
- `SPECTRE_PATCH_QUEUE_MAX_ACTIVE_JOBS_PER_KEY`: queued/running jobs for one key.
- `SPECTRE_PATCH_QUEUE_MAX_HEAVY_JOBS`: total large 3D/heavy jobs.
- `SPECTRE_PATCH_QUEUE_MAX_HEAVY_JOBS_PER_KEY`: large 3D/heavy jobs for one key.

Use stricter limits during a launch if a single customer or script starts
submitting many huge 3D jobs.

## When to move beyond SQLite

SQLite with WAL is acceptable for the first launch because the job queue is
simple and artifacts live on the attached disk. Move the job database to
Postgres when any of these are true:

- You need multiple Render services/containers sharing the same queue.
- Queue writes or worker claims start hitting lock contention.
- You want independent API and worker autoscaling.
- You need durable operational analytics across deploys and restarts.

Postgres is the next architecture step; object storage for artifacts should come
with it so workers do not depend on one attached disk.

## Launch-hour triage

If the queue spikes:

1. Check `/metrics` for total depth and `queue_lanes`.
2. If `small` jobs are delayed, increase `SPECTRE_PATCH_WORKER_COUNT` if CPU and
   memory allow.
3. If `heavy` jobs dominate, lower heavy per-key limits first.
4. If disk grows faster than GC can prune, shorten retention or temporarily
   restrict heavy 3D exports.
5. If HTTP remains healthy but queue wait is high, communicate the wait rather
   than redeploying risky code under pressure.
