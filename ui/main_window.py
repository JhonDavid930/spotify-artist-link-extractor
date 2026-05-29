"""PySide6 main window for Spotify Artist Link Extractor.

Copyright (c) 2026 Jhon David (art. David Appleton).
All rights reserved.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from PySide6.QtCore import (
    QAbstractTableModel,
    QRegularExpression,
    QSettings,
    QSortFilterProxyModel,
    Qt,
    QThread,
    QUrl,
    Signal,
)
from PySide6.QtGui import QAction, QDesktopServices, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QRadioButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from services.exporter import TABLE_COLUMNS, export_csv, export_excel, export_json, export_txt
from services.extractor import ExtractionOptions, ExtractionStats, SpotifyArtistExtractor, TrackRecord
from spotify_api.client import SpotifyApiError, SpotifyArtist, SpotifyAuthError, SpotifyClient
from spotify_api.parser import SpotifyUrlError, extract_spotify_input


MARKETS = ["ES", "US", "GB", "MX", "DO", "FR", "DE", "BR", "GLOBAL"]


class TrackTableModel(QAbstractTableModel):
    def __init__(self) -> None:
        super().__init__()
        self.records: list[TrackRecord] = []

    def rowCount(self, parent: Any = None) -> int:
        return len(self.records)

    def columnCount(self, parent: Any = None) -> int:
        return len(TABLE_COLUMNS)

    def data(self, index: Any, role: int = Qt.DisplayRole) -> Any:
        if not index.isValid():
            return None
        record = self.records[index.row()]
        row = record.to_table_row()
        value = row[TABLE_COLUMNS[index.column()]]
        if role in {Qt.DisplayRole, Qt.EditRole}:
            return value
        if role == Qt.ToolTipRole:
            return str(value)
        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole) -> Any:
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return TABLE_COLUMNS[section]
        return super().headerData(section, orientation, role)

    def set_records(self, records: list[TrackRecord]) -> None:
        self.beginResetModel()
        self.records = records
        self.endResetModel()

    def clear(self) -> None:
        self.set_records([])


class RowFilterProxyModel(QSortFilterProxyModel):
    def filterAcceptsRow(self, source_row: int, source_parent: Any) -> bool:
        pattern = self.filterRegularExpression().pattern().lower()
        if not pattern:
            return True
        model = self.sourceModel()
        if model is None:
            return True
        for column in range(model.columnCount()):
            index = model.index(source_row, column, source_parent)
            if pattern in str(model.data(index, Qt.DisplayRole)).lower():
                return True
        return False


class ExtractionWorker(QThread):
    progress = Signal(str, int, object)
    extraction_completed = Signal(object, object, object)
    failed = Signal(str)

    def __init__(self, spotify_input: str, options: ExtractionOptions, env_path: Path) -> None:
        super().__init__()
        self.spotify_input = spotify_input
        self.options = options
        self.env_path = env_path

    def run(self) -> None:
        try:
            parsed_input = extract_spotify_input(self.spotify_input)
            load_dotenv(self.env_path)
            client = SpotifyClient(
                os.getenv("SPOTIFY_CLIENT_ID", "").strip(),
                os.getenv("SPOTIFY_CLIENT_SECRET", "").strip(),
            )
            client.rate_limit_callback = self._rate_limited
            extractor = SpotifyArtistExtractor(client, self._progress)
            if parsed_input.item_type == "artist":
                artist, records, stats = extractor.extract(parsed_input.item_id, self.options)
            elif parsed_input.item_type == "album":
                artist, records, stats = extractor.extract_album(parsed_input.item_id, self.options)
            elif parsed_input.item_type == "track":
                artist, records, stats = extractor.extract_track(parsed_input.item_id)
            else:
                raise SpotifyUrlError("Tipo de enlace de Spotify no soportado.")
            if not records:
                raise SpotifyApiError("No se encontraron tracks con las opciones seleccionadas.")
            self.extraction_completed.emit(artist, records, stats)
        except (SpotifyUrlError, SpotifyAuthError, SpotifyApiError) as exc:
            self.failed.emit(str(exc))
        except Exception as exc:
            self.failed.emit(f"Error inesperado: {exc}")

    def _progress(self, step: str, progress: int, stats: ExtractionStats) -> None:
        self.progress.emit(step, progress, stats)

    def _rate_limited(self, retry_after: int) -> None:
        if retry_after > 30:
            self.progress.emit(f"Rate limit de Spotify: {retry_after}s", 0, ExtractionStats())
        else:
            self.progress.emit(f"Rate limit: esperando {retry_after}s", 0, ExtractionStats())


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Spotify Artist Link Extractor")
        self.resize(1280, 820)
        self.settings = QSettings("PapiSoftware", "SpotifyArtistLinkExtractor")
        self.records: list[TrackRecord] = []
        self.artist: SpotifyArtist | None = None
        self.worker: ExtractionWorker | None = None

        self.table_model = TrackTableModel()
        self.proxy_model = RowFilterProxyModel()
        self.proxy_model.setSourceModel(self.table_model)
        self.proxy_model.setSortCaseSensitivity(Qt.CaseInsensitive)

        self._build_ui()
        self._connect_actions()
        self._apply_dark_theme()

    def _build_ui(self) -> None:
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(22, 20, 22, 16)
        layout.setSpacing(16)

        title = QLabel("Spotify Artist Link Extractor")
        title.setObjectName("Title")
        subtitle = QLabel("Extrae enlaces oficiales de tracks usando Spotify Web API, sin scraping y con dedupe seguro.")
        subtitle.setObjectName("Subtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        input_group = QGroupBox("Input")
        input_layout = QGridLayout(input_group)
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://open.spotify.com/artist/ARTIST_ID, /album/ID o /track/ID")
        self.extract_button = QPushButton("Extract Tracks")
        self.open_artist_button = QPushButton("Open Artist in Spotify")
        self.open_artist_button.setEnabled(False)
        input_layout.addWidget(QLabel("Spotify URL or URI"), 0, 0)
        input_layout.addWidget(self.url_input, 1, 0)
        input_layout.addWidget(self.extract_button, 1, 1)
        input_layout.addWidget(self.open_artist_button, 1, 2)
        input_layout.setColumnStretch(0, 1)
        layout.addWidget(input_group)

        options_group = QGroupBox("Options")
        options_layout = QGridLayout(options_group)
        self.album_checkbox = QCheckBox("Include albums")
        self.single_checkbox = QCheckBox("Include singles")
        self.appears_on_checkbox = QCheckBox("Include appears_on")
        self.compilation_checkbox = QCheckBox("Include compilations")
        self.album_checkbox.setChecked(True)
        self.single_checkbox.setChecked(True)
        self.main_artist_checkbox = QCheckBox("Only include tracks where this artist is one of the track artists")
        self.main_artist_checkbox.setChecked(True)
        self.isrc_dedupe_checkbox = QCheckBox("Dedupe tracks by ISRC")
        self.isrc_dedupe_checkbox.setChecked(False)
        self.isrc_dedupe_checkbox.setEnabled(False)
        self.enrich_metadata_checkbox = QCheckBox("Enrich ISRC/popularity metadata")
        self.enrich_metadata_checkbox.setChecked(False)
        self.album_name_dedupe_checkbox = QCheckBox("Dedupe albums by normalized name + release date")
        self.market_combo = QComboBox()
        self.market_combo.addItems(MARKETS)
        self.market_combo.setCurrentText("ES")
        self.txt_urls_radio = QRadioButton("TXT URLs only")
        self.txt_full_radio = QRadioButton("TXT full lines")
        self.txt_urls_radio.setChecked(True)

        options_layout.addWidget(self.album_checkbox, 0, 0)
        options_layout.addWidget(self.single_checkbox, 0, 1)
        options_layout.addWidget(self.appears_on_checkbox, 0, 2)
        options_layout.addWidget(self.compilation_checkbox, 0, 3)
        options_layout.addWidget(QLabel("Market"), 1, 0)
        options_layout.addWidget(self.market_combo, 1, 1)
        options_layout.addWidget(self.main_artist_checkbox, 1, 2, 1, 2)
        options_layout.addWidget(self.enrich_metadata_checkbox, 2, 0, 1, 2)
        options_layout.addWidget(self.isrc_dedupe_checkbox, 2, 2)
        options_layout.addWidget(self.album_name_dedupe_checkbox, 2, 3)
        options_layout.addWidget(self.txt_urls_radio, 3, 0)
        options_layout.addWidget(self.txt_full_radio, 3, 1)
        layout.addWidget(options_group)

        tools_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search/filter results")
        self.copy_selected_button = QPushButton("Copy Selected Rows")
        self.copy_urls_button = QPushButton("Copy Selected URLs")
        self.copy_all_urls_button = QPushButton("Copy All URLs")
        self.clear_button = QPushButton("Clear Results")
        tools_layout.addWidget(self.search_input, 1)
        tools_layout.addWidget(self.copy_selected_button)
        tools_layout.addWidget(self.copy_urls_button)
        tools_layout.addWidget(self.copy_all_urls_button)
        tools_layout.addWidget(self.clear_button)
        layout.addLayout(tools_layout)

        self.table = QTableView()
        self.table.setModel(self.proxy_model)
        self.table.setSortingEnabled(True)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setSelectionMode(QTableView.ExtendedSelection)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table, 1)

        export_layout = QHBoxLayout()
        self.csv_button = QPushButton("Export CSV")
        self.txt_button = QPushButton("Export TXT")
        self.excel_button = QPushButton("Export Excel")
        self.json_button = QPushButton("Export JSON")
        export_layout.addStretch(1)
        export_layout.addWidget(self.csv_button)
        export_layout.addWidget(self.txt_button)
        export_layout.addWidget(self.excel_button)
        export_layout.addWidget(self.json_button)
        layout.addLayout(export_layout)

        footer = QHBoxLayout()
        self.status_label = QLabel("Ready")
        self.stats_label = QLabel("Albums: 0 | Tracks: 0 | Unique: 0")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        footer.addWidget(self.status_label, 2)
        footer.addWidget(self.stats_label, 2)
        footer.addWidget(self.progress_bar, 1)
        layout.addLayout(footer)

        copyright_label = QLabel("Copyright (c) 2026 Jhon David (art. David Appleton). All rights reserved.")
        copyright_label.setObjectName("Copyright")
        layout.addWidget(copyright_label)

        self.setCentralWidget(root)

        copy_action = QAction("Copy", self)
        copy_action.setShortcut(QKeySequence.Copy)
        copy_action.triggered.connect(self.copy_selected_rows)
        self.addAction(copy_action)

    def _connect_actions(self) -> None:
        self.extract_button.clicked.connect(self.start_extraction)
        self.enrich_metadata_checkbox.toggled.connect(self.isrc_dedupe_checkbox.setEnabled)
        self.open_artist_button.clicked.connect(self.open_artist)
        self.search_input.textChanged.connect(self.apply_filter)
        self.copy_selected_button.clicked.connect(self.copy_selected_rows)
        self.copy_urls_button.clicked.connect(self.copy_selected_urls)
        self.copy_all_urls_button.clicked.connect(self.copy_all_urls)
        self.clear_button.clicked.connect(self.clear_results)
        self.csv_button.clicked.connect(lambda: self.export_records("csv"))
        self.txt_button.clicked.connect(lambda: self.export_records("txt"))
        self.excel_button.clicked.connect(lambda: self.export_records("xlsx"))
        self.json_button.clicked.connect(lambda: self.export_records("json"))

    def start_extraction(self) -> None:
        include_groups = self._selected_groups()
        if not include_groups:
            self.show_error("Selecciona al menos un tipo de album.")
            return

        market = self.market_combo.currentText()
        options = ExtractionOptions(
            include_groups=include_groups,
            market=None if market == "GLOBAL" else market,
            dedupe_albums_by_name_release=self.album_name_dedupe_checkbox.isChecked(),
            dedupe_tracks_by_isrc=self.isrc_dedupe_checkbox.isChecked(),
            only_main_artist_tracks=self.main_artist_checkbox.isChecked(),
            enrich_full_metadata=self.enrich_metadata_checkbox.isChecked(),
            fetch_artist_profile=False,
        )
        env_path = Path(__file__).resolve().parents[1] / ".env"
        self._set_busy(True)
        self.worker = ExtractionWorker(self.url_input.text(), options, env_path)
        self.worker.progress.connect(self.update_progress)
        self.worker.extraction_completed.connect(self.extraction_finished)
        self.worker.failed.connect(self.extraction_failed)
        self.worker.start()

    def _selected_groups(self) -> list[str]:
        groups: list[str] = []
        if self.album_checkbox.isChecked():
            groups.append("album")
        if self.single_checkbox.isChecked():
            groups.append("single")
        if self.appears_on_checkbox.isChecked():
            groups.append("appears_on")
        if self.compilation_checkbox.isChecked():
            groups.append("compilation")
        return groups

    def update_progress(self, step: str, progress: int, stats: ExtractionStats) -> None:
        self.status_label.setText(step)
        if progress:
            self.progress_bar.setValue(progress)
        self.stats_label.setText(
            f"Albums: {stats.albums_unique}/{stats.albums_found} | "
            f"Tracks: {stats.tracks_found} | Unique: {stats.tracks_unique}"
        )

    def extraction_finished(self, artist: SpotifyArtist, records: list[TrackRecord], stats: ExtractionStats) -> None:
        self.artist = artist
        self.records = records
        self.table_model.set_records(records)
        self.table.resizeColumnsToContents()
        self.open_artist_button.setEnabled(bool(artist.spotify_url))
        self.update_progress("Done", 100, stats)
        self._set_busy(False)

    def extraction_failed(self, message: str) -> None:
        self._set_busy(False)
        self.status_label.setText("Error")
        self.show_error(message)

    def apply_filter(self, value: str) -> None:
        self.proxy_model.setFilterRegularExpression(QRegularExpression.escape(value))

    def copy_selected_rows(self) -> None:
        rows = self._selected_source_rows()
        lines = ["\t".join(TABLE_COLUMNS)]
        for row in rows:
            record_row = self.records[row].to_table_row()
            lines.append("\t".join(str(record_row[column]) for column in TABLE_COLUMNS))
        QApplication.clipboard().setText("\n".join(lines))

    def copy_selected_urls(self) -> None:
        rows = self._selected_source_rows()
        urls = [self.records[row].spotify_track_url for row in rows if self.records[row].spotify_track_url]
        QApplication.clipboard().setText("\n".join(urls))

    def copy_all_urls(self) -> None:
        urls = [record.spotify_track_url for record in self.records if record.spotify_track_url]
        QApplication.clipboard().setText("\n".join(urls))

    def _selected_source_rows(self) -> list[int]:
        selected = self.table.selectionModel().selectedRows()
        rows: list[int] = []
        for proxy_index in selected:
            source_index = self.proxy_model.mapToSource(proxy_index)
            rows.append(source_index.row())
        return sorted(set(rows))

    def clear_results(self) -> None:
        self.records = []
        self.artist = None
        self.table_model.clear()
        self.open_artist_button.setEnabled(False)
        self.progress_bar.setValue(0)
        self.status_label.setText("Ready")
        self.stats_label.setText("Albums: 0 | Tracks: 0 | Unique: 0")

    def export_records(self, export_type: str) -> None:
        if not self.records:
            self.show_error("No hay resultados para exportar.")
            return
        folder = self.settings.value("last_export_folder", str(Path.home()))
        filters = {
            "csv": "CSV Files (*.csv)",
            "txt": "Text Files (*.txt)",
            "xlsx": "Excel Files (*.xlsx)",
            "json": "JSON Files (*.json)",
        }
        path, _ = QFileDialog.getSaveFileName(self, "Export results", str(Path(folder) / f"spotify_tracks.{export_type}"), filters[export_type])
        if not path:
            return
        self.settings.setValue("last_export_folder", str(Path(path).parent))
        try:
            if export_type == "csv":
                export_csv(self.records, path)
            elif export_type == "txt":
                export_txt(self.records, path, full_format=self.txt_full_radio.isChecked())
            elif export_type == "xlsx":
                export_excel(self.records, path)
            elif export_type == "json":
                export_json(self.records, path)
            self.status_label.setText(f"Exported: {path}")
        except Exception as exc:
            self.show_error(f"No se pudo exportar el archivo: {exc}")

    def open_artist(self) -> None:
        if self.artist and self.artist.spotify_url:
            QDesktopServices.openUrl(QUrl(self.artist.spotify_url))

    def _set_busy(self, busy: bool) -> None:
        self.extract_button.setEnabled(not busy)
        self.url_input.setEnabled(not busy)
        self.progress_bar.setValue(0 if busy else self.progress_bar.value())
        if busy:
            self.status_label.setText("Starting")

    def show_error(self, message: str) -> None:
        QMessageBox.critical(self, "Spotify Artist Link Extractor", message)

    def _apply_dark_theme(self) -> None:
        self.setStyleSheet(
            """
            QWidget {
                background: #111418;
                color: #edf2f7;
                font-family: Segoe UI, Arial, sans-serif;
                font-size: 13px;
            }
            #Title {
                font-size: 26px;
                font-weight: 700;
                color: #ffffff;
            }
            #Subtitle {
                color: #aab6c5;
                font-size: 13px;
            }
            #Copyright {
                color: #7f8da3;
                font-size: 11px;
            }
            QGroupBox {
                border: 1px solid #293241;
                border-radius: 8px;
                margin-top: 12px;
                padding: 14px;
                background: #171b21;
                font-weight: 600;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
                color: #c6d0dc;
            }
            QLineEdit, QComboBox {
                min-height: 34px;
                border: 1px solid #344154;
                border-radius: 6px;
                padding: 5px 10px;
                background: #0d1014;
                color: #f8fafc;
                selection-background-color: #1db954;
            }
            QLineEdit:focus, QComboBox:focus {
                border-color: #1db954;
            }
            QPushButton {
                min-height: 34px;
                border: 1px solid #344154;
                border-radius: 6px;
                padding: 6px 12px;
                background: #202734;
                color: #f8fafc;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #293346;
                border-color: #4b5d76;
            }
            QPushButton:pressed {
                background: #1a202b;
            }
            QPushButton:disabled {
                color: #6d7785;
                background: #171b21;
            }
            QCheckBox, QRadioButton {
                min-height: 28px;
                color: #dce4ee;
            }
            QTableView {
                gridline-color: #293241;
                border: 1px solid #293241;
                border-radius: 8px;
                background: #0d1014;
                alternate-background-color: #151a20;
                selection-background-color: #1db954;
                selection-color: #06100a;
            }
            QHeaderView::section {
                background: #1d2430;
                color: #f8fafc;
                padding: 8px;
                border: 0;
                border-right: 1px solid #293241;
                font-weight: 700;
            }
            QProgressBar {
                min-height: 16px;
                border: 1px solid #344154;
                border-radius: 8px;
                background: #0d1014;
                text-align: center;
            }
            QProgressBar::chunk {
                border-radius: 7px;
                background: #1db954;
            }
            """
        )
