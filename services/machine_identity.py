"""Local machine identity helpers for license binding."""

from __future__ import annotations

import hashlib
import os
import platform
import uuid


def get_machine_code() -> str:
    """Return a short support-friendly code for this Windows user/device."""
    raw_fingerprint = _raw_machine_fingerprint()
    digest = hashlib.sha256(raw_fingerprint.encode("utf-8")).hexdigest().upper()
    return "-".join(digest[index : index + 5] for index in range(0, 20, 5))


def get_machine_hash(machine_code: str | None = None) -> str:
    """Return the private value stored in the signed license payload."""
    code = (machine_code or get_machine_code()).strip().upper()
    normalized_code = "".join(ch for ch in code if ch.isalnum())
    return hashlib.sha256(normalized_code.encode("utf-8")).hexdigest()


def normalize_machine_code(machine_code: str) -> str:
    normalized = "".join(ch for ch in machine_code.strip().upper() if ch.isalnum())
    if len(normalized) != 20:
        raise ValueError("Machine code must contain 20 letters or numbers.")
    return "-".join(normalized[index : index + 5] for index in range(0, 20, 5))


def _raw_machine_fingerprint() -> str:
    parts = [
        platform.node(),
        platform.system(),
        platform.release(),
        str(uuid.getnode()),
        os.environ.get("COMPUTERNAME", ""),
        os.environ.get("USERNAME", ""),
        os.environ.get("USERDOMAIN", ""),
    ]
    return "|".join(part.strip().lower() for part in parts if part)
