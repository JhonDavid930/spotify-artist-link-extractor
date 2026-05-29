# Changelog

Copyright (c) 2026 Jhon David (art. David Appleton). All rights reserved.

## 0.1.0 - 2026-05-27

- Created PySide6 desktop app structure.
- Added Spotify Client Credentials authentication.
- Added artist URL and URI parser.
- Added album and track extraction with pagination.
- Added track metadata enrichment through batch `/tracks` endpoint.
- Added album and track deduplication strategies.
- Added sortable, searchable results table.
- Added copy actions and export to CSV, TXT, Excel, and JSON.
- Added dark professional desktop interface.
- Updated Spotify pagination compatibility for Developer Mode apps that reject `limit` values above 10 on artist albums.
- Added fallback from blocked batch track metadata endpoint to individual track metadata requests.
- Added a hard cap for large Spotify `Retry-After` values so the desktop app does not freeze for hours.
- Allowed extraction to finish with simplified track metadata when Spotify rate-limits full track enrichment.
- Added optional ISRC/popularity enrichment, disabled by default to avoid exhausting Spotify Developer Mode limits.
- Optimized the default path for fast official Spotify track link extraction without full metadata calls.
- Added one-second request pacing to reduce Spotify Development Mode 429 errors during large artist extractions.
- Improved rate-limit messages with actionable retry timing instead of a vague background wait.
- Skipped the artist profile endpoint in default link-only mode to save one catalog request per extraction.
- Added support for direct Spotify album and track URLs/URIs in addition to artist profiles.
- Added project copyright notice for Jhon David (art. David Appleton).
