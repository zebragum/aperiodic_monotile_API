"""Lightweight synchronous persistence for patch jobs."""

from __future__ import annotations

import json
import secrets
import hashlib
import sqlite3
import time
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
  api_key_hash TEXT,
  size_class TEXT NOT NULL DEFAULT 'standard',
  estimated_seconds REAL NOT NULL DEFAULT 20.0,
  claimed_at REAL,
  claimed_by TEXT,
  finished_at REAL
);
CREATE UNIQUE INDEX IF NOT EXISTS ix_patch_jobs_idem
  ON patch_jobs(tier, idempotency_key)
  WHERE idempotency_key IS NOT NULL;
CREATE INDEX IF NOT EXISTS ix_patch_jobs_status_created
  ON patch_jobs(status, created);
CREATE INDEX IF NOT EXISTS ix_patch_jobs_active_key
  ON patch_jobs(api_key_hash, status, created);
CREATE INDEX IF NOT EXISTS ix_patch_jobs_lane
  ON patch_jobs(status, size_class, created);
CREATE TABLE IF NOT EXISTS api_keys (
  key_hash TEXT PRIMARY KEY,
  key_prefix TEXT NOT NULL,
  tier TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active',
  created REAL NOT NULL,
  label TEXT,
  customer_email TEXT,
  stripe_customer_id TEXT,
  stripe_subscription_id TEXT,
  stripe_checkout_session_id TEXT UNIQUE,
  expires_at REAL,
  one_time_plaintext TEXT
);
CREATE INDEX IF NOT EXISTS ix_api_keys_status
  ON api_keys(status, tier);
CREATE TABLE IF NOT EXISTS leads (
  id TEXT PRIMARY KEY,
  created REAL NOT NULL,
  email TEXT NOT NULL,
  name TEXT,
  company TEXT,
  use_case TEXT,
  source TEXT,
  status TEXT NOT NULL DEFAULT 'new'
);
CREATE UNIQUE INDEX IF NOT EXISTS ix_leads_email
  ON leads(email);
CREATE INDEX IF NOT EXISTS ix_leads_created
  ON leads(created);
CREATE TABLE IF NOT EXISTS bug_reports (
  id TEXT PRIMARY KEY,
  created REAL NOT NULL,
  request_id TEXT,
  email TEXT,
  severity TEXT,
  summary TEXT NOT NULL,
  details TEXT,
  page_url TEXT,
  user_agent TEXT,
  status TEXT NOT NULL DEFAULT 'new',
  client_ip_hash TEXT
);
CREATE INDEX IF NOT EXISTS ix_bug_reports_created
  ON bug_reports(created);
CREATE INDEX IF NOT EXISTS ix_bug_reports_request
  ON bug_reports(request_id);
"""


def _add_column_if_missing(conn: sqlite3.Connection, table: str, column: str, ddl: str) -> None:
    """Add a SQLite column once, tolerating startup races between API/workers."""

    cols = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
    if column in cols:
        return
    try:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")
    except sqlite3.OperationalError as e:
        if "duplicate column name" not in str(e).lower():
            raise


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
    if cols:
        _add_column_if_missing(conn, "patch_jobs", "api_key_hash", "api_key_hash TEXT")
        _add_column_if_missing(
            conn,
            "patch_jobs",
            "size_class",
            "size_class TEXT NOT NULL DEFAULT 'standard'",
        )
        _add_column_if_missing(
            conn,
            "patch_jobs",
            "estimated_seconds",
            "estimated_seconds REAL NOT NULL DEFAULT 20.0",
        )
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_patch_jobs_idem"
        " ON patch_jobs(tier, idempotency_key)"
        " WHERE idempotency_key IS NOT NULL"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS ix_patch_jobs_status_created"
        " ON patch_jobs(status, created)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS ix_patch_jobs_active_key"
        " ON patch_jobs(api_key_hash, status, created)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS ix_patch_jobs_lane"
        " ON patch_jobs(status, size_class, created)"
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS api_keys (
          key_hash TEXT PRIMARY KEY,
          key_prefix TEXT NOT NULL,
          tier TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'active',
          created REAL NOT NULL,
          label TEXT,
          customer_email TEXT,
          stripe_customer_id TEXT,
          stripe_subscription_id TEXT,
          stripe_checkout_session_id TEXT UNIQUE,
          expires_at REAL,
          one_time_plaintext TEXT
        )
        """
    )
    api_cols = {row["name"] for row in conn.execute("PRAGMA table_info(api_keys)")}
    if api_cols and "expires_at" not in api_cols:
        conn.execute("ALTER TABLE api_keys ADD COLUMN expires_at REAL")
    if api_cols and "one_time_plaintext" not in api_cols:
        conn.execute("ALTER TABLE api_keys ADD COLUMN one_time_plaintext TEXT")
    conn.execute("CREATE INDEX IF NOT EXISTS ix_api_keys_status ON api_keys(status, tier)")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS leads (
          id TEXT PRIMARY KEY,
          created REAL NOT NULL,
          email TEXT NOT NULL,
          name TEXT,
          company TEXT,
          use_case TEXT,
          source TEXT,
          status TEXT NOT NULL DEFAULT 'new'
        )
        """
    )
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_leads_email ON leads(email)")
    conn.execute("CREATE INDEX IF NOT EXISTS ix_leads_created ON leads(created)")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS bug_reports (
          id TEXT PRIMARY KEY,
          created REAL NOT NULL,
          request_id TEXT,
          email TEXT,
          severity TEXT,
          summary TEXT NOT NULL,
          details TEXT,
          page_url TEXT,
          user_agent TEXT,
          status TEXT NOT NULL DEFAULT 'new',
          client_ip_hash TEXT
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS ix_bug_reports_created ON bug_reports(created)")
    conn.execute("CREATE INDEX IF NOT EXISTS ix_bug_reports_request ON bug_reports(request_id)")
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
    api_key_hash_value: str | None = None,
    size_class: str = "standard",
    estimated_seconds: float = 20.0,
) -> tuple[str, bool]:
    """Insert or return existing row id when idempotency key collides; returns (job_id, created)."""

    if idempotency_key is not None:
        existing = find_by_idempotency(conn, tier=tier, key=idempotency_key)
        if existing is not None:
            return existing["id"], False

    job_id = str(uuid4())
    conn.execute(
        "INSERT INTO patch_jobs("
        "id, created, status, tier, request_json, idempotency_key, api_key_hash, size_class, estimated_seconds"
        ") VALUES(?,?,?,?,?,?,?,?,?)",
        (
            job_id,
            time.time(),
            "queued",
            tier,
            json.dumps(body, sort_keys=True),
            idempotency_key,
            api_key_hash_value,
            size_class,
            float(estimated_seconds),
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
              ORDER BY
                CASE size_class
                  WHEN 'small' THEN 0
                  WHEN 'standard' THEN 1
                  WHEN 'heavy' THEN 2
                  ELSE 1
                END,
                created ASC
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


def queue_depth_by_lane(conn: sqlite3.Connection) -> dict[str, dict[str, int]]:
    """Return queue/running counts grouped by launch-spike job lane."""

    rows = conn.execute(
        """
        SELECT COALESCE(size_class, 'standard') AS size_class, status, COUNT(*) AS n
          FROM patch_jobs
         WHERE status IN ('queued', 'running')
         GROUP BY COALESCE(size_class, 'standard'), status
        """
    ).fetchall()
    out: dict[str, dict[str, int]] = {
        "small": {"queued": 0, "running": 0},
        "standard": {"queued": 0, "running": 0},
        "heavy": {"queued": 0, "running": 0},
    }
    for r in rows:
        lane = str(r["size_class"] or "standard")
        if lane not in out:
            out[lane] = {"queued": 0, "running": 0}
        out[lane][str(r["status"])] = int(r["n"])
    return out


def active_job_count(
    conn: sqlite3.Connection,
    *,
    api_key_hash_value: str | None = None,
    size_class: str | None = None,
) -> int:
    """Count queued/running jobs, optionally scoped by API key hash and lane."""

    clauses = ["status IN ('queued', 'running')"]
    params: list[object] = []
    if api_key_hash_value is not None:
        clauses.append("api_key_hash=?")
        params.append(api_key_hash_value)
    if size_class is not None:
        clauses.append("COALESCE(size_class, 'standard')=?")
        params.append(size_class)
    row = conn.execute(
        f"SELECT COUNT(*) AS n FROM patch_jobs WHERE {' AND '.join(clauses)}",
        params,
    ).fetchone()
    return int(row["n"] if row is not None else 0)


def queue_position(conn: sqlite3.Connection, job_id: str) -> dict[str, float | int | str] | None:
    """Estimate a queued job's lane-aware position and wait time.

    Small jobs intentionally jump ahead of standard/heavy jobs. This mirrors the
    worker's claim order, so the returned position is more useful than a simple
    oldest-first count during launch spikes.
    """

    row = fetch_job(conn, job_id)
    if row is None:
        return None
    status = str(row["status"])
    size_class = str(row["size_class"] or "standard")
    if status == "completed":
        return {"status": status, "size_class": size_class, "position": 0, "estimated_wait_seconds": 0.0}
    if status == "failed":
        return {"status": status, "size_class": size_class, "position": 0, "estimated_wait_seconds": 0.0}
    if status == "running":
        return {"status": status, "size_class": size_class, "position": 0, "estimated_wait_seconds": 0.0}

    lane_rank = {"small": 0, "standard": 1, "heavy": 2}.get(size_class, 1)
    queued_ahead = conn.execute(
        """
        SELECT COUNT(*) AS n, COALESCE(SUM(estimated_seconds), 0) AS seconds
          FROM patch_jobs
         WHERE status='queued'
           AND (
             CASE size_class
               WHEN 'small' THEN 0
               WHEN 'standard' THEN 1
               WHEN 'heavy' THEN 2
               ELSE 1
             END < ?
             OR (
               CASE size_class
                 WHEN 'small' THEN 0
                 WHEN 'standard' THEN 1
                 WHEN 'heavy' THEN 2
                 ELSE 1
               END = ?
               AND created < ?
             )
           )
        """,
        (lane_rank, lane_rank, float(row["created"])),
    ).fetchone()
    running = conn.execute(
        "SELECT COALESCE(SUM(estimated_seconds), 0) AS seconds FROM patch_jobs WHERE status='running'"
    ).fetchone()
    ahead_count = int(queued_ahead["n"] if queued_ahead is not None else 0)
    ahead_seconds = float(queued_ahead["seconds"] if queued_ahead is not None else 0.0)
    running_seconds = float(running["seconds"] if running is not None else 0.0)
    return {
        "status": status,
        "size_class": size_class,
        "position": ahead_count + 1,
        "estimated_wait_seconds": max(0.0, ahead_seconds + running_seconds),
    }


def artifact_dir(storage_root: Path | str, job_id: str) -> Path:
    p = Path(storage_root) / job_id
    p.mkdir(parents=True, exist_ok=True)
    return p


def hash_api_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


def generate_api_key(prefix: str = "mono_live") -> str:
    return f"{prefix}_{secrets.token_urlsafe(32)}"


def lookup_api_key(conn: sqlite3.Connection, api_key: str) -> sqlite3.Row | None:
    cur = conn.execute(
        """
        SELECT * FROM api_keys
         WHERE key_hash=?
           AND status='active'
           AND (expires_at IS NULL OR expires_at > ?)
         LIMIT 1
        """,
        (hash_api_key(api_key), time.time()),
    )
    return cur.fetchone()


def create_api_key(
    conn: sqlite3.Connection,
    *,
    tier: str,
    label: str | None = None,
    customer_email: str | None = None,
    stripe_customer_id: str | None = None,
    stripe_subscription_id: str | None = None,
    stripe_checkout_session_id: str | None = None,
    expires_at: float | None = None,
    reveal_once: bool = False,
) -> str:
    api_key = generate_api_key()
    conn.execute(
        """
        INSERT INTO api_keys(
            key_hash, key_prefix, tier, status, created, label, customer_email,
            stripe_customer_id, stripe_subscription_id, stripe_checkout_session_id,
            expires_at, one_time_plaintext
        )
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            hash_api_key(api_key),
            api_key[:18],
            tier,
            "active",
            time.time(),
            label,
            customer_email,
            stripe_customer_id,
            stripe_subscription_id,
            stripe_checkout_session_id,
            expires_at,
            api_key if reveal_once else None,
        ),
    )
    conn.commit()
    return api_key


def find_api_key_by_checkout_session(
    conn: sqlite3.Connection,
    stripe_checkout_session_id: str,
) -> sqlite3.Row | None:
    cur = conn.execute(
        "SELECT * FROM api_keys WHERE stripe_checkout_session_id=? LIMIT 1",
        (stripe_checkout_session_id,),
    )
    return cur.fetchone()


def clear_one_time_plaintext(conn: sqlite3.Connection, key_hash: str) -> None:
    conn.execute("UPDATE api_keys SET one_time_plaintext=NULL WHERE key_hash=?", (key_hash,))
    conn.commit()


def create_or_update_lead(
    conn: sqlite3.Connection,
    *,
    email: str,
    name: str | None = None,
    company: str | None = None,
    use_case: str | None = None,
    source: str | None = None,
) -> tuple[str, bool]:
    normalized_email = email.strip().lower()
    existing = conn.execute("SELECT id FROM leads WHERE email=? LIMIT 1", (normalized_email,)).fetchone()
    if existing is not None:
        conn.execute(
            """
            UPDATE leads
               SET name=COALESCE(?, name),
                   company=COALESCE(?, company),
                   use_case=COALESCE(?, use_case),
                   source=COALESCE(?, source)
             WHERE id=?
            """,
            (name, company, use_case, source, existing["id"]),
        )
        conn.commit()
        return existing["id"], False

    lead_id = str(uuid4())
    conn.execute(
        """
        INSERT INTO leads(id, created, email, name, company, use_case, source, status)
        VALUES(?,?,?,?,?,?,?,'new')
        """,
        (lead_id, time.time(), normalized_email, name, company, use_case, source),
    )
    conn.commit()
    return lead_id, True


def list_leads(conn: sqlite3.Connection, *, limit: int = 500) -> list[sqlite3.Row]:
    cur = conn.execute(
        """
        SELECT id, created, email, name, company, use_case, source, status
          FROM leads
         ORDER BY created DESC
         LIMIT ?
        """,
        (int(limit),),
    )
    return list(cur.fetchall())


def create_bug_report(
    conn: sqlite3.Connection,
    *,
    summary: str,
    details: str | None = None,
    email: str | None = None,
    request_id: str | None = None,
    severity: str | None = None,
    page_url: str | None = None,
    user_agent: str | None = None,
    client_ip_hash: str | None = None,
) -> str:
    """Persist a bug report and return its id.

    All free-form fields are size-clamped by the caller. This helper is the
    single place that touches the bug_reports table so admin export queries can
    rely on a stable column shape.
    """

    bug_id = str(uuid4())
    conn.execute(
        """
        INSERT INTO bug_reports(
            id, created, request_id, email, severity, summary, details,
            page_url, user_agent, status, client_ip_hash
        )
        VALUES(?,?,?,?,?,?,?,?,?,'new',?)
        """,
        (
            bug_id,
            time.time(),
            request_id,
            email,
            severity,
            summary,
            details,
            page_url,
            user_agent,
            client_ip_hash,
        ),
    )
    conn.commit()
    return bug_id


def list_bug_reports(conn: sqlite3.Connection, *, limit: int = 500) -> list[sqlite3.Row]:
    cur = conn.execute(
        """
        SELECT id, created, request_id, email, severity, summary, details,
               page_url, user_agent, status
          FROM bug_reports
         ORDER BY created DESC
         LIMIT ?
        """,
        (int(limit),),
    )
    return list(cur.fetchall())
