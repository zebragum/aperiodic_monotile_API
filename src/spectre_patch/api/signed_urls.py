"""Helpers that frontends use when minting CDN-friendly download URLs."""

from __future__ import annotations

import time

from spectre_patch.security.downloads import sign_download


def build_signed_relative_path(job_id: str, filename: str, *, ttl_sec: int, secret: str) -> str:
    exp = int(time.time()) + int(ttl_sec)
    sig = sign_download(secret.encode("utf-8"), job_id=job_id, fname=filename, exp=exp)
    return f"/v1/downloads/{job_id}/{filename}?exp={exp}&sig={sig}"
