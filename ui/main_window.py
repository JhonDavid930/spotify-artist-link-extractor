"""PySide6 main window for Spotify Artist Link Extractor.

Copyright (c) 2026 Jhon David (art. David Appleton).
All rights reserved.
"""

from __future__ import annotations

import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

from PySide6.QtCore import (
    QAbstractTableModel,
    QRegularExpression,
    QSettings,
    QSortFilterProxyModel,
    Qt,
    QThread,
    QTimer,
    QUrl,
    Signal,
)
from PySide6.QtGui import QAction, QDesktopServices, QIcon, QKeySequence, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QPlainTextEdit,
    QRadioButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from services.exporter import TABLE_COLUMNS, export_csv, export_excel, export_json, export_txt
from services.extractor import ExtractionCancelled, ExtractionOptions, ExtractionStats, SpotifyArtistExtractor, TrackRecord
from services.license_manager import LicenseStatus, validate_license
from services.machine_identity import get_machine_code, get_machine_hash
from services.secure_store import PROTECTED_PREFIXES, protect_secret, unprotect_secret
from spotify_api.client import SpotifyApiError, SpotifyArtist, SpotifyAuthError, SpotifyClient
from spotify_api.parser import SpotifyUrlError, extract_spotify_input


MARKETS = ["ES", "US", "GB", "MX", "DO", "FR", "DE", "BR", "GLOBAL"]
LICENSE_RENEWAL_WARNING_DAYS = 7

TABLE_COLUMN_LABELS = {
    "Artist Searched": "Artista",
    "Track Name": "Cancion",
    "Track Artists": "Artistas",
    "Album Name": "Album",
    "Album Type": "Tipo",
    "Release Date": "Fecha",
    "Track Number": "Pista",
    "Disc Number": "Disco",
    "Duration": "Duracion",
    "Explicit": "Explicita",
    "ISRC": "ISRC",
    "Spotify Track URL": "Link de Spotify",
    "Track ID": "Track ID",
    "Album ID": "Album ID",
}


def resource_path(relative_path: str) -> str:
    base_path = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
    return str(base_path / relative_path)


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
            return TABLE_COLUMN_LABELS.get(TABLE_COLUMNS[section], TABLE_COLUMNS[section])
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


class ConfigurationDialog(QDialog):
    def __init__(self, settings: QSettings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle("Activar Spotify Artist Link Extractor")
        self.setWindowIcon(QIcon(resource_path("assets/brand_mark.png")))
        self.setModal(True)
        self.setMinimumWidth(720)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(16)

        brand_row = QHBoxLayout()
        brand_logo = QLabel()
        brand_logo.setObjectName("BrandMark")
        brand_pixmap = QPixmap(resource_path("assets/brand_mark.png"))
        if not brand_pixmap.isNull():
            brand_logo.setPixmap(brand_pixmap.scaled(58, 58, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        brand_logo.setFixedSize(64, 64)
        brand_copy = QVBoxLayout()
        brand_copy.setSpacing(4)
        title = QLabel("Activa tu estudio de enlaces")
        title.setObjectName("DialogTitle")
        intro = QLabel(
            "Introduce tus datos de acceso una sola vez. La informacion queda guardada de forma privada en este equipo."
        )
        intro.setObjectName("DialogSubtitle")
        intro.setWordWrap(True)
        brand_copy.addWidget(title)
        brand_copy.addWidget(intro)
        brand_row.addWidget(brand_logo)
        brand_row.addLayout(brand_copy, 1)
        layout.addLayout(brand_row)

        spotify_group = QGroupBox("Conexion con Spotify")
        spotify_layout = QGridLayout(spotify_group)
        spotify_layout.setContentsMargins(16, 18, 16, 16)
        spotify_layout.setHorizontalSpacing(12)
        spotify_layout.setVerticalSpacing(8)

        self.client_id_input = QLineEdit(str(settings.value("spotify_client_id", "")))
        self.client_secret_input = QLineEdit(unprotect_secret(str(settings.value("spotify_client_secret", ""))))
        self.client_secret_input.setEchoMode(QLineEdit.Password)
        self.client_id_input.setPlaceholderText("Pega tu Spotify Client ID")
        self.client_secret_input.setPlaceholderText("Pega tu Spotify Client Secret")
        self.client_id_input.setMinimumHeight(42)
        self.client_secret_input.setMinimumHeight(42)

        client_id_label = QLabel("Client ID")
        client_id_label.setBuddy(self.client_id_input)
        client_secret_label = QLabel("Client Secret")
        client_secret_label.setBuddy(self.client_secret_input)
        id_hint = QLabel("Esta informacion esta en Spotify Developer Dashboard > tu app > Settings.")
        id_hint.setObjectName("FieldHint")
        secret_hint = QLabel("Se oculta por privacidad y no se incluye dentro de ningun export.")
        secret_hint.setObjectName("FieldHint")
        self.spotify_developer_button = QPushButton("Abrir Spotify Developer")
        self.spotify_developer_button.setObjectName("SecondaryButton")
        self.spotify_developer_button.setMinimumHeight(42)
        self.spotify_developer_button.clicked.connect(self.open_spotify_developer)
        self.toggle_secret_button = QPushButton("Mostrar")
        self.toggle_secret_button.setObjectName("SecondaryButton")
        self.toggle_secret_button.setMinimumHeight(42)
        self.toggle_secret_button.clicked.connect(self.toggle_secret_visibility)

        spotify_layout.addWidget(client_id_label, 0, 0)
        spotify_layout.addWidget(self.client_id_input, 0, 1)
        spotify_layout.addWidget(self.spotify_developer_button, 0, 2)
        spotify_layout.addWidget(id_hint, 1, 1, 1, 2)
        spotify_layout.addWidget(client_secret_label, 2, 0)
        spotify_layout.addWidget(self.client_secret_input, 2, 1)
        spotify_layout.addWidget(self.toggle_secret_button, 2, 2)
        spotify_layout.addWidget(secret_hint, 3, 1, 1, 2)
        spotify_layout.setColumnStretch(1, 1)
        layout.addWidget(spotify_group)

        license_group = QGroupBox("Acceso del software")
        license_layout = QVBoxLayout(license_group)
        license_layout.setContentsMargins(16, 18, 16, 16)
        license_layout.setSpacing(8)
        machine_row = QHBoxLayout()
        machine_copy = QVBoxLayout()
        machine_label = QLabel("Codigo de este equipo")
        machine_label.setObjectName("SectionLabel")
        self.machine_code_input = QLineEdit(get_machine_code())
        self.machine_code_input.setReadOnly(True)
        self.machine_code_input.setMinimumHeight(42)
        machine_hint = QLabel("Si tu licencia esta limitada a un equipo, envia este codigo al vendedor.")
        machine_hint.setObjectName("FieldHint")
        machine_copy.addWidget(machine_label)
        machine_copy.addWidget(self.machine_code_input)
        machine_copy.addWidget(machine_hint)
        self.copy_machine_button = QPushButton("Copiar codigo")
        self.copy_machine_button.setObjectName("SecondaryButton")
        self.copy_machine_button.setMinimumHeight(42)
        self.copy_machine_button.clicked.connect(self.copy_machine_code)
        machine_row.addLayout(machine_copy, 1)
        machine_row.addWidget(self.copy_machine_button, 0, Qt.AlignBottom)
        license_label = QLabel("Clave de licencia")
        self.license_input = QPlainTextEdit(str(settings.value("license_key", "")))
        self.license_input.setPlaceholderText("Pega aqui tu licencia")
        self.license_input.setFixedHeight(104)
        license_hint = QLabel(
            "La licencia activa el software durante el periodo contratado. Si vence, podras renovarla con una nueva clave."
        )
        license_hint.setObjectName("FieldHint")
        license_label.setBuddy(self.license_input)
        license_layout.addLayout(machine_row)
        license_layout.addWidget(license_label)
        license_layout.addWidget(self.license_input)
        license_layout.addWidget(license_hint)
        layout.addWidget(license_group)

        self.status_label = QLabel("")
        self.status_label.setObjectName("SetupStatus")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        self.save_button = buttons.button(QDialogButtonBox.Save)
        self.cancel_button = buttons.button(QDialogButtonBox.Cancel)
        self.save_button.setText("Guardar y activar")
        self.cancel_button.setText("Cancelar")
        self.save_button.setObjectName("PrimaryButton")
        self.cancel_button.setObjectName("SecondaryButton")
        self.save_button.setMinimumHeight(42)
        self.cancel_button.setMinimumHeight(42)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def accept(self) -> None:
        client_id = self.client_id_input.text().strip()
        client_secret = self.client_secret_input.text().strip()
        license_key = self.license_input.toPlainText().strip()
        license_status = validate_license(license_key, machine_hash=get_machine_hash())

        if not client_id or not client_secret:
            self.set_status("Faltan Spotify Client ID o Client Secret.", error=True)
            return
        if not license_status.valid:
            self.set_status(self._friendly_license_error(license_status.message), error=True)
            return

        self.set_status("Validando credenciales con Spotify...", error=False)
        QApplication.processEvents()
        try:
            SpotifyClient(client_id, client_secret, timeout=15).authenticate()
        except SpotifyAuthError as exc:
            self.set_status(str(exc), error=True)
            return

        self.settings.setValue("spotify_client_id", client_id)
        self.settings.setValue("spotify_client_secret", protect_secret(client_secret))
        self.settings.setValue("license_key", license_key)
        self.settings.setValue("license_last_validated_date", date.today().isoformat())
        self.settings.sync()
        super().accept()

    def toggle_secret_visibility(self) -> None:
        if self.client_secret_input.echoMode() == QLineEdit.Password:
            self.client_secret_input.setEchoMode(QLineEdit.Normal)
            self.toggle_secret_button.setText("Ocultar")
        else:
            self.client_secret_input.setEchoMode(QLineEdit.Password)
            self.toggle_secret_button.setText("Mostrar")

    def open_spotify_developer(self) -> None:
        QDesktopServices.openUrl(QUrl("https://developer.spotify.com/"))

    def copy_machine_code(self) -> None:
        QApplication.clipboard().setText(self.machine_code_input.text())
        self.set_status("Codigo de equipo copiado. Envialo al vendedor para activar este equipo.", error=False)

    def _friendly_license_error(self, detail: str) -> str:
        normalized_detail = detail.lower()
        if "expir" in normalized_detail or "venc" in normalized_detail:
            return "La licencia ha vencido. Solicita una nueva licencia para seguir usando el software."
        if "reloj" in normalized_detail:
            return "La fecha del equipo no coincide con la licencia. Revisa la fecha del sistema e intentalo otra vez."
        if "todavía no" in normalized_detail or "todavia no" in normalized_detail:
            return "Esta licencia aun no esta disponible para su uso. Revisa la fecha de inicio o solicita soporte."
        if "falta" in normalized_detail:
            return "Pega una licencia valida para activar el software."
        if "otro equipo" in normalized_detail or "equipo autorizado" in normalized_detail:
            return "Esta licencia no corresponde a este equipo. Copia el codigo de este equipo y solicita una licencia actualizada."
        return "La licencia no es valida. Revisa que la hayas copiado completa o solicita una nueva licencia."

    def set_status(self, message: str, error: bool) -> None:
        self.status_label.setText(message)
        self.status_label.setProperty("state", "error" if error else "success")
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)


class ExtractionWorker(QThread):
    progress = Signal(str, int, object)
    extraction_completed = Signal(object, object, object)
    extraction_cancelled = Signal(object, object, object, object)
    failed = Signal(str)

    def __init__(self, spotify_input: str, options: ExtractionOptions, client_id: str, client_secret: str) -> None:
        super().__init__()
        self.spotify_input = spotify_input
        self.options = options
        self.client_id = client_id
        self.client_secret = client_secret
        self._cancel_requested = False

    def cancel(self) -> None:
        self._cancel_requested = True

    def run(self) -> None:
        try:
            parsed_input = extract_spotify_input(self.spotify_input)
            client = SpotifyClient(self.client_id, self.client_secret)
            client.rate_limit_callback = self._rate_limited
            extractor = SpotifyArtistExtractor(client, self._progress, self._is_cancelled)
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
        except ExtractionCancelled as exc:
            self.extraction_cancelled.emit(exc.artist, exc.records, exc.stats, exc.completed_album_ids)
        except (SpotifyUrlError, SpotifyAuthError, SpotifyApiError) as exc:
            self.failed.emit(str(exc))
        except Exception as exc:
            self.failed.emit(f"Error inesperado: {exc}")

    def _progress(self, step: str, progress: int, stats: ExtractionStats) -> None:
        self.progress.emit(step, progress, stats)

    def _is_cancelled(self) -> bool:
        return self._cancel_requested

    def _rate_limited(self, retry_after: int) -> None:
        if retry_after > 30:
            self.progress.emit(f"Rate limit de Spotify: {retry_after}s", 0, ExtractionStats())
        else:
            self.progress.emit(f"Rate limit: esperando {retry_after}s", 0, ExtractionStats())


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Spotify Artist Link Extractor")
        self.setWindowIcon(QIcon(resource_path("assets/brand_mark.png")))
        self.resize(1280, 820)
        self.settings = QSettings("PapiSoftware", "SpotifyArtistLinkExtractor")
        self.records: list[TrackRecord] = []
        self.artist: SpotifyArtist | None = None
        self.worker: ExtractionWorker | None = None
        self.results_expanded = False
        self.resume_available = False
        self.resume_input = ""
        self.completed_album_ids: set[str] = set()
        self.current_run_is_resume = False

        self.table_model = TrackTableModel()
        self.proxy_model = RowFilterProxyModel()
        self.proxy_model.setSourceModel(self.table_model)
        self.proxy_model.setSortCaseSensitivity(Qt.CaseInsensitive)

        self._build_ui()
        self._connect_actions()
        self._apply_dark_theme()
        self._ensure_configuration()

    def _build_ui(self) -> None:
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(24, 22, 24, 16)
        layout.setSpacing(18)

        hero = QWidget()
        self.hero_panel = hero
        hero.setObjectName("HeroPanel")
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(18, 16, 18, 16)
        hero_layout.setSpacing(16)
        logo = QLabel()
        logo.setObjectName("BrandMark")
        brand_pixmap = QPixmap(resource_path("assets/brand_mark.png"))
        if not brand_pixmap.isNull():
            logo.setPixmap(brand_pixmap.scaled(76, 76, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        logo.setFixedSize(82, 82)
        hero_copy = QVBoxLayout()
        hero_copy.setSpacing(5)
        title = QLabel("Spotify Artist Link Extractor")
        title.setObjectName("Title")
        subtitle = QLabel("Convierte perfiles, albumes o canciones de Spotify en listas limpias de enlaces oficiales.")
        subtitle.setObjectName("Subtitle")
        hint = QLabel("Pensado para artistas, managers y equipos creativos: pega un enlace, extrae, copia o exporta.")
        hint.setObjectName("HeroHint")
        hero_copy.addWidget(title)
        hero_copy.addWidget(subtitle)
        hero_copy.addWidget(hint)
        hero_layout.addWidget(logo)
        hero_layout.addLayout(hero_copy, 1)
        layout.addWidget(hero)

        input_group = QGroupBox("Pega tu enlace")
        input_layout = QGridLayout(input_group)
        input_layout.setContentsMargins(18, 20, 18, 18)
        input_layout.setHorizontalSpacing(10)
        input_layout.setVerticalSpacing(8)
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://open.spotify.com/artist/ID, /album/ID o /track/ID")
        self.url_input.setMinimumHeight(46)
        self.extract_button = QPushButton("Extraer enlaces")
        self.extract_button.setObjectName("PrimaryButton")
        self.cancel_button = QPushButton("Detener")
        self.cancel_button.setObjectName("DangerButton")
        self.cancel_button.setEnabled(False)
        self.settings_button = QPushButton("Activacion")
        self.settings_button.setObjectName("SecondaryButton")
        self.open_artist_button = QPushButton("Abrir en Spotify")
        self.open_artist_button.setObjectName("SecondaryButton")
        self.open_artist_button.setEnabled(False)
        input_label = QLabel("Enlace de Spotify")
        input_label.setObjectName("SectionLabel")
        input_layout.addWidget(input_label, 0, 0)
        input_layout.addWidget(self.url_input, 1, 0)
        input_layout.addWidget(self.extract_button, 1, 1)
        input_layout.addWidget(self.cancel_button, 1, 2)
        input_layout.addWidget(self.settings_button, 1, 3)
        input_layout.addWidget(self.open_artist_button, 1, 4)
        input_layout.setColumnStretch(0, 1)
        layout.addWidget(input_group)

        options_group = QGroupBox("Preferencias")
        self.options_group = options_group
        options_layout = QGridLayout(options_group)
        options_layout.setContentsMargins(18, 20, 18, 18)
        options_layout.setHorizontalSpacing(12)
        options_layout.setVerticalSpacing(8)
        self.album_checkbox = QCheckBox("Albumes")
        self.single_checkbox = QCheckBox("Singles")
        self.appears_on_checkbox = QCheckBox("Colaboraciones")
        self.compilation_checkbox = QCheckBox("Compilaciones")
        self.album_checkbox.setChecked(True)
        self.single_checkbox.setChecked(True)
        self.main_artist_checkbox = QCheckBox("Solo canciones donde aparece este artista")
        self.main_artist_checkbox.setChecked(True)
        self.isrc_dedupe_checkbox = QCheckBox("Deduplicar por ISRC")
        self.isrc_dedupe_checkbox.setChecked(False)
        self.isrc_dedupe_checkbox.setEnabled(False)
        self.enrich_metadata_checkbox = QCheckBox("Metadata avanzada: ISRC y popularidad")
        self.enrich_metadata_checkbox.setChecked(False)
        self.album_name_dedupe_checkbox = QCheckBox("Deduplicar albumes por nombre + fecha")
        self.market_combo = QComboBox()
        self.market_combo.addItems(MARKETS)
        self.market_combo.setCurrentText("ES")
        self.market_combo.setMinimumHeight(38)
        self.txt_urls_radio = QRadioButton("TXT: solo links")
        self.txt_full_radio = QRadioButton("TXT: nombre + artistas + link")
        self.txt_urls_radio.setChecked(True)

        options_layout.addWidget(self.album_checkbox, 0, 0)
        options_layout.addWidget(self.single_checkbox, 0, 1)
        options_layout.addWidget(self.appears_on_checkbox, 0, 2)
        options_layout.addWidget(self.compilation_checkbox, 0, 3)
        market_label = QLabel("Pais/mercado")
        market_label.setObjectName("SectionLabel")
        options_layout.addWidget(market_label, 1, 0)
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
        self.search_input.setPlaceholderText("Buscar en resultados")
        self.search_input.setMinimumHeight(42)
        self.copy_selected_button = QPushButton("Copiar filas")
        self.copy_urls_button = QPushButton("Copiar links")
        self.copy_all_urls_button = QPushButton("Copiar todos los links")
        self.clear_button = QPushButton("Limpiar")
        self.expand_results_button = QPushButton("Vista amplia")
        self.export_button = QPushButton("Exportar")
        self.export_menu = QMenu(self.export_button)
        self.export_csv_action = self.export_menu.addAction("CSV")
        self.export_txt_action = self.export_menu.addAction("TXT")
        self.export_excel_action = self.export_menu.addAction("Excel")
        self.export_json_action = self.export_menu.addAction("JSON")
        self.export_button.setMenu(self.export_menu)
        tools_layout.addWidget(self.search_input, 1)
        tools_layout.addWidget(self.copy_selected_button)
        tools_layout.addWidget(self.copy_urls_button)
        tools_layout.addWidget(self.copy_all_urls_button)
        tools_layout.addWidget(self.clear_button)
        tools_layout.addWidget(self.expand_results_button)
        tools_layout.addWidget(self.export_button)
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
        self.table.setMinimumHeight(340)
        self.table.setWordWrap(False)
        self.table.verticalHeader().setDefaultSectionSize(34)
        layout.addWidget(self.table, 3)

        footer = QHBoxLayout()
        self.status_label = QLabel("Listo")
        self.stats_label = QLabel("Albumes: 0 | Canciones: 0 | Unicas: 0")
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

        copy_action = QAction("Copiar", self)
        copy_action.setShortcut(QKeySequence.Copy)
        copy_action.triggered.connect(self.copy_selected_rows)
        self.addAction(copy_action)

    def _connect_actions(self) -> None:
        self.extract_button.clicked.connect(self.start_extraction)
        self.cancel_button.clicked.connect(self.cancel_extraction)
        self.settings_button.clicked.connect(self.open_configuration)
        self.enrich_metadata_checkbox.toggled.connect(self.isrc_dedupe_checkbox.setEnabled)
        self.open_artist_button.clicked.connect(self.open_artist)
        self.url_input.textChanged.connect(self.handle_input_changed)
        self.search_input.textChanged.connect(self.apply_filter)
        self.copy_selected_button.clicked.connect(self.copy_selected_rows)
        self.copy_urls_button.clicked.connect(self.copy_selected_urls)
        self.copy_all_urls_button.clicked.connect(self.copy_all_urls)
        self.clear_button.clicked.connect(self.clear_results)
        self.expand_results_button.clicked.connect(self.toggle_results_view)
        self.export_csv_action.triggered.connect(lambda: self.export_records("csv"))
        self.export_txt_action.triggered.connect(lambda: self.export_records("txt"))
        self.export_excel_action.triggered.connect(lambda: self.export_records("xlsx"))
        self.export_json_action.triggered.connect(lambda: self.export_records("json"))

    def start_extraction(self) -> None:
        if not self._has_valid_runtime_access(show_dialog=True):
            return

        include_groups = self._selected_groups()
        if not include_groups:
            self.show_error("Selecciona al menos un tipo de album.")
            return

        market = self.market_combo.currentText()
        spotify_input = self.url_input.text().strip()
        is_resume = self.resume_available and spotify_input == self.resume_input
        if not is_resume:
            self.records = []
            self.table_model.clear()
            self.completed_album_ids.clear()
            self.resume_available = False
        self.current_run_is_resume = is_resume
        options = ExtractionOptions(
            include_groups=include_groups,
            market=None if market == "GLOBAL" else market,
            dedupe_albums_by_name_release=self.album_name_dedupe_checkbox.isChecked(),
            dedupe_tracks_by_isrc=self.isrc_dedupe_checkbox.isChecked(),
            only_main_artist_tracks=self.main_artist_checkbox.isChecked(),
            enrich_full_metadata=self.enrich_metadata_checkbox.isChecked(),
            fetch_artist_profile=False,
            skip_album_ids=tuple(sorted(self.completed_album_ids)) if is_resume else (),
        )
        self._set_busy(True)
        self.worker = ExtractionWorker(
            spotify_input,
            options,
            str(self.settings.value("spotify_client_id", "")).strip(),
            unprotect_secret(str(self.settings.value("spotify_client_secret", "")).strip()),
        )
        self.worker.progress.connect(self.update_progress)
        self.worker.extraction_completed.connect(self.extraction_finished)
        self.worker.extraction_cancelled.connect(self.extraction_cancelled)
        self.worker.failed.connect(self.extraction_failed)
        self.worker.finished.connect(self.worker_finished)
        self.worker.start()

    def cancel_extraction(self) -> None:
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.cancel_button.setEnabled(False)
            self.status_label.setText("Deteniendo...")

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
            f"Albumes: {stats.albums_unique}/{stats.albums_found} | "
            f"Canciones: {stats.tracks_found} | Unicas: {stats.tracks_unique}"
        )

    def extraction_finished(self, artist: SpotifyArtist, records: list[TrackRecord], stats: ExtractionStats) -> None:
        self.artist = artist
        self.records = self._merge_records(self.records, records) if self.current_run_is_resume else records
        self.table_model.set_records(records)
        self.table_model.set_records(self.records)
        self._resize_result_columns()
        self.open_artist_button.setEnabled(bool(artist.spotify_url))
        self.resume_available = False
        self.resume_input = ""
        self.completed_album_ids.clear()
        self.extract_button.setText("Extraer enlaces")
        self.update_progress("Listo", 100, ExtractionStats(
            albums_found=stats.albums_found,
            albums_unique=stats.albums_unique,
            tracks_found=len(self.records),
            tracks_unique=len(self.records),
        ))
        self._set_busy(False)

    def extraction_cancelled(
        self,
        artist: SpotifyArtist | None,
        records: list[TrackRecord],
        stats: ExtractionStats,
        completed_album_ids: set[str],
    ) -> None:
        if artist:
            self.artist = artist
            self.open_artist_button.setEnabled(bool(artist.spotify_url))
        self.records = self._merge_records(self.records, records)
        self.table_model.set_records(self.records)
        self._resize_result_columns()
        self.completed_album_ids = set(completed_album_ids)
        self.resume_available = True
        self.resume_input = self.url_input.text().strip()
        self.extract_button.setText("Continuar")
        self.status_label.setText("Pausado. Puedes continuar desde el último álbum completado.")
        self.stats_label.setText(
            f"Albumes: {len(self.completed_album_ids)}/{stats.albums_unique} | "
            f"Canciones: {len(self.records)} | Unicas: {len(self.records)}"
        )
        self._set_busy(False)

    def extraction_failed(self, message: str) -> None:
        self._set_busy(False)
        if "cancelada" in message.lower():
            self.status_label.setText("Cancelado")
            return
        self.status_label.setText("Error")
        self.show_error(message)

    def worker_finished(self) -> None:
        self.worker = None
        self._set_busy(False)

    def apply_filter(self, value: str) -> None:
        self.proxy_model.setFilterRegularExpression(QRegularExpression.escape(value))

    def handle_input_changed(self, value: str) -> None:
        if self.resume_available and value.strip() != self.resume_input:
            self.extract_button.setText("Extraer enlaces")

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
        self.resume_available = False
        self.resume_input = ""
        self.completed_album_ids.clear()
        self.extract_button.setText("Extraer enlaces")
        self.table_model.clear()
        self.open_artist_button.setEnabled(False)
        self.progress_bar.setValue(0)
        self.status_label.setText("Listo")
        self.stats_label.setText("Albumes: 0 | Canciones: 0 | Unicas: 0")
        self.set_results_expanded(False)

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
        path, _ = QFileDialog.getSaveFileName(self, "Exportar resultados", str(Path(folder) / f"spotify_tracks.{export_type}"), filters[export_type])
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
            self.status_label.setText(f"Exportado: {path}")
        except Exception as exc:
            self.show_error(f"No se pudo exportar el archivo: {exc}")

    def open_artist(self) -> None:
        if self.artist and self.artist.spotify_url:
            QDesktopServices.openUrl(QUrl(self.artist.spotify_url))

    def open_configuration(self) -> bool:
        dialog = ConfigurationDialog(self.settings, self)
        dialog.setStyleSheet(self.styleSheet())
        accepted = dialog.exec() == QDialog.Accepted
        if accepted:
            status = self._license_status()
            self.status_label.setText(status.message)
            self._show_license_renewal_warning(status, force=True)
        return accepted

    def _ensure_configuration(self) -> None:
        if not self._has_valid_runtime_access(show_dialog=False):
            configured = self.open_configuration()
            if not configured or not self._has_valid_runtime_access(show_dialog=False):
                self.status_label.setText("Activacion requerida")
                QTimer.singleShot(0, QApplication.quit)
        else:
            status = self._license_status()
            self.status_label.setText(status.message)
            self._show_license_renewal_warning(status)

    def _has_valid_runtime_access(self, show_dialog: bool) -> bool:
        client_id = str(self.settings.value("spotify_client_id", "")).strip()
        raw_client_secret = str(self.settings.value("spotify_client_secret", "")).strip()
        client_secret = unprotect_secret(raw_client_secret)
        status = self._license_status()
        if client_id and client_secret and status.valid:
            if raw_client_secret and not raw_client_secret.startswith(PROTECTED_PREFIXES):
                self.settings.setValue("spotify_client_secret", protect_secret(client_secret))
                self.settings.sync()
            return True

        if show_dialog:
            message = status.message if not status.valid else "Faltan credenciales de Spotify API."
            self.show_error(message)
            return self.open_configuration()
        return False

    def _license_status(self) -> LicenseStatus:
        last_validated = self._last_validated_date()
        status = validate_license(
            str(self.settings.value("license_key", "")).strip(),
            minimum_allowed_date=last_validated,
            machine_hash=get_machine_hash(),
        )
        if status.valid:
            today_text = date.today().isoformat()
            if not last_validated or today_text > last_validated.isoformat():
                self.settings.setValue("license_last_validated_date", today_text)
                self.settings.sync()
        return status

    def _last_validated_date(self) -> date | None:
        raw_value = str(self.settings.value("license_last_validated_date", "")).strip()
        if not raw_value:
            return None
        try:
            return datetime.strptime(raw_value, "%Y-%m-%d").date()
        except ValueError:
            return None

    def _license_days_remaining(self, status: LicenseStatus) -> int | None:
        if not status.valid or not status.expires_at:
            return None
        try:
            expires_at = datetime.strptime(status.expires_at, "%Y-%m-%d").date()
        except ValueError:
            return None
        return (expires_at - date.today()).days

    def _show_license_renewal_warning(self, status: LicenseStatus, force: bool = False) -> None:
        days_remaining = self._license_days_remaining(status)
        if days_remaining is None or days_remaining > LICENSE_RENEWAL_WARNING_DAYS:
            return

        today_text = date.today().isoformat()
        last_warning = str(self.settings.value("license_last_warning_date", "")).strip()
        if not force and last_warning == today_text:
            return

        self.settings.setValue("license_last_warning_date", today_text)
        self.settings.sync()
        plural = "día" if days_remaining == 1 else "días"
        QMessageBox.warning(
            self,
            "Renovar licencia",
            (
                f"Tu licencia vence en {days_remaining} {plural}.\n\n"
                "Contacta con Jhon David (art. David Appleton) para renovar y recibir una nueva clave de licencia."
            ),
        )

    def _set_busy(self, busy: bool) -> None:
        self.extract_button.setEnabled(not busy)
        self.cancel_button.setEnabled(busy)
        self.url_input.setEnabled(not busy)
        self.settings_button.setEnabled(not busy)
        self.progress_bar.setValue(0 if busy else self.progress_bar.value())
        if busy:
            self.status_label.setText("Preparando extraccion")

    def toggle_results_view(self) -> None:
        self.set_results_expanded(not self.results_expanded)

    def set_results_expanded(self, expanded: bool) -> None:
        self.results_expanded = expanded
        self.hero_panel.setVisible(not expanded)
        self.options_group.setVisible(not expanded)
        self.expand_results_button.setText("Vista normal" if expanded else "Vista amplia")

    def _merge_records(self, existing: list[TrackRecord], incoming: list[TrackRecord]) -> list[TrackRecord]:
        merged: list[TrackRecord] = []
        seen: set[str] = set()
        for record in [*existing, *incoming]:
            if record.track_id in seen:
                continue
            seen.add(record.track_id)
            merged.append(record)
        return merged

    def _resize_result_columns(self) -> None:
        self.table.resizeColumnsToContents()
        preferred_widths = {
            0: 150,
            1: 230,
            2: 220,
            3: 240,
            11: 360,
            12: 190,
            13: 190,
        }
        for column, width in preferred_widths.items():
            self.table.setColumnWidth(column, width)

    def show_error(self, message: str) -> None:
        QMessageBox.critical(self, "Spotify Artist Link Extractor", message)

    def _apply_dark_theme(self) -> None:
        self.setStyleSheet(
            """
            QWidget {
                background: #0b0f14;
                color: #f4f7fb;
                font-family: Segoe UI, Arial, sans-serif;
                font-size: 13px;
            }
            QDialog {
                background: #0b0f14;
            }
            #HeroPanel {
                border: 1px solid #2b3948;
                border-radius: 14px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #172018, stop:0.48 #111923, stop:1 #19161f);
            }
            #BrandMark {
                background: transparent;
            }
            #Title {
                background: transparent;
                font-size: 29px;
                font-weight: 700;
                color: #ffffff;
            }
            #DialogTitle {
                background: transparent;
                font-size: 24px;
                font-weight: 700;
                color: #ffffff;
            }
            #Subtitle {
                background: transparent;
                color: #d9e6db;
                font-size: 14px;
            }
            #HeroHint {
                background: transparent;
                color: #aab7c7;
                font-size: 12px;
            }
            #DialogSubtitle {
                background: transparent;
                color: #b8c6d6;
                font-size: 13px;
                line-height: 1.5;
            }
            #Copyright {
                color: #7f8da0;
                font-size: 11px;
            }
            #SectionLabel {
                color: #cdd8e6;
                font-weight: 600;
            }
            #FieldHint {
                color: #91a1b5;
                font-size: 12px;
            }
            #SetupStatus {
                min-height: 38px;
                border: 1px solid #334154;
                border-radius: 8px;
                padding: 8px 10px;
                background: #131a22;
                color: #b8c4d4;
            }
            #SetupStatus[state="error"] {
                border-color: #b94747;
                background: #241719;
                color: #ffc7c7;
            }
            #SetupStatus[state="success"] {
                border-color: #1ed760;
                background: #102718;
                color: #baf5cf;
            }
            QGroupBox {
                border: 1px solid #293746;
                border-radius: 12px;
                margin-top: 12px;
                padding: 14px;
                background: #111820;
                font-weight: 600;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
                color: #d8b86f;
            }
            QLineEdit, QComboBox {
                min-height: 36px;
                border: 1px solid #344458;
                border-radius: 8px;
                padding: 6px 12px;
                background: #090d12;
                color: #f8fafc;
                selection-background-color: #1ed760;
            }
            QLineEdit:focus, QComboBox:focus {
                border-color: #1ed760;
                background: #0d131a;
            }
            QPlainTextEdit {
                border: 1px solid #344458;
                border-radius: 8px;
                padding: 8px 10px;
                background: #090d12;
                color: #f8fafc;
                selection-background-color: #1ed760;
            }
            QPlainTextEdit:focus {
                border-color: #1ed760;
            }
            QPushButton {
                min-height: 38px;
                border: 1px solid #35465c;
                border-radius: 8px;
                padding: 7px 14px;
                background: #1a2330;
                color: #f8fafc;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #243147;
                border-color: #5d718d;
            }
            QPushButton:pressed {
                background: #141c28;
            }
            QPushButton:disabled {
                color: #717d8c;
                background: #151b23;
                border-color: #273241;
            }
            QPushButton#PrimaryButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1ed760, stop:1 #d8b86f);
                border-color: #60df8a;
                color: #06100a;
                font-weight: 700;
                padding-left: 20px;
                padding-right: 20px;
            }
            QPushButton#PrimaryButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #35ec76, stop:1 #eccb82);
                border-color: #9df2b3;
            }
            QPushButton#PrimaryButton:pressed {
                background: #18b853;
                border-color: #18b853;
            }
            QPushButton#SecondaryButton {
                background: #121a24;
                border-color: #334458;
                color: #e2ebf6;
                padding-left: 16px;
                padding-right: 16px;
            }
            QPushButton#SecondaryButton:hover {
                background: #1e2a3a;
                border-color: #5d718d;
            }
            QPushButton#DangerButton {
                background: #2a1518;
                border-color: #9f3b45;
                color: #ffd8dc;
            }
            QPushButton#DangerButton:hover {
                background: #3a1d22;
                border-color: #d45764;
            }
            QPushButton#DangerButton:disabled {
                color: #806268;
                background: #171b21;
                border-color: #33252a;
            }
            QMenu {
                border: 1px solid #35465c;
                border-radius: 8px;
                padding: 6px;
                background: #111820;
                color: #f4f7fb;
            }
            QMenu::item {
                min-width: 130px;
                padding: 8px 18px;
                border-radius: 6px;
            }
            QMenu::item:selected {
                background: #1ed760;
                color: #06100a;
            }
            QCheckBox, QRadioButton {
                min-height: 28px;
                color: #dce4ee;
            }
            QCheckBox::indicator, QRadioButton::indicator {
                width: 16px;
                height: 16px;
            }
            QCheckBox::indicator:checked, QRadioButton::indicator:checked {
                background: #1ed760;
                border: 1px solid #8df0a9;
            }
            QCheckBox::indicator:unchecked, QRadioButton::indicator:unchecked {
                background: #0b1016;
                border: 1px solid #415168;
            }
            QTableView {
                gridline-color: #24303d;
                border: 1px solid #293746;
                border-radius: 10px;
                background: #090d12;
                alternate-background-color: #101822;
                selection-background-color: #1ed760;
                selection-color: #06100a;
            }
            QHeaderView::section {
                background: #192331;
                color: #f8fafc;
                padding: 8px;
                border: 0;
                border-right: 1px solid #2a3747;
                font-weight: 700;
            }
            QProgressBar {
                min-height: 16px;
                border: 1px solid #334458;
                border-radius: 8px;
                background: #090d12;
                text-align: center;
            }
            QProgressBar::chunk {
                border-radius: 7px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1ed760, stop:1 #d8b86f);
            }
            """
        )
