"""Offline license creation and validation with asymmetric signatures."""

from __future__ import annotations

import base64
import json
import os
import re
import secrets
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey


LEGACY_LICENSE_PREFIX = "SLE2"
PUBLIC_LICENSE_PREFIX = "ADL"
LICENSE_PREFIX = LEGACY_LICENSE_PREFIX
PUBLIC_KEY_B64 = "cGY6Fe1LN9EItFBijRqdqvvLsJPZhZgaPYiQz2yKEJE"
MAX_LICENSE_DAYS = 366
MAX_LICENSE_LENGTH = 4096
TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")
PUBLIC_TOKEN_PATTERN = re.compile(r"^[A-Z2-7-]+$")


@dataclass(frozen=True)
class LicenseStatus:
    valid: bool
    message: str
    customer: str = ""
    expires_at: str = ""
    license_id: str = ""
    email: str = ""
    lifetime: bool = False
    machine_bound: bool = False


def create_license(
    customer: str,
    days: int = 60,
    issued_at: date | None = None,
    *,
    email: str = "",
    license_id: str | None = None,
    lifetime: bool = False,
    machine_hash: str = "",
) -> str:
    """Create a signed license with a private key that is never bundled in the app."""
    if not lifetime and (days < 1 or days > MAX_LICENSE_DAYS):
        raise ValueError(f"License duration must be between 1 and {MAX_LICENSE_DAYS} days.")

    start_date = issued_at or date.today()
    normalized_email = email.strip().lower()[:160]
    payload = {
        "customer": customer.strip()[:120] or "Licensed User",
        "email": normalized_email,
        "issued_at": start_date.isoformat(),
        "expires_at": None if lifetime else (start_date + timedelta(days=days)).isoformat(),
        "license_id": license_id or secrets.token_hex(8).upper(),
        "lifetime": lifetime,
        "machine_hash": machine_hash.strip().lower(),
        "nonce": secrets.token_urlsafe(12),
        "version": PUBLIC_LICENSE_PREFIX,
    }
    payload_bytes = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    payload_token = _b64encode(payload_bytes)
    signature = _sign_with_private_key(payload_token.encode("ascii"))
    envelope = json.dumps(
        {"payload": payload_token, "signature": signature},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return _format_public_key(_public_encode(envelope))


def validate_license(
    license_key: str,
    today: date | None = None,
    minimum_allowed_date: date | None = None,
    machine_hash: str | None = None,
) -> LicenseStatus:
    key = license_key.strip()
    if not key:
        return LicenseStatus(False, "Falta la licencia.")
    if len(key) > MAX_LICENSE_LENGTH:
        return LicenseStatus(False, "La licencia es demasiado larga.")

    try:
        decoded_key = _decode_public_key(key) if _looks_like_public_key(key) else key
    except (ValueError, json.JSONDecodeError):
        return LicenseStatus(False, "Formato de licencia inválido.")
    parts = decoded_key.split(".")
    if len(parts) == 3 and parts[0] == LEGACY_LICENSE_PREFIX:
        payload_token, signature_token = parts[1], parts[2]
    elif len(parts) == 2:
        payload_token, signature_token = parts[0], parts[1]
    else:
        return LicenseStatus(False, "Formato de licencia inválido.")

    if not TOKEN_PATTERN.fullmatch(payload_token) or not TOKEN_PATTERN.fullmatch(signature_token):
        return LicenseStatus(False, "La licencia contiene caracteres inválidos.")

    try:
        _public_key().verify(_b64decode(signature_token), payload_token.encode("ascii"))
        payload = json.loads(_b64decode(payload_token).decode("utf-8"))
    except (InvalidSignature, ValueError, json.JSONDecodeError):
        return LicenseStatus(False, "Firma de licencia inválida.")

    parsed = _parse_payload(payload)
    if not parsed.valid:
        return parsed

    issued_at = datetime.strptime(str(payload["issued_at"]), "%Y-%m-%d").date()
    expires_value = payload.get("expires_at")
    lifetime = bool(payload.get("lifetime"))
    expires_at = None if lifetime else datetime.strptime(str(expires_value), "%Y-%m-%d").date()
    current_date = today or date.today()
    license_machine_hash = str(payload.get("machine_hash", "")).strip().lower()

    if minimum_allowed_date and current_date < minimum_allowed_date:
        return LicenseStatus(False, "Reloj del sistema no válido para esta licencia.")
    if issued_at > current_date + timedelta(days=1):
        return LicenseStatus(False, "La licencia todavía no es válida.")
    if license_machine_hash and machine_hash and license_machine_hash != machine_hash.strip().lower():
        return LicenseStatus(False, "Esta licencia pertenece a otro equipo.")
    if license_machine_hash and machine_hash is None:
        return LicenseStatus(False, "No se pudo validar el equipo autorizado.")
    if expires_at and current_date > expires_at:
        return LicenseStatus(
            False,
            f"Licencia expirada el {expires_at.isoformat()}.",
            customer=str(payload.get("customer", "")),
            expires_at=expires_at.isoformat(),
            license_id=str(payload.get("license_id", "")),
            email=str(payload.get("email", "")),
            lifetime=lifetime,
            machine_bound=bool(license_machine_hash),
        )

    return LicenseStatus(
        True,
        "Licencia vitalicia válida." if lifetime else f"Licencia válida hasta {expires_at.isoformat()}.",
        customer=str(payload.get("customer", "")),
        expires_at="Lifetime" if lifetime else (expires_at.isoformat() if expires_at else ""),
        license_id=str(payload.get("license_id", "")),
        email=str(payload.get("email", "")),
        lifetime=lifetime,
        machine_bound=bool(license_machine_hash),
    )


def generate_private_key() -> tuple[str, str]:
    private_key = Ed25519PrivateKey.generate()
    private_raw = private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_raw = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return _b64encode(private_raw), _b64encode(public_raw)


def _parse_payload(payload: object) -> LicenseStatus:
    if not isinstance(payload, dict):
        return LicenseStatus(False, "Contenido de licencia inválido.")

    required = {"customer", "issued_at", "expires_at", "license_id", "version"}
    if not required.issubset(payload):
        return LicenseStatus(False, "Contenido de licencia incompleto.")
    if payload.get("version") not in {LEGACY_LICENSE_PREFIX, PUBLIC_LICENSE_PREFIX}:
        return LicenseStatus(False, "Versión de licencia no soportada.")
    if not isinstance(payload.get("customer"), str) or len(payload["customer"]) > 120:
        return LicenseStatus(False, "Cliente de licencia inválido.")
    if not isinstance(payload.get("email", ""), str) or len(str(payload.get("email", ""))) > 160:
        return LicenseStatus(False, "Email de licencia inválido.")
    if not isinstance(payload.get("license_id"), str) or not re.fullmatch(r"[A-F0-9]{16}", payload["license_id"]):
        return LicenseStatus(False, "ID de licencia inválido.")
    if not isinstance(payload.get("machine_hash", ""), str) or len(str(payload.get("machine_hash", ""))) > 128:
        return LicenseStatus(False, "Equipo de licencia inválido.")

    try:
        issued_at = datetime.strptime(str(payload["issued_at"]), "%Y-%m-%d").date()
        lifetime = bool(payload.get("lifetime"))
        expires_at = None if lifetime else datetime.strptime(str(payload["expires_at"]), "%Y-%m-%d").date()
    except ValueError:
        return LicenseStatus(False, "Fechas de licencia inválidas.")

    if not lifetime and expires_at:
        duration = (expires_at - issued_at).days
    else:
        duration = 1
    if not lifetime and (duration < 1 or duration > MAX_LICENSE_DAYS):
        return LicenseStatus(False, "Duración de licencia inválida.")

    return LicenseStatus(True, "Licencia estructuralmente válida.")


def _looks_like_public_key(key: str) -> bool:
    normalized = key.strip()
    return normalized.upper().startswith(f"{PUBLIC_LICENSE_PREFIX}-") and bool(PUBLIC_TOKEN_PATTERN.fullmatch(normalized))


def _format_public_key(token: str) -> str:
    grouped = "-".join(token[index : index + 5] for index in range(0, len(token), 5))
    return f"{PUBLIC_LICENSE_PREFIX}-{grouped}"


def _decode_public_key(key: str) -> str:
    parts = key.strip().split("-")
    if not parts or parts[0].upper() != PUBLIC_LICENSE_PREFIX:
        raise ValueError("Invalid public license prefix.")
    public_token = "".join(parts[1:])
    envelope = json.loads(_public_decode(public_token).decode("utf-8"))
    if not isinstance(envelope, dict):
        raise ValueError("Invalid public license envelope.")
    payload_token = str(envelope.get("payload", ""))
    signature_token = str(envelope.get("signature", ""))
    return f"{payload_token}.{signature_token}"


def _public_encode(value: bytes) -> str:
    return base64.b32encode(value).decode("ascii").rstrip("=")


def _public_decode(value: str) -> bytes:
    normalized = value.strip().upper()
    padding = "=" * (-len(normalized) % 8)
    return base64.b32decode(normalized + padding)


def _private_key() -> Ed25519PrivateKey:
    private_key_b64 = os.environ.get("SLE_LICENSE_PRIVATE_KEY_B64", "").strip()
    if not private_key_b64:
        key_path = _private_key_path()
        if key_path.exists():
            private_key_b64 = key_path.read_text(encoding="utf-8").strip()
    if not private_key_b64:
        raise RuntimeError(
            "Missing private license key. Set SLE_LICENSE_PRIVATE_KEY_B64 or create tools/private/ed25519_private_key.txt."
        )
    return Ed25519PrivateKey.from_private_bytes(_b64decode(private_key_b64))


def _private_key_path() -> Path:
    candidates = [
        Path.cwd() / "tools" / "private" / "ed25519_private_key.txt",
        Path(__file__).resolve().parents[1] / "tools" / "private" / "ed25519_private_key.txt",
    ]
    if getattr(sys, "frozen", False):
        candidates.insert(0, Path(sys.executable).resolve().parent / "tools" / "private" / "ed25519_private_key.txt")
    return next((path for path in candidates if path.exists()), candidates[0])


def _public_key() -> Ed25519PublicKey:
    return Ed25519PublicKey.from_public_bytes(_b64decode(PUBLIC_KEY_B64))


def _sign_with_private_key(message: bytes) -> str:
    return _b64encode(_private_key().sign(message))


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)
