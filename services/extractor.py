"""Track extraction orchestration for Spotify artist catalog data."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Callable

from spotify_api.client import SpotifyArtist, SpotifyClient
from spotify_api.parser import normalize_album_key


@dataclass(frozen=True)
class ExtractionOptions:
    include_groups: list[str]
    market: str | None
    dedupe_albums_by_name_release: bool = False
    dedupe_tracks_by_isrc: bool = False
    only_main_artist_tracks: bool = True
    enrich_full_metadata: bool = False
    fetch_artist_profile: bool = False
    skip_album_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class ExtractionStats:
    albums_found: int = 0
    albums_unique: int = 0
    tracks_found: int = 0
    tracks_unique: int = 0


@dataclass
class TrackRecord:
    artist_searched: str
    track_name: str
    track_artists: str
    album_name: str
    album_type: str
    release_date: str
    track_number: int
    disc_number: int
    duration: str
    explicit: bool
    isrc: str
    spotify_track_url: str
    track_id: str
    album_id: str
    duration_ms: int
    popularity: int | None
    preview_url: str
    artist_ids: str
    album_release_date: str
    album_total_tracks: int

    def to_table_row(self) -> dict[str, object]:
        return {
            "Artist Searched": self.artist_searched,
            "Track Name": self.track_name,
            "Track Artists": self.track_artists,
            "Album Name": self.album_name,
            "Album Type": self.album_type,
            "Release Date": self.release_date,
            "Track Number": self.track_number,
            "Disc Number": self.disc_number,
            "Duration": self.duration,
            "Explicit": "Yes" if self.explicit else "No",
            "ISRC": self.isrc,
            "Spotify Track URL": self.spotify_track_url,
            "Track ID": self.track_id,
            "Album ID": self.album_id,
        }

    def to_metadata(self) -> dict[str, object]:
        return asdict(self)


ProgressCallback = Callable[[str, int, ExtractionStats], None]
CancelCallback = Callable[[], bool]


class ExtractionCancelled(RuntimeError):
    """Raised when the user cancels extraction after a safe checkpoint."""

    def __init__(
        self,
        message: str,
        artist: SpotifyArtist | None = None,
        records: list[TrackRecord] | None = None,
        stats: ExtractionStats | None = None,
        completed_album_ids: set[str] | None = None,
    ) -> None:
        super().__init__(message)
        self.artist = artist
        self.records = records or []
        self.stats = stats or ExtractionStats()
        self.completed_album_ids = completed_album_ids or set()


class SpotifyArtistExtractor:
    """Coordinates Spotify API calls and deterministic deduplication."""

    def __init__(
        self,
        client: SpotifyClient,
        progress_callback: ProgressCallback | None = None,
        cancel_callback: CancelCallback | None = None,
    ) -> None:
        self.client = client
        self.progress_callback = progress_callback
        self.cancel_callback = cancel_callback

    def extract(self, artist_id: str, options: ExtractionOptions) -> tuple[SpotifyArtist, list[TrackRecord], ExtractionStats]:
        stats = ExtractionStats()
        self._emit("Authenticating", 5, stats)
        self.client.authenticate()

        self._emit("Fetching albums", 20, stats)
        albums = self.client.get_artist_albums(artist_id, options.include_groups, options.market)
        artist = self._resolve_artist(artist_id, albums, options.fetch_artist_profile)
        albums_unique = self._dedupe_albums(albums, options.dedupe_albums_by_name_release)
        stats = ExtractionStats(albums_found=len(albums), albums_unique=len(albums_unique))
        self._emit("Fetching tracks", 35, stats)

        skip_album_ids = set(options.skip_album_ids)
        completed_album_ids = set(skip_album_ids)
        simplified_records: list[TrackRecord] = []
        for index, album in enumerate(albums_unique, start=1):
            album_id = album.get("id", "")
            if album_id in skip_album_ids:
                continue
            self._raise_if_cancelled(artist, simplified_records, stats, completed_album_ids)
            tracks = self.client.get_album_tracks(album_id, options.market)
            for track in tracks:
                if not track or not track.get("id"):
                    continue
                if options.only_main_artist_tracks and not self._has_artist(track, artist.artist_id):
                    continue
                simplified_records.append(self._build_record(artist, album, track, None))
            if album_id:
                completed_album_ids.add(album_id)
            progress = 35 + int((index / max(len(albums_unique), 1)) * 35)
            unique_partial = self._dedupe_tracks_by_id(simplified_records)
            stats = ExtractionStats(
                albums_found=len(albums),
                albums_unique=len(albums_unique),
                tracks_found=len(simplified_records),
                tracks_unique=len(unique_partial),
            )
            self._emit("Fetching tracks", progress, stats)
            self._raise_if_cancelled(artist, unique_partial, stats, completed_album_ids)

        unique_by_id = self._dedupe_tracks_by_id(simplified_records)
        stats = ExtractionStats(
            albums_found=len(albums),
            albums_unique=len(albums_unique),
            tracks_found=len(simplified_records),
            tracks_unique=len(unique_by_id),
        )
        if options.enrich_full_metadata:
            self._emit("Enriching metadata", 75, stats)
        else:
            self._emit("Preparing links", 90, stats)

        full_tracks = {}
        if options.enrich_full_metadata:
            self._raise_if_cancelled(artist, unique_by_id, stats, completed_album_ids)
            full_tracks = self.client.get_tracks([record.track_id for record in unique_by_id], options.market)
        enriched = [
            self._merge_full_track(record, full_tracks.get(record.track_id))
            for record in unique_by_id
        ]

        if options.dedupe_tracks_by_isrc and options.enrich_full_metadata:
            enriched = self._dedupe_tracks_by_isrc(enriched)

        stats = ExtractionStats(
            albums_found=len(albums),
            albums_unique=len(albums_unique),
            tracks_found=len(simplified_records),
            tracks_unique=len(enriched),
        )
        if options.enrich_full_metadata and len(full_tracks) < len(unique_by_id):
            self._emit("Done - Spotify limited some full metadata", 100, stats)
        else:
            self._emit("Done", 100, stats)
        return artist, enriched, stats

    def extract_album(self, album_id: str, options: ExtractionOptions) -> tuple[SpotifyArtist, list[TrackRecord], ExtractionStats]:
        stats = ExtractionStats()
        self._emit("Authenticating", 5, stats)
        self.client.authenticate()

        self._emit("Fetching album tracks", 30, stats)
        self._raise_if_cancelled()
        album = {
            "id": album_id,
            "name": "",
            "album_type": "album",
            "release_date": "",
            "total_tracks": 0,
        }
        artist = SpotifyArtist(
            artist_id="",
            name="Album input",
            spotify_url=f"https://open.spotify.com/album/{album_id}",
        )
        tracks = self.client.get_album_tracks(album_id, options.market)
        self._raise_if_cancelled()
        records = [self._build_record(artist, album, track, None) for track in tracks if track and track.get("id")]
        unique = self._dedupe_tracks_by_id(records)
        stats = ExtractionStats(albums_found=1, albums_unique=1, tracks_found=len(records), tracks_unique=len(unique))
        self._emit("Done", 100, stats)
        return artist, unique, stats

    def extract_track(self, track_id: str) -> tuple[SpotifyArtist, list[TrackRecord], ExtractionStats]:
        artist = SpotifyArtist(
            artist_id="",
            name="Track input",
            spotify_url=f"https://open.spotify.com/track/{track_id}",
        )
        record = TrackRecord(
            artist_searched="Track input",
            track_name="",
            track_artists="",
            album_name="",
            album_type="",
            release_date="",
            track_number=0,
            disc_number=0,
            duration="0:00",
            explicit=False,
            isrc="",
            spotify_track_url=f"https://open.spotify.com/track/{track_id}",
            track_id=track_id,
            album_id="",
            duration_ms=0,
            popularity=None,
            preview_url="",
            artist_ids="",
            album_release_date="",
            album_total_tracks=0,
        )
        stats = ExtractionStats(albums_found=0, albums_unique=0, tracks_found=1, tracks_unique=1)
        self._emit("Done", 100, stats)
        return artist, [record], stats

    def _emit(self, step: str, progress: int, stats: ExtractionStats) -> None:
        if self.progress_callback:
            self.progress_callback(step, progress, stats)

    def _raise_if_cancelled(
        self,
        artist: SpotifyArtist | None = None,
        records: list[TrackRecord] | None = None,
        stats: ExtractionStats | None = None,
        completed_album_ids: set[str] | None = None,
    ) -> None:
        if self.cancel_callback and self.cancel_callback():
            raise ExtractionCancelled(
                "Extracción detenida. Puedes continuar desde el último álbum completado.",
                artist=artist,
                records=records,
                stats=stats,
                completed_album_ids=completed_album_ids,
            )

    def _dedupe_albums(self, albums: list[dict], by_name_release: bool) -> list[dict]:
        seen_ids: set[str] = set()
        seen_names: set[str] = set()
        unique: list[dict] = []
        for album in albums:
            album_id = album.get("id", "")
            if album_id in seen_ids:
                continue
            seen_ids.add(album_id)
            if by_name_release:
                key = normalize_album_key(album.get("name", ""), album.get("release_date", ""))
                if key in seen_names:
                    continue
                seen_names.add(key)
            unique.append(album)
        return unique

    def _resolve_artist(self, artist_id: str, albums: list[dict], fetch_profile: bool) -> SpotifyArtist:
        if fetch_profile:
            return self.client.get_artist(artist_id)

        for album in albums:
            for artist in album.get("artists", []):
                if artist.get("id") == artist_id:
                    return SpotifyArtist(
                        artist_id=artist_id,
                        name=artist.get("name", artist_id),
                        spotify_url=(artist.get("external_urls") or {}).get(
                            "spotify",
                            f"https://open.spotify.com/artist/{artist_id}",
                        ),
                    )

        return SpotifyArtist(
            artist_id=artist_id,
            name=artist_id,
            spotify_url=f"https://open.spotify.com/artist/{artist_id}",
        )

    def _dedupe_tracks_by_id(self, records: list[TrackRecord]) -> list[TrackRecord]:
        seen: set[str] = set()
        unique: list[TrackRecord] = []
        for record in records:
            if record.track_id in seen:
                continue
            seen.add(record.track_id)
            unique.append(record)
        return unique

    def _dedupe_tracks_by_isrc(self, records: list[TrackRecord]) -> list[TrackRecord]:
        seen_isrcs: set[str] = set()
        unique: list[TrackRecord] = []
        for record in records:
            if record.isrc:
                if record.isrc in seen_isrcs:
                    continue
                seen_isrcs.add(record.isrc)
            unique.append(record)
        return unique

    def _has_artist(self, track: dict, artist_id: str) -> bool:
        return any(artist.get("id") == artist_id for artist in track.get("artists", []))

    def _build_record(self, artist: SpotifyArtist, album: dict, track: dict, full_track: dict | None) -> TrackRecord:
        source = full_track or track
        artists = source.get("artists") or track.get("artists", [])
        artist_names = ", ".join(item.get("name", "") for item in artists if item.get("name"))
        artist_ids = ", ".join(item.get("id", "") for item in artists if item.get("id"))
        duration_ms = int(source.get("duration_ms") or track.get("duration_ms") or 0)
        return TrackRecord(
            artist_searched=artist.name,
            track_name=source.get("name") or track.get("name", ""),
            track_artists=artist_names,
            album_name=album.get("name", ""),
            album_type=album.get("album_type", ""),
            release_date=album.get("release_date", ""),
            track_number=int(source.get("track_number") or track.get("track_number") or 0),
            disc_number=int(source.get("disc_number") or track.get("disc_number") or 0),
            duration=format_duration(duration_ms),
            explicit=bool(source.get("explicit", track.get("explicit", False))),
            isrc=(source.get("external_ids") or {}).get("isrc", ""),
            spotify_track_url=(source.get("external_urls") or track.get("external_urls") or {}).get("spotify", ""),
            track_id=source.get("id") or track.get("id", ""),
            album_id=album.get("id", ""),
            duration_ms=duration_ms,
            popularity=source.get("popularity"),
            preview_url=source.get("preview_url") or "",
            artist_ids=artist_ids,
            album_release_date=album.get("release_date", ""),
            album_total_tracks=int(album.get("total_tracks") or 0),
        )

    def _merge_full_track(self, record: TrackRecord, full_track: dict | None) -> TrackRecord:
        if not full_track:
            return record
        return self._build_record(
            SpotifyArtist(record.artist_ids, record.artist_searched, ""),
            {
                "id": record.album_id,
                "name": record.album_name,
                "album_type": record.album_type,
                "release_date": record.album_release_date,
                "total_tracks": record.album_total_tracks,
            },
            record.to_metadata(),
            full_track,
        )


def format_duration(duration_ms: int) -> str:
    seconds = max(duration_ms // 1000, 0)
    minutes, remaining_seconds = divmod(seconds, 60)
    return f"{minutes}:{remaining_seconds:02d}"
