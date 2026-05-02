"""HTTP smoke + idempotency tests using FastAPI TestClient."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient


def _build_app(tmp: Path, *, atlas_dir: Path | None = None):
    os.environ["SPECTRE_PATCH_STORAGE_DIR"] = str(tmp / "jobs")
    os.environ["SPECTRE_PATCH_DB_PATH"] = str(tmp / "monotile.db")
    os.environ["SPECTRE_PATCH_API_SECRET"] = "test-secret"
    # Tests run jobs inside the request lifecycle; production deployments use
    # the dedicated worker process and would leave this off.
    os.environ["SPECTRE_PATCH_RUN_JOBS_IN_PROCESS"] = "true"
    os.environ["SPECTRE_PATCH_RATE_LIMIT_POST_PATCH"] = "10000/minute"
    if atlas_dir is None:
        atlas_dir = tmp / "atlas_empty"
        atlas_dir.mkdir(parents=True, exist_ok=True)
    os.environ["SPECTRE_PATCH_ATLAS_DIR"] = str(atlas_dir)
    from spectre_patch.api import main as api_main  # noqa: PLC0415

    api_main.svc_settings.cache_clear()
    api_main.limits_defaults.cache_clear()
    return api_main.create_app()


def test_capabilities_ok():
    with tempfile.TemporaryDirectory() as tmp:
        with TestClient(_build_app(Path(tmp))) as client:
            resp = client.get("/v1/capabilities")
            assert resp.status_code == 200
            body = resp.json()
            assert "spectre_tile_1_1" in body["supported_tile_families"]
            assert "circle" in body["supported_masks"]
            assert "atlas" in body
            # Empty atlas dir → no cores available, but the field still surfaces.
            assert body["atlas"]["available"] is False
            assert body["atlas"]["cores"] == []
            assert body["atlas"]["max_canonical_full_side"] == 0.0
            assert "operational" in body


def test_healthz_and_readyz():
    with tempfile.TemporaryDirectory() as tmp:
        with TestClient(_build_app(Path(tmp))) as client:
            health = client.get("/healthz")
            assert health.status_code == 200
            assert health.json()["status"] == "ok"

            ready = client.get("/readyz")
            assert ready.status_code == 200
            body = ready.json()
            assert body["db"] is True
            assert body["storage"] is True


def test_metrics_returns_queue_depth():
    with tempfile.TemporaryDirectory() as tmp:
        with TestClient(_build_app(Path(tmp))) as client:
            r = client.get("/metrics")
            assert r.status_code == 200
            body = r.json()
            assert "queue" in body
            for key in ("queued", "running", "completed", "failed"):
                assert key in body["queue"]


def test_request_id_is_returned():
    with tempfile.TemporaryDirectory() as tmp:
        with TestClient(_build_app(Path(tmp))) as client:
            r = client.get("/v1/capabilities")
            assert "x-request-id" in {k.lower() for k in r.headers.keys()}


def test_request_id_passthrough():
    with tempfile.TemporaryDirectory() as tmp:
        with TestClient(_build_app(Path(tmp))) as client:
            rid = "test-rid-12345"
            r = client.get("/v1/capabilities", headers={"X-Request-ID": rid})
            assert r.headers.get("x-request-id") == rid


def test_api_key_required_when_configured():
    os.environ["SPECTRE_PATCH_REQUIRE_API_KEY"] = "true"
    os.environ["SPECTRE_PATCH_API_KEY_TIERS_JSON"] = '{"free-secret":"tier_free","pro-secret":"tier_pro"}'
    try:
        with tempfile.TemporaryDirectory() as tmp:
            with TestClient(_build_app(Path(tmp))) as client:
                # Missing key → 401
                r = client.get("/v1/capabilities")
                assert r.status_code == 401
                # Wrong key → 403
                r = client.get("/v1/capabilities", headers={"X-API-Key": "wrong"})
                assert r.status_code == 403
                # Valid key → 200
                r = client.get("/v1/capabilities", headers={"X-API-Key": "free-secret"})
                assert r.status_code == 200
    finally:
        os.environ.pop("SPECTRE_PATCH_REQUIRE_API_KEY", None)
        os.environ.pop("SPECTRE_PATCH_API_KEY_TIERS_JSON", None)


def test_api_key_tier_map_overrides_client_claimed_tier():
    """A free key must not become paid just because the client sends X-API-Tier."""

    os.environ["SPECTRE_PATCH_REQUIRE_API_KEY"] = "true"
    os.environ["SPECTRE_PATCH_API_KEY_TIERS_JSON"] = '{"free-secret":"tier_free","pro-secret":"tier_pro"}'
    try:
        with tempfile.TemporaryDirectory() as tmp:
            with TestClient(_build_app(Path(tmp))) as client:
                body = {
                    "tile_family": "spectre_tile_1_1",
                    "scale": 1.0,
                    "rotation_deg": 0.0,
                    "coverage_half_extent": 1.5,
                    "substitution_iterations": 2,
                    "formats": ["csv"],
                    "mask": {"type": "square", "center": [0, 0], "half_side": 8.0},
                }
                r = client.post(
                    "/v1/patch",
                    json=body,
                    headers={"X-API-Key": "free-secret", "X-API-Tier": "tier_pro"},
                )
                assert r.status_code == 200
                assert r.json()["tier"] == "tier_free"

                r = client.post(
                    "/v1/patch",
                    json={**body, "seed": "paid"},
                    headers={"X-API-Key": "pro-secret"},
                )
                assert r.status_code == 200
                assert r.json()["tier"] == "tier_pro"
    finally:
        os.environ.pop("SPECTRE_PATCH_REQUIRE_API_KEY", None)
        os.environ.pop("SPECTRE_PATCH_API_KEY_TIERS_JSON", None)


def test_capabilities_with_built_atlas():
    """Build a small atlas in a tmpdir and verify /v1/capabilities reflects it."""

    from spectre_patch.atlas import build_core  # noqa: PLC0415

    with tempfile.TemporaryDirectory() as tmp:
        atlas_dir = Path(tmp) / "atlas"
        atlas_dir.mkdir(parents=True, exist_ok=True)
        build_core(
            iterations=4,
            out_dir=atlas_dir,
            tile_family="spectre_tile_1_1",
            patch_version="0.0.0",
            overwrite=True,
            raster_resolution_override=256,
        )
        with TestClient(_build_app(Path(tmp), atlas_dir=atlas_dir)) as client:
            resp = client.get("/v1/capabilities")
            assert resp.status_code == 200
            body = resp.json()
            assert body["atlas"]["available"] is True
            assert body["atlas"]["max_canonical_half_side"] > 0
            assert any(c["iterations"] == 4 for c in body["atlas"]["cores"])


def test_idempotency_dedupes_jobs():
    with tempfile.TemporaryDirectory() as tmp:
        with TestClient(_build_app(Path(tmp))) as client:
            body = {
                "tile_family": "spectre_tile_1_1",
                "scale": 1.0,
                "rotation_deg": 0.0,
                "coverage_half_extent": 1.5,
                "substitution_iterations": 2,
                "formats": ["csv"],
                "mask": {"type": "square", "center": [0, 0], "half_side": 8.0},
            }
            h = {"Idempotency-Key": "abc-123", "X-API-Tier": "tier_pro"}
            r1 = client.post("/v1/patch", json=body, headers=h)
            r2 = client.post("/v1/patch", json=body, headers=h)
            assert r1.status_code == 200 and r2.status_code == 200
            assert r1.json()["job_id"] == r2.json()["job_id"]
            assert r2.json()["status"] == "deduplicated"


def test_signed_url_bundle_after_completion():
    with tempfile.TemporaryDirectory() as tmp:
        with TestClient(_build_app(Path(tmp))) as client:
            body = {
                "tile_family": "spectre_tile_1_1",
                "scale": 1.0,
                "rotation_deg": 0.0,
                "coverage_half_extent": 1.5,
                "substitution_iterations": 2,
                "formats": ["csv", "json"],
                "mask": {"type": "square", "center": [0, 0], "half_side": 8.0},
            }
            r = client.post("/v1/patch", json=body, headers={"X-API-Tier": "tier_pro"})
            assert r.status_code == 200
            job_id = r.json()["job_id"]

            j = {}
            for _ in range(40):
                j = client.get(f"/v1/jobs/{job_id}").json()
                if j["status"] in ("completed", "failed"):
                    break
            assert j["status"] == "completed", j

            urls = client.get(f"/v1/jobs/{job_id}/urls").json()
            assert "tiles.csv" in urls["urls"]
            assert urls["urls"]["tiles.csv"].startswith("/v1/downloads/")
