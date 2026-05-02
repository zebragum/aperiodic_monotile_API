"""Deterministic identifiers for emitted tiles."""

from __future__ import annotations

import hashlib
from typing import Iterable


def stable_tile_id(
    *,
    tile_family: str,
    patch_version: str,
    seed: str | None,
    path_suffix: Iterable[int],
) -> str:
    """Collision-resistant deterministic id from semver + opaque seed token + DFS path."""

    path_part = ".".join(str(i) for i in path_suffix)
    seed_canon = "(none)" if seed is None or seed == "" else seed
    raw = "|".join(
        ["smkgs.v1", tile_family, patch_version, seed_canon, path_part]
    ).encode("utf-8")
    h = hashlib.sha256(raw).hexdigest()
    safe_fam = tile_family.replace(".", "_").replace("/", "_")
    return f"t_{safe_fam}__pv{patch_version}__{h[:26]}"
