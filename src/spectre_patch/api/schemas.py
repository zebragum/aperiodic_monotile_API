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
    """Axis-aligned rectangle in canonical coordinates."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["rectangle"] = "rectangle"
    bounds: dict | None = None  # {xmin, ymin, xmax, ymax}
    center: list[float] | None = Field(default=None, min_length=2, max_length=2)
    width: Annotated[float, Field(gt=0, le=1.0e7)] | None = None
    height: Annotated[float, Field(gt=0, le=1.0e7)] | None = None

    @field_validator("bounds")
    @classmethod
    def _check_bounds(cls, v: dict | None) -> dict | None:
        if v is None:
            return v
        for k in ("xmin", "ymin", "xmax", "ymax"):
            if k not in v:
                raise ValueError(f"rectangle.bounds missing key: {k}")
            if not isinstance(v[k], (int, float)):
                raise ValueError(f"rectangle.bounds.{k} must be a number")
        if v["xmin"] >= v["xmax"] or v["ymin"] >= v["ymax"]:
            raise ValueError("rectangle.bounds must satisfy xmin<xmax, ymin<ymax")
        return v

    @model_validator(mode="after")
    def _check_rectangle_shape(self) -> "MaskRectangleBody":
        has_bounds = self.bounds is not None
        has_center_size = self.center is not None and self.width is not None and self.height is not None
        if has_bounds == has_center_size:
            raise ValueError(
                "rectangle requires exactly one of bounds or center+width+height"
            )
        return self


class MaskSquareBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["square"] = "square"
    center: list[float] = Field(..., min_length=2, max_length=2)
    half_side: Annotated[float, Field(gt=0, le=1.0e7)]


class MaskCircleBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["circle"] = "circle"
    center: list[float] = Field(..., min_length=2, max_length=2)
    radius: Annotated[float, Field(gt=0, le=1.0e7)]


class MaskHexagonBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["regular_hexagon", "hexagon"] = "regular_hexagon"
    center: list[float] = Field(..., min_length=2, max_length=2)
    circumradius: Annotated[float, Field(gt=0, le=1.0e7)]


class MaskTriangleBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["triangle"] = "triangle"
    center: list[float] = Field(..., min_length=2, max_length=2)
    side_length: Annotated[float, Field(gt=0, le=1.0e7)]
    rotation_deg: Annotated[float, Field(ge=-3600.0, le=3600.0)] = 90.0


class MaskRoundedRectBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["rounded_rect", "rounded-rect"] = "rounded_rect"
    center: list[float] = Field(..., min_length=2, max_length=2)
    width: Annotated[float, Field(gt=0, le=1.0e7)]
    height: Annotated[float, Field(gt=0, le=1.0e7)]
    corner_radius: Annotated[float, Field(ge=0, le=1.0e7)] = 0.0


_SUPPORTED_FORMATS = {"svg", "svgz", "csv", "json", "stl", "glb", "instance_json", "png", "jpg", "jpeg"}

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

    coverage_half_extent: Annotated[float, Field(gt=0.0, le=2.0e7)] = 4.5
    substitution_iterations: Annotated[int, Field(ge=0, le=12)] | None = None

    retention: Literal["centroid", "intersection", "clip"] = "centroid"

    formats: list[str] = Field(default_factory=lambda: ["svg", "csv", "json"])
    force_substitution: bool = False

    # Format-specific options
    stl_extrusion_mm: Annotated[float, Field(gt=0.0, le=1.0e4)] = 1.0
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

    mask: dict

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

        if self.png_width_px is not None and self.png_height_px is None:
            raise ValueError("png_width_px requires png_height_px")
        if self.png_height_px is not None and self.png_width_px is None:
            raise ValueError("png_height_px requires png_width_px")
        if self.jpg_width_px is not None and self.jpg_height_px is None:
            raise ValueError("jpg_width_px requires jpg_height_px")
        if self.jpg_height_px is not None and self.jpg_width_px is None:
            raise ValueError("jpg_height_px requires jpg_width_px")
        return self
