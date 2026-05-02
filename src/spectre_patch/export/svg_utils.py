"""Low-level helpers for deterministic SVG serialization."""

from __future__ import annotations

import hashlib

import numpy as np

from spectre_patch.core.spectre_t11 import PROTOTILE_RING


def prototile_path_d(xy: np.ndarray = PROTOTILE_RING) -> str:
    pts = xy.astype(np.float64, copy=False)
    cmds: list[str] = []
    for i in range(len(pts)):
        x, y = float(pts[i, 0]), float(pts[i, 1])
        letter = "M" if i == 0 else "L"
        cmds.append(f"{letter}{x:.8g} {y:.8g}")
    cmds.append("Z")
    return " ".join(cmds)


def svg_matrix_tuple_from_world6(a: float, b: float, tx: float, c: float, d: float, ty: float) -> tuple[str, ...]:
    """SVG matrix(a,b,c,d,e,f) per https://developer.mozilla.org/docs/Web/SVG/Attribute/transform."""

    return tuple(f"{float(v):.8g}" for v in (a, c, b, d, tx, ty))


def deterministic_palette(hex_seed: str) -> tuple[str, str]:
    h = hashlib.sha256(hex_seed.encode("utf-8")).digest()
    hue = int.from_bytes(h[0:2], "big") / 65535.0 * 359.999
    lightness = 0.42 + ((h[2] % 60) / 60.0) * 0.18
    saturation = 0.38 + ((h[3] % 50) / 50.0) * 0.22
    return _hls_to_rgb_hex(hue, lightness, saturation)


def _hls_to_rgb_hex(h_deg: float, l: float, s: float) -> tuple[str, str]:
    h = float(h_deg) % 360.0 / 360.0
    chroma = (1 - abs(2 * l - 1)) * s
    x = chroma * (1 - abs((h * 6) % 2 - 1))
    m = l - chroma / 2
    r1, g1, b1 = _rgb_sector(h * 6, chroma, x)
    rf = int(round((r1 + m) * 255))
    gf = int(round((g1 + m) * 255))
    bf = int(round((b1 + m) * 255))
    fill = f"#{rf:02x}{gf:02x}{bf:02x}"
    stroke_rgb = tuple(max(18, min(255, comp - 40)) for comp in (rf, gf, bf))
    stroke = f"#{stroke_rgb[0]:02x}{stroke_rgb[1]:02x}{stroke_rgb[2]:02x}"
    return fill, stroke


def _rgb_sector(sec: float, c: float, x: float) -> tuple[float, float, float]:
    if sec < 1:
        return c, x, 0.0
    if sec < 2:
        return x, c, 0.0
    if sec < 3:
        return 0.0, c, x
    if sec < 4:
        return 0.0, x, c
    if sec < 5:
        return x, 0.0, c
    return c, 0.0, x
