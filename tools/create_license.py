"""Private helper for creating customer licenses."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.license_manager import create_license, generate_private_key
from services.machine_identity import get_machine_hash, normalize_machine_code


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a Spotify Artist Link Extractor license.")
    parser.add_argument("customer", nargs="?", help="Customer or buyer name")
    parser.add_argument("--days", type=int, default=60, help="License duration in days")
    parser.add_argument("--email", default="", help="Optional customer email")
    parser.add_argument("--license-id", default="", help="Existing license ID when renewing")
    parser.add_argument("--machine-code", default="", help="Optional customer machine code")
    parser.add_argument("--lifetime", action="store_true", help="Create a lifetime license")
    parser.add_argument(
        "--generate-private-key",
        action="store_true",
        help="Generate a new private/public key pair for a new product signing root.",
    )
    args = parser.parse_args()
    if args.generate_private_key:
        private_key, public_key = generate_private_key()
        print("PRIVATE_KEY_B64=" + private_key)
        print("PUBLIC_KEY_B64=" + public_key)
        return 0
    if not args.customer:
        parser.error("customer is required unless --generate-private-key is used")
    machine_hash = ""
    if args.machine_code:
        machine_hash = get_machine_hash(normalize_machine_code(args.machine_code))
    print(
        create_license(
            args.customer,
            args.days,
            email=args.email,
            license_id=args.license_id or None,
            lifetime=args.lifetime,
            machine_hash=machine_hash,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
