"""Lightweight synchronous persistence for patch jobs."""

from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

SCHEMA_SQL = """\
CREATE TABLE IF NOT EXISTS patch_jobs (
  id TEXT PRIMARY KEY,
  created REAL NOT NULL,
  status TEXT NOT NULL,
  tier TEXT DEFAULT 'tier_free',
  request_json TEXT NOT NULL,
  result_json TEXT,
  error TEXT,
  idempotency_key TEXT,
  claimed_at REAL,
  claimed_by TEXT,
  finished_at REAL
);
CREATE UNIQUE INDEX IF NOT EXISTS ix_patch_jobs_idem
  ON patch_jobs(tier, idempotency_key)
  WHERE idempotency_key IS NOT NULL;
CREATE INDEX IF NOT EXISTS ix_patch_jobs_status_created
  ON patch_jobs(status, created);
"""


def _migrate(conn: sqlite3.Connection) -> None:
    cols = {row["name"] for row in conn.execute("PRAGMA table_info(patch_jobs)")}
    if cols and "idempotency_key" not in cols:
        conn.execute("ALTER TABLE patch_jobs ADD COLUMN idempotency_key TEXT")
    if cols and "claimed_at" not in cols:
        conn.execute("ALTER TABLE patch_jobs ADD COLUMN claimed_at REAL")
    if cols and "claimed_by" not in cols:
        conn.execute("ALTER TABLE patch_jobs ADD COLUMN claimed_by TEXT")
    if cols and "finished_at" not in cols:
        conn.execute("ALTER TABLE patch_jobs ADD COLUMN finished_at REAL")
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_patch_jobs_idem"
        " ON patch_jobs(tier, idempotency_key)"
        " WHERE idempotency_key IS NOT NULL"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS ix_patch_jobs_status_created"
        " ON patch_jobs(status, created)"
    )
    conn.commit()


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False, timeout=30.0)
    conn.row_factory = sqlite3.Row
    # WAL mode lets the worker write while the API reads concurrently. busy_timeout
    # gives the writer 5s to acquire the lock instead of failing immediately.
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.executescript(SCHEMA_SQL)
    _migrate(conn)
    return conn


def find_by_idempotency(conn: sqlite3.Connection, *, tier: str, key: str) -> sqlite3.Row | None:
    cur = conn.execute(
        "SELECT * FROM patch_jobs WHERE tier=? AND idempotency_key=? LIMIT 1",
        (tier, key),
    )
    return cur.fetchone()


def enqueue_job(
    conn: sqlite3.Connection,
    tier: str,
    body: dict,
    *,
    idempotency_key: str | None = None,
) -> tuple[str, bool]:
    """Insert or return existing row id when idempotency key collides; returns (job_id, created)."""

    if idempotency_key is not None:
        existing = find_by_idempotency(conn, tier=tier, key=idempotency_key)
        if existing is not None:
            return existing["id"], False

    job_id = str(uuid4())
    conn.execute(
        "INSERT INTO patch_jobs(id, created, status, tier, request_json, idempotency_key)"
        " VALUES(?,?,?,?,?,?)",
        (
            job_id,
            time.time(),
            "queued",
            tier,
            json.dumps(body, sort_keys=True),
            idempotency_key,
        ),
    )
    conn.commit()
    return job_id, True


def mark_done(conn: sqlite3.Connection, job_id: str, result: dict) -> None:
    conn.execute(
        "UPDATE patch_jobs SET status=?, result_json=?, finished_at=? WHERE id=?",
        ("completed", json.dumps(result, sort_keys=True), time.time(), job_id),
    )
    conn.commit()


def mark_failed(conn: sqlite3.Connection, job_id: str, err: str) -> None:
    conn.execute(
        "UPDATE patch_jobs SET status=?, error=?, finished_at=? WHERE id=?",
        ("failed", err, time.time(), job_id),
    )
    conn.commit()


def fetch_job(conn: sqlite3.Connection, job_id: str) -> sqlite3.Row | None:
    cur = conn.execute("SELECT * FROM patch_jobs WHERE id=?", (job_id,))
    return cur.fetchone()


def claim_next_queued(
    conn: sqlite3.Connection,
    *,
    worker_id: str,
) -> sqlite3.Row | None:
    """Atomically transition the oldest queued job to ``running`` and return it.

    Returns ``None`` when nothing is queued. Uses a single UPDATE with a
    ``WHERE id IN (SELECT id FROM ... ORDER BY created LIMIT 1)`` pattern so two
    workers racing for the same job will only have one win the row update.
    """

    now = time.time()
    cur = conn.execute(
        """
        UPDATE patch_jobs
           SET status='running', claimed_at=?, claimed_by=?
         WHERE id = (
             SELECT id FROM patch_jobs
              WHERE status='queued'
              ORDER BY created ASC
              LIMIT 1
         )
        """,
        (now, worker_id),
    )
    conn.commit()
    if cur.rowcount == 0:
        return None
    inner = conn.execute(
        "SELECT id FROM patch_jobs"
        " WHERE status='running' AND claimed_by=? AND claimed_at=?",
        (worker_id, now),
    ).fetchone()
    if inner is None:
        return None
    return fetch_job(conn, inner["id"])


def requeue_stale_running(conn: sqlite3.Connection, *, max_age_sec: float) -> int:
    """Move ``running`` jobs older than ``max_age_sec`` back to ``queued``.

    Returns the number of jobs re-queued. Call at worker startup to recover
    from previous crashes that left jobs in ``running`` without a live owner.
    """

    cutoff = time.time() - float(max_age_sec)
    cur = conn.execute(
        """
        UPDATE patch_jobs
           SET status='queued', claimed_at=NULL, claimed_by=NULL
         WHERE status='running'
           AND (claimed_at IS NULL OR claimed_at < ?)
        """,
        (cutoff,),
    )
    conn.commit()
    return int(cur.rowcount)


def queue_depth(conn: sqlite3.Connection) -> dict[str, int]:
    """Return ``{queued: int, running: int, completed: int, failed: int}``."""

    rows = conn.execute(
        "SELECT status, COUNT(*) AS n FROM patch_jobs GROUP BY status"
    ).fetchall()
    out = {"queued": 0, "running": 0, "completed": 0, "failed": 0}
    for r in rows:
        out[str(r["status"])] = int(r["n"])
    return out


def artifact_dir(storage_root: Path | str, job_id: str) -> Path:
    p = Path(storage_root) / job_id
    p.mkdir(parents=True, exist_ok=True)
    return p
