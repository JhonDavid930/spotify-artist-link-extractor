"""Export helpers for extracted Spotify track records."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pandas as pd

from services.extractor import TrackRecord


TABLE_COLUMNS = [
    "Artist Searched",
    "Track Name",
    "Track Artists",
    "Album Name",
    "Album Type",
    "Release Date",
    "Track Number",
    "Disc Number",
    "Duration",
    "Explicit",
    "ISRC",
    "Spotify Track URL",
    "Track ID",
    "Album ID",
]


def export_csv(records: list[TrackRecord], path: str | Path) -> None:
    rows = [record.to_table_row() for record in records]
    with Path(path).open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=TABLE_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def export_txt(records: list[TrackRecord], path: str | Path, full_format: bool = False) -> None:
    with Path(path).open("w", encoding="utf-8") as file:
        for record in records:
            if full_format:
                file.write(f"{record.track_name} - {record.track_artists} - {record.spotify_track_url}\n")
            else:
                file.write(f"{record.spotify_track_url}\n")


def export_excel(records: list[TrackRecord], path: str | Path) -> None:
    dataframe = pd.DataFrame([record.to_table_row() for record in records], columns=TABLE_COLUMNS)
    dataframe.to_excel(path, index=False, engine="openpyxl")


def export_json(records: list[TrackRecord], path: str | Path) -> None:
    with Path(path).open("w", encoding="utf-8") as file:
        json.dump([record.to_metadata() for record in records], file, ensure_ascii=False, indent=2)
