"""Optional PNG/JPEG raster export via cairosvg — disabled when dependency missing."""

from __future__ import annotations

from pathlib import Path


def _require_cairo():
    try:
        import cairosvg  # type: ignore[import-not-found]  # noqa: PLC0415
    except Exception as e:
        raise RuntimeError(
            "Raster export disabled — install `pip install spectre-patch-api[png]` (cairosvg, Pillow)."
        ) from e
    return cairosvg


def render_svg_string_to_png_file(
    svg_text: str, png_path: str | Path, *, width_px: int, height_px: int
) -> None:
    """Rasterize SVG markup to PNG."""

    cairosvg = _require_cairo()
    cairosvg.svg2png(
        bytestring=svg_text.encode("utf-8"),
        write_to=str(png_path),
        output_width=int(width_px),
        output_height=int(height_px),
    )


def render_svg_to_png_file(svg_path: str, png_path: str, *, width_px: int, height_px: int) -> None:
    """Rasterize an on-disk SVG file to PNG."""

    svg_text = Path(svg_path).read_text(encoding="utf-8")
    render_svg_string_to_png_file(svg_text, png_path, width_px=width_px, height_px=height_px)


def render_svg_string_to_jpeg_file(
    svg_text: str,
    jpeg_path: str | Path,
    *,
    width_px: int,
    height_px: int,
    quality: int = 92,
) -> None:
    """Rasterize SVG markup to JPEG (RGB via PNG intermediate inside cairosvg)."""

    import io  # noqa: PLC0415

    try:
        from PIL import Image  # noqa: PLC0415
    except Exception as e:
        raise RuntimeError(
            "JPEG export needs Pillow — install `pip install spectre-patch-api[png]`."
        ) from e

    cairosvg = _require_cairo()
    buf = io.BytesIO()
    cairosvg.svg2png(
        bytestring=svg_text.encode("utf-8"),
        write_to=buf,
        output_width=int(width_px),
        output_height=int(height_px),
    )
    buf.seek(0)
    with Image.open(buf) as im:
        im.convert("RGB").save(
            jpeg_path,
            format="JPEG",
            quality=int(quality),
            optimize=True,
        )
