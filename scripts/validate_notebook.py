"""Quick validator: open the deep-atlas notebook, print the cell summary."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    p = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("notebooks/build_deep_atlas_colab.ipynb")
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    nb = json.loads(p.read_text(encoding="utf-8"))
    print(f"cells: {len(nb['cells'])}")
    for i, cell in enumerate(nb["cells"]):
        src = cell["source"]
        line0 = (src[0] if isinstance(src, list) else src).splitlines()[0] if src else ""
        line0_ascii = line0.encode("ascii", errors="replace").decode("ascii")
        print(f"  [{i:2d}] {cell['cell_type']:<9s} | {line0_ascii[:80]}")
    print()
    print("nbformat:", nb.get("nbformat"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
