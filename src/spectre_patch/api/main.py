"""HTTP surface for deterministic monotile infrastructure.

Production model
----------------
- The API is read-mostly: it accepts ``POST /v1/patch`` requests, persists them
  into the SQLite ``patch_jobs`` table, and returns a job id immediately.
- A separate worker process (``spectre-patch-worker``) drains the queue and
  produces artifacts on disk.
- A development fallback exists: when ``run_jobs_in_process=true`` the API
  schedules the worker via FastAPI's ``BackgroundTasks`` so single-process
  ``uvicorn --reload`` setups still produce artifacts. This is **not** safe in
  production because in-flight jobs are lost on API restart.

Operational endpoints
---------------------
- ``GET /healthz`` — liveness (always 200)
- ``GET /readyz``  — readiness: DB connectable + artifact dir writable
- ``GET /v1/capabilities`` — formats, masks, atlas inventory
- ``POST /v1/patch`` — enqueue a job
- ``GET /v1/jobs/{id}`` — status + result manifest + atlas resolution
- ``GET /v1/jobs/{id}/urls`` — signed download bundle
- ``GET /v1/downloads/{id}/{filename}`` — signed artifact download
"""

from __future__ import annotations

import logging
import os
import json
import sqlite3
import time
import uuid
from contextlib import asynccontextmanager, suppress
from functools import lru_cache
from pathlib import Path

from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from pydantic_settings import BaseSettings, SettingsConfigDict
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from spectre_patch import PATCH_ENGINE_SEMVER
from spectre_patch.api.schemas import PatchRequest
from spectre_patch.atlas import AtlasIndex
from spectre_patch.config_limits import LimitsSettings
from spectre_patch.jobs import repo as job_repo
from spectre_patch.jobs.tasks import run_patch_job
from spectre_patch.api.signed_urls import build_signed_relative_path
from spectre_patch.security.downloads import verify_download


logger = logging.getLogger("spectre_patch.api")


class ServiceSettings(BaseSettings):
    """Service wiring for disk + SQLite + signatures + auth + CORS."""

    model_config = SettingsConfigDict(env_prefix="SPECTRE_PATCH_", env_file=".env", extra="ignore")

    api_secret: str = "please-change-this-secret-key"
    storage_dir: Path = Path("data/jobs")
    db_path: Path = Path("data/monotile.db")
    atlas_dir: Path = Path("data/atlas")

    # Auth
    require_api_key: bool = False
    valid_api_keys: str = ""  # comma-separated; if non-empty, key must be in this set
    api_key_tiers_json: str = ""
    """JSON object mapping API key -> tier, e.g.
    {"free_xxx":"tier_free","pro_yyy":"tier_pro"}. Production deployments
    should use this instead of trusting client-supplied tier headers.
    """

    # Job execution
    run_jobs_in_process: bool = False
    """Dev / single-host convenience: run jobs via BackgroundTasks. Production
    deployments should leave this False and run ``spectre-patch-worker``."""

    # Signed URL TTL clamps
    download_ttl_seconds: int = 900

    # CORS
    cors_allow_origins: str = ""  # comma-separated, "*" allows all
    cors_allow_credentials: bool = False
    cors_allow_methods: str = "GET,POST,OPTIONS"
    cors_allow_headers: str = "Content-Type,Idempotency-Key,X-API-Key,X-API-Tier,X-Request-ID"

    # Rate limit (slowapi)
    rate_limit_post_patch: str = "30/minute"

    # Logging
    log_level: str = "INFO"


@lru_cache
def svc_settings() -> ServiceSettings:
    return ServiceSettings()


@lru_cache
def limits_defaults() -> LimitsSettings:
    return LimitsSettings()


def _split_csv(s: str) -> list[str]:
    return [p.strip() for p in s.split(",") if p.strip()]


def _api_key_tier_map(cfg: ServiceSettings | None = None) -> dict[str, str]:
    """Parse the server-side API-key tier map.

    ``valid_api_keys`` remains as a backwards-compatible allow-list, mapping
    every listed key to ``tier_pro``. ``api_key_tiers_json`` is the production
    path because it lets us issue distinct free/pro keys without trusting
    `X-API-Tier`.
    """

    cfg = cfg or svc_settings()
    out = {k: "tier_pro" for k in _split_csv(cfg.valid_api_keys)}
    if cfg.api_key_tiers_json.strip():
        try:
            parsed = json.loads(cfg.api_key_tiers_json)
        except json.JSONDecodeError as e:
            raise RuntimeError("SPECTRE_PATCH_API_KEY_TIERS_JSON is not valid JSON") from e
        if not isinstance(parsed, dict):
            raise RuntimeError("SPECTRE_PATCH_API_KEY_TIERS_JSON must be a JSON object")
        for key, tier in parsed.items():
            if not isinstance(key, str) or not key.strip():
                raise RuntimeError("API key map contains an empty/non-string key")
            if not isinstance(tier, str) or not tier.strip():
                raise RuntimeError(f"API key {key!r} maps to an invalid tier")
            out[key] = tier.strip().lower()
    return out


limiter = Limiter(key_func=get_remote_address)


def _dump_request(body: PatchRequest) -> dict:
    return body.model_dump(exclude_none=False)


def _api_key_dependency(request: Request, api_key: str | None = Header(default=None, alias="X-API-Key")) -> str | None:
    """Enforce X-API-Key when configured. Used by every ``/v1/*`` endpoint."""

    cfg = svc_settings()
    tier_map = _api_key_tier_map(cfg)
    if not cfg.require_api_key:
        if api_key and api_key in tier_map:
            setattr(request.state, "monotile_tier", tier_map[api_key])
        return api_key
    if not api_key:
        raise HTTPException(status_code=401, detail="Missing X-API-Key")
    if tier_map and api_key not in tier_map:
        raise HTTPException(status_code=403, detail="Invalid X-API-Key")
    setattr(request.state, "monotile_tier", tier_map.get(api_key, "tier_free"))
    return api_key


def create_app() -> FastAPI:
    cfg = svc_settings()

    logging.basicConfig(
        level=getattr(logging, str(cfg.log_level).upper(), logging.INFO),
        format='{"ts":"%(asctime)s","lvl":"%(levelname)s","name":"%(name)s","msg":%(message)r}',
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        cfg.storage_dir.mkdir(parents=True, exist_ok=True)
        Path(cfg.atlas_dir).mkdir(parents=True, exist_ok=True)
        app.state.db = job_repo.connect(Path(cfg.db_path))
        app.state.atlas = AtlasIndex.load(Path(cfg.atlas_dir))
        app.state.boot_time = time.time()
        logger.info(
            "API ready: atlas_cores=%d run_jobs_in_process=%s require_api_key=%s",
            len(app.state.atlas.entries),
            cfg.run_jobs_in_process,
            cfg.require_api_key,
        )
        try:
            yield
        finally:
            with suppress(Exception):
                app.state.db.close()

    app = FastAPI(
        title="Spectre Patch API",
        version=PATCH_ENGINE_SEMVER,
        description=(
            "Deterministic Tier-1 API for Spectre / Tile(1,1) patches + masking + exporters. "
            "Attribution docs live in packaged `docs/ATTRIBUTION.md`."
        ),
        openapi_tags=[
            {"name": "ops"},
            {"name": "capabilities"},
            {"name": "jobs"},
        ],
        lifespan=lifespan,
    )
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    cors_origins = _split_csv(cfg.cors_allow_origins)
    if cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_credentials=bool(cfg.cors_allow_credentials),
            allow_methods=_split_csv(cfg.cors_allow_methods),
            allow_headers=_split_csv(cfg.cors_allow_headers),
            expose_headers=["X-Request-ID"],
        )

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        # Stable request ID (passed through if the client supplied one) so logs
        # downstream tools and the worker can correlate per-request work.
        rid = request.headers.get("x-request-id") or str(uuid.uuid4())
        setattr(request.state, "request_id", rid)
        # Default to free. Auth dependency upgrades this from the server-side
        # API key map; in production we must not trust X-API-Tier from clients.
        setattr(request.state, "monotile_tier", "tier_free")
        started = time.perf_counter()
        try:
            response: Response = await call_next(request)
        except Exception:
            elapsed = time.perf_counter() - started
            logger.exception("unhandled request error rid=%s elapsed=%.3f", rid, elapsed)
            raise
        elapsed = time.perf_counter() - started
        response.headers["X-Request-ID"] = rid
        # Security headers (modest defaults, override at the proxy if needed).
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        if request.url.path.startswith("/v1/"):
            logger.info(
                "rid=%s method=%s path=%s status=%s elapsed=%.3f tier=%s",
                rid,
                request.method,
                request.url.path,
                response.status_code,
                elapsed,
                request.state.monotile_tier,
            )
        return response

    # ---------------------------------------------------------- ops ----
    @app.get("/healthz", tags=["ops"], include_in_schema=False)
    async def healthz() -> JSONResponse:
        return JSONResponse({"status": "ok", "ts": time.time()})

    @app.get("/readyz", tags=["ops"], include_in_schema=False)
    async def readyz() -> JSONResponse:
        # DB connectable
        try:
            app.state.db.execute("SELECT 1").fetchone()
            db_ok = True
        except Exception as e:
            db_ok = False
            logger.warning("readyz: DB not ready: %s", e)
        # Storage writable
        store_ok = True
        try:
            (Path(cfg.storage_dir) / ".ready_probe").write_text("ok", encoding="utf-8")
        except Exception as e:
            store_ok = False
            logger.warning("readyz: storage not writable: %s", e)
        body = {
            "db": db_ok,
            "storage": store_ok,
            "atlas_cores": len(app.state.atlas.entries),
            "boot_age_sec": time.time() - getattr(app.state, "boot_time", time.time()),
        }
        ok = db_ok and store_ok
        return JSONResponse(body, status_code=200 if ok else 503)

    @app.get("/metrics", tags=["ops"], include_in_schema=False)
    async def metrics() -> JSONResponse:
        depth = job_repo.queue_depth(app.state.db)
        return JSONResponse(
            {
                "queue": depth,
                "atlas_cores": len(app.state.atlas.entries),
                "boot_age_sec": time.time() - getattr(app.state, "boot_time", time.time()),
            }
        )

    # --------------------------------------------------------- root ----
    @app.get("/", include_in_schema=False)
    async def root_redirect() -> JSONResponse:
        return JSONResponse(
            {
                "docs": "/docs",
                "capabilities": "/v1/capabilities",
                "healthz": "/healthz",
                "readyz": "/readyz",
            }
        )

    # ------------------------------------------------- capabilities ----
    @app.get("/v1/capabilities", tags=["capabilities"])
    async def caps(_: str | None = Depends(_api_key_dependency)):
        lim = limits_defaults()
        atlas_index: AtlasIndex = getattr(app.state, "atlas", AtlasIndex(root=Path(".")))
        atlas_entries = []
        max_extent = 0.0
        for e in sorted(atlas_index.entries, key=lambda x: x.iterations):
            atlas_entries.append(
                {
                    "tile_family": e.tile_family,
                    "iterations": e.iterations,
                    "tile_count": e.tile_count,
                    "inscribed_half_side": e.inscribed_half_side,
                    "inscribed_center": list(e.inscribed_center),
                    "patch_version": e.patch_version,
                }
            )
            if e.inscribed_half_side > max_extent:
                max_extent = e.inscribed_half_side
        return {
            "patch_engine_semver": PATCH_ENGINE_SEMVER,
            "supported_tile_families": ["spectre_tile_1_1"],
            "supported_masks": [
                "square",
                "rectangle",
                "circle",
                "regular_hexagon",
                "triangle",
                "rounded_rect",
            ],
            "supported_formats": [
                "svg",
                "csv",
                "json",
                "stl",
                "glb",
                "instance_json",
                "png",
            ],
            "supported_retention": ["centroid", "intersection", "clip"],
            "limits": lim.model_dump(),
            "atlas": {
                "available": bool(atlas_entries),
                "max_canonical_half_side": max_extent,
                "max_canonical_full_side": max_extent * 2.0,
                "cores": atlas_entries,
            },
            "coordinate_convention": (
                "Canonical Tile(1,1) planar coordinates (unit-edge reference). "
                "Global client scale ∈ ℝ⁺ and rotation_deg are similarity transforms applied after substitution."
            ),
            "operational": {
                "run_jobs_in_process": cfg.run_jobs_in_process,
                "rate_limit_post_patch": cfg.rate_limit_post_patch,
                "download_ttl_seconds_max": 7 * 24 * 3600,
            },
        }

    # -------------------------------------------------------- jobs ----
    @app.post("/v1/patch", tags=["jobs"])
    @limiter.limit(cfg.rate_limit_post_patch)
    async def post_patch(
        request: Request,
        bg: BackgroundTasks,
        body: PatchRequest,
        idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
        _: str | None = Depends(_api_key_dependency),
    ) -> dict:
        conn: sqlite3.Connection = app.state.db
        tier = getattr(request.state, "monotile_tier", "tier_free")
        blob = _dump_request(body)
        job_id, created = job_repo.enqueue_job(
            conn, tier, blob, idempotency_key=idempotency_key
        )
        if created and cfg.run_jobs_in_process:
            # Dev convenience only — see module docstring.
            bg.add_task(
                run_patch_job,
                conn,
                job_id=job_id,
                storage_root=Path(cfg.storage_dir),
                base_limits=LimitsSettings(),
                atlas_index=getattr(app.state, "atlas", None),
            )

        out = {
            "job_id": job_id,
            "status": "queued" if created else "deduplicated",
            "tier": tier,
            "request_id": request.state.request_id,
        }
        if idempotency_key:
            out["idempotency_key"] = idempotency_key
        return out

    @app.get("/v1/jobs/{job_id}", tags=["jobs"])
    async def get_job(job_id: str, _: str | None = Depends(_api_key_dependency)):
        conn = app.state.db
        row = job_repo.fetch_job(conn, job_id)
        if row is None:
            raise HTTPException(status_code=404, detail="job not found")
        return dict(row)

    @app.get("/v1/jobs/{job_id}/urls", tags=["jobs"])
    async def signed_url_bundle(
        job_id: str,
        ttl_seconds: int = 900,
        _: str | None = Depends(_api_key_dependency),
    ) -> dict:
        conn = app.state.db
        row = job_repo.fetch_job(conn, job_id)
        if row is None:
            raise HTTPException(status_code=404, detail="job not found")
        if row["status"] != "completed":
            return {"job_id": job_id, "status": row["status"], "urls": {}}
        ttl = max(60, min(int(ttl_seconds), 7 * 24 * 3600))
        artdir = Path(cfg.storage_dir) / job_id
        if not artdir.is_dir():
            raise HTTPException(status_code=404, detail="artifacts missing")
        urls: dict[str, str] = {}
        for p in sorted(artdir.iterdir()):
            if not p.is_file():
                continue
            urls[p.name] = build_signed_relative_path(
                job_id, p.name, ttl_sec=ttl, secret=cfg.api_secret
            )
        return {"job_id": job_id, "status": row["status"], "ttl_seconds": ttl, "urls": urls}

    @app.get("/v1/downloads/{job_id}/{filename}", tags=["jobs"])
    async def signed_download(job_id: str, filename: str, exp: int, sig: str):
        # Path traversal hardening — only basenames are allowed in URLs.
        if "/" in filename or "\\" in filename or filename.startswith(".."):
            raise HTTPException(status_code=400, detail="invalid filename")
        secret = cfg.api_secret.encode()
        now = int(time.time())
        if exp < now:
            raise HTTPException(status_code=410, detail="expired signature")
        if not verify_download(secret, job_id=job_id, fname=filename, exp=exp, sig=sig):
            raise HTTPException(status_code=403, detail="signature mismatch")

        fp = Path(cfg.storage_dir) / job_id / filename
        try:
            fp_resolved = fp.resolve()
            store_resolved = Path(cfg.storage_dir).resolve()
            if not str(fp_resolved).startswith(str(store_resolved)):
                raise HTTPException(status_code=400, detail="invalid path")
        except Exception as e:
            raise HTTPException(status_code=400, detail="invalid path") from e
        if not fp.is_file():
            raise HTTPException(status_code=404, detail="artifact missing")

        ctype_map = {
            ".svg": "image/svg+xml",
            ".svgz": "image/svg+xml",
            ".stl": "model/stl",
            ".png": "image/png",
            ".csv": "text/csv",
            ".json": "application/json",
            ".glb": "model/gltf-binary",
        }
        ctype = ctype_map.get(fp.suffix.lower(), "application/octet-stream")
        # svgz is gzipped already on disk, mark Content-Encoding so browsers
        # decompress automatically on the wire.
        headers = {}
        if fp.suffix.lower() == ".svgz":
            headers["Content-Encoding"] = "gzip"
        return FileResponse(fp, filename=filename, media_type=ctype, headers=headers)

    return app


app = create_app()


__all__ = ["create_app", "app", "ServiceSettings", "svc_settings"]


# Allow `python -m spectre_patch.api.main` for quick smoke runs.
if __name__ == "__main__":  # pragma: no cover
    import uvicorn  # noqa: PLC0415

    host = os.environ.get("SPECTRE_PATCH_API_HOST", "127.0.0.1")
    port = int(os.environ.get("SPECTRE_PATCH_API_PORT", "8000"))
    uvicorn.run("spectre_patch.api.main:app", host=host, port=port, log_level="info")
