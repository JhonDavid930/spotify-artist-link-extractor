"""Helpers for parsing Spotify identifiers from user input."""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse


SPOTIFY_ID_PATTERN = re.compile(r"^[A-Za-z0-9]{22}$")


class SpotifyUrlError(ValueError):
    """Raised when an artist URL or URI cannot be parsed safely."""


@dataclass(frozen=True)
class SpotifyInput:
    item_type: str
    item_id: str


SUPPORTED_TYPES = {"artist", "album", "track"}


def extract_artist_id(value: str) -> str:
    """Extract a Spotify artist ID from common web URLs or Spotify URIs."""
    parsed_input = extract_spotify_input(value)
    if parsed_input.item_type != "artist":
        raise SpotifyUrlError("La URL debe ser de artista para esta operación.")
    return parsed_input.item_id


def extract_spotify_input(value: str) -> SpotifyInput:
    """Extract a Spotify artist, album, or track ID from web URLs or Spotify URIs."""
    candidate = value.strip()
    if not candidate:
        raise SpotifyUrlError("Pega una URL o URI de Spotify.")

    if candidate.startswith("spotify:"):
        parts = candidate.split(":")
        if len(parts) != 3 or parts[1] not in SUPPORTED_TYPES:
            raise SpotifyUrlError("La URI debe ser spotify:artist:ID, spotify:album:ID o spotify:track:ID.")
        return SpotifyInput(parts[1], _validate_spotify_id(parts[2].strip(), parts[1]))

    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https"} or parsed.netloc.lower() != "open.spotify.com":
        raise SpotifyUrlError("La URL debe pertenecer a open.spotify.com o usar una URI spotify:tipo:ID.")

    parts = [part for part in parsed.path.split("/") if part]
    item_type = next((part for part in parts if part in SUPPORTED_TYPES), "")
    if not item_type:
        raise SpotifyUrlError("La URL debe ser de artista, album o track de Spotify.")

    item_index = parts.index(item_type)
    if item_index + 1 >= len(parts):
        raise SpotifyUrlError("No se encontró el ID de Spotify en la URL.")

    return SpotifyInput(item_type, _validate_spotify_id(parts[item_index + 1], item_type))


def _validate_spotify_id(item_id: str, item_type: str) -> str:
    if not SPOTIFY_ID_PATTERN.match(item_id):
        raise SpotifyUrlError(f"El ID de {item_type} de Spotify no tiene un formato válido.")
    return item_id


def normalize_album_key(name: str, release_date: str) -> str:
    normalized_name = re.sub(r"[^a-z0-9]+", " ", name.lower()).strip()
    return f"{normalized_name}|{release_date.strip()}"
