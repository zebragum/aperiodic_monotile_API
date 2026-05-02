"""Worker-side integration: enqueue via repo, drain via worker.run_loop in a thread."""

from __future__ import annotations

import json
import tempfile
import threading
import time
from pathlib import Path

from spectre_patch.config_limits import LimitsSettings
from spectre_patch.jobs import repo as job_repo
from spectre_patch.jobs.tasks import run_patch_job
from spectre_patch.jobs.worker import _SHUTDOWN, run_loop


def _enqueue_csv_job(conn, *, half_side: float = 8.0, depth: int = 2) -> str:
    body = {
        "tile_family": "spectre_tile_1_1",
        "scale": 1.0,
        "rotation_deg": 0.0,
        "tx": 0.0,
        "ty": 0.0,
        "coverage_half_extent": 1.5,
        "substitution_iterations": depth,
        "formats": ["csv"],
        "retention": "centroid",
        "mask": {"type": "square", "center": [0.0, 0.0], "half_side": half_side},
    }
    job_id, created = job_repo.enqueue_job(conn, "tier_pro", body)
    assert created
    return job_id


def test_worker_drains_queued_job():
    _SHUTDOWN.clear()
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        db_path = tmp_path / "jobs.db"
        store = tmp_path / "jobs"
        atlas = tmp_path / "atlas"
        store.mkdir(parents=True, exist_ok=True)
        atlas.mkdir(parents=True, exist_ok=True)

        # Enqueue first so the worker sees a queued job at startup.
        conn = job_repo.connect(db_path)
        job_id = _enqueue_csv_job(conn)
        conn.close()

        thread = threading.Thread(
            target=run_loop,
            kwargs={
                "db_path": db_path,
                "storage_root": store,
                "atlas_dir": atlas,
                "base_limits": LimitsSettings(),
                "worker_id": "test-worker",
                "poll_interval_sec": 0.05,
                "max_idle_sleep_sec": 0.1,
                "requeue_after_sec": 60.0,
            },
            daemon=True,
        )
        thread.start()

        try:
            deadline = time.time() + 30.0
            row = None
            while time.time() < deadline:
                conn = job_repo.connect(db_path)
                row = job_repo.fetch_job(conn, job_id)
                conn.close()
                if row is not None and row["status"] in ("completed", "failed"):
                    break
                time.sleep(0.1)
            assert row is not None, "row never appeared"
            assert row["status"] == "completed", f"job ended with {row['status']}: {row['error']}"
            result = json.loads(row["result_json"])
            assert "tiles.csv" in result["artifacts"]
            assert result["tiles"] > 0
        finally:
            _SHUTDOWN.set()
            thread.join(timeout=5.0)


def test_svg_job_accepts_null_optional_render_fields():
    """Serialized Pydantic requests include explicit nulls for omitted SVG knobs."""

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        db_path = tmp_path / "jobs.db"
        store = tmp_path / "jobs"
        store.mkdir(parents=True, exist_ok=True)
        conn = job_repo.connect(db_path)
        body = {
            "tile_family": "spectre_tile_1_1",
            "scale": 8.0,
            "rotation_deg": 0.0,
            "tx": 0.0,
            "ty": 0.0,
            "coverage_half_extent": 4.5,
            "substitution_iterations": 2,
            "formats": ["svg"],
            "retention": "clip",
            "mask": {"type": "square", "center": [0.0, 0.0], "half_side": 6.25},
            "svg_compact": True,
            "svg_fill": "#d94738",
            "svg_margin": 0.0,
            "svg_opacity": None,
            "svg_pixel_target": 100,
            "svg_stroke": "#1b1b1b",
            "svg_stroke_width": None,
        }
        job_id, created = job_repo.enqueue_job(conn, "tier_free", body)
        assert created

        run_patch_job(
            conn,
            job_id=job_id,
            storage_root=store,
            base_limits=LimitsSettings(),
        )

        row = job_repo.fetch_job(conn, job_id)
        assert row is not None
        assert row["status"] == "completed", row["error"]
        assert (job_repo.artifact_dir(store, job_id) / "patch.svg").exists()
        conn.close()


def test_requeue_stale_running():
    """If a running job has no claimed_at (or a stale one), worker re-queues it."""

    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "jobs.db"
        conn = job_repo.connect(db_path)

        # Insert a "running" job manually with old claimed_at to simulate a crashed worker.
        body = {
            "tile_family": "spectre_tile_1_1",
            "scale": 1.0,
            "mask": {"type": "square", "center": [0, 0], "half_side": 8.0},
            "formats": ["csv"],
            "retention": "centroid",
        }
        job_id, _ = job_repo.enqueue_job(conn, "tier_pro", body)
        ancient = time.time() - 99999
        conn.execute(
            "UPDATE patch_jobs SET status='running', claimed_at=?, claimed_by='dead-worker' WHERE id=?",
            (ancient, job_id),
        )
        conn.commit()

        n = job_repo.requeue_stale_running(conn, max_age_sec=10.0)
        assert n == 1
        row = job_repo.fetch_job(conn, job_id)
        assert row["status"] == "queued"
        assert row["claimed_at"] is None
        conn.close()
