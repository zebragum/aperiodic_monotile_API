"""Out-of-process patch worker.

Responsible for draining the SQLite job queue. The API process only writes
``queued`` rows; this worker (one or more replicas) picks them up, runs
:func:`spectre_patch.jobs.tasks.run_patch_job`, and updates terminal status.

Why a separate process? FastAPI's in-process ``BackgroundTasks`` runs jobs
inside the API event loop. If the API restarts (or autoscales / crashes /
SIGTERMs during a long render) the job is silently lost — and queueing more
work behind a CPU-bound rasteriser blocks the HTTP response loop. Running the
worker as its own process decouples those failure domains: API restarts don't
kill jobs, worker restarts don't drop HTTP traffic, and platforms with shared
storage can scale either side independently.

Run::

    spectre-patch-worker --workers 2 --atlas data/atlas

Env (same prefix as the API):

- ``SPECTRE_PATCH_DB_PATH``        — path to the SQLite job DB
- ``SPECTRE_PATCH_STORAGE_DIR``    — artifact root
- ``SPECTRE_PATCH_ATLAS_DIR``      — atlas root (optional)
- ``SPECTRE_PATCH_WORKER_ID``      — identifier recorded against claimed jobs
"""

from __future__ import annotations

import argparse
import logging
import os
import signal
import socket
import sys
import time
from contextlib import suppress
from pathlib import Path
from threading import Event

from spectre_patch.atlas import AtlasIndex
from spectre_patch.config_limits import LimitsSettings
from spectre_patch.jobs import repo as job_repo
from spectre_patch.jobs.tasks import run_patch_job


logger = logging.getLogger("spectre_patch.worker")


_SHUTDOWN = Event()


def _install_signal_handlers() -> None:
    def _handler(signum: int, _frame) -> None:  # type: ignore[no-untyped-def]
        logger.info("worker received signal=%s; draining", signum)
        _SHUTDOWN.set()

    signal.signal(signal.SIGINT, _handler)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _handler)


def _default_worker_id() -> str:
    suffix = os.environ.get("HOSTNAME") or socket.gethostname() or "host"
    return f"{suffix}#{os.getpid()}"


def run_loop(
    *,
    db_path: Path,
    storage_root: Path,
    atlas_dir: Path | None,
    base_limits: LimitsSettings,
    worker_id: str,
    poll_interval_sec: float = 0.5,
    max_idle_sleep_sec: float = 5.0,
    requeue_after_sec: float = 7200.0,
) -> int:
    """Drain the queue forever (or until SIGINT/SIGTERM).

    The polling backs off exponentially when idle (capped at ``max_idle_sleep_sec``)
    and resets to ``poll_interval_sec`` whenever a job is claimed.
    """

    conn = job_repo.connect(db_path)
    storage_root.mkdir(parents=True, exist_ok=True)

    requeued = job_repo.requeue_stale_running(conn, max_age_sec=requeue_after_sec)
    if requeued:
        logger.warning("requeued %d stale running jobs at startup", requeued)
    failed_stale = job_repo.fail_stale_running_jobs(
        conn, max_age_sec=float(base_limits.max_wall_time_sec)
    )
    if failed_stale:
        logger.warning("failed %d stale running jobs at startup (wall time)", failed_stale)

    atlas_index: AtlasIndex | None = None
    if atlas_dir is not None:
        atlas_index = AtlasIndex.load(atlas_dir)
        if atlas_index.entries:
            logger.info(
                "loaded atlas: %d cores up to inscribed_half_side=%.1f",
                len(atlas_index.entries),
                max(e.inscribed_half_side for e in atlas_index.entries),
            )
        else:
            logger.info("atlas dir %s empty — falling back to live substitution", atlas_dir)

    sleep_for = poll_interval_sec
    drained = 0
    while not _SHUTDOWN.is_set():
        try:
            row = job_repo.claim_next_queued(conn, worker_id=worker_id)
        except Exception:
            logger.exception("claim_next_queued failed; backing off")
            time.sleep(min(max_idle_sleep_sec, sleep_for * 2.0))
            continue
        if row is None:
            failed = job_repo.fail_stale_running_jobs(
                conn, max_age_sec=float(base_limits.max_wall_time_sec)
            )
            if failed:
                logger.warning("failed %d stale running jobs (wall time)", failed)
            time.sleep(sleep_for)
            sleep_for = min(max_idle_sleep_sec, sleep_for * 1.5)
            continue
        sleep_for = poll_interval_sec
        job_id = str(row["id"])
        started = time.perf_counter()
        try:
            run_patch_job(
                conn,
                job_id=job_id,
                storage_root=storage_root,
                base_limits=base_limits,
                atlas_index=atlas_index,
            )
        except Exception as e:
            logger.exception("run_patch_job %s crashed; marking failed", job_id)
            with suppress(Exception):
                job_repo.mark_failed(conn, job_id, f"worker crash: {e}")
        elapsed = time.perf_counter() - started
        drained += 1
        logger.info("job %s drained in %.2fs (total drained=%d)", job_id, elapsed, drained)

    logger.info("worker shutting down (drained=%d)", drained)
    with suppress(Exception):
        conn.close()
    return 0


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="spectre-patch-worker", description="Patch job worker")
    p.add_argument("--db-path", default=os.environ.get("SPECTRE_PATCH_DB_PATH", "data/monotile.db"))
    p.add_argument(
        "--storage-dir",
        default=os.environ.get("SPECTRE_PATCH_STORAGE_DIR", "data/jobs"),
    )
    p.add_argument(
        "--atlas",
        default=os.environ.get("SPECTRE_PATCH_ATLAS_DIR", "data/atlas"),
    )
    p.add_argument(
        "--worker-id",
        default=os.environ.get("SPECTRE_PATCH_WORKER_ID", _default_worker_id()),
    )
    p.add_argument("--poll-interval-sec", type=float, default=0.5)
    p.add_argument("--max-idle-sleep-sec", type=float, default=5.0)
    p.add_argument("--requeue-after-sec", type=float, default=7200.0)
    p.add_argument(
        "--log-level",
        default=os.environ.get("SPECTRE_PATCH_LOG_LEVEL", "INFO"),
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, str(args.log_level).upper(), logging.INFO),
        format="%(asctime)s %(levelname)-7s %(name)s %(message)s",
    )
    _install_signal_handlers()

    atlas_dir: Path | None = None
    if args.atlas:
        atlas_dir = Path(args.atlas)
        if not atlas_dir.is_dir():
            logger.warning("atlas dir %s missing; running without atlas", atlas_dir)
            atlas_dir = None

    return run_loop(
        db_path=Path(args.db_path),
        storage_root=Path(args.storage_dir),
        atlas_dir=atlas_dir,
        base_limits=LimitsSettings(),
        worker_id=str(args.worker_id),
        poll_interval_sec=float(args.poll_interval_sec),
        max_idle_sleep_sec=float(args.max_idle_sleep_sec),
        requeue_after_sec=float(args.requeue_after_sec),
    )


if __name__ == "__main__":
    sys.exit(main())
