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
import hmac
import hashlib
import re
import csv
from io import StringIO
from contextlib import asynccontextmanager, suppress
from functools import lru_cache
from pathlib import Path

import httpx
from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from pydantic_settings import BaseSettings, SettingsConfigDict
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from spectre_patch import PATCH_ENGINE_SEMVER
from spectre_patch.api.schemas import PatchRequest
from spectre_patch.atlas import AtlasIndex
from spectre_patch.config_limits import FREE_TIER_RASTER_FORMATS, LimitsSettings
from spectre_patch.jobs import repo as job_repo
from spectre_patch.jobs.tasks import run_patch_job
from spectre_patch.api.signed_urls import build_signed_relative_path
from spectre_patch.security.downloads import verify_download


logger = logging.getLogger("spectre_patch.api")


class ServiceSettings(BaseSettings):
    """Service wiring for disk + SQLite + signatures + auth + CORS."""

    model_config = SettingsConfigDict(env_prefix="SPECTRE_PATCH_", env_file=(".env", "../.env"), extra="ignore")

    api_secret: str = "please-change-this-secret-key"
    storage_dir: Path = Path("data/jobs")
    db_path: Path = Path("data/monotile.db")
    atlas_dir: Path = Path("data/atlas")

    # Auth
    require_api_key: bool = False
    valid_api_keys: str = ""  # comma-separated; if non-empty, key must be in this set
    api_key_tiers_json: str = ""
    """JSON object mapping API key -> tier, e.g.
    {"free_xxx":"tier_free","solo_yyy":"tier_solo"}. Production deployments
    should use this instead of trusting client-supplied tier headers.
    """
    admin_token: str = ""

    # Job execution
    run_jobs_in_process: bool = False
    """Dev / single-host convenience: run jobs via BackgroundTasks. Production
    deployments should leave this False and run ``spectre-patch-worker``."""

    # Signed URL lifetime is server-fixed. Keep it <= the GC retention window or
    # callers may receive 404s when they redeem URLs after artifacts are cleaned.
    download_ttl_seconds: int = 900
    download_ttl_seconds_max: int = 3600

    # CORS
    cors_allow_origins: str = ""  # comma-separated, "*" allows all
    cors_allow_credentials: bool = False
    cors_allow_methods: str = "GET,POST,OPTIONS"
    cors_allow_headers: str = "Content-Type,Idempotency-Key,X-API-Key,X-API-Tier,X-Request-ID,X-Admin-Token"

    # Rate limit (slowapi)
    rate_limit_post_patch: str = "30/minute"
    rate_limit_billing_checkout: str = "10/minute"
    rate_limit_billing_claim: str = "20/minute"
    rate_limit_leads: str = "10/minute"

    # Logging
    log_level: str = "INFO"

    # Billing / self-serve signup. Leave unset to disable billing endpoints.
    public_site_url: str = "https://aperiodic-monotile-site.onrender.com"
    support_bug_report_url: str = ""
    """Public-facing URL the API points users to when something goes wrong.
    Falls back to ``{public_site_url}/contact.html`` (with a ``rid`` query
    param) when unset. Override per-deployment to point at Linear/Sentry/etc."""
    stripe_secret_key: str = ""
    stripe_price_id_day_pass: str = ""
    # Legacy Solo monthly Stripe Price id — used when the explicit Solo monthly id below is unset.
    stripe_price_id_studio: str = ""
    stripe_price_id_solo_monthly: str = ""
    stripe_price_id_solo_yearly: str = ""
    stripe_price_id_teams_monthly: str = ""
    stripe_price_id_teams_yearly: str = ""
    stripe_webhook_secret: str = ""


@lru_cache
def svc_settings() -> ServiceSettings:
    return ServiceSettings()


@lru_cache
def limits_defaults() -> LimitsSettings:
    return LimitsSettings()


def _split_csv(s: str) -> list[str]:
    return [p.strip() for p in s.split(",") if p.strip()]


# Map HTTP status codes to short, stable, machine-readable slugs so clients
# (and our own JS widget) can branch on them without parsing English. New codes
# only get added here — never returned ad-hoc from request handlers.
_HTTP_STATUS_ERROR_CODE: dict[int, str] = {
    400: "bad_request",
    401: "missing_api_key",
    402: "payment_required",
    403: "forbidden",
    404: "not_found",
    409: "conflict",
    410: "gone",
    415: "unsupported_media_type",
    422: "invalid_request",
    429: "rate_limited",
    500: "internal_error",
    502: "upstream_error",
    503: "unavailable",
    504: "upstream_timeout",
}


def _support_url_for(cfg: ServiceSettings, request_id: str | None) -> str:
    base = cfg.support_bug_report_url.strip() or (
        f"{cfg.public_site_url.rstrip('/')}/contact.html"
    )
    if not request_id:
        return base
    sep = "&" if "?" in base else "?"
    return f"{base}{sep}rid={request_id}"


def _error_envelope(
    *,
    cfg: ServiceSettings,
    status_code: int,
    message: object,
    request_id: str | None,
    error_code: str | None = None,
    extras: dict | None = None,
) -> dict:
    """Build the customer-facing error body.

    `message` is whatever the handler passed to ``HTTPException(detail=...)``.
    For Pydantic / validation errors we pass a list; for everything else a
    string. We never include traceback text, the local filesystem path, the
    request body, or internal worker error strings in the response — those are
    only kept in the structured server log, addressable by ``request_id``.
    """

    code = error_code or _HTTP_STATUS_ERROR_CODE.get(status_code, "error")
    body: dict = {
        "error": {
            "code": code,
            "status": status_code,
            "message": message if isinstance(message, (str, list, dict)) else str(message),
            "request_id": request_id,
            "support": _support_url_for(cfg, request_id),
        }
    }
    if extras:
        body["error"].update(extras)
    return body


def _api_key_tier_map(cfg: ServiceSettings | None = None) -> dict[str, str]:
    """Parse the server-side API-key tier map.

    ``valid_api_keys`` remains as a backwards-compatible allow-list, mapping
    every listed key to ``tier_solo``. ``api_key_tiers_json`` is the production
    path because it lets us issue distinct free/paid keys without trusting
    `X-API-Tier`.
    """

    cfg = cfg or svc_settings()
    out = {k: "tier_solo" for k in _split_csv(cfg.valid_api_keys)}
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


async def _json_object_body(request: Request) -> dict:
    try:
        body = await request.json()
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail="Request body must be valid JSON") from e
    if not isinstance(body, dict):
        raise HTTPException(status_code=422, detail="Request body must be a JSON object")
    return body


def _tier_for_api_key(request: Request, api_key: str, cfg: ServiceSettings) -> str | None:
    tier_map = _api_key_tier_map(cfg)
    if api_key in tier_map:
        return tier_map[api_key]
    conn = getattr(request.app.state, "db", None)
    if conn is not None:
        row = job_repo.lookup_api_key(conn, api_key)
        if row is not None:
            return str(row["tier"])
    return None


def _admin_token_dependency(
    admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
) -> None:
    cfg = svc_settings()
    if not cfg.admin_token:
        raise HTTPException(status_code=503, detail="Admin API is not configured")
    if not admin_token:
        raise HTTPException(status_code=401, detail="Missing X-Admin-Token")
    if not hmac.compare_digest(admin_token, cfg.admin_token):
        raise HTTPException(status_code=403, detail="Invalid X-Admin-Token")


def _api_key_dependency(request: Request, api_key: str | None = Header(default=None, alias="X-API-Key")) -> str | None:
    """Enforce X-API-Key when configured. Used by every ``/v1/*`` endpoint."""

    cfg = svc_settings()
    if not cfg.require_api_key:
        if api_key:
            tier = _tier_for_api_key(request, api_key, cfg)
            if tier:
                setattr(request.state, "monotile_tier", tier)
        return api_key
    if not api_key:
        raise HTTPException(status_code=401, detail="Missing X-API-Key")
    tier = _tier_for_api_key(request, api_key, cfg)
    if tier is None:
        raise HTTPException(status_code=403, detail="Invalid X-API-Key")
    setattr(request.state, "monotile_tier", tier)
    return api_key


def _billing_configured(cfg: ServiceSettings) -> bool:
    if not cfg.stripe_secret_key:
        return False
    return bool(
        cfg.stripe_price_id_solo_monthly
        or cfg.stripe_price_id_day_pass
        or cfg.stripe_price_id_solo_yearly
        or cfg.stripe_price_id_teams_monthly
        or cfg.stripe_price_id_teams_yearly
        or cfg.stripe_price_id_studio
    )


_CHECKOUT_PLAN_TO_FIELD: tuple[tuple[str, str, str, str, float | None], ...] = (
    ("day_pass", "tier_day_pass", "stripe_price_id_day_pass", "payment", 24 * 3600.0),
    ("solo_monthly", "tier_solo", "stripe_price_id_solo_monthly", "subscription", None),
    ("solo_yearly", "tier_solo", "stripe_price_id_solo_yearly", "subscription", None),
    ("teams_monthly", "tier_teams", "stripe_price_id_teams_monthly", "subscription", None),
    ("teams_yearly", "tier_teams", "stripe_price_id_teams_yearly", "subscription", None),
)


def _plan_defaults(plan_slug: str) -> tuple[str | None, float | None]:
    """Return ``(tier, key_ttl_seconds)`` for a known plan slug.

    Used as a server-side fallback when Stripe session metadata is missing or
    malformed, so a webhook can't silently grant a permanent Solo key to a Day
    Pass purchase. Returns ``(None, None)`` for unrecognised plan slugs.
    """

    for slug, tier, _attr, _mode, ttl in _CHECKOUT_PLAN_TO_FIELD:
        if slug == plan_slug:
            return tier, ttl
    return None, None


def _checkout_price_and_tier(
    cfg: ServiceSettings,
    plan_raw: object,
) -> tuple[str, str, str, str, float | None]:
    """Resolve (stripe_price_id, api_tier_slug, canonical_plan_slug, checkout_mode, ttl)."""

    plan = str(plan_raw or "").strip().lower().replace("-", "_")
    if plan in ("solo", "solo_month"):
        plan = "solo_monthly"
    elif plan in ("day", "daypass", "day_pass_daily"):
        plan = "day_pass"
    elif plan == "solo_year":
        plan = "solo_yearly"
    elif plan == "teams_month":
        plan = "teams_monthly"
    elif plan == "teams_year":
        plan = "teams_yearly"

    if not plan:
        plan = "solo_monthly"

    for slug, tier, attr, mode, ttl_seconds in _CHECKOUT_PLAN_TO_FIELD:
        if slug == plan:
            price_id = str(getattr(cfg, attr, "") or "").strip()
            if not price_id and slug == "solo_monthly" and cfg.stripe_price_id_studio.strip():
                price_id = cfg.stripe_price_id_studio.strip()
            if price_id:
                return price_id, tier, slug, mode, ttl_seconds
            raise HTTPException(
                status_code=503,
                detail=f"Stripe price for {slug.replace('_', ' ')} is not configured.",
            )

    detail = ", ".join(s[0] for s in _CHECKOUT_PLAN_TO_FIELD)
    raise HTTPException(
        status_code=422,
        detail=f'Invalid billing plan "{plan}". Use one of: {detail}',
    )


def _verify_stripe_signature(payload: bytes, sig_header: str, secret: str) -> bool:
    parts: dict[str, list[str]] = {}
    for item in sig_header.split(","):
        if "=" not in item:
            continue
        k, v = item.split("=", 1)
        parts.setdefault(k, []).append(v)
    try:
        ts = int(parts.get("t", ["0"])[0])
    except ValueError:
        return False
    if abs(time.time() - ts) > 300:
        return False
    signed = f"{ts}.".encode("utf-8") + payload
    expected = hmac.new(secret.encode("utf-8"), signed, hashlib.sha256).hexdigest()
    return any(hmac.compare_digest(expected, sig) for sig in parts.get("v1", []))


async def _stripe_post(cfg: ServiceSettings, path: str, data: dict[str, str]) -> dict:
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.post(
            f"https://api.stripe.com/v1/{path.lstrip('/')}",
            data=data,
            auth=(cfg.stripe_secret_key, ""),
        )
    if resp.status_code >= 400:
        # Stripe's response can contain product/customer metadata we shouldn't
        # ship downstream. Log for ourselves, surface a generic detail.
        logger.error("stripe POST %s failed status=%s body=%s", path, resp.status_code, resp.text)
        raise HTTPException(
            status_code=502,
            detail="Payment provider rejected the request. Please try again or contact support.",
        )
    return resp.json()


async def _stripe_get(cfg: ServiceSettings, path: str) -> dict:
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.get(
            f"https://api.stripe.com/v1/{path.lstrip('/')}",
            auth=(cfg.stripe_secret_key, ""),
        )
    if resp.status_code >= 400:
        logger.error("stripe GET %s failed status=%s body=%s", path, resp.status_code, resp.text)
        raise HTTPException(
            status_code=502,
            detail="Payment provider rejected the request. Please try again or contact support.",
        )
    return resp.json()


def _checkout_key_expires_at(session: dict) -> float | None:
    metadata = session.get("metadata") or {}
    ttl_raw = metadata.get("key_ttl_seconds")
    if not ttl_raw:
        return None
    try:
        ttl_seconds = float(ttl_raw)
    except (TypeError, ValueError):
        return None
    created = session.get("created")
    try:
        start = float(created)
    except (TypeError, ValueError):
        start = time.time()
    return start + max(60.0, ttl_seconds)


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
            {"name": "billing"},
            {"name": "jobs"},
        ],
        lifespan=lifespan,
    )
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        rid = getattr(request.state, "request_id", None)
        return JSONResponse(
            _error_envelope(
                cfg=cfg,
                status_code=exc.status_code,
                message=exc.detail,
                request_id=rid,
            ),
            status_code=exc.status_code,
            headers={"X-Request-ID": rid or ""},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        rid = getattr(request.state, "request_id", None)
        # Pydantic errors are already structured and don't leak server paths.
        return JSONResponse(
            _error_envelope(
                cfg=cfg,
                status_code=422,
                message=exc.errors(),
                request_id=rid,
                error_code="invalid_request",
            ),
            status_code=422,
            headers={"X-Request-ID": rid or ""},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        rid = getattr(request.state, "request_id", None)
        # The full traceback already lands in the structured log thanks to the
        # `request_context` middleware logger.exception() call. We only return
        # a generic body so private details (paths, SQL, env state) never reach
        # the wire. Operators correlate via request_id.
        logger.exception("unhandled error rid=%s exc=%r", rid, exc)
        return JSONResponse(
            _error_envelope(
                cfg=cfg,
                status_code=500,
                message=(
                    "Something went wrong on our side. Include the request_id "
                    "below when filing a bug report and we can find the matching log."
                ),
                request_id=rid,
                error_code="internal_error",
            ),
            status_code=500,
            headers={"X-Request-ID": rid or ""},
        )

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
        origin = request.headers.get("origin")
        cors_allowed = _split_csv(cfg.cors_allow_origins)
        cors_ok = bool(origin and ("*" in cors_allowed or origin in cors_allowed))
        if request.method == "OPTIONS" and cors_ok:
            return Response(
                status_code=204,
                headers={
                    "Access-Control-Allow-Origin": "*" if "*" in cors_allowed else origin,
                    "Access-Control-Allow-Methods": cfg.cors_allow_methods,
                    "Access-Control-Allow-Headers": cfg.cors_allow_headers,
                    "Access-Control-Max-Age": "600",
                },
            )
        started = time.perf_counter()
        try:
            response: Response = await call_next(request)
        except Exception:
            elapsed = time.perf_counter() - started
            logger.exception("unhandled request error rid=%s elapsed=%.3f", rid, elapsed)
            raise
        elapsed = time.perf_counter() - started
        response.headers["X-Request-ID"] = rid
        if cors_ok:
            response.headers["Access-Control-Allow-Origin"] = "*" if "*" in cors_allowed else origin
            response.headers["Access-Control-Allow-Methods"] = cfg.cors_allow_methods
            response.headers["Access-Control-Allow-Headers"] = cfg.cors_allow_headers
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
            "roadmap": {
                "tile_families": [
                    {"id": "spectre_tile_1_1", "status": "supported", "label": "Spectre / Tile(1,1)"},
                    {"id": "einstein_hat_tile", "status": "planned", "label": "Einstein Hat monotile (same API hooks)"},
                    {"id": "turtle_tile", "status": "planned", "label": "Companion turtle monotile family"},
                ],
            },
            "free_tier_formats": sorted(FREE_TIER_RASTER_FORMATS),
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
                "stl_zip",
                "obj_zip",
                "glb",
                "instance_json",
                "png",
                "jpg",
                "jpeg",
            ],
            "output_notes": {
                "glb": "Instanced 3D scene: one prototile mesh plus per-tile transforms.",
                "stl": "Whole-panel mesh output.",
                "stl_zip": "Independent STL files, one per tile.",
                "obj_zip": "Independent OBJ files, one per tile.",
            },
            "boundary_behavior": "clip",
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
                "download_ttl_seconds_max": int(cfg.download_ttl_seconds_max),
                "artifact_retention_note": (
                    "Generated artifacts are kept for roughly one hour after the job completes. "
                    "Download or copy them to your own storage if you need them longer."
                ),
            },
        }

    # ------------------------------------------------------ billing ----
    @app.post("/v1/leads", tags=["billing"])
    @limiter.limit(cfg.rate_limit_leads)
    async def create_lead(request: Request) -> dict:
        body = await _json_object_body(request)
        email = str(body.get("email") or "").strip().lower()
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
            raise HTTPException(status_code=422, detail="Valid email is required")

        def clean(key: str, max_len: int = 500) -> str | None:
            value = str(body.get(key) or "").strip()
            return value[:max_len] if value else None

        lead_id, created = job_repo.create_or_update_lead(
            app.state.db,
            email=email,
            name=clean("name", 120),
            company=clean("company", 160),
            use_case=clean("use_case", 1000),
            source=clean("source", 120) or "website",
        )
        return {"lead_id": lead_id, "status": "created" if created else "updated"}

    @app.post("/v1/bug-reports", tags=["billing"])
    @limiter.limit(cfg.rate_limit_leads)
    async def create_bug_report(request: Request) -> dict:
        """Capture a customer bug report.

        Body JSON: ``summary`` (required, <= 240 chars), optional ``details``
        (<= 8000 chars), ``email``, ``request_id``, ``severity``, ``page_url``,
        ``user_agent``. The endpoint is intentionally unauthenticated so docs
        and dashboards can submit on a customer's behalf; auth would just slow
        people down when they're already frustrated.
        """

        body = await _json_object_body(request)

        def clean(key: str, max_len: int) -> str | None:
            value = str(body.get(key) or "").strip()
            return value[:max_len] if value else None

        summary = clean("summary", 240)
        if not summary:
            raise HTTPException(status_code=422, detail="summary is required")

        # Hash the client IP so repeat abusers can be rate-limited / pruned
        # without storing PII.
        client_host = (request.client.host if request.client else "") or ""
        ip_hash = hashlib.sha256(
            (client_host + cfg.api_secret).encode("utf-8")
        ).hexdigest()[:16] if client_host else None

        bug_id = job_repo.create_bug_report(
            app.state.db,
            summary=summary,
            details=clean("details", 8000),
            email=clean("email", 160),
            request_id=clean("request_id", 80),
            severity=clean("severity", 16),
            page_url=clean("page_url", 500),
            user_agent=clean("user_agent", 500),
            client_ip_hash=ip_hash,
        )
        rid = getattr(request.state, "request_id", None)
        return {
            "bug_id": bug_id,
            "status": "received",
            "request_id": rid,
            "support": _support_url_for(cfg, rid),
        }

    @app.get(
        "/v1/admin/bug-reports",
        tags=["billing"],
        include_in_schema=False,
        response_model=None,
    )
    async def admin_bug_reports(
        _: None = Depends(_admin_token_dependency),
        fmt: str = Query(default="json", pattern="^(json|csv)$"),
        limit: int = Query(default=500, ge=1, le=5000),
    ):
        rows = job_repo.list_bug_reports(app.state.db, limit=limit)
        payload = [
            {
                "id": row["id"],
                "created": row["created"],
                "request_id": row["request_id"],
                "email": row["email"],
                "severity": row["severity"],
                "summary": row["summary"],
                "details": row["details"],
                "page_url": row["page_url"],
                "user_agent": row["user_agent"],
                "status": row["status"],
            }
            for row in rows
        ]
        if fmt == "csv":
            buf = StringIO()
            writer = csv.DictWriter(
                buf,
                fieldnames=[
                    "id",
                    "created",
                    "request_id",
                    "email",
                    "severity",
                    "summary",
                    "details",
                    "page_url",
                    "user_agent",
                    "status",
                ],
            )
            writer.writeheader()
            writer.writerows(payload)
            return Response(
                buf.getvalue(),
                media_type="text/csv; charset=utf-8",
                headers={"Content-Disposition": 'attachment; filename="monotile-bug-reports.csv"'},
            )
        return {"bug_reports": payload, "count": len(payload)}

    @app.get("/v1/admin/leads", tags=["billing"], include_in_schema=False, response_model=None)
    async def admin_leads(
        _: None = Depends(_admin_token_dependency),
        fmt: str = Query(default="json", pattern="^(json|csv)$"),
        limit: int = Query(default=500, ge=1, le=5000),
    ):
        rows = job_repo.list_leads(app.state.db, limit=limit)
        payload = [
            {
                "id": row["id"],
                "created": row["created"],
                "email": row["email"],
                "name": row["name"],
                "company": row["company"],
                "use_case": row["use_case"],
                "source": row["source"],
                "status": row["status"],
            }
            for row in rows
        ]
        if fmt == "csv":
            buf = StringIO()
            writer = csv.DictWriter(
                buf,
                fieldnames=["id", "created", "email", "name", "company", "use_case", "source", "status"],
            )
            writer.writeheader()
            writer.writerows(payload)
            return Response(
                buf.getvalue(),
                media_type="text/csv; charset=utf-8",
                headers={"Content-Disposition": 'attachment; filename="monotile-leads.csv"'},
            )
        return {"leads": payload, "count": len(payload)}

    @app.get("/v1/billing/status", tags=["billing"])
    async def billing_status() -> dict:
        return {
            "stripe_configured": _billing_configured(cfg),
            "checkout_available": _billing_configured(cfg),
            "studio_checkout_available": _billing_configured(cfg),
            "plans": {
                "day_pass": bool(cfg.stripe_price_id_day_pass),
                "solo_monthly": bool(cfg.stripe_price_id_solo_monthly or cfg.stripe_price_id_studio),
                "solo_yearly": bool(cfg.stripe_price_id_solo_yearly),
                "teams_monthly": bool(cfg.stripe_price_id_teams_monthly),
                "teams_yearly": bool(cfg.stripe_price_id_teams_yearly),
            },
            "public_site_url": cfg.public_site_url,
        }

    @app.post("/v1/billing/checkout", tags=["billing"])
    @limiter.limit(cfg.rate_limit_billing_checkout)
    async def create_checkout(request: Request) -> dict:
        """Start Stripe Checkout.

        Body JSON (optional unless defaulting): ``email``, ``plan`` — one of
        ``day_pass``, ``solo_monthly``, ``solo_yearly``, ``teams_monthly``, ``teams_yearly``.
        Omitted ``plan`` defaults to ``solo_monthly`` (falls back to
        ``stripe_price_id_studio`` when ``stripe_price_id_solo_monthly`` is unset).
        """

        if not _billing_configured(cfg):
            raise HTTPException(status_code=503, detail="Billing is not configured yet")
        body = await _json_object_body(request)
        email = str(body.get("email") or "").strip() or None
        stripe_price_id, tier, plan_slug, checkout_mode, ttl_seconds = _checkout_price_and_tier(
            cfg,
            body.get("plan"),
        )
        success_url = f"{cfg.public_site_url.rstrip('/')}/docs.html?checkout=success&session_id={{CHECKOUT_SESSION_ID}}#access"
        cancel_url = f"{cfg.public_site_url.rstrip('/')}/#pricing"
        data = {
            "mode": checkout_mode,
            "line_items[0][price]": stripe_price_id,
            "line_items[0][quantity]": "1",
            "success_url": success_url,
            "cancel_url": cancel_url,
            "metadata[tier]": tier,
            "metadata[checkout_plan]": plan_slug[:80],
            "allow_promotion_codes": "true",
        }
        if ttl_seconds is not None:
            data["metadata[key_ttl_seconds]"] = str(int(ttl_seconds))
        if email:
            data["customer_email"] = email
        session = await _stripe_post(cfg, "checkout/sessions", data)
        return {
            "checkout_url": session["url"],
            "session_id": session["id"],
            "tier": tier,
            "plan": plan_slug,
        }

    @app.post("/v1/billing/claim-key", tags=["billing"])
    @limiter.limit(cfg.rate_limit_billing_claim)
    async def claim_checkout_key(request: Request) -> dict:
        if not _billing_configured(cfg):
            raise HTTPException(status_code=503, detail="Billing is not configured yet")
        body = await _json_object_body(request)
        session_id = str(body.get("session_id") or "").strip()
        if not session_id.startswith("cs_"):
            raise HTTPException(status_code=422, detail="session_id is required")

        existing = job_repo.find_api_key_by_checkout_session(app.state.db, session_id)
        if existing is not None:
            api_key = existing["one_time_plaintext"]
            if not api_key:
                return {
                    "status": "already_claimed",
                    "key_prefix": existing["key_prefix"],
                    "tier": existing["tier"],
                }
            job_repo.clear_one_time_plaintext(app.state.db, existing["key_hash"])
            return {"status": "created", "api_key": api_key, "tier": existing["tier"]}

        session = await _stripe_get(cfg, f"checkout/sessions/{session_id}")
        if session.get("payment_status") != "paid":
            raise HTTPException(status_code=402, detail="Checkout session is not paid")
        metadata = session.get("metadata") or {}
        tier = str(metadata.get("tier") or "").strip().lower()
        plan_slug = str(metadata.get("checkout_plan") or "").strip().lower()
        plan_tier, plan_ttl = _plan_defaults(plan_slug)
        if not tier and plan_tier:
            tier = plan_tier
        if not tier:
            logger.error(
                "stripe claim: session=%s missing tier metadata (plan=%r); refusing to mint",
                session_id, metadata.get("checkout_plan"),
            )
            raise HTTPException(
                status_code=409,
                detail="Could not determine plan for this checkout. Contact support with the session id.",
            )
        expires_at = _checkout_key_expires_at(session)
        if expires_at is None and plan_ttl is not None:
            created = session.get("created")
            try:
                start = float(created)
            except (TypeError, ValueError):
                start = time.time()
            expires_at = start + plan_ttl
        api_key = job_repo.create_api_key(
            app.state.db,
            tier=tier,
            label="stripe-checkout",
            customer_email=session.get("customer_email") or session.get("customer_details", {}).get("email"),
            stripe_customer_id=session.get("customer"),
            stripe_subscription_id=session.get("subscription"),
            stripe_checkout_session_id=session_id,
            expires_at=expires_at,
        )
        return {"status": "created", "api_key": api_key, "tier": tier}

    @app.post("/v1/billing/webhook", tags=["billing"], include_in_schema=False)
    async def stripe_webhook(request: Request) -> dict:
        if not cfg.stripe_webhook_secret:
            raise HTTPException(status_code=503, detail="Stripe webhook is not configured")
        payload = await request.body()
        sig = request.headers.get("stripe-signature", "")
        if not _verify_stripe_signature(payload, sig, cfg.stripe_webhook_secret):
            raise HTTPException(status_code=400, detail="Invalid Stripe signature")
        event = json.loads(payload.decode("utf-8"))
        if event.get("type") == "checkout.session.completed":
            session = event.get("data", {}).get("object", {})
            session_id = str(session.get("id") or "")
            metadata = session.get("metadata") or {}
            tier = str(metadata.get("tier") or "").strip().lower()
            plan_slug = str(metadata.get("checkout_plan") or "").strip().lower()
            plan_tier, plan_ttl = _plan_defaults(plan_slug)
            if not tier and plan_tier:
                tier = plan_tier
            if (
                session_id
                and tier
                and job_repo.find_api_key_by_checkout_session(app.state.db, session_id) is None
            ):
                expires_at = _checkout_key_expires_at(session)
                # Day Pass and similar finite-TTL plans must always have an
                # expiry; falling back to the canonical plan TTL prevents a
                # malformed session from minting a permanent key.
                if expires_at is None and plan_ttl is not None:
                    created = session.get("created")
                    try:
                        start = float(created)
                    except (TypeError, ValueError):
                        start = time.time()
                    expires_at = start + plan_ttl
                job_repo.create_api_key(
                    app.state.db,
                    tier=tier,
                    label="stripe-webhook",
                    customer_email=session.get("customer_email") or session.get("customer_details", {}).get("email"),
                    stripe_customer_id=session.get("customer"),
                    stripe_subscription_id=session.get("subscription"),
                    stripe_checkout_session_id=session_id,
                    expires_at=expires_at,
                    reveal_once=True,
                )
            elif session_id and not tier:
                # Stripe still expects a 200 ack to stop redelivery, but we
                # log loudly so a malformed session never silently mints keys.
                logger.error(
                    "stripe webhook: cannot mint API key for session=%s — missing tier metadata "
                    "(checkout_plan=%r). Inspect the Stripe Dashboard.",
                    session_id,
                    metadata.get("checkout_plan"),
                )
        return {"received": True}

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
        if tier == "tier_free":
            disallowed = sorted(set(body.formats) - FREE_TIER_RASTER_FORMATS)
            if disallowed:
                raise HTTPException(
                    status_code=422,
                    detail=(
                        "free tier accepts only raster preview formats "
                        f"({', '.join(sorted(FREE_TIER_RASTER_FORMATS))}); "
                        f"disallowed: {', '.join(disallowed)}"
                    ),
                )
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
        _: str | None = Depends(_api_key_dependency),
    ) -> dict:
        conn = app.state.db
        row = job_repo.fetch_job(conn, job_id)
        if row is None:
            raise HTTPException(status_code=404, detail="job not found")
        if row["status"] != "completed":
            return {"job_id": job_id, "status": row["status"], "urls": {}}
        ttl = max(60, min(int(cfg.download_ttl_seconds), int(cfg.download_ttl_seconds_max)))
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
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".zip": "application/zip",
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
