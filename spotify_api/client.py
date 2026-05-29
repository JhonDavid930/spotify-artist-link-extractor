"""Small Spotify Web API client using Client Credentials OAuth."""

from __future__ import annotations

import base64
import re
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Callable

import requests


class SpotifyApiError(RuntimeError):
    """Raised for Spotify API failures with clean user-facing messages."""


class SpotifyAuthError(SpotifyApiError):
    """Raised when Client Credentials authentication fails."""


class SpotifyRateLimitError(SpotifyApiError):
    """Raised when Spotify keeps rate-limiting after retries."""


@dataclass(frozen=True)
class SpotifyArtist:
    artist_id: str
    name: str
    spotify_url: str


class SpotifyClient:
    """Authenticated Spotify Web API client with in-memory token refresh."""

    TOKEN_URL = "https://accounts.spotify.com/api/token"
    API_BASE_URL = "https://api.spotify.com/v1"
    ARTIST_ALBUMS_LIMIT = 10
    ALBUM_TRACKS_LIMIT = 50
    TRACKS_BATCH_LIMIT = 50
    MAX_RATE_LIMIT_WAIT_SECONDS = 30
    MIN_REQUEST_INTERVAL_SECONDS = 1.0

    def __init__(self, client_id: str, client_secret: str, timeout: int = 30) -> None:
        if not client_id or not client_secret:
            raise SpotifyAuthError("Faltan SPOTIFY_CLIENT_ID o SPOTIFY_CLIENT_SECRET en el archivo .env.")
        self.client_id = client_id
        self.client_secret = client_secret
        self.timeout = timeout
        self.session = requests.Session()
        self._access_token: str | None = None
        self._expires_at = 0.0
        self._last_catalog_request_at = 0.0
        self.rate_limit_callback: Callable[[int], None] | None = None

    def authenticate(self) -> None:
        credentials = f"{self.client_id}:{self.client_secret}".encode("utf-8")
        encoded = base64.b64encode(credentials).decode("ascii")
        headers = {
            "Authorization": f"Basic {encoded}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        try:
            response = self.session.post(
                self.TOKEN_URL,
                headers=headers,
                data={"grant_type": "client_credentials"},
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise SpotifyAuthError(f"No se pudo conectar con Spotify Accounts: {exc}") from exc

        if response.status_code != 200:
            raise SpotifyAuthError("Spotify rechazó la autenticación. Revisa Client ID y Client Secret.")

        payload = response.json()
        self._access_token = payload["access_token"]
        self._expires_at = time.time() + int(payload.get("expires_in", 3600)) - 60

    def get_artist(self, artist_id: str) -> SpotifyArtist:
        payload = self.get(f"/artists/{artist_id}")
        return SpotifyArtist(
            artist_id=payload["id"],
            name=payload["name"],
            spotify_url=payload.get("external_urls", {}).get("spotify", ""),
        )

    def get_artist_albums(
        self,
        artist_id: str,
        include_groups: list[str],
        market: str | None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "include_groups": ",".join(include_groups),
            "limit": self.ARTIST_ALBUMS_LIMIT,
            "offset": 0,
        }
        if market:
            params["market"] = market

        albums: list[dict[str, Any]] = []
        while True:
            payload = self.get(f"/artists/{artist_id}/albums", params=params)
            albums.extend(payload.get("items", []))
            if not payload.get("next"):
                break
            params["offset"] += params["limit"]
        return albums

    def get_album_tracks(self, album_id: str, market: str | None) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"limit": self.ALBUM_TRACKS_LIMIT, "offset": 0}
        if market:
            params["market"] = market

        tracks: list[dict[str, Any]] = []
        while True:
            payload = self.get(f"/albums/{album_id}/tracks", params=params)
            tracks.extend(payload.get("items", []))
            if not payload.get("next"):
                break
            params["offset"] += params["limit"]
        return tracks

    def get_tracks(self, track_ids: list[str], market: str | None) -> dict[str, dict[str, Any]]:
        hydrated: dict[str, dict[str, Any]] = {}
        for chunk_start in range(0, len(track_ids), self.TRACKS_BATCH_LIMIT):
            chunk = track_ids[chunk_start : chunk_start + self.TRACKS_BATCH_LIMIT]
            params: dict[str, Any] = {"ids": ",".join(chunk)}
            if market:
                params["market"] = market
            try:
                payload = self.get("/tracks", params=params)
            except SpotifyRateLimitError:
                return hydrated
            except SpotifyApiError as exc:
                if "HTTP 403" not in str(exc) and "Forbidden" not in str(exc):
                    raise
                hydrated.update(self._get_tracks_individually(chunk, market))
                continue
            for track in payload.get("tracks", []):
                if track and track.get("id"):
                    hydrated[track["id"]] = track
        return hydrated

    def _get_tracks_individually(self, track_ids: list[str], market: str | None) -> dict[str, dict[str, Any]]:
        hydrated: dict[str, dict[str, Any]] = {}
        for track_id in track_ids:
            params: dict[str, Any] = {}
            if market:
                params["market"] = market
            try:
                track = self.get(f"/tracks/{track_id}", params=params)
            except SpotifyRateLimitError:
                break
            except SpotifyApiError:
                continue
            if track and track.get("id"):
                hydrated[track["id"]] = track
        return hydrated

    def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        self._ensure_token()
        url = f"{self.API_BASE_URL}{path}"
        return self._request("GET", url, params=params)

    def _ensure_token(self) -> None:
        if not self._access_token or time.time() >= self._expires_at:
            self.authenticate()

    def _request(self, method: str, url: str, **kwargs: Any) -> dict[str, Any]:
        for attempt in range(4):
            self._pace_catalog_requests()
            headers = kwargs.pop("headers", {})
            headers["Authorization"] = f"Bearer {self._access_token}"
            try:
                response = self.session.request(method, url, headers=headers, timeout=self.timeout, **kwargs)
            except requests.RequestException as exc:
                raise SpotifyApiError(f"Error de red al conectar con Spotify: {exc}") from exc

            if response.status_code == 401 and attempt == 0:
                self.authenticate()
                continue

            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", "1"))
                if self.rate_limit_callback:
                    self.rate_limit_callback(retry_after)
                if retry_after > self.MAX_RATE_LIMIT_WAIT_SECONDS:
                    raise SpotifyRateLimitError(
                        self._format_rate_limit_message(retry_after)
                    )
                time.sleep(retry_after)
                continue

            if response.status_code == 404:
                raise SpotifyApiError("Spotify no encontró ese artista o recurso. Revisa que el enlace sea de un perfil de artista público.")

            if response.status_code >= 400:
                raise SpotifyApiError(self._format_error_response(response))

            return response.json()

        raise SpotifyRateLimitError("Spotify sigue limitando la petición tras varios reintentos.")

    def _pace_catalog_requests(self) -> None:
        elapsed = time.time() - self._last_catalog_request_at
        if elapsed < self.MIN_REQUEST_INTERVAL_SECONDS:
            time.sleep(self.MIN_REQUEST_INTERVAL_SECONDS - elapsed)
        self._last_catalog_request_at = time.time()

    def _format_rate_limit_message(self, retry_after: int) -> str:
        retry_time = datetime.now() + timedelta(seconds=retry_after)
        return (
            "Spotify aplicó rate limit a esta app. "
            f"Retry-After: {retry_after}s. "
            f"Vuelve a probar aproximadamente a las {retry_time:%H:%M} "
            "o usa otro Client ID de una app nueva. No se esperará en segundo plano."
        )

    def _format_error_response(self, response: requests.Response) -> str:
        try:
            payload = response.json()
        except ValueError:
            payload = {}

        message = ""
        error = payload.get("error") if isinstance(payload, dict) else None
        if isinstance(error, dict):
            message = str(error.get("message", "")).strip()
        elif isinstance(error, str):
            message = error.strip()

        if not message:
            message = response.text[:220].strip()

        message = re.sub(r"\s+", " ", message)
        if message:
            return f"Spotify devolvió HTTP {response.status_code}: {message}"
        return f"Spotify devolvió un error HTTP {response.status_code}."
