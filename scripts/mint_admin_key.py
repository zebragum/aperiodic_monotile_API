"""Mint a fresh admin-tier API key and stage it for Render sync.

The script intentionally:

- Generates a cryptographically random key via :func:`secrets.token_urlsafe`.
  No user-supplied passwords or memorable strings are accepted, because the
  API key map lives in a single env variable and a weak entry there compromises
  every tier.
- Merges the new key into ``SPECTRE_PATCH_API_KEY_TIERS_JSON`` in the local
  ``.env`` (root preferred; ``spectre_patch_api/.env`` otherwise). The map
  preserves every existing key/tier mapping.
- Writes the full new key into ``.env`` under ``SPECTRE_PATCH_<LABEL>_API_KEY``
  so the operator can copy it locally. Both ``.env`` files are git-ignored.
- Prints only the key *prefix* to stdout. Never the full key.

After running this, run ``python scripts/sync_render_env.py`` to push the
updated tier map into Render.

Usage:
    python scripts/mint_admin_key.py --label zebragum-admin --tier tier_teams
"""

from __future__ import annotations

import argparse
import json
import re
import secrets
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENV_CANDIDATES = (ROOT / ".env", ROOT / "spectre_patch_api" / ".env")
TIER_MAP_KEY = "SPECTRE_PATCH_API_KEY_TIERS_JSON"


def _parse_env_text(text: str) -> tuple[dict[str, str], list[str]]:
    """Return ``(parsed, ordered_keys)`` so we can rewrite preserving order."""

    out: dict[str, str] = {}
    keys: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        k = key.strip()
        out[k] = value.strip().strip('"').strip("'")
        keys.append(k)
    return out, keys


def _load_env_path() -> Path:
    for candidate in ENV_CANDIDATES:
        if candidate.exists():
            return candidate
    # Fall back to the most likely repo-root location so we don't write into
    # the package directory if no env exists yet.
    return ENV_CANDIDATES[0]


def _save_env(path: Path, parsed: dict[str, str]) -> None:
    """Rewrite ``.env`` keeping existing comments and ordering when possible."""

    if path.exists():
        original = path.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
    else:
        original = []

    seen: set[str] = set()
    lines: list[str] = []
    for raw in original:
        if "=" not in raw or raw.strip().startswith("#"):
            lines.append(raw)
            continue
        key = raw.split("=", 1)[0].strip()
        if key in parsed:
            lines.append(f"{key}={parsed[key]}\n")
            seen.add(key)
        else:
            lines.append(raw)

    appended = [f"{k}={v}\n" for k, v in parsed.items() if k not in seen]
    if appended and lines and not lines[-1].endswith("\n"):
        lines.append("\n")
    lines.extend(appended)

    path.write_text("".join(lines), encoding="utf-8")


def _slugify_label(label: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9]+", "_", label.strip().upper()).strip("_")
    return safe or "ADMIN"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else "")
    p.add_argument("--label", default="zebragum-admin")
    p.add_argument("--tier", default="tier_teams")
    p.add_argument("--prefix", default="mono_live")
    p.add_argument(
        "--env-path",
        default=None,
        help="Override the .env path to write into (defaults to the repo root or spectre_patch_api/.env).",
    )
    args = p.parse_args(argv)

    env_path = Path(args.env_path).resolve() if args.env_path else _load_env_path()
    env_path.parent.mkdir(parents=True, exist_ok=True)

    raw = env_path.read_text(encoding="utf-8", errors="replace") if env_path.exists() else ""
    parsed, _order = _parse_env_text(raw)

    tier_map_raw = parsed.get(TIER_MAP_KEY, "").strip()
    tier_map: dict[str, str] = {}
    if tier_map_raw:
        try:
            tier_map = json.loads(tier_map_raw)
            if not isinstance(tier_map, dict):
                raise ValueError("not an object")
        except (ValueError, json.JSONDecodeError) as e:
            print(
                f"ERROR: {TIER_MAP_KEY} in {env_path} is not valid JSON: {e}",
                file=sys.stderr,
            )
            return 2

    new_key = f"{args.prefix}_{secrets.token_urlsafe(32)}"
    tier_map[new_key] = args.tier
    parsed[TIER_MAP_KEY] = json.dumps(tier_map, sort_keys=True, separators=(",", ":"))

    label_env_name = f"SPECTRE_PATCH_{_slugify_label(args.label)}_API_KEY"
    parsed[label_env_name] = new_key

    _save_env(env_path, parsed)

    # Only show enough of the value to confirm which key was minted. The full
    # key is now in the .env file the user can inspect locally.
    prefix_visible = new_key[: len(args.prefix) + 1 + 8]
    print(
        f"Minted {args.tier} key for label '{args.label}': {prefix_visible}…"
        f" (full value stored as {label_env_name} in {env_path})."
    )
    print(
        "Next: run `python scripts/sync_render_env.py` from spectre_patch_api/"
        " to push the updated tier map into Render."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
