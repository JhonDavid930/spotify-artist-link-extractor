# Security Audit

Copyright (c) 2026 Jhon David (art. David Appleton). All rights reserved.

## Scope

Audit performed from an attacker-minded defensive perspective against:

- Activation and license validation.
- Local Spotify credential storage.
- Packaged executable behavior.
- Spotify API error handling.
- Dependency vulnerability exposure.

## High-Risk Findings Fixed

### Embedded license signing secret

Previous risk: the app used an HMAC secret in application code. Anyone who obtained the source or reverse engineered the executable could forge licenses.

Fix: license validation now uses Ed25519 signatures. The executable contains only public verification capability. The private signing key stays outside Git in `tools/private/` or `SLE_LICENSE_PRIVATE_KEY_B64`.

### Setup cancel bypass

Previous risk: canceling activation allowed the main window to remain visible.

Fix: if the startup activation dialog is canceled without valid Spotify credentials and a valid license, the app exits immediately.

### Plaintext Spotify Client Secret storage

Previous risk: Spotify Client Secret was stored directly in local application settings.

Fix: on Windows, the Client Secret is protected using DPAPI before storage. On macOS/Linux, the app attempts to use the system keyring/keychain and falls back to local per-user encryption if no keyring backend is available. Existing plaintext values are migrated to protected storage after successful validation.

### Saving unverified credentials

Previous risk: any non-empty Client ID/Secret pair could be saved.

Fix: the setup dialog authenticates against Spotify Accounts before saving credentials.

## Medium-Risk Findings Fixed

### Clock rollback

Risk: users could try to extend offline license validity by moving the system clock backwards.

Fix: the app stores the last successful license validation date and rejects obvious rollback attempts.

### Weak payload validation

Risk: malformed or oversized license payloads could cause brittle validation paths.

Fix: license validation now checks prefix, token characters, maximum length, required fields, version, date order, maximum duration, license ID format, and signature.

### Spotify response hardening

Risk: malformed auth JSON or malformed `Retry-After` values could cause unclean failures.

Fix: authentication response parsing and rate-limit parsing now fail cleanly.

## Verification

Commands run:

```bash
python -m unittest discover -s tests -p "test_*.py"
python -m compileall app.py ui services spotify_api tools tests
python -m pip_audit -r requirements.txt
pyinstaller --noconfirm --clean --onefile --windowed --name SpotifyArtistLinkExtractor-Licensed --add-data "assets;assets" app.py
```

Results:

- Unit/security tests passed.
- Python compilation passed.
- `pip-audit` found no known vulnerabilities in product dependencies.
- Rebuilt executable does not contain the private Ed25519 signing key.
- `tools/private/` is ignored by Git.
- License Studio is an internal-only tool and must not be distributed with customer builds.

## Residual Risks

- Offline desktop licensing can be patched by a determined reverse engineer. Public-key signatures prevent license forgery, but no client-only system can be perfectly tamper-proof.
- DPAPI/keyring protection is user-context security. Malware running as the same OS user may still access data through that user's context. The local encrypted fallback is a compatibility layer, not a replacement for a managed OS keychain.
- Licenses can now be machine-bound with a customer-visible device code. A non-bound license is still intentionally portable.
- Offline machine binding raises the cost of casual sharing, but a determined reverse engineer could still patch a client-only desktop app.
- The executable is not code-signed yet. Windows SmartScreen and tamper trust would improve with a code-signing certificate.

## Recommended Next Hardening

- Add code signing for release builds.
- Add optional online license activation for higher-value distributions and remote renewal without sending a replacement key.
- Keep the private license signing key backed up offline and never commit it.
