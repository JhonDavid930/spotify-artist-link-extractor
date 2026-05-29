# Spotify Artist Link Extractor

Desktop app in Python 3.11+ to extract official Spotify track links from a Spotify artist profile using the Spotify Web API.

The app does not scrape Spotify pages, does not download audio, and only retrieves metadata plus official track URLs.

## Ownership

Copyright (c) 2026 Jhon David (art. David Appleton). All rights reserved.

See [COPYRIGHT.md](COPYRIGHT.md) for the project authorship notice.

## Features

- Paste Spotify artist, album, or track URLs/URIs.
- Supports `open.spotify.com/artist/...`, `/album/...`, `/track/...`, localized URLs like `/intl-es/artist/...`, query strings, and Spotify URIs.
- Uses Spotify Client Credentials OAuth flow.
- Fetches artist albums, singles, appears_on, and compilations with pagination.
- Deduplicates albums and tracks.
- Extracts official Spotify track URLs quickly from artist albums and singles.
- Skips the artist profile endpoint by default to reduce API usage in link-only mode.
- Optional enrichment with ISRC, popularity, and preview URL.
- Optional ISRC/popularity enrichment. It is disabled by default because new Spotify Developer Mode apps can rate-limit or block bulk metadata enrichment.
- Modern PySide6 dark desktop UI with sortable/searchable table.
- Exports CSV, TXT, Excel, and JSON.

## Create A Spotify Developer App

1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard).
2. Sign in with your Spotify account.
3. Click **Create app**.
4. Add an app name and description.
5. Use any valid Redirect URI, for example `http://localhost:8888/callback`.
6. Save the app.
7. Open the app settings and copy:
   - Client ID
   - Client Secret

This desktop tool uses the Client Credentials flow, so it does not need user login or playlist permissions.

## Configure Environment

Copy `.env.example` to `.env` in this folder:

```ini
SPOTIFY_CLIENT_ID=your_client_id_here
SPOTIFY_CLIENT_SECRET=your_client_secret_here
```

Never commit `.env` to Git. Secrets stay local.

## Install

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

On macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python app.py
```

## User Flow

1. Open the app.
2. Paste a Spotify artist, album, or track URL/URI.
3. Choose market and album group options.
4. Click **Extract Tracks**.
5. Review the sortable/filterable results table.
6. Export as CSV, TXT, Excel, or JSON.

## Spotify Developer Mode Limits

Spotify may apply strict rate limits to new Developer Mode apps. The app avoids long freezes by refusing to wait for very large `Retry-After` values. Full metadata enrichment can require many individual track requests when Spotify blocks batch metadata, so it is optional and disabled by default. For normal link extraction, leave **Enrich ISRC/popularity metadata** turned off.

The default link-only mode uses the smallest practical API surface:

- list artist releases
- list tracks inside each release
- deduplicate by Spotify track ID

It skips full track metadata and artist profile lookups.

## Documentation

Deep project documentation lives in:

- [docs/TECH_SPEC.md](docs/TECH_SPEC.md)
- [docs/DEPLOY_GUIDE.md](docs/DEPLOY_GUIDE.md)
- [docs/CHANGELOG.md](docs/CHANGELOG.md)
