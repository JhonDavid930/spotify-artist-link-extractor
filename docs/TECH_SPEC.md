# Technical Specification

Copyright (c) 2026 Jhon David (art. David Appleton). All rights reserved.

## Architecture

The app is split into four layers:

- `app.py`: PySide6 application entry point.
- `ui/main_window.py`: UI composition, table model, background worker, status, copy, and export actions.
- `spotify_api/`: URL parsing and Spotify Web API client.
- `services/`: extraction orchestration and file exporters.

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

- Secrets are loaded from `.env`.
- No secrets are committed.
- No scraping.
- No audio download.
- Only official HTTPS Spotify Web API endpoints are used.
