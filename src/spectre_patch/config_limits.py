"""Operational limits — defaults suitable for Tier-1 infra."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class LimitsSettings(BaseSettings):
    """Env-overridable limits and pricing SKU hooks."""

    model_config = SettingsConfigDict(env_prefix="SPECTRE_PATCH_", env_file=(".env", "../.env"), extra="ignore")

    max_supertile_iterations: int = 26
    max_tiles_per_job: int = 400_000
    sync_max_tiles: int = 8000

    svg_max_tiles_hard: int = 25_000
    png_max_dimension_px: int = 16_000
    png_max_pixels: int = 50_000_000

    max_output_bytes_soft: int = 30 * (1024**3) - 1
    max_wall_time_sec: float = 3600.0
    job_gc_hours: int = 24

    stl_tile_instancing_floor: int = 50_000

    svg_max_chars: int = 400_000_000

    redis_url: str | None = None



# Raster-only formats exposed on the unpaid SKU — enforced in the API worker.
FREE_TIER_RASTER_FORMATS: frozenset[str] = frozenset({"png", "jpg", "jpeg"})


# Public marketing labels keyed by internal API tier id (``tier_teams`` = Pro plan).
TIER_PUBLIC_LABELS: dict[str, str] = {
    "tier_free": "Free",
    "tier_day_pass": "Day Pass",
    "tier_solo": "Solo",
    "tier_teams": "Pro",
}

DEFAULT_TIER_RULES: dict[str, dict[str, int | float | bool]] = {
    "tier_free": {
        "max_tiles_per_job": 2500,
        "max_wall_time_sec": 120,
        "stl_instancing_required": False,
    },
    "tier_day_pass": {
        "max_tiles_per_job": 40_000,
        "max_wall_time_sec": 3600.0,
        "stl_instancing_required": False,
    },
    "tier_solo": {
        "max_tiles_per_job": 40_000,
        "max_wall_time_sec": 3600.0,
        "stl_instancing_required": False,
    },
    "tier_teams": {
        "max_tiles_per_job": 400_000,
        "max_wall_time_sec": 3600.0,
        "stl_instancing_required": False,
    },
}


def tier_limits_resolver(tier_key: str, base: LimitsSettings) -> LimitsSettings:
    """Billing SKU integration hook — merges known tier limits into LimitsSettings."""

    overrides = DEFAULT_TIER_RULES.get(tier_key, {})
    payload = base.model_dump()
    mtp = overrides.get("max_tiles_per_job")
    if isinstance(mtp, int):
        payload["max_tiles_per_job"] = mtp
    mwt = overrides.get("max_wall_time_sec")
    if isinstance(mwt, (int, float)):
        payload["max_wall_time_sec"] = float(mwt)
    return LimitsSettings.model_validate(payload)
