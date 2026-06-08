"""Cross-platform PyInstaller build helper."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Build desktop executables for the current operating system.")
    parser.add_argument(
        "target",
        choices=("app", "license-studio"),
        help="Build the customer app or the internal License Studio.",
    )
    args = parser.parse_args()

    if args.target == "app":
        entrypoint = "app.py"
        name = "SpotifyArtistLinkExtractor-Licensed"
    else:
        entrypoint = "tools/license_studio.py"
        name = "SpotifyLicenseStudio"

    data_separator = ";" if os.name == "nt" else ":"
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--windowed",
        "--name",
        name,
        "--add-data",
        f"assets{data_separator}assets",
        entrypoint,
    ]
    subprocess.run(command, cwd=PROJECT_ROOT, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
