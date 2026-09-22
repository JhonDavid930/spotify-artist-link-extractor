#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
if [ -x "dist/SpotifyLicenseStudio" ]; then
  ./dist/SpotifyLicenseStudio
elif [ -x ".venv/bin/python" ]; then
  .venv/bin/python tools/license_studio.py
else
  python3 tools/license_studio.py
fi
