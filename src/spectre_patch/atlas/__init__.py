"""Pre-computed canonical core patches as an atlas (depth-quantised LOD).

Most API requests crop a small region from a much larger tiled patch. Building
the patch from scratch on every request is wasteful at depths >=7, so the
atlas pre-computes a few canonical cores (depths 5..N) once, persists them as
compact numpy archives, and the request path simply selects the smallest core
that contains the requested mask, then crops + applies retention.

Public API:

- :class:`spectre_patch.atlas.AtlasIndex` — load the manifest of available cores.
- :func:`spectre_patch.atlas.select_core` — pick the smallest core for a request.
- :func:`spectre_patch.atlas.build_core` — write a core to disk (CLI / Colab).
- :class:`spectre_patch.atlas.LoadedCore` — mmap'd in-memory view of a core file.

Storage format (see :mod:`spectre_patch.atlas.schema`):

- ``core_<family>_n<N>.npz`` per depth, deterministic content.
- ``index.json`` per atlas directory listing all cores + their inscribed squares.
"""

from spectre_patch.atlas.builder import build_core
from spectre_patch.atlas.dispatch import (
    AtlasResolution,
    enumerate_emitted_or_atlas,
    get_default_core_cache,
)
from spectre_patch.atlas.engine import enumerate_emitted_from_core
from spectre_patch.atlas.loader import LoadedCore, load_core
from spectre_patch.atlas.schema import (
    ATLAS_FORMAT_VERSION,
    AtlasIndex,
    AtlasIndexEntry,
)
from spectre_patch.atlas.selector import (
    MaskExtent,
    maximum_supported_half_side,
    select_core,
)

__all__ = [
    "ATLAS_FORMAT_VERSION",
    "AtlasIndex",
    "AtlasIndexEntry",
    "AtlasResolution",
    "LoadedCore",
    "MaskExtent",
    "build_core",
    "enumerate_emitted_from_core",
    "enumerate_emitted_or_atlas",
    "get_default_core_cache",
    "load_core",
    "maximum_supported_half_side",
    "select_core",
]
