"""Pick the cheapest atlas core that fully contains a request's mask."""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt

from spectre_patch.atlas.schema import AtlasIndex, AtlasIndexEntry


@dataclass(frozen=True, slots=True)
class MaskExtent:
    """Canonical-coordinate description of how big a mask is.

    ``half_side`` is the half-extent of the smallest axis-aligned square that
    contains the mask, centered at ``center``. The atlas selector picks the
    smallest core whose ``inscribed_half_side`` is at least this big and whose
    inscribed center is close enough to ``center`` to actually contain the mask.
    """

    center: tuple[float, float]
    half_side: float

    @classmethod
    def from_bbox(cls, bbox: tuple[float, float, float, float]) -> "MaskExtent":
        minx, miny, maxx, maxy = bbox
        cx = 0.5 * (minx + maxx)
        cy = 0.5 * (miny + maxy)
        hs = 0.5 * max(maxx - minx, maxy - miny)
        return cls(center=(cx, cy), half_side=hs)

    @classmethod
    def from_circle(cls, center: tuple[float, float], radius: float) -> "MaskExtent":
        return cls(center=center, half_side=float(radius))


def _entry_has_capacity(entry: AtlasIndexEntry, extent: MaskExtent) -> bool:
    """True iff ``entry``'s inscribed square is big enough to contain the request.

    Center alignment is *not* checked here. The dispatcher translates the user's
    mask onto the core's inscribed_center at crop time and undoes the shift on
    emit, so any core whose inscribed square has sufficient half-side can serve
    a request positioned anywhere in the user's canonical frame.
    """

    if entry.inscribed_half_side <= 0:
        return False
    return entry.inscribed_half_side + 1e-9 >= extent.half_side


def select_core(
    index: AtlasIndex,
    *,
    tile_family: str,
    extent: MaskExtent,
) -> AtlasIndexEntry:
    """Pick the smallest-iteration entry whose inscribed square fits ``extent``.

    Raises :class:`LookupError` if no core is large enough.
    """

    candidates = index.for_family(tile_family)
    if not candidates:
        raise LookupError(f"atlas has no cores for tile_family={tile_family!r}")

    for entry in candidates:
        if _entry_has_capacity(entry, extent):
            return entry

    biggest = candidates[-1]
    raise LookupError(
        f"no atlas core large enough for mask half_side={extent.half_side:.3f}; "
        f"biggest core (n={biggest.iterations}) has "
        f"inscribed_half_side={biggest.inscribed_half_side:.3f}. "
        f"Build a deeper core or shrink the mask."
    )


def maximum_supported_half_side(index: AtlasIndex, *, tile_family: str) -> float:
    """Largest mask half-side this atlas can serve from any core."""

    candidates = index.for_family(tile_family)
    if not candidates:
        return 0.0
    return float(max(e.inscribed_half_side for e in candidates))


def estimate_mask_diagonal(extent: MaskExtent) -> float:
    """Diagonal length helper for diagnostic logging."""

    return float(extent.half_side * 2.0 * sqrt(2.0))
