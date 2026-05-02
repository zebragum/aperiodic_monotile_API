"""Atlas schema + manifest types.

A core file is a single ``.npz`` archive holding all leaf tiles of a depth-N
substitution patch (rooted at canonical Delta, IDENTITY transform). The arrays
are ordered exactly like ``spectre_patch.core.spectre_t11.iter_placed_tiles``
so DFS-path-based ``stable_tile_id`` reconstruction round-trips bit-for-bit.

Layout (all arrays C-contiguous, row-aligned):

================  =================  ==============================================
Array             Dtype / shape      Meaning
================  =================  ==============================================
``affine6``       ``f8``  (T, 6)     Canonical 2D affine of each leaf, row-major.
``centroid``     ``f8``  (T, 2)     Cached canonical centroid, computed at build.
``label_idx``    ``u1``  (T,)       Index into ``TILE_NAMES`` for the leaf label.
``path_packed``  ``u8``  (T,)       DFS child indices packed 3 bits each, LSB first.
``path_depth``   ``u1``  (T,)       Number of indices used (0..21).
================  =================  ==============================================

Scalars stored alongside (also persisted into ``index.json`` for fast lookup
without opening the npz):

- ``schema_version``: integer (currently :data:`ATLAS_FORMAT_VERSION`).
- ``tile_family``: e.g. ``"spectre_tile_1_1"``.
- ``patch_version``: generator semver, e.g. ``"0.1.0"``.
- ``iterations``: substitution depth (N).
- ``tile_count``: T (number of leaves).
- ``bbox``: (minx, miny, maxx, maxy) of the full patch (canonical units).
- ``inscribed_center``: (cx, cy) center of the largest fully covered square.
- ``inscribed_half_side``: half-side of that square (canonical units).
- ``builder_seconds``: wall time spent building (informational).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable

ATLAS_FORMAT_VERSION = 1
DEFAULT_TILE_FAMILY = "spectre_tile_1_1"


@dataclass(frozen=True, slots=True)
class AtlasIndexEntry:
    """One row of ``index.json``."""

    tile_family: str
    iterations: int
    patch_version: str
    file: str  # relative to the atlas root, e.g. "core_spectre_t11_n6.npz"
    tile_count: int
    bbox: tuple[float, float, float, float]
    inscribed_center: tuple[float, float]
    inscribed_half_side: float
    inscribed_method: str
    file_bytes: int
    schema_version: int = ATLAS_FORMAT_VERSION

    def as_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "AtlasIndexEntry":
        return cls(
            tile_family=str(d["tile_family"]),
            iterations=int(d["iterations"]),
            patch_version=str(d["patch_version"]),
            file=str(d["file"]),
            tile_count=int(d["tile_count"]),
            bbox=tuple(float(x) for x in d["bbox"]),  # type: ignore[arg-type]
            inscribed_center=tuple(float(x) for x in d["inscribed_center"]),  # type: ignore[arg-type]
            inscribed_half_side=float(d["inscribed_half_side"]),
            inscribed_method=str(d.get("inscribed_method", "unknown")),
            file_bytes=int(d.get("file_bytes", 0)),
            schema_version=int(d.get("schema_version", ATLAS_FORMAT_VERSION)),
        )


@dataclass(frozen=True, slots=True)
class AtlasIndex:
    """In-memory view of an atlas directory's manifest."""

    root: Path
    entries: tuple[AtlasIndexEntry, ...] = field(default_factory=tuple)

    @classmethod
    def load(cls, root: Path | str) -> "AtlasIndex":
        rp = Path(root)
        idx = rp / "index.json"
        if not idx.exists():
            return cls(root=rp, entries=())
        data = json.loads(idx.read_text(encoding="utf-8"))
        entries = tuple(AtlasIndexEntry.from_dict(e) for e in data.get("entries", []))
        return cls(root=rp, entries=entries)

    def with_entry(self, entry: AtlasIndexEntry) -> "AtlasIndex":
        keep = tuple(
            e for e in self.entries
            if not (e.tile_family == entry.tile_family and e.iterations == entry.iterations)
        )
        return AtlasIndex(root=self.root, entries=keep + (entry,))

    def write(self) -> Path:
        self.root.mkdir(parents=True, exist_ok=True)
        idx = self.root / "index.json"
        payload = {
            "schema_version": ATLAS_FORMAT_VERSION,
            "entries": [e.as_dict() for e in sorted(
                self.entries, key=lambda x: (x.tile_family, x.iterations)
            )],
        }
        idx.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        return idx

    def for_family(self, tile_family: str) -> tuple[AtlasIndexEntry, ...]:
        return tuple(
            sorted(
                (e for e in self.entries if e.tile_family == tile_family),
                key=lambda x: x.iterations,
            )
        )

    def file_for(self, tile_family: str, iterations: int) -> Path | None:
        for e in self.entries:
            if e.tile_family == tile_family and e.iterations == iterations:
                return self.root / e.file
        return None

    def __iter__(self) -> Iterable[AtlasIndexEntry]:  # type: ignore[override]
        return iter(self.entries)


def pack_dfs_path(path: tuple[int, ...]) -> tuple[int, int]:
    """Pack a DFS child-index path into a single uint64 (LSB-first, 3 bits each).

    Returns (packed, depth). Raises if any index >= 8 or depth > 21.
    """

    if len(path) > 21:
        raise ValueError(f"DFS path too deep for uint64 packing: depth={len(path)}")
    packed = 0
    for i, idx in enumerate(path):
        if idx < 0 or idx >= 8:
            raise ValueError(f"DFS child index out of range [0,8): {idx} at level {i}")
        packed |= (int(idx) & 0x7) << (3 * i)
    return packed, len(path)


def unpack_dfs_path(packed: int, depth: int) -> tuple[int, ...]:
    """Inverse of :func:`pack_dfs_path`."""

    return tuple((int(packed) >> (3 * i)) & 0x7 for i in range(int(depth)))


def core_filename(tile_family: str, iterations: int) -> str:
    """Canonical filename for an atlas core."""

    safe_family = tile_family.replace(".", "_").replace("/", "_")
    return f"core_{safe_family}_n{int(iterations)}.npz"
