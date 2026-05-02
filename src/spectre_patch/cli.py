"""CLI entry for `spectre-patch-srv` → uvicorn."""

import os
import sys


def main() -> None:
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8000"))
    try:
        import uvicorn  # noqa: PLC0415
    except ImportError as e:
        raise SystemExit(
            "uvicorn not installed — run `pip install uvicorn` or "
            "`pip install spectre-patch-api` with default extras."
        ) from e
    sys.argv = [
        sys.argv[0],
        "spectre_patch.api.main:app",
        "--host",
        host,
        "--port",
        str(port),
    ]
    uvicorn.main()


if __name__ == "__main__":
    main()
