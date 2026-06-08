"""Security-focused smoke tests."""

from __future__ import annotations

import unittest
from datetime import date

from services.license_manager import create_license, validate_license
from services.secure_store import protect_secret, unprotect_secret


VALID_TEST_LICENSE = (
    "SLE2.eyJjdXN0b21lciI6IlNlY3VyaXR5IFRlc3QiLCJleHBpcmVzX2F0IjoiMjAyNi0wMy0wMiIs"
    "Imlzc3VlZF9hdCI6IjIwMjYtMDEtMDEiLCJsaWNlbnNlX2lkIjoiMUZEODhDMkFERUI5MEVDMiIs"
    "InZlcnNpb24iOiJTTEUyIn0.gJvuXIv90ODdQ5Hse0WZAVOxpXqoulJEBN7ah-1CGRAvB7yz-ugXx"
    "QZyqO0MnoEHph64uJqiZXodZVim-TZZAQ"
)


class LicenseSecurityTests(unittest.TestCase):
    def test_valid_signed_license_passes(self) -> None:
        status = validate_license(VALID_TEST_LICENSE, today=date(2026, 1, 2))
        self.assertTrue(status.valid)

    def test_tampered_license_fails(self) -> None:
        tampered = VALID_TEST_LICENSE[:-1] + ("A" if VALID_TEST_LICENSE[-1] != "A" else "B")
        status = validate_license(tampered, today=date(2026, 1, 2))
        self.assertFalse(status.valid)

    def test_expired_license_fails(self) -> None:
        status = validate_license(VALID_TEST_LICENSE, today=date(2026, 3, 3))
        self.assertFalse(status.valid)

    def test_clock_rollback_fails(self) -> None:
        status = validate_license(
            VALID_TEST_LICENSE,
            today=date(2026, 1, 4),
            minimum_allowed_date=date(2026, 1, 5),
        )
        self.assertFalse(status.valid)

    def test_valid_license_near_expiration_still_passes(self) -> None:
        status = validate_license(VALID_TEST_LICENSE, today=date(2026, 2, 24))
        self.assertTrue(status.valid)
        self.assertEqual(status.expires_at, "2026-03-02")

    def test_public_license_format_validates(self) -> None:
        license_key = create_license("Public Format Test", 60, issued_at=date(2026, 1, 1))
        self.assertTrue(license_key.startswith("ADL-"))
        status = validate_license(license_key, today=date(2026, 1, 2))
        self.assertTrue(status.valid)
        self.assertEqual(status.customer, "Public Format Test")

    def test_machine_bound_license_rejects_other_machine(self) -> None:
        license_key = create_license(
            "Machine Bound Test",
            60,
            issued_at=date(2026, 1, 1),
            machine_hash="authorized-machine",
        )
        status = validate_license(license_key, today=date(2026, 1, 2), machine_hash="different-machine")
        self.assertFalse(status.valid)

    def test_lifetime_license_does_not_expire(self) -> None:
        license_key = create_license("Lifetime Test", issued_at=date(2026, 1, 1), lifetime=True)
        status = validate_license(license_key, today=date(2036, 1, 1))
        self.assertTrue(status.valid)
        self.assertTrue(status.lifetime)


class SecureStoreTests(unittest.TestCase):
    def test_secret_round_trip(self) -> None:
        secret = "spotify-client-secret-test"
        protected = protect_secret(secret)
        self.assertEqual(unprotect_secret(protected), secret)


if __name__ == "__main__":
    unittest.main()
