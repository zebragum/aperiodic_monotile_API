"""Mask geometries and centroid / intersection / clip retention (canonical coordinates)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Union

import numpy as np
from shapely.geometry import Point
from shapely.geometry import box as shp_box
from shapely.geometry.base import BaseGeometry


class RetentionMode(str, Enum):
    centroid = "centroid"
    intersection = "intersection"
    clip = "clip"


@dataclass(frozen=True, slots=True)
class MaskRect:
    xmin: float
    ymin: float
    xmax: float
    ymax: float


@dataclass(frozen=True, slots=True)
class MaskSquare:
    center: tuple[float, float]
    half_side: float


@dataclass(frozen=True, slots=True)
class MaskCircle:
    center: tuple[float, float]
    radius: float


@dataclass(frozen=True, slots=True)
class MaskHexagon:
    center: tuple[float, float]
    circumradius: float


@dataclass(frozen=True, slots=True)
class MaskTriangle:
    """Equilateral triangle centered at its centroid."""

    center: tuple[float, float]
    side_length: float
    rotation_deg: float = 90.0


@dataclass(frozen=True, slots=True)
class MaskRoundedRect:
    """Axis-aligned rectangle with equal corner radii."""

    center: tuple[float, float]
    width: float
    height: float
    corner_radius: float


Mask = Union[
    MaskRect,
    MaskSquare,
    MaskCircle,
    MaskHexagon,
    MaskTriangle,
    MaskRoundedRect,
]


def hexagon_polygon(center: tuple[float, float], R: float) -> BaseGeometry:
    cx, cy = center
    angles = np.deg2rad(30.0 + 60.0 * np.arange(6))
    pts = np.column_stack([cx + R * np.cos(angles), cy + R * np.sin(angles)])
    from shapely.geometry import Polygon  # noqa: PLC0415

    return Polygon(pts)


def triangle_polygon(center: tuple[float, float], side_length: float, rotation_deg: float = 90.0) -> BaseGeometry:
    cx, cy = center
    radius = float(side_length) / np.sqrt(3.0)
    angles = np.deg2rad(float(rotation_deg) + 120.0 * np.arange(3))
    pts = np.column_stack([cx + radius * np.cos(angles), cy + radius * np.sin(angles)])
    from shapely.geometry import Polygon  # noqa: PLC0415

    return Polygon(pts)


def _rounded_rectangle(center: tuple[float, float], w: float, h: float, r: float) -> BaseGeometry:
    """Rounded rect as linear ring with arc approximations."""
    cx, cy = center
    w2, h2 = w / 2.0, h / 2.0
    r = float(min(abs(r), w2, h2))
    if r <= 0.0:
        return shp_box(cx - w2, cy - h2, cx + w2, cy + h2)
    corners = [(w2 - r, h2 - r), (-w2 + r, h2 - r), (-w2 + r, -h2 + r), (w2 - r, -h2 + r)]
    normal = [(1.0, 1.0), (-1.0, 1.0), (-1.0, -1.0), (1.0, -1.0)]
    from shapely.geometry import Polygon  # noqa: PLC0415

    ring: list[tuple[float, float]] = []
    segs = 8
    for (bx, by), (nx, ny) in zip(corners, normal, strict=True):
        bx, by = cx + bx, cy + by
        for i in range(segs + 1):
            t = np.pi / 2 * (i / segs)
            ux, uy = nx * np.cos(t), ny * np.sin(t)
            ring.append((bx + r * ux, by + r * uy))
    return Polygon(ring)


def mask_polygon(mask: Mask) -> BaseGeometry:
    if isinstance(mask, MaskRect):
        return shp_box(mask.xmin, mask.ymin, mask.xmax, mask.ymax)
    if isinstance(mask, MaskSquare):
        cx, cy = mask.center
        h = mask.half_side
        return shp_box(cx - h, cy - h, cx + h, cy + h)
    if isinstance(mask, MaskCircle):
        cx, cy = mask.center
        return Point(cx, cy).buffer(mask.radius, resolution=96)
    if isinstance(mask, MaskHexagon):
        return hexagon_polygon(mask.center, mask.circumradius)
    if isinstance(mask, MaskTriangle):
        return triangle_polygon(mask.center, mask.side_length, mask.rotation_deg)
    if isinstance(mask, MaskRoundedRect):
        return _rounded_rectangle(mask.center, mask.width, mask.height, mask.corner_radius)
    raise TypeError(f"Unknown mask type {type(mask)!r}")


def centroid_inside(mask_poly: BaseGeometry, xy: np.ndarray) -> bool:
    p = Point(float(xy[0]), float(xy[1]))
    return mask_poly.buffer(1e-12).covers(p)


def retains_tile_result(
    mode: RetentionMode,
    tile_poly: BaseGeometry,
    mask_poly: BaseGeometry,
    centroid_xy: np.ndarray,
) -> tuple[bool, BaseGeometry | None]:
    """Returns (keep, clipped_geom). clipped_geom is populated only when keep and mode == clip."""

    if mode == RetentionMode.centroid:
        return centroid_inside(mask_poly, centroid_xy), None
    if mode == RetentionMode.intersection:
        inter = tile_poly.intersection(mask_poly)
        try:
            return inter.area > 1e-10, None
        except Exception:
            return False, None
    if mode == RetentionMode.clip:
        inter = tile_poly.intersection(mask_poly)
        try:
            if inter.is_empty or inter.area <= 1e-10:
                return False, None
        except Exception:
            return False, None
        return True, inter
    raise ValueError(mode)
