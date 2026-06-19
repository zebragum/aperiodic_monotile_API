"""Pydantic payloads for Tier-1 endpoints.

Validation is deliberately strict: every field has a sensible bound, the
``mask`` discriminator is structurally validated, and unknown formats are
rejected so a misspelled ``"sgv"`` doesn't silently produce nothing. The aim
is for ``HTTP 422`` errors to be informative without falling through to
worker-side ``ValueError``s after the request has been billed and queued.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


# ---------------------------------------------------------- masks ----
class MaskRectangleBody(BaseModel):
    """Axis-aligned rectangle centered at the canonical origin."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["rectangle"] = "rectangle"
    width: Annotated[float, Field(gt=0, le=1.0e7)]
    height: Annotated[float, Field(gt=0, le=1.0e7)]


class MaskSquareBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["square"] = "square"
    half_side: Annotated[float, Field(gt=0, le=1.0e7)]


class MaskCircleBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["circle"] = "circle"
    radius: Annotated[float, Field(gt=0, le=1.0e7)]


class MaskHexagonBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["regular_hexagon", "hexagon"] = "regular_hexagon"
    circumradius: Annotated[float, Field(gt=0, le=1.0e7)]


class MaskTriangleBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["triangle"] = "triangle"
    side_length: Annotated[float, Field(gt=0, le=1.0e7)]
    rotation_deg: Annotated[float, Field(ge=-3600.0, le=3600.0)] = 90.0


class MaskRoundedRectBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["rounded_rect", "rounded-rect"] = "rounded_rect"
    width: Annotated[float, Field(gt=0, le=1.0e7)]
    height: Annotated[float, Field(gt=0, le=1.0e7)]
    corner_radius: Annotated[float, Field(ge=0, le=1.0e7)] = 0.0


_SUPPORTED_FORMATS = {
    "svg",
    "svgz",
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
}

# ------------------------------------------------------- request ----
class PatchRequest(BaseModel):
    """The ``POST /v1/patch`` request body."""

    model_config = ConfigDict(extra="forbid")

    tile_family: Literal["spectre_tile_1_1"] = "spectre_tile_1_1"
    patch_version: str | None = Field(default=None, max_length=64)
    seed: str | None = Field(default=None, max_length=128)

    # Client-side similarity (applied AFTER the canonical generator).
    scale: Annotated[float, Field(gt=0.0, le=1.0e6)] = 1.0
    tx: Annotated[float, Field(ge=-1.0e9, le=1.0e9)] = 0.0
    ty: Annotated[float, Field(ge=-1.0e9, le=1.0e9)] = 0.0
    rotation_deg: Annotated[float, Field(ge=-3600.0, le=3600.0)] = 0.0

    substitution_iterations: Annotated[int, Field(ge=0, le=12)] | None = None

    formats: list[str] = Field(default_factory=lambda: ["svg", "csv", "json"])
    force_substitution: bool = False

    # Format-specific options
    stl_extrusion_mm: Annotated[float, Field(ge=0.0, le=1.0e4)] = 1.0
    png_width_px: Annotated[int, Field(gt=0, le=32_000)] | None = None
    png_height_px: Annotated[int, Field(gt=0, le=32_000)] | None = None
    jpg_width_px: Annotated[int, Field(gt=0, le=32_000)] | None = None
    jpg_height_px: Annotated[int, Field(gt=0, le=32_000)] | None = None
    jpg_quality: Annotated[int, Field(ge=40, le=100)] | None = None

    svg_fill: str | None = Field(default=None, max_length=32)
    svg_stroke: str | None = Field(default=None, max_length=32)
    svg_stroke_width: Annotated[float, Field(ge=0.0, le=100.0)] | None = None
    svg_opacity: Annotated[float, Field(ge=0.0, le=1.0)] | None = None
    svg_deterministic_palette: bool = False
    svg_pixel_target: Annotated[int, Field(gt=0, le=32_000)] | None = None
    svg_margin: Annotated[float, Field(ge=0.0, le=10_000.0)] | None = None
    svg_compact: bool = False
    force_svg_large: bool = False

    side_style: Literal["flat", "curvy", "wavy", "jagged", "blocky", "custom"] = "flat"
    side_style_amplitude: Annotated[float, Field(ge=0.0, le=0.75)] = 0.12
    tile_edge_ratio: Annotated[float, Field(ge=0.25, le=4.0)] = 1.0
    side_style_wavy_segments: Annotated[int, Field(ge=4, le=64)] = 10
    side_profile_normalized: list[list[float]] | None = None
    palette_by_label: dict[str, dict[str, str | float | bool]] | None = None

    mask: dict

    @field_validator("side_style", mode="before")
    @classmethod
    def _normalize_side_style(cls, v: object) -> str:
        if v is None or (isinstance(v, str) and not v.strip()):
            return "flat"
        from spectre_patch.export.tile_styling import normalize_side_style

        return normalize_side_style(str(v))

    @field_validator("palette_by_label")
    @classmethod
    def _validate_palette_by_label(
        cls, v: dict[str, dict[str, str | float | bool]] | None
    ) -> dict[str, dict[str, str | float | bool]] | None:
        if v is None:
            return v
        if not v:
            raise ValueError("palette_by_label must not be empty when provided")
        allowed = {"fill", "stroke", "opacity", "transparent"}
        for label, spec in v.items():
            if not isinstance(spec, dict):
                raise ValueError(f"palette_by_label[{label!r}] must be an object")
            bad = set(spec.keys()) - allowed
            if bad:
                raise ValueError(
                    f"palette_by_label[{label!r}] unknown keys {sorted(bad)}; allowed={sorted(allowed)}"
                )
            if "opacity" in spec:
                op = float(spec["opacity"])
                if op < 0.0 or op > 1.0:
                    raise ValueError(f"palette_by_label[{label!r}].opacity must be within [0, 1]")
        return v

    @field_validator("formats")
    @classmethod
    def _validate_formats(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("formats must not be empty")
        cleaned = [str(f).strip().lower() for f in v]
        bad = [f for f in cleaned if f not in _SUPPORTED_FORMATS]
        if bad:
            raise ValueError(
                f"unsupported formats {bad}; supported={sorted(_SUPPORTED_FORMATS)}"
            )
        return cleaned

    @field_validator("svg_fill", "svg_stroke")
    @classmethod
    def _validate_svg_color(cls, v: str | None) -> str | None:
        if v is None:
            return v
        s = v.strip()
        # Permit #RGB, #RRGGBB, #RRGGBBAA, named colors, and url(#...) for gradients.
        if not s:
            raise ValueError("color must be non-empty")
        if any(ch in s for ch in ("<", ">", '"', "'", "\n", "\r")):
            raise ValueError("color contains illegal characters")
        return s

    @model_validator(mode="after")
    def _validate_mask(self) -> "PatchRequest":
        m = self.mask
        if not isinstance(m, dict):
            raise ValueError("mask must be an object")
        mt = str(m.get("type", "")).strip().lower()
        if mt == "rectangle":
            MaskRectangleBody.model_validate(m)
        elif mt == "square":
            MaskSquareBody.model_validate(m)
        elif mt == "circle":
            MaskCircleBody.model_validate(m)
        elif mt in ("regular_hexagon", "hexagon"):
            MaskHexagonBody.model_validate(m)
        elif mt == "triangle":
            MaskTriangleBody.model_validate(m)
        elif mt in ("rounded_rect", "rounded-rect"):
            MaskRoundedRectBody.model_validate(m)
        else:
            raise ValueError(
                f"unsupported mask.type={mt!r}; supported="
                "[rectangle, square, circle, regular_hexagon, triangle, rounded_rect]"
            )

        # One-sided raster dimensions → square output (copy the provided edge).
        updates: dict[str, int] = {}
        if self.png_width_px is not None and self.png_height_px is None:
            updates["png_height_px"] = int(self.png_width_px)
        elif self.png_height_px is not None and self.png_width_px is None:
            updates["png_width_px"] = int(self.png_height_px)
        if self.jpg_width_px is not None and self.jpg_height_px is None:
            updates["jpg_height_px"] = int(self.jpg_width_px)
        elif self.jpg_height_px is not None and self.jpg_width_px is None:
            updates["jpg_width_px"] = int(self.jpg_height_px)
        if updates:
            return self.model_copy(update=updates)
        return self
