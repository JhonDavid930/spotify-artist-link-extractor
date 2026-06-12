# Changelog

Copyright (c) 2026 Jhon David (art. David Appleton). All rights reserved.

## 1.0.0 - 2026-06-12

- Prepared the first distributable Windows release package for customers.
- Added private License Studio for creating, renewing, suspending, revoking, reactivating, copying, saving, and emailing customer licenses.
- Added customer inventory with optional email, device code binding, remaining-time status, lifetime licenses, and organized private license storage.
- Added customer-facing activation keys with a cleaner grouped format while preserving signed offline validation.
- Added optional machine-bound licenses using a customer-visible device code from the activation dialog.
- Added secure runtime activation with Spotify credentials and customer license validation.
- Added cross-platform build helper for Windows, macOS, and Linux PyInstaller builds.
- Added macOS/Linux shell launchers and cross-platform secret protection through system keyring/keychain with encrypted local fallback.
- Added resumable extraction, cancel support, manual expanded results view, and one-button export menu.
- Added premium branding, dark interface refinements, Spanish customer-facing copy, and Spotify Developer shortcut.
- Added security audit documentation, unit/security tests, and dependency vulnerability audit workflow.
- Fixed License Studio private key discovery when running the packaged executable from `dist/`.

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
- Added runtime setup dialog for Spotify API credentials.
- Added offline 60-day license key validation and private license generator.
- Prepared distributable builds to avoid embedding Spotify API credentials.
- Refined API and license setup UX with grouped sections, helper text, clearer validation feedback, and stronger dark-mode styling.
- Added a premium app logo/brand mark for creative users and applied it to the main window, activation dialog, and application icon.
- Redesigned the desktop UX copy and dark visual system so the product feels clearer for artists, managers, and non-technical users.
- Fixed activation security flow so canceling the initial setup without valid credentials and license closes the app instead of opening the main interface.
- Replaced embedded HMAC license signing secret with Ed25519 public-key verification.
- Added Windows DPAPI protection for locally stored Spotify Client Secret values.
- Added Spotify credential verification before saving activation settings.
- Added basic clock-rollback detection through the last successful license validation date.
- Added internal License Studio desktop UI for generating, copying, and saving signed customer licenses.
- Added a safe cancel button for long Spotify extractions.
- Added expanded results view so large link lists have more table space after extraction.
- Upgraded stopping behavior into resumable extraction checkpoints that continue from completed albums.
- Replaced separate export buttons with one Export dropdown menu.
- Made expanded results view manual-only instead of automatically activating after extraction.
- Added renewal warning when a valid license has 7 days or less remaining.
- Added customer-facing activation keys with a cleaner grouped format while preserving signed offline validation.
- Added optional machine-bound licenses using a customer-visible device code from the activation dialog.
- Upgraded License Studio into a private inventory manager with customer name, optional email, device code, remaining time, renewal, lifetime licenses, TXT saving, and email draft preparation.
- Added cross-platform build helper for Windows, macOS, and Linux PyInstaller builds.
- Added macOS/Linux shell launchers and cross-platform secret protection through system keyring/keychain with encrypted local fallback.
