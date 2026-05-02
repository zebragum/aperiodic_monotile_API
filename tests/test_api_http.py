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
    for k in (
        "SPECTRE_PATCH_STRIPE_SECRET_KEY",
        "SPECTRE_PATCH_STRIPE_PRICE_ID_STUDIO",
        "SPECTRE_PATCH_STRIPE_WEBHOOK_SECRET",
    ):
        os.environ.pop(k, None)
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
            assert "triangle" in body["supported_masks"]
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


def test_configured_cors_origin_is_returned():
    os.environ["SPECTRE_PATCH_CORS_ALLOW_ORIGINS"] = "https://site.example"
    try:
        with tempfile.TemporaryDirectory() as tmp:
            with TestClient(_build_app(Path(tmp))) as client:
                r = client.get(
                    "/v1/billing/status",
                    headers={"Origin": "https://site.example"},
                )
                assert r.status_code == 200
                assert r.headers["access-control-allow-origin"] == "https://site.example"

                r = client.options(
                    "/v1/billing/status",
                    headers={
                        "Origin": "https://site.example",
                        "Access-Control-Request-Method": "POST",
                    },
                )
                assert r.status_code == 204
                assert r.headers["access-control-allow-origin"] == "https://site.example"
    finally:
        os.environ.pop("SPECTRE_PATCH_CORS_ALLOW_ORIGINS", None)


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


def test_database_api_key_authenticates_paid_tier():
    os.environ["SPECTRE_PATCH_REQUIRE_API_KEY"] = "true"
    os.environ.pop("SPECTRE_PATCH_API_KEY_TIERS_JSON", None)
    try:
        with tempfile.TemporaryDirectory() as tmp:
            app = _build_app(Path(tmp))
            with TestClient(app) as client:
                from spectre_patch.jobs import repo as job_repo  # noqa: PLC0415

                api_key = job_repo.create_api_key(app.state.db, tier="tier_pro", label="test")
                r = client.get("/v1/capabilities", headers={"X-API-Key": api_key})
                assert r.status_code == 200

                body = {
                    "tile_family": "spectre_tile_1_1",
                    "scale": 1.0,
                    "coverage_half_extent": 1.5,
                    "substitution_iterations": 2,
                    "formats": ["csv"],
                    "mask": {"type": "square", "center": [0, 0], "half_side": 8.0},
                }
                r = client.post("/v1/patch", json=body, headers={"X-API-Key": api_key})
                assert r.status_code == 200
                assert r.json()["tier"] == "tier_pro"
    finally:
        os.environ.pop("SPECTRE_PATCH_REQUIRE_API_KEY", None)


def test_billing_endpoints_report_disabled_without_stripe_config():
    with tempfile.TemporaryDirectory() as tmp:
        with TestClient(_build_app(Path(tmp))) as client:
            r = client.get("/v1/billing/status")
            assert r.status_code == 200
            assert r.json()["stripe_configured"] is False

            r = client.post("/v1/billing/checkout", json={"email": "buyer@example.com"})
            assert r.status_code == 503


def test_lead_capture_creates_and_updates_lead():
    with tempfile.TemporaryDirectory() as tmp:
        with TestClient(_build_app(Path(tmp))) as client:
            body = {
                "email": "Designer@Example.com",
                "name": "Designer",
                "company": "Studio",
                "use_case": "Blender panels",
                "source": "test",
            }
            r = client.post("/v1/leads", json=body)
            assert r.status_code == 200
            first = r.json()
            assert first["status"] == "created"

            r = client.post("/v1/leads", json={**body, "use_case": "Laser cutting"})
            assert r.status_code == 200
            second = r.json()
            assert second["status"] == "updated"
            assert second["lead_id"] == first["lead_id"]

            r = client.post("/v1/leads", json={"email": "not-an-email"})
            assert r.status_code == 422


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


def test_shape_svg_smoke_requests_complete():
    cases = [
        {
            "name": "100u-circle-1000px",
            "scale": 1.0,
            "svg_pixel_target": 1000,
            "mask": {"type": "circle", "center": [0, 0], "radius": 50.0},
        },
        {
            "name": "9x4-rectangle",
            "scale": 1.0,
            "svg_pixel_target": 900,
            "mask": {
                "type": "rectangle",
                "bounds": {"xmin": -45.0, "ymin": -20.0, "xmax": 45.0, "ymax": 20.0},
            },
        },
        {
            "name": "50u-triangle",
            "scale": 1.0,
            "svg_pixel_target": 500,
            "mask": {"type": "triangle", "center": [0, 0], "side_length": 50.0},
        },
    ]
    with tempfile.TemporaryDirectory() as tmp:
        with TestClient(_build_app(Path(tmp))) as client:
            for case in cases:
                body = {
                    "tile_family": "spectre_tile_1_1",
                    "scale": case["scale"],
                    "coverage_half_extent": 80.0,
                    "substitution_iterations": 4,
                    "formats": ["svg"],
                    "retention": "clip",
                    "svg_compact": True,
                    "svg_fill": "#d94738",
                    "svg_stroke": "#1b1b1b",
                    "svg_stroke_width": 0.25,
                    "svg_margin": 0.0,
                    "svg_pixel_target": case["svg_pixel_target"],
                    "mask": case["mask"],
                }
                r = client.post(
                    "/v1/patch",
                    json=body,
                    headers={"Idempotency-Key": f"shape-smoke-{case['name']}"},
                )
                assert r.status_code == 200, r.text
                job_id = r.json()["job_id"]
                job = client.get(f"/v1/jobs/{job_id}").json()
                assert job["status"] == "completed", job

                urls = client.get(f"/v1/jobs/{job_id}/urls").json()
                assert "patch.svg" in urls["urls"]
