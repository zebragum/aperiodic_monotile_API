"""Prototile outline styling for export (side styles and Tile edge-ratio stretch)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
from shapely.geometry import Polygon
from shapely.validation import make_valid

from spectre_patch.core.spectre_t11 import PROTOTILE_CENTROID, PROTOTILE_RING

SideStyle = Literal["flat", "curvy", "wavy", "jagged", "blocky", "custom"]

SIDE_STYLES: tuple[SideStyle, ...] = ("flat", "curvy", "wavy", "jagged", "blocky", "custom")


def normalize_side_style(value: str) -> SideStyle:
    s = str(value).strip().lower()
    if s in ("curved", "curve"):
        return "curvy"
    if s not in SIDE_STYLES:
        raise ValueError(f"unsupported side_style={value!r}; supported={list(SIDE_STYLES)}")
    return s  # type: ignore[return-value]


@dataclass(frozen=True, slots=True)
class TileVisualStyle:
    side_style: SideStyle = "flat"
    side_style_amplitude: float = 0.12
    tile_edge_ratio: float = 1.0
    wavy_segments_per_edge: int = 10
    side_profile_normalized: tuple[tuple[float, float], ...] | None = None

    @classmethod
    def from_request(cls, req: dict) -> TileVisualStyle:
        raw_profile = req.get("side_profile_normalized")
        profile: tuple[tuple[float, float], ...] | None = None
        if raw_profile is not None:
            profile = normalize_side_profile(raw_profile)

        raw_style = req.get("side_style")
        style: SideStyle = "flat"
        if profile is not None:
            style = "custom"
        elif raw_style is not None and str(raw_style).strip():
            style = normalize_side_style(str(raw_style))
        amp = float(req.get("side_style_amplitude", 0.12))
        if amp < 0.0 or amp > 0.75:
            raise ValueError("side_style_amplitude must be within [0, 0.75]")
        ratio = float(req.get("tile_edge_ratio", 1.0))
        if ratio < 0.25 or ratio > 4.0:
            raise ValueError("tile_edge_ratio must be within [0.25, 4.0]")
        segs = int(req.get("side_style_wavy_segments", 10))
        if segs < 4 or segs > 64:
            raise ValueError("side_style_wavy_segments must be within [4, 64]")
        return cls(
            side_style=style,
            side_style_amplitude=amp,
            tile_edge_ratio=ratio,
            wavy_segments_per_edge=segs,
            side_profile_normalized=profile,
        )


def build_base_ring(tile_edge_ratio: float = 1.0) -> np.ndarray:
    """Anisotropic stretch of the canonical prototile (visual export only; placement stays Tile(1,1))."""

    if abs(float(tile_edge_ratio) - 1.0) < 1e-9:
        return PROTOTILE_RING.astype(np.float64, copy=True)
    c = PROTOTILE_CENTROID
    ring = PROTOTILE_RING.astype(np.float64, copy=True)
    r = float(tile_edge_ratio)
    sx = float(np.sqrt(r))
    sy = 1.0 / sx
    ring[:, 0] = c[0] + (ring[:, 0] - c[0]) * sx
    ring[:, 1] = c[1] + (ring[:, 1] - c[1]) * sy
    return ring


_PROFILE_ENDPOINT_TOL = 1e-3
_PROFILE_MAX_POINTS = 64


def normalize_side_profile(raw: object) -> tuple[tuple[float, float], ...]:
    """Validate a normalized edge profile from (0,0) to (1,0) in edge-local coordinates.

    Matches the alternating-edge decoration model from the Spectre paper and
    community tooling (e.g. aspartate/spectre): x runs along the edge, y is
  perpendicular offset as a fraction of edge length.
    """

    if not isinstance(raw, (list, tuple)) or len(raw) < 2:
        raise ValueError("side_profile_normalized must be a list of at least 2 [x, y] points")
    if len(raw) > _PROFILE_MAX_POINTS:
        raise ValueError(f"side_profile_normalized supports up to {_PROFILE_MAX_POINTS} points")

    points: list[tuple[float, float]] = []
    for i, item in enumerate(raw):
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise ValueError(f"side_profile_normalized[{i}] must be [x, y]")
        x, y = float(item[0]), float(item[1])
        if not 0.0 <= x <= 1.0:
            raise ValueError(f"side_profile_normalized[{i}].x must be within [0, 1]")
        if abs(y) > 0.75:
            raise ValueError(f"side_profile_normalized[{i}].y must be within [-0.75, 0.75]")
        points.append((x, y))

    if np.linalg.norm(np.array(points[0]) - np.array((0.0, 0.0))) > _PROFILE_ENDPOINT_TOL:
        raise ValueError("side_profile_normalized must start near (0, 0)")
    if np.linalg.norm(np.array(points[-1]) - np.array((1.0, 0.0))) > _PROFILE_ENDPOINT_TOL:
        raise ValueError("side_profile_normalized must end near (1, 0)")

  # Keep x monotonic so the profile traces the edge forward.
    for i in range(1, len(points)):
        if points[i][0] < points[i - 1][0]:
            raise ValueError("side_profile_normalized x coordinates must be non-decreasing")

    return tuple(points)


def _rotate_point_about(point: np.ndarray, angle: float, origin: np.ndarray) -> np.ndarray:
    c, s = float(np.cos(angle)), float(np.sin(angle))
    px, py = float(point[0] - origin[0]), float(point[1] - origin[1])
    return np.array(
        [origin[0] + c * px - s * py, origin[1] + s * px + c * py],
        dtype=np.float64,
    )


def inverse_side_profile(profile: np.ndarray) -> np.ndarray:
    """Mirror profile for alternating edges (180° rotation about edge midpoint)."""

    origin = np.array([0.5, 0.0], dtype=np.float64)
    out = np.empty_like(profile)
    for i, row in enumerate(reversed(profile)):
        rotated = _rotate_point_about(row, np.pi, origin)
        out[i] = rotated
    return out


def decorate_ring_with_profile(
    ring: np.ndarray,
    profile_normalized: np.ndarray | list | tuple,
    *,
    amplitude: float = 1.0,
    alternate_edges: bool = True,
) -> np.ndarray:
    """Replace each polygon edge with a scaled, rotated copy of a normalized profile."""

    profile = np.asarray(profile_normalized, dtype=np.float64)
    if profile.shape[0] < 2:
        return ring.astype(np.float64, copy=True)

    amp = float(amplitude)
    profile = profile.copy()
    profile[:, 1] *= amp
    inverse = inverse_side_profile(profile) if alternate_edges else profile

    pts = ring.astype(np.float64, copy=False)
    n = len(pts)
    out: list[np.ndarray] = []
    chirality = 1

    for i in range(n):
        p0 = pts[i]
        p1 = pts[(i + 1) % n]
        edge = p1 - p0
        elen = float(np.linalg.norm(edge))
        if elen < 1e-12:
            continue
        angle = float(np.arctan2(edge[1], edge[0]))
        edge_profile = profile if chirality == 1 else inverse

        for j, row in enumerate(edge_profile):
            local = row * elen
            rotated = _rotate_point_about(local, angle, np.zeros(2))
            world = rotated + p0
            if j == 0 and out:
                continue
            out.append(world)

        if alternate_edges:
            chirality *= -1

    if not out:
        return pts.copy()
    return np.asarray(out, dtype=np.float64)


def style_ring_vertices(
    ring: np.ndarray,
    style: SideStyle,
    amplitude: float,
    *,
    wavy_segments_per_edge: int = 10,
) -> np.ndarray:
    """Closed vertex ring (N vertices; first point not repeated at end)."""

    pts = ring.astype(np.float64, copy=False)
    n = len(pts)
    if style == "flat" or amplitude <= 1e-12:
        return pts.copy()

    amp = float(amplitude)
    segs = max(4, int(wavy_segments_per_edge))
    out: list[np.ndarray] = []

    for i in range(n):
        p0 = pts[i]
        p1 = pts[(i + 1) % n]
        edge = p1 - p0
        elen = float(np.linalg.norm(edge))
        if elen < 1e-12:
            continue
        tangent = edge / elen
        normal = np.array([-tangent[1], tangent[0]], dtype=np.float64)
        sign = 1.0 if (i % 2 == 0) else -1.0
        bulge = sign * amp * elen

        if style == "curvy":
            for k in range(segs):
                t0 = k / segs
                t1 = (k + 1) / segs
                q0 = (1 - t0) * p0 + t0 * p1
                q1 = (1 - t1) * p0 + t1 * p1
                s0 = 4 * t0 * (1 - t0)
                s1 = 4 * t1 * (1 - t1)
                v0 = q0 + normal * bulge * s0
                v1 = q1 + normal * bulge * s1
                if k == 0:
                    out.append(v0)
                out.append(v1)
        elif style == "wavy":
            # Full-period sine is anti-symmetric about the edge midpoint, so its
            # Spectre mirror equals itself — keep the same orientation on every
            # edge (no per-edge sign flip, unlike the symmetric bump styles).
            mag = amp * elen * 0.55
            for k in range(segs):
                t = k / segs
                base = (1 - t) * p0 + t * p1
                wave = np.sin(t * np.pi * 2.0) * mag
                out.append(base + normal * wave)
        elif style == "jagged":
            mid = (p0 + p1) * 0.5 + normal * bulge
            out.append(p0.copy())
            out.append(mid)
        elif style == "blocky":
            inset = 0.22
            q0 = (1 - inset) * p0 + inset * p1
            q1 = inset * p0 + (1 - inset) * p1
            out.append(p0.copy())
            out.append(q0 + normal * bulge)
            out.append(q1 + normal * bulge)
        else:
            out.append(p0.copy())

    if not out:
        return pts.copy()
    return np.asarray(out, dtype=np.float64)


def export_ring_for_style(style: TileVisualStyle) -> np.ndarray:
    base = build_base_ring(style.tile_edge_ratio)
    if style.side_profile_normalized is not None:
        return decorate_ring_with_profile(
            base,
            np.asarray(style.side_profile_normalized, dtype=np.float64),
            amplitude=style.side_style_amplitude,
            alternate_edges=True,
        )
    return style_ring_vertices(
        base,
        style.side_style,
        style.side_style_amplitude,
        wavy_segments_per_edge=style.wavy_segments_per_edge,
    )


def ring_to_polygon(ring: np.ndarray) -> Polygon:
    poly = Polygon(ring)
    if not poly.is_valid:
        poly = make_valid(poly)  # type: ignore[assignment]
    if not isinstance(poly, Polygon):
        poly = poly.convex_hull if hasattr(poly, "convex_hull") else Polygon(ring)
    return poly  # noqa: TRY300


def ring_to_svg_path_d(ring: np.ndarray) -> str:
    pts = ring.astype(np.float64, copy=False)
    cmds: list[str] = []
    for i in range(len(pts)):
        x, y = float(pts[i, 0]), float(pts[i, 1])
        cmds.append(f"{'M' if i == 0 else 'L'}{x:.8g} {y:.8g}")
    cmds.append("Z")
    return " ".join(cmds)
