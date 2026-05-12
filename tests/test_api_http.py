"""HTTP smoke + idempotency tests using FastAPI TestClient."""

from __future__ import annotations

import io
import os
import sqlite3
import tempfile
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


def _cairo_raster_deps_functional() -> bool:
    """True when cairosvg can rasterize at least once (needs libcairo/GTK stack)."""

    try:
        import cairosvg  # noqa: PLC0415
        from PIL import Image  # noqa: PLC0415
        png_buf = io.BytesIO()
        cairosvg.svg2png(
            bytestring=b'<svg xmlns="http://www.w3.org/2000/svg"/>',
            write_to=png_buf,
            output_width=2,
            output_height=2,
        )
        png_buf.seek(0)
        with Image.open(png_buf) as im:
            im.load()
        return True
    except Exception:
        return False


def _build_app(
    tmp: Path,
    *,
    atlas_dir: Path | None = None,
    admin_token: str | None = None,
    extra_env: dict[str, str] | None = None,
):
    os.environ["SPECTRE_PATCH_STORAGE_DIR"] = str(tmp / "jobs")
    os.environ["SPECTRE_PATCH_DB_PATH"] = str(tmp / "monotile.db")
    os.environ["SPECTRE_PATCH_API_SECRET"] = "test-secret"
    for k in (
        "SPECTRE_PATCH_STRIPE_SECRET_KEY",
        "SPECTRE_PATCH_STRIPE_PRICE_ID_STUDIO",
        "SPECTRE_PATCH_STRIPE_PRICE_ID_DAY_PASS",
        "SPECTRE_PATCH_STRIPE_PRICE_ID_SOLO_MONTHLY",
        "SPECTRE_PATCH_STRIPE_PRICE_ID_SOLO_YEARLY",
        "SPECTRE_PATCH_STRIPE_PRICE_ID_TEAMS_MONTHLY",
        "SPECTRE_PATCH_STRIPE_PRICE_ID_TEAMS_YEARLY",
        "SPECTRE_PATCH_STRIPE_WEBHOOK_SECRET",
    ):
        os.environ[k] = ""
    for k in (
        "SPECTRE_PATCH_QUEUE_MAX_ACTIVE_JOBS",
        "SPECTRE_PATCH_QUEUE_MAX_ACTIVE_JOBS_PER_KEY",
        "SPECTRE_PATCH_QUEUE_MAX_HEAVY_JOBS",
        "SPECTRE_PATCH_QUEUE_MAX_HEAVY_JOBS_PER_KEY",
    ):
        os.environ.pop(k, None)
    if admin_token is None:
        os.environ.pop("SPECTRE_PATCH_ADMIN_TOKEN", None)
    else:
        os.environ["SPECTRE_PATCH_ADMIN_TOKEN"] = admin_token
    for key, value in (extra_env or {}).items():
        os.environ[key] = value
    # Tests run jobs inside the request lifecycle; production deployments use
    # the dedicated worker process and would leave this off.
    os.environ["SPECTRE_PATCH_RUN_JOBS_IN_PROCESS"] = (extra_env or {}).get(
        "SPECTRE_PATCH_RUN_JOBS_IN_PROCESS",
        "true",
    )
    os.environ["SPECTRE_PATCH_RATE_LIMIT_POST_PATCH"] = "10000/minute"
    os.environ["SPECTRE_PATCH_RATE_LIMIT_BILLING_CHECKOUT"] = "10000/minute"
    os.environ["SPECTRE_PATCH_RATE_LIMIT_BILLING_CLAIM"] = "10000/minute"
    os.environ["SPECTRE_PATCH_RATE_LIMIT_LEADS"] = "10000/minute"
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
            assert "roadmap" in body
            assert "free_tier_formats" in body
            assert set(body["free_tier_formats"]) == {"jpeg", "jpg", "png"}
            assert any(f.get("status") == "planned" for f in body["roadmap"]["tile_families"])


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
            assert "queue_lanes" in body
            for key in ("queued", "running", "completed", "failed"):
                assert key in body["queue"]


def test_existing_sqlite_job_table_migrates_queue_columns():
    from spectre_patch.jobs import repo as job_repo  # noqa: PLC0415

    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "monotile.db"
        raw = sqlite3.connect(db_path)
        raw.execute(
            """
            CREATE TABLE patch_jobs (
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
            )
            """
        )
        raw.commit()
        raw.close()

        conn = job_repo.connect(db_path)
        try:
            cols = {row["name"] for row in conn.execute("PRAGMA table_info(patch_jobs)")}
            assert {"api_key_hash", "size_class", "estimated_seconds"} <= cols
            indexes = {row["name"] for row in conn.execute("PRAGMA index_list(patch_jobs)")}
            assert "ix_patch_jobs_active_key" in indexes
            assert "ix_patch_jobs_lane" in indexes
        finally:
            conn.close()


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
    os.environ["SPECTRE_PATCH_API_KEY_TIERS_JSON"] = '{"free-secret":"tier_free","solo-secret":"tier_solo"}'
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
    os.environ["SPECTRE_PATCH_API_KEY_TIERS_JSON"] = '{"free-secret":"tier_free","solo-secret":"tier_solo"}'
    try:
        with tempfile.TemporaryDirectory() as tmp:
            with TestClient(_build_app(Path(tmp))) as client:
                body = {
                    "tile_family": "spectre_tile_1_1",
                    "scale": 1.0,
                    "rotation_deg": 0.0,
                    "substitution_iterations": 2,
                    "formats": ["jpg"],
                    "jpg_width_px": 256,
                    "jpg_height_px": 256,
                    "mask": {"type": "square", "half_side": 8.0},
                }
                r = client.post(
                    "/v1/patch",
                    json=body,
                    headers={"X-API-Key": "free-secret", "X-API-Tier": "tier_solo"},
                )
                assert r.status_code == 200
                assert r.json()["tier"] == "tier_free"

                r = client.post(
                    "/v1/patch",
                    json={**body, "seed": "paid"},
                    headers={"X-API-Key": "solo-secret"},
                )
                assert r.status_code == 200
                assert r.json()["tier"] == "tier_solo"
    finally:
        os.environ.pop("SPECTRE_PATCH_REQUIRE_API_KEY", None)
        os.environ.pop("SPECTRE_PATCH_API_KEY_TIERS_JSON", None)


def test_queued_job_returns_lane_and_wait_metadata():
    os.environ["SPECTRE_PATCH_REQUIRE_API_KEY"] = "true"
    os.environ["SPECTRE_PATCH_API_KEY_TIERS_JSON"] = '{"solo-secret":"tier_solo"}'
    try:
        with tempfile.TemporaryDirectory() as tmp:
            with TestClient(
                _build_app(
                    Path(tmp),
                    extra_env={"SPECTRE_PATCH_RUN_JOBS_IN_PROCESS": "false"},
                )
            ) as client:
                r = client.post(
                    "/v1/patch",
                    headers={"X-API-Key": "solo-secret"},
                    json={
                        "formats": ["glb"],
                        "mask": {"type": "circle", "radius": 20.0},
                    },
                )
                assert r.status_code == 200
                payload = r.json()
                assert payload["status"] == "queued"
                assert payload["size_class"] == "heavy"
                assert payload["queue"]["position"] == 1

                status = client.get(
                    f"/v1/jobs/{payload['job_id']}",
                    headers={"X-API-Key": "solo-secret"},
                )
                assert status.status_code == 200
                assert status.json()["queue"]["size_class"] == "heavy"

                metrics = client.get("/metrics")
                assert metrics.json()["queue_lanes"]["heavy"]["queued"] == 1
    finally:
        os.environ.pop("SPECTRE_PATCH_REQUIRE_API_KEY", None)
        os.environ.pop("SPECTRE_PATCH_API_KEY_TIERS_JSON", None)


def test_queue_backpressure_limits_one_api_key():
    os.environ["SPECTRE_PATCH_REQUIRE_API_KEY"] = "true"
    os.environ["SPECTRE_PATCH_API_KEY_TIERS_JSON"] = '{"solo-secret":"tier_solo"}'
    try:
        with tempfile.TemporaryDirectory() as tmp:
            with TestClient(
                _build_app(
                    Path(tmp),
                    extra_env={
                        "SPECTRE_PATCH_RUN_JOBS_IN_PROCESS": "false",
                        "SPECTRE_PATCH_QUEUE_MAX_ACTIVE_JOBS_PER_KEY": "1",
                    },
                )
            ) as client:
                body = {
                    "formats": ["png"],
                    "png_width_px": 128,
                    "png_height_px": 128,
                    "mask": {"type": "square", "half_side": 4.0},
                }
                first = client.post("/v1/patch", headers={"X-API-Key": "solo-secret"}, json=body)
                assert first.status_code == 200

                second = client.post(
                    "/v1/patch",
                    headers={"X-API-Key": "solo-secret"},
                    json={**body, "seed": "second"},
                )
                assert second.status_code == 429
                assert "queued or running jobs" in second.json()["error"]["message"]
    finally:
        os.environ.pop("SPECTRE_PATCH_REQUIRE_API_KEY", None)
        os.environ.pop("SPECTRE_PATCH_API_KEY_TIERS_JSON", None)


def test_free_tier_patch_rejects_vector_formats():
    with tempfile.TemporaryDirectory() as tmp:
        with TestClient(_build_app(Path(tmp))) as client:
            body = {
                "tile_family": "spectre_tile_1_1",
                "scale": 1.0,
                "substitution_iterations": 2,
                "formats": ["svg"],
                "mask": {"type": "square", "half_side": 8.0},
            }
            r = client.post("/v1/patch", json=body)
            assert r.status_code == 422


def test_public_patch_request_rejects_internal_geometry_knobs():
    with tempfile.TemporaryDirectory() as tmp:
        with TestClient(_build_app(Path(tmp))) as client:
            base = {
                "tile_family": "spectre_tile_1_1",
                "scale": 1.0,
                "substitution_iterations": 2,
                "formats": ["jpg"],
                "jpg_width_px": 240,
                "jpg_height_px": 240,
                "mask": {"type": "square", "half_side": 8.0},
            }
            for patch in (
                {"retention": "centroid"},
                {"coverage_half_extent": 1.5},
                {"mask": {"type": "square", "center": [0, 0], "half_side": 8.0}},
            ):
                r = client.post("/v1/patch", json={**base, **patch})
                assert r.status_code == 422


@pytest.mark.skipif(
    not _cairo_raster_deps_functional(),
    reason="cairo / cairosvg raster stack unavailable (install GTK+cairo or use Docker/Linux CI)",
)
def test_free_tier_patch_jpeg_smoke():
    with tempfile.TemporaryDirectory() as tmp:
        with TestClient(_build_app(Path(tmp))) as client:
            body = {
                "tile_family": "spectre_tile_1_1",
                "scale": 1.0,
                "substitution_iterations": 2,
                "formats": ["jpg"],
                "jpg_width_px": 240,
                "jpg_height_px": 240,
                "mask": {"type": "square", "half_side": 8.0},
            }
            r = client.post("/v1/patch", json=body)
            assert r.status_code == 200
            job_id = r.json()["job_id"]
            row = {}
            for _ in range(50):
                row = client.get(f"/v1/jobs/{job_id}").json()
                if row["status"] in ("completed", "failed"):
                    break
            assert row["status"] == "completed"
            urls = client.get(f"/v1/jobs/{job_id}/urls").json()
            assert "patch.jpg" in urls["urls"]


def test_database_api_key_authenticates_paid_tier():
    os.environ["SPECTRE_PATCH_REQUIRE_API_KEY"] = "true"
    os.environ.pop("SPECTRE_PATCH_API_KEY_TIERS_JSON", None)
    try:
        with tempfile.TemporaryDirectory() as tmp:
            app = _build_app(Path(tmp))
            with TestClient(app) as client:
                from spectre_patch.jobs import repo as job_repo  # noqa: PLC0415

                api_key = job_repo.create_api_key(app.state.db, tier="tier_solo", label="test")
                r = client.get("/v1/capabilities", headers={"X-API-Key": api_key})
                assert r.status_code == 200

                body = {
                    "tile_family": "spectre_tile_1_1",
                    "scale": 1.0,
                    "substitution_iterations": 2,
                    "formats": ["csv"],
                    "mask": {"type": "square", "half_side": 8.0},
                }
                r = client.post("/v1/patch", json=body, headers={"X-API-Key": api_key})
                assert r.status_code == 200
                assert r.json()["tier"] == "tier_solo"
    finally:
        os.environ.pop("SPECTRE_PATCH_REQUIRE_API_KEY", None)


def test_paid_patch_writes_independent_3d_zip_artifacts():
    with tempfile.TemporaryDirectory() as tmp:
        app = _build_app(Path(tmp))
        with TestClient(app) as client:
            from spectre_patch.jobs import repo as job_repo  # noqa: PLC0415

            api_key = job_repo.create_api_key(app.state.db, tier="tier_solo", label="zip-3d")
            body = {
                "tile_family": "spectre_tile_1_1",
                "scale": 1.0,
                "substitution_iterations": 2,
                "formats": ["stl_zip", "obj_zip"],
                "stl_extrusion_mm": 1.25,
                "mask": {"type": "square", "half_side": 8.0},
            }
            r = client.post("/v1/patch", json=body, headers={"X-API-Key": api_key})
            assert r.status_code == 200, r.text
            job_id = r.json()["job_id"]
            row = {}
            for _ in range(40):
                row = client.get(f"/v1/jobs/{job_id}").json()
                if row["status"] in ("completed", "failed"):
                    break
            assert row["status"] == "completed", row
            urls = client.get(f"/v1/jobs/{job_id}/urls").json()
            assert "tiles_stl.zip" in urls["urls"]
            assert "tiles_obj.zip" in urls["urls"]

            art = Path(tmp) / "jobs" / job_id
            with zipfile.ZipFile(art / "tiles_stl.zip") as stl_zip:
                names = stl_zip.namelist()
                assert "manifest.json" in names
                assert any(name.startswith("tiles/") and name.endswith(".stl") for name in names)
            with zipfile.ZipFile(art / "tiles_obj.zip") as obj_zip:
                names = obj_zip.namelist()
                obj_name = next(name for name in names if name.startswith("tiles/") and name.endswith(".obj"))
                assert "manifest.json" in names
                assert b"\nv " in obj_zip.read(obj_name)


def test_billing_endpoints_report_disabled_without_stripe_config():
    with tempfile.TemporaryDirectory() as tmp:
        with TestClient(_build_app(Path(tmp))) as client:
            r = client.get("/v1/billing/status")
            assert r.status_code == 200
            assert r.json()["stripe_configured"] is False

            r = client.post("/v1/billing/checkout", json={"email": "buyer@example.com"})
            assert r.status_code == 503


def test_billing_checkout_day_pass_uses_payment_mode(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        app = _build_app(
            Path(tmp),
            extra_env={
                "SPECTRE_PATCH_STRIPE_SECRET_KEY": "sk_test_123",
                "SPECTRE_PATCH_STRIPE_PRICE_ID_DAY_PASS": "price_day",
            },
        )
        from spectre_patch.api import main as api_main  # noqa: PLC0415

        async def fake_stripe_post(cfg, path, data):
            assert path == "checkout/sessions"
            assert data["mode"] == "payment"
            assert data["line_items[0][price]"] == "price_day"
            assert data["metadata[tier]"] == "tier_day_pass"
            assert data["metadata[checkout_plan]"] == "day_pass"
            assert data["metadata[key_ttl_seconds]"] == str(24 * 3600)
            return {"url": "https://checkout.example/day", "id": "cs_test_day"}

        monkeypatch.setattr(api_main, "_stripe_post", fake_stripe_post)
        with TestClient(app) as client:
            r = client.get("/v1/billing/status")
            assert r.status_code == 200
            assert r.json()["plans"]["day_pass"] is True

            r = client.post(
                "/v1/billing/checkout",
                json={"email": "buyer@example.com", "plan": "day_pass"},
            )
            assert r.status_code == 200
            assert r.json()["tier"] == "tier_day_pass"
            assert r.json()["plan"] == "day_pass"
            assert r.json()["checkout_url"] == "https://checkout.example/day"


def test_database_api_key_expiry_blocks_authentication():
    with tempfile.TemporaryDirectory() as tmp:
        app = _build_app(Path(tmp))
        with TestClient(app) as client:
            from spectre_patch.jobs import repo as job_repo  # noqa: PLC0415

            api_key = job_repo.create_api_key(
                app.state.db,
                tier="tier_day_pass",
                label="expired-pass",
                expires_at=0.0,
            )
            r = client.get("/v1/capabilities", headers={"X-API-Key": api_key})
            assert r.status_code == 200

            body = {
                "tile_family": "spectre_tile_1_1",
                "scale": 1.0,
                "substitution_iterations": 2,
                "formats": ["svg"],
                "mask": {"type": "square", "half_side": 8.0},
            }
            r = client.post("/v1/patch", json=body, headers={"X-API-Key": api_key})
            assert r.status_code == 422


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


def test_lead_capture_rejects_malformed_json():
    with tempfile.TemporaryDirectory() as tmp:
        with TestClient(_build_app(Path(tmp))) as client:
            r = client.post(
                "/v1/leads",
                content="{not-json",
                headers={"Content-Type": "application/json"},
            )
            assert r.status_code == 400


def test_admin_leads_requires_token_and_exports_json_csv():
    with tempfile.TemporaryDirectory() as tmp:
        with TestClient(_build_app(Path(tmp), admin_token="admin-secret")) as client:
            client.post(
                "/v1/leads",
                json={
                    "email": "buyer@example.com",
                    "name": "Buyer",
                    "company": "Studio",
                    "use_case": "Laser cutting",
                    "source": "test",
                },
            )

            r = client.get("/v1/admin/leads")
            assert r.status_code == 401

            headers = {"X-Admin-Token": "admin-secret"}
            r = client.get("/v1/admin/leads", headers=headers)
            assert r.status_code == 200
            body = r.json()
            assert body["count"] == 1
            assert body["leads"][0]["email"] == "buyer@example.com"

            r = client.get("/v1/admin/leads?fmt=csv", headers=headers)
            assert r.status_code == 200
            assert "buyer@example.com" in r.text
            assert r.headers["content-type"].startswith("text/csv")


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
        app = _build_app(Path(tmp))
        with TestClient(app) as client:
            from spectre_patch.jobs import repo as job_repo  # noqa: PLC0415

            api_key = job_repo.create_api_key(app.state.db, tier="tier_solo", label="idem")
            body = {
                "tile_family": "spectre_tile_1_1",
                "scale": 1.0,
                "rotation_deg": 0.0,
                "substitution_iterations": 2,
                "formats": ["csv"],
                "mask": {"type": "square", "half_side": 8.0},
            }
            h = {"Idempotency-Key": "abc-123", "X-API-Key": api_key}
            r1 = client.post("/v1/patch", json=body, headers=h)
            r2 = client.post("/v1/patch", json=body, headers=h)
            assert r1.status_code == 200 and r2.status_code == 200
            assert r1.json()["job_id"] == r2.json()["job_id"]
            assert r2.json()["status"] == "deduplicated"


def test_signed_url_bundle_after_completion():
    with tempfile.TemporaryDirectory() as tmp:
        app = _build_app(Path(tmp))
        with TestClient(app) as client:
            from spectre_patch.jobs import repo as job_repo  # noqa: PLC0415

            api_key = job_repo.create_api_key(app.state.db, tier="tier_solo", label="signed")
            body = {
                "tile_family": "spectre_tile_1_1",
                "scale": 1.0,
                "rotation_deg": 0.0,
                "substitution_iterations": 2,
                "formats": ["csv", "json"],
                "mask": {"type": "square", "half_side": 8.0},
            }
            r = client.post("/v1/patch", json=body, headers={"X-API-Key": api_key})
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
            "mask": {"type": "circle", "radius": 50.0},
        },
        {
            "name": "9x4-rectangle",
            "scale": 1.0,
            "svg_pixel_target": 900,
            "mask": {"type": "rectangle", "width": 90.0, "height": 40.0},
        },
        {
            "name": "50u-triangle",
            "scale": 1.0,
            "svg_pixel_target": 500,
            "mask": {"type": "triangle", "side_length": 50.0},
        },
    ]
    with tempfile.TemporaryDirectory() as tmp:
        app = _build_app(Path(tmp))
        with TestClient(app) as client:
            from spectre_patch.jobs import repo as job_repo  # noqa: PLC0415

            api_key = job_repo.create_api_key(app.state.db, tier="tier_solo", label="svg-shapes")
            for case in cases:
                body = {
                    "tile_family": "spectre_tile_1_1",
                    "scale": case["scale"],
                    "substitution_iterations": 4,
                    "formats": ["svg"],
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
                    headers={
                        "Idempotency-Key": f"shape-smoke-{case['name']}",
                        "X-API-Key": api_key,
                    },
                )
                assert r.status_code == 200, r.text
                job_id = r.json()["job_id"]
                job = client.get(f"/v1/jobs/{job_id}").json()
                assert job["status"] == "completed", job

                urls = client.get(f"/v1/jobs/{job_id}/urls").json()
                assert "patch.svg" in urls["urls"]
