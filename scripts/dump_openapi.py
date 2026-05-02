"""Write the live OpenAPI document to `docs/openapi.json` for downstream SDK gen."""

from __future__ import annotations

import json
from pathlib import Path

from spectre_patch.api.main import create_app


def main(out: Path = Path("docs/openapi.json")) -> None:
    app = create_app()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(app.openapi(), indent=2, sort_keys=True), encoding="utf-8")
    print(f"wrote {out} ({out.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
