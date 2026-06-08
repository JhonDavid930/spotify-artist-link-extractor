"""Cross-platform helpers for protecting local secrets."""

from __future__ import annotations

import base64
import ctypes
import hashlib
import os
import platform
import sys
from ctypes import wintypes

from cryptography.fernet import Fernet, InvalidToken


DPAPI_PREFIX = "dpapi:"
KEYRING_PREFIX = "keyring:"
LOCAL_PREFIX = "localenc:"
PROTECTED_PREFIXES = (DPAPI_PREFIX, KEYRING_PREFIX, LOCAL_PREFIX)
KEYRING_SERVICE = "SpotifyArtistLinkExtractor"
KEYRING_ACCOUNT = "spotify_client_secret"


class DATA_BLOB(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_char)),
    ]


def protect_secret(secret: str) -> str:
    if not secret:
        return ""
    if sys.platform == "win32":
        encrypted = _crypt_protect_data(secret.encode("utf-8"))
        return f"{DPAPI_PREFIX}{base64.urlsafe_b64encode(encrypted).decode('ascii')}"
    if _store_in_keyring(secret):
        return f"{KEYRING_PREFIX}{KEYRING_ACCOUNT}"
    encrypted = _local_fernet().encrypt(secret.encode("utf-8")).decode("ascii")
    return f"{LOCAL_PREFIX}{encrypted}"


def unprotect_secret(value: str) -> str:
    if not value:
        return ""
    if value.startswith(DPAPI_PREFIX):
        if sys.platform != "win32":
            return ""
        try:
            encrypted = base64.urlsafe_b64decode(value[len(DPAPI_PREFIX) :].encode("ascii"))
            return _crypt_unprotect_data(encrypted).decode("utf-8")
        except Exception:
            return ""
    if value.startswith(KEYRING_PREFIX):
        return _read_from_keyring(value[len(KEYRING_PREFIX) :].strip() or KEYRING_ACCOUNT)
    if value.startswith(LOCAL_PREFIX):
        try:
            token = value[len(LOCAL_PREFIX) :].encode("ascii")
            return _local_fernet().decrypt(token).decode("utf-8")
        except (InvalidToken, ValueError):
            return ""
    return value


def _store_in_keyring(secret: str) -> bool:
    try:
        import keyring  # type: ignore

        keyring.set_password(KEYRING_SERVICE, KEYRING_ACCOUNT, secret)
        return True
    except Exception:
        return False


def _read_from_keyring(account: str) -> str:
    try:
        import keyring  # type: ignore

        return keyring.get_password(KEYRING_SERVICE, account) or ""
    except Exception:
        return ""


def _local_fernet() -> Fernet:
    digest = hashlib.sha256(_local_key_material().encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def _local_key_material() -> str:
    parts = [
        platform.node(),
        platform.system(),
        platform.release(),
        os.environ.get("USER", ""),
        os.environ.get("USERNAME", ""),
        os.environ.get("HOME", ""),
        os.environ.get("USERPROFILE", ""),
    ]
    return "|".join(part.strip().lower() for part in parts if part) or "spotify-artist-link-extractor"


def _bytes_from_blob(blob: DATA_BLOB) -> bytes:
    try:
        return ctypes.string_at(blob.pbData, blob.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(blob.pbData)


def _crypt_protect_data(data: bytes) -> bytes:
    data_buffer = ctypes.create_string_buffer(data)
    data_in = DATA_BLOB(len(data), ctypes.cast(data_buffer, ctypes.POINTER(ctypes.c_char)))
    data_out = DATA_BLOB()
    if not ctypes.windll.crypt32.CryptProtectData(
        ctypes.byref(data_in),
        None,
        None,
        None,
        None,
        0,
        ctypes.byref(data_out),
    ):
        raise RuntimeError("No se pudo proteger el secreto local.")
    return _bytes_from_blob(data_out)


def _crypt_unprotect_data(data: bytes) -> bytes:
    data_buffer = ctypes.create_string_buffer(data)
    data_in = DATA_BLOB(len(data), ctypes.cast(data_buffer, ctypes.POINTER(ctypes.c_char)))
    data_out = DATA_BLOB()
    if not ctypes.windll.crypt32.CryptUnprotectData(
        ctypes.byref(data_in),
        None,
        None,
        None,
        None,
        0,
        ctypes.byref(data_out),
    ):
        raise RuntimeError("No se pudo leer el secreto local protegido.")
    return _bytes_from_blob(data_out)
