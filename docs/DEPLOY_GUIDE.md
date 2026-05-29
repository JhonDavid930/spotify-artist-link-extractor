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

5. Create `.env` from `.env.example`.
6. Add your Spotify Client ID and Client Secret.
7. Run the app.

```bash
python app.py
```

## Production Notes

- Keep `.env` private.
- Use a separate Spotify Developer app for production distribution.
- Package with PyInstaller only after testing the normal Python run path.
- Do not bundle real credentials inside a packaged executable.
