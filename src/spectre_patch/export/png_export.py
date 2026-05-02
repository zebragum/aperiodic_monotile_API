"""Optional PNG export via cairosvg — disabled when dependency missing."""

from __future__ import annotations


def render_svg_to_png_file(svg_path: str, png_path: str, *, width_px: int, height_px: int) -> None:
    """Rasterize deterministic SVG bounds using cairosvg."""

    try:
        import cairosvg  # type: ignore[import-not-found]  # noqa: PLC0415
    except Exception as e:
        raise RuntimeError(
            "PNG export disabled — install `pip install spectre-patch-api[png]` (cairosvg)."
        ) from e

    cairosvg.svg2png(
        url=svg_path,
        write_to=png_path,
        output_width=int(width_px),
        output_height=int(height_px),
    )
