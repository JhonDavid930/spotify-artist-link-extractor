# Deploy Guide

Copyright (c) 2026 Jhon David (art. David Appleton). All rights reserved.

This is a desktop application. There is no server deploy.

## Local Setup

1. Install Python 3.11 or newer.
2. Open a terminal in the project folder.
3. Create a virtual environment.

Windows:

```bash
python -m venv .venv
.venv\Scripts\activate
```

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

4. Install dependencies.

```bash
pip install -r requirements.txt
```

5. Run the app.
6. Enter Spotify Client ID, Spotify Client Secret, and a valid license in the setup dialog.

```bash
python app.py
```

On macOS/Linux you can also run:

```bash
./run_app.sh
```

## Production Notes

- Keep `.env` private.
- Use a separate Spotify Developer app for production distribution.
- Package with PyInstaller only after testing the normal Python run path.
- Do not bundle real credentials inside a packaged executable.
- For customer builds, distribute the licensed executable without `.env`.
- Include the `assets` directory in PyInstaller builds so the app logo and branded activation dialog render correctly.
- Keep `tools/private/` out of Git. It contains the Ed25519 private signing key.
- Generate customer licenses with `python tools/create_license.py "Customer Name" --days 60`.
- Or use the internal desktop generator with `run_license_studio.bat` on Windows or `./run_license_studio.sh` on macOS/Linux.
- If building from a clean machine, set `SLE_LICENSE_PRIVATE_KEY_B64` or recreate `tools/private/ed25519_private_key.txt` before generating licenses.

## Cross-Platform Builds

PyInstaller builds must be created on the target operating system. Build Windows on Windows, macOS on macOS, and Linux on Linux.

Customer app:

```bash
python tools/build.py app
```

Internal License Studio:

```bash
python tools/build.py license-studio
```

Expected output:

- Windows: `dist/SpotifyArtistLinkExtractor-Licensed.exe`
- macOS: `dist/SpotifyArtistLinkExtractor-Licensed`
- Linux: `dist/SpotifyArtistLinkExtractor-Licensed`

For polished public distribution, wrap the generated app with a platform-native installer:

- Windows: Inno Setup, MSIX, or NSIS.
- macOS: signed `.app` plus `.dmg`.
- Linux: AppImage, `.deb`, `.rpm`, or Flatpak.
