"""Prune expired patch jobs and artifact directories.

Launch deployments use SQLite plus local artifact storage. This command keeps
the attached disk from filling by deleting terminal jobs after a retention
window. It never deletes queued/running jobs.
"""

from __future__ import annotations

import argparse
import logging
import os
import shutil
import sqlite3
import sys
import time
from pathlib import Path

from spectre_patch.jobs import repo as job_repo

logger = logging.getLogger("spectre_patch.gc")

TERMINAL_STATUSES = ("completed", "failed")


def _expired_jobs(conn: sqlite3.Connection, *, cutoff: float, limit: int) -> list[sqlite3.Row]:
    placeholders = ",".join("?" for _ in TERMINAL_STATUSES)
    return list(
        conn.execute(
            f"""
            SELECT id, status, created, finished_at
            FROM patch_jobs
            WHERE status IN ({placeholders})
              AND COALESCE(finished_at, created) < ?
            ORDER BY COALESCE(finished_at, created) ASC
            LIMIT ?
            """,
            (*TERMINAL_STATUSES, cutoff, int(limit)),
        )
    )


def prune_jobs(
    *,
    db_path: Path,
    storage_dir: Path,
    older_than_hours: float,
    limit: int,
    dry_run: bool,
) -> dict[str, int]:
    conn = job_repo.connect(db_path)
    cutoff = time.time() - (float(older_than_hours) * 3600.0)
    jobs = _expired_jobs(conn, cutoff=cutoff, limit=limit)

    removed_artifacts = 0
    removed_rows = 0
    storage_root = storage_dir.resolve()

    for row in jobs:
        job_id = str(row["id"])
        artifact_path = (storage_root / job_id).resolve()
        if storage_root not in artifact_path.parents:
            logger.warning("skipping unsafe artifact path for job_id=%s path=%s", job_id, artifact_path)
            continue

        if artifact_path.exists():
            logger.info("prune artifact dir job_id=%s path=%s dry_run=%s", job_id, artifact_path, dry_run)
            if not dry_run:
                shutil.rmtree(artifact_path)
            removed_artifacts += 1

        logger.info("prune job row job_id=%s status=%s dry_run=%s", job_id, row["status"], dry_run)
        if not dry_run:
            conn.execute("DELETE FROM patch_jobs WHERE id=?", (job_id,))
            removed_rows += 1

    if not dry_run:
        conn.commit()
    conn.close()

    return {
        "matched": len(jobs),
        "artifact_dirs": removed_artifacts,
        "rows": removed_rows,
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Prune old terminal jobs and generated artifacts.")
    p.add_argument("--db-path", default=os.environ.get("SPECTRE_PATCH_DB_PATH", "data/monotile.db"))
    p.add_argument(
        "--storage-dir",
        default=os.environ.get("SPECTRE_PATCH_STORAGE_DIR", "data/jobs"),
    )
    p.add_argument(
        "--older-than-hours",
        type=float,
        default=float(os.environ.get("SPECTRE_PATCH_JOB_GC_HOURS", "24")),
    )
    p.add_argument("--limit", type=int, default=1000)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--log-level", default=os.environ.get("SPECTRE_PATCH_LOG_LEVEL", "INFO"))
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, str(args.log_level).upper(), logging.INFO),
        format="%(asctime)s %(levelname)-7s %(name)s %(message)s",
    )
    result = prune_jobs(
        db_path=Path(args.db_path),
        storage_dir=Path(args.storage_dir),
        older_than_hours=float(args.older_than_hours),
        limit=int(args.limit),
        dry_run=bool(args.dry_run),
    )
    print(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
