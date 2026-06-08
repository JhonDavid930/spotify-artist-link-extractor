# Technical Specification

Copyright (c) 2026 Jhon David (art. David Appleton). All rights reserved.

## Architecture

The app is split into four layers:

- `app.py`: PySide6 application entry point.
- `ui/main_window.py`: UI composition, table model, background worker, status, copy, and export actions.
- `spotify_api/`: URL parsing and Spotify Web API client.
- `services/`: extraction orchestration and file exporters.
- `assets/`: packaged brand assets used by the desktop window and activation dialog.

## Brand And UX System

The desktop UI uses a dark creative visual system aimed at artists, managers, and non-technical creative teams. The interface avoids developer-first wording where possible and favors direct actions such as extracting, copying, and exporting links.

Core brand asset:

- `assets/brand_mark.png`: premium app mark combining link, waveform, spotlight, green accent, and champagne highlight.

Packaging uses `resource_path()` so the same asset path works both in local Python runs and inside PyInstaller one-file builds.

## Spotify API

Authentication uses Client Credentials OAuth:

- `POST https://accounts.spotify.com/api/token`
- `grant_type=client_credentials`
- `Authorization: Basic base64(client_id:client_secret)`

Catalog endpoints:

- `GET /v1/artists/{artist_id}`
- `GET /v1/artists/{artist_id}/albums`
- `GET /v1/albums/{album_id}/tracks`
- `GET /v1/tracks?ids=...`

Artist albums pagination uses `limit=10` because Spotify Developer Mode apps currently reject higher values on this endpoint. Album tracks pagination uses `limit=50`. Both increment `offset` until `next` is empty.

The default extraction path is optimized for Spotify track links. It uses artist albums plus album tracks and does not call full track metadata endpoints unless the user enables enrichment. It also skips `GET /artists/{id}` by default and infers the artist name from album artist metadata when available.

Track metadata enrichment is optional and disabled by default to preserve Spotify Developer Mode quota. When enabled, it first tries the batch `/tracks?ids=...` endpoint. If Spotify blocks it with `403 Forbidden`, the client falls back to individual `/tracks/{id}` requests so ISRC and popularity can still be collected when the single-track endpoint is available.

Catalog requests are paced at one request per second by default. This keeps link extraction slower but more stable under Spotify Development Mode limits.

## Error Handling

The client converts low-level failures into user-facing exceptions:

- Missing credentials
- Authentication failure
- Network errors
- HTTP 404
- HTTP 429 with automatic `Retry-After` wait and retry
- Generic Spotify HTTP errors

## Deduplication

Albums:

- Always deduped by album ID.
- Optionally deduped by normalized album name plus release date.

Tracks:

- Always deduped by track ID.
- Optionally deduped by ISRC after full track metadata enrichment.

## UI Threading

Extraction runs in `ExtractionWorker`, a `QThread` subclass.

The worker emits:

- `progress(step, percent, stats)`
- `finished(artist, records, stats)`
- `failed(message)`

The main thread only updates widgets from Qt signal handlers.
Long artist extractions support cooperative pause/resume. The UI marks the worker as canceled, the extractor stops at safe album checkpoints, returns partial records plus completed album IDs, and the next run can skip completed albums to continue without repeating finished album requests.

## Data Model

`TrackRecord` stores table fields and additional metadata:

- track ID, track name, artists, artist IDs
- album ID, album name, album type, release date, total tracks
- duration, explicit flag, ISRC, popularity, preview URL
- official Spotify track URL

## Supported Input Types

The parser accepts Spotify web URLs and Spotify URIs for:

- artist: extracts all track links from selected release groups.
- album: extracts all track links from that album.
- track: normalizes and returns that single track link without an API request.

## Security

- Runtime Spotify credentials are entered by the user through the setup dialog and stored in local OS application settings.
- Spotify Client Secret is protected with Windows DPAPI on Windows, system keyring/keychain when available on macOS/Linux, or a local per-user encrypted fallback.
- The setup dialog verifies Spotify credentials against the Spotify Accounts API before saving them.
- Distributed builds do not embed the developer `.env` file.
- Licenses are offline keys signed with Ed25519 and expire by date.
- The executable embeds only the Ed25519 public verification key. The private signing key is stored outside Git under `tools/private/` or provided through `SLE_LICENSE_PRIVATE_KEY_B64`.
- The app stores the last successful validation date and rejects obvious clock rollback attempts.
- No secrets are committed.
- No scraping.
- No audio download.
- Only official HTTPS Spotify Web API endpoints are used.

## Licensing

- The application validates license keys before extraction.
- Customer-facing keys use the grouped `ADL-...` format.
- Legacy `SLE2` keys remain supported for compatibility.
- signature: Ed25519 over the payload token

The private generator lives in `tools/create_license.py` and defaults to 60 days.
When a valid license has 7 days or less remaining, the UI shows a renewal warning once per day.
