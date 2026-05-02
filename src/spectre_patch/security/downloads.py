"""HMAC-signed short-lived artifact URLs."""

from __future__ import annotations

import hmac
from hashlib import sha256


def sign_download(secret: bytes, *, job_id: str, fname: str, exp: int) -> str:
    msg = f"{job_id}:{fname}:{exp}".encode("utf-8")
    digest = hmac.new(secret, msg, sha256).hexdigest()
    return digest


def verify_download(secret: bytes, *, job_id: str, fname: str, exp: int, sig: str) -> bool:
    expect = sign_download(secret, job_id=job_id, fname=fname, exp=exp)
    return hmac.compare_digest(expect, sig)
