"""End-to-end worker smoke: enqueue via repo, drain via worker, verify artifact."""

from __future__ import annotations

import json
import shutil
import threading
import time
from pathlib import Path

from spectre_patch.config_limits import LimitsSettings
from spectre_patch.jobs import repo as job_repo
from spectre_patch.jobs.worker import _SHUTDOWN, run_loop


def main() -> int:
    here = Path("data/_smoke_e2e")
    if here.exists():
        shutil.rmtree(here)
    here.mkdir(parents=True)

    db = here / "jobs.db"
    store = here / "jobs"
    atlas = here / "atlas"
    store.mkdir()
    atlas.mkdir()

    conn = job_repo.connect(db)
    body = {
        "tile_family": "spectre_tile_1_1",
        "scale": 1.0, "rotation_deg": 0.0, "tx": 0.0, "ty": 0.0,
        "substitution_iterations": 3,
        "formats": ["csv", "json", "stl_zip", "obj_zip"],
        "mask": {"type": "circle", "radius": 8.0},
    }
    job_id, _ = job_repo.enqueue_job(conn, "tier_solo", body)
    conn.close()
    print(f"queued job: {job_id}")

    _SHUTDOWN.clear()
    t = threading.Thread(
        target=run_loop,
        kwargs={
            "db_path": db,
            "storage_root": store,
            "atlas_dir": atlas,
            "base_limits": LimitsSettings(),
            "worker_id": "smoke",
            "poll_interval_sec": 0.05,
            "max_idle_sleep_sec": 0.1,
            "requeue_after_sec": 60.0,
        },
        daemon=True,
    )
    t.start()

    deadline = time.time() + 30
    while time.time() < deadline:
        conn = job_repo.connect(db)
        row = job_repo.fetch_job(conn, job_id)
        conn.close()
        if row and row["status"] in ("completed", "failed"):
            break
        time.sleep(0.1)

    _SHUTDOWN.set()
    t.join(timeout=5)

    if row is None or row["status"] != "completed":
        print(f"FAIL: row={dict(row) if row else None}")
        return 1
    result = json.loads(row["result_json"])
    print(f"completed: artifacts={result['artifacts']} tiles={result['tiles']}")
    print(f"           atlas={result.get('atlas')}")
    artpath = store / job_id
    assert (artpath / "tiles.csv").is_file()
    assert (artpath / "tiles.json").is_file()
    print("artifacts:", sorted(p.name for p in artpath.iterdir()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
