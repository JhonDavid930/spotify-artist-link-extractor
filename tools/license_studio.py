"""Internal license inventory UI for Spotify Artist Link Extractor."""

from __future__ import annotations

import json
import re
import sys
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QPlainTextEdit,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from services.license_manager import create_license, validate_license
from services.machine_identity import get_machine_hash, normalize_machine_code
from ui.main_window import resource_path


PRIVATE_DIR = Path(__file__).resolve().parent / "private"
LICENSE_DIR = PRIVATE_DIR / "licenses"
INVENTORY_PATH = LICENSE_DIR / "inventory.json"


@dataclass
class LicenseRecord:
    customer: str
    email: str
    license_id: str
    license_key: str
    issued_at: str
    expires_at: str
    lifetime: bool
    machine_code: str
    created_at: str
    updated_at: str
    status: str = "active"


class LicenseStudioWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("License Studio - Spotify Artist Link Extractor")
        self.setWindowIcon(QIcon(resource_path("assets/brand_mark.png")))
        self.resize(1240, 820)
        self.records: list[LicenseRecord] = []
        self.current_license = ""
        self._build_ui()
        self._apply_theme()
        self.load_inventory()

    def _build_ui(self) -> None:
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(14)

        header = QHBoxLayout()
        logo = QLabel()
        pixmap = QPixmap(resource_path("assets/brand_mark.png"))
        if not pixmap.isNull():
            logo.setPixmap(pixmap.scaled(62, 62, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        logo.setFixedSize(70, 70)
        header_copy = QVBoxLayout()
        title = QLabel("License Studio")
        title.setObjectName("Title")
        subtitle = QLabel("Inventario privado para crear, renovar y administrar licencias de clientes.")
        subtitle.setObjectName("Subtitle")
        header_copy.addWidget(title)
        header_copy.addWidget(subtitle)
        header.addWidget(logo)
        header.addLayout(header_copy, 1)
        layout.addLayout(header)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignLeft)
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(10)
        self.customer_input = QLineEdit()
        self.customer_input.setPlaceholderText("Nombre de la persona o empresa")
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Correo opcional para avisos y envio")
        self.machine_code_input = QLineEdit()
        self.machine_code_input.setPlaceholderText("Codigo de equipo opcional, ejemplo XXXXX-XXXXX-XXXXX-XXXXX")
        self.days_input = QSpinBox()
        self.days_input.setRange(1, 366)
        self.days_input.setValue(60)
        self.days_input.setSuffix(" dias")
        self.lifetime_check = QCheckBox("Licencia de por vida")
        self.lifetime_check.stateChanged.connect(self.toggle_lifetime)
        form.addRow("Cliente", self.customer_input)
        form.addRow("Email", self.email_input)
        form.addRow("Equipo", self.machine_code_input)
        form.addRow("Duracion", self.days_input)
        form.addRow("", self.lifetime_check)
        layout.addLayout(form)

        actions = QHBoxLayout()
        self.create_button = QPushButton("Crear licencia")
        self.create_button.setObjectName("PrimaryButton")
        self.renew_button = QPushButton("Renovar seleccionada")
        self.copy_button = QPushButton("Copiar licencia")
        self.save_button = QPushButton("Guardar TXT")
        self.email_button = QPushButton("Preparar email")
        self.suspend_button = QPushButton("Suspender")
        self.revoke_button = QPushButton("Revocar")
        self.reactivate_button = QPushButton("Reactivar")
        self.revoke_button.setObjectName("DangerButton")
        self.reactivate_button.setObjectName("SuccessButton")
        self.clear_button = QPushButton("Limpiar")
        for button in (
            self.create_button,
            self.renew_button,
            self.copy_button,
            self.save_button,
            self.email_button,
            self.suspend_button,
            self.revoke_button,
            self.reactivate_button,
            self.clear_button,
        ):
            actions.addWidget(button)
        actions.addStretch(1)
        layout.addLayout(actions)

        self.summary_label = QLabel("Inventario vacio")
        self.summary_label.setObjectName("SummaryCard")
        self.summary_label.setWordWrap(True)
        layout.addWidget(self.summary_label)

        self.inventory_table = QTableWidget(0, 8)
        self.inventory_table.setHorizontalHeaderLabels(
            ["Cliente", "Email", "Licencia ID", "Estado", "Expira", "Restante", "Equipo", "Actualizado"]
        )
        self.inventory_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.inventory_table.verticalHeader().setVisible(False)
        self.inventory_table.setColumnWidth(0, 210)
        self.inventory_table.setColumnWidth(1, 220)
        self.inventory_table.setColumnWidth(2, 150)
        self.inventory_table.setColumnWidth(3, 120)
        self.inventory_table.setColumnWidth(4, 120)
        self.inventory_table.setColumnWidth(5, 130)
        self.inventory_table.setColumnWidth(6, 190)
        self.inventory_table.setColumnWidth(7, 170)
        self.inventory_table.setMinimumHeight(280)
        self.inventory_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.inventory_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.inventory_table.setSelectionMode(QTableWidget.SingleSelection)
        self.inventory_table.setAlternatingRowColors(True)
        self.inventory_table.setShowGrid(False)
        self.inventory_table.itemSelectionChanged.connect(self.populate_selected_record)
        layout.addWidget(self.inventory_table, 2)

        self.license_output = QPlainTextEdit()
        self.license_output.setPlaceholderText("La licencia lista para cliente aparecera aqui.")
        self.license_output.setMinimumHeight(86)
        self.license_output.setMaximumHeight(118)
        layout.addWidget(self.license_output)

        self.status_label = QLabel("Uso interno. El inventario se guarda en tools/private/licenses.")
        self.status_label.setObjectName("Hint")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        footer = QLabel("No distribuir License Studio ni la carpeta privada de licencias.")
        footer.setObjectName("Footer")
        layout.addWidget(footer)

        self.setCentralWidget(root)
        self.create_button.clicked.connect(self.create_license_record)
        self.renew_button.clicked.connect(self.renew_selected_license)
        self.copy_button.clicked.connect(self.copy_license)
        self.save_button.clicked.connect(self.save_license_txt)
        self.email_button.clicked.connect(self.prepare_email)
        self.suspend_button.clicked.connect(lambda: self.set_selected_status("suspended"))
        self.revoke_button.clicked.connect(lambda: self.set_selected_status("revoked"))
        self.reactivate_button.clicked.connect(lambda: self.set_selected_status("active"))
        self.clear_button.clicked.connect(self.clear_form)

    def toggle_lifetime(self) -> None:
        self.days_input.setEnabled(not self.lifetime_check.isChecked())

    def create_license_record(self) -> None:
        customer = self.customer_input.text().strip()
        if not customer:
            self.show_error("Escribe el nombre del cliente.")
            return
        self._upsert_record(customer=customer, license_id=None)

    def renew_selected_license(self) -> None:
        record = self.selected_record()
        if not record:
            self.show_error("Selecciona una licencia del inventario para renovarla.")
            return
        if record.status == "revoked":
            self.show_error("Esta licencia esta revocada. Reactivala primero si realmente quieres renovarla.")
            return
        self.customer_input.setText(record.customer)
        self.email_input.setText(record.email)
        self.machine_code_input.setText(record.machine_code)
        self._upsert_record(customer=record.customer, license_id=record.license_id)

    def _upsert_record(self, customer: str, license_id: str | None) -> None:
        email = self.email_input.text().strip().lower()
        machine_code = self.machine_code_input.text().strip()
        try:
            normalized_machine = normalize_machine_code(machine_code) if machine_code else ""
        except ValueError as exc:
            self.show_error(str(exc))
            return

        machine_hash = get_machine_hash(normalized_machine) if normalized_machine else ""
        lifetime = self.lifetime_check.isChecked()
        try:
            license_key = create_license(
                customer,
                self.days_input.value(),
                email=email,
                license_id=license_id,
                lifetime=lifetime,
                machine_hash=machine_hash,
            )
        except Exception as exc:
            self.show_error(str(exc))
            return

        status = validate_license(license_key, machine_hash=machine_hash or None)
        if not status.valid:
            self.show_error(status.message)
            return

        now_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        existing = self.find_record(status.license_id)
        record = LicenseRecord(
            customer=status.customer,
            email=email,
            license_id=status.license_id,
            license_key=license_key,
            issued_at=date.today().isoformat(),
            expires_at=status.expires_at,
            lifetime=status.lifetime,
            machine_code=normalized_machine,
            created_at=existing.created_at if existing else now_text,
            updated_at=now_text,
            status=existing.status if existing else "active",
        )
        if existing:
            self.records[self.records.index(existing)] = record
            action = "renovada"
        else:
            self.records.append(record)
            action = "creada"
        self.current_license = license_key
        self.license_output.setPlainText(license_key)
        self.save_inventory()
        self.refresh_table(select_license_id=record.license_id)
        self.save_record_file(record)
        self.status_label.setText(f"Licencia {action} para {record.customer}. ID {record.license_id}.")

    def selected_record(self) -> LicenseRecord | None:
        selected = self.inventory_table.selectedItems()
        if not selected:
            return None
        row = selected[0].row()
        license_id = self.inventory_table.item(row, 2).text()
        return self.find_record(license_id)

    def populate_selected_record(self) -> None:
        record = self.selected_record()
        if not record:
            return
        self.customer_input.setText(record.customer)
        self.email_input.setText(record.email)
        self.machine_code_input.setText(record.machine_code)
        self.lifetime_check.setChecked(record.lifetime)
        self.license_output.setPlainText(record.license_key)
        self.current_license = record.license_key
        self.status_label.setText(f"Licencia seleccionada: {record.customer}.")

    def set_selected_status(self, status: str) -> None:
        record = self.selected_record()
        if not record:
            self.show_error("Selecciona una licencia del inventario.")
            return
        if status == "revoked":
            confirmed = QMessageBox.question(
                self,
                "Revocar licencia",
                (
                    f"Vas a marcar como revocada la licencia de {record.customer}.\n\n"
                    "Esto no borra la licencia que el cliente ya tenga instalada offline, "
                    "pero bloquea renovaciones accidentales en tu inventario."
                ),
            )
            if confirmed != QMessageBox.Yes:
                return
        record.status = status
        record.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.save_inventory()
        self.refresh_table(select_license_id=record.license_id)
        labels = {"active": "reactivada", "suspended": "suspendida", "revoked": "revocada"}
        self.status_label.setText(f"Licencia {labels.get(status, status)}: {record.customer}.")

    def copy_license(self) -> None:
        license_key = self.license_output.toPlainText().strip()
        if not license_key:
            self.show_error("No hay licencia para copiar.")
            return
        QApplication.clipboard().setText(license_key)
        self.status_label.setText("Licencia copiada al portapapeles.")

    def save_license_txt(self) -> None:
        record = self.selected_record()
        license_key = self.license_output.toPlainText().strip()
        if not license_key:
            self.show_error("No hay licencia para guardar.")
            return
        default_name = f"{self._slug(record.customer if record else 'cliente')}_licencia.txt"
        path, _ = QFileDialog.getSaveFileName(self, "Guardar licencia", str(LICENSE_DIR / default_name), "Text Files (*.txt)")
        if not path:
            return
        Path(path).write_text(license_key, encoding="utf-8")
        self.status_label.setText(f"Licencia guardada en {path}")

    def prepare_email(self) -> None:
        record = self.selected_record()
        if not record:
            self.show_error("Selecciona una licencia para preparar el email.")
            return
        if not record.email:
            self.show_error("Este cliente no tiene email guardado.")
            return
        subject = "Tu licencia de Spotify Artist Link Extractor"
        body = (
            f"Hola {record.customer},\n\n"
            "Te envio tu licencia actualizada para activar Spotify Artist Link Extractor.\n\n"
            f"{record.license_key}\n\n"
            "Pega esta clave en la pantalla de activacion del software.\n\n"
            "Saludos,\n"
            "Jhon David (art. David Appleton)"
        )
        mailto = f"mailto:{quote(record.email)}?subject={quote(subject)}&body={quote(body)}"
        QDesktopServices.openUrl(QUrl(mailto))

    def clear_form(self) -> None:
        self.customer_input.clear()
        self.email_input.clear()
        self.machine_code_input.clear()
        self.days_input.setValue(60)
        self.lifetime_check.setChecked(False)
        self.license_output.clear()
        self.current_license = ""
        self.inventory_table.clearSelection()
        self.status_label.setText("Formulario limpio.")

    def load_inventory(self) -> None:
        LICENSE_DIR.mkdir(parents=True, exist_ok=True)
        if not INVENTORY_PATH.exists():
            self.records = []
            self.refresh_table()
            return
        try:
            data = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
            self.records = [LicenseRecord(**item) for item in data if isinstance(item, dict)]
        except Exception as exc:
            self.records = []
            self.show_error(f"No se pudo leer el inventario: {exc}")
        self.refresh_table()

    def save_inventory(self) -> None:
        LICENSE_DIR.mkdir(parents=True, exist_ok=True)
        INVENTORY_PATH.write_text(
            json.dumps([asdict(record) for record in self.records], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def save_record_file(self, record: LicenseRecord) -> None:
        folder = LICENSE_DIR / self._slug(record.customer)
        folder.mkdir(parents=True, exist_ok=True)
        filename = f"{record.license_id}_{date.today().isoformat()}.txt"
        (folder / filename).write_text(record.license_key, encoding="utf-8")

    def refresh_table(self, select_license_id: str = "") -> None:
        self.records.sort(key=lambda item: item.updated_at, reverse=True)
        self.inventory_table.setRowCount(len(self.records))
        for row, record in enumerate(self.records):
            values = [
                record.customer,
                record.email or "No indicado",
                record.license_id,
                self._record_state(record),
                "De por vida" if record.lifetime else record.expires_at,
                "Sin limite" if record.lifetime else self._days_left_text(record),
                record.machine_code or "No bloqueada",
                record.updated_at,
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() ^ Qt.ItemIsEditable)
                item.setToolTip(value)
                self.inventory_table.setItem(row, column, item)
            self.inventory_table.setRowHeight(row, 44)
            if select_license_id and record.license_id == select_license_id:
                self.inventory_table.selectRow(row)
        self.update_summary()

    def update_summary(self) -> None:
        total = len(self.records)
        active = sum(1 for record in self.records if record.status == "active" and not record.lifetime and self._record_state(record) == "Activa")
        expiring = sum(1 for record in self.records if record.status == "active" and not record.lifetime and self._record_state(record) == "Por vencer")
        expired = sum(1 for record in self.records if record.status == "active" and not record.lifetime and self._record_state(record) == "Vencida")
        lifetime = sum(1 for record in self.records if record.status == "active" and record.lifetime)
        suspended = sum(1 for record in self.records if record.status == "suspended")
        revoked = sum(1 for record in self.records if record.status == "revoked")
        self.summary_label.setText(
            f"Total: {total}   |   Activas: {active}   |   Por vencer: {expiring}   |   Vencidas: {expired}   |   De por vida: {lifetime}   |   Suspendidas: {suspended}   |   Revocadas: {revoked}"
        )

    def find_record(self, license_id: str) -> LicenseRecord | None:
        return next((record for record in self.records if record.license_id == license_id), None)

    def _record_state(self, record: LicenseRecord) -> str:
        if record.status == "revoked":
            return "Revocada"
        if record.status == "suspended":
            return "Suspendida"
        if record.lifetime:
            return "Vitalicia"
        days_left = self._days_left(record)
        if days_left < 0:
            return "Vencida"
        if days_left <= 7:
            return "Por vencer"
        return "Activa"

    def _days_left_text(self, record: LicenseRecord) -> str:
        days_left = self._days_left(record)
        if days_left < 0:
            return f"Vencida hace {abs(days_left)} dias"
        return f"{days_left} dias"

    def _days_left(self, record: LicenseRecord) -> int:
        try:
            expires_at = datetime.strptime(record.expires_at, "%Y-%m-%d").date()
        except ValueError:
            return 0
        return (expires_at - date.today()).days

    def _slug(self, value: str) -> str:
        slug = re.sub(r"[^A-Za-z0-9]+", "_", value.strip()).strip("_")
        return slug or "cliente"

    def show_error(self, message: str) -> None:
        QMessageBox.critical(self, "License Studio", message)

    def _apply_theme(self) -> None:
        self.setStyleSheet(
            """
            QWidget {
                background: #0b0f14;
                color: #f4f7fb;
                font-family: Segoe UI, Arial, sans-serif;
                font-size: 13px;
            }
            #Title {
                font-size: 28px;
                font-weight: 700;
                color: #ffffff;
            }
            #Subtitle, #Hint {
                color: #aab7c7;
            }
            #SummaryCard {
                border: 1px solid #2b3d51;
                border-radius: 10px;
                padding: 12px 14px;
                background: #111a25;
                color: #d8e6f8;
                font-weight: 700;
            }
            #Footer {
                color: #d8b86f;
                font-size: 12px;
            }
            QLineEdit, QSpinBox, QPlainTextEdit {
                border: 1px solid #344458;
                border-radius: 8px;
                padding: 8px 12px;
                background: #090d12;
                color: #f8fafc;
                selection-background-color: #1ed760;
            }
            QLineEdit:focus, QSpinBox:focus, QPlainTextEdit:focus {
                border-color: #1ed760;
            }
            QCheckBox {
                padding: 8px 0;
                color: #e8eef7;
            }
            QTableWidget {
                border: 1px solid #263647;
                border-radius: 10px;
                background: #090d12;
                alternate-background-color: #101823;
                gridline-color: #263647;
                selection-background-color: #1b3a2a;
                selection-color: #ffffff;
                outline: none;
            }
            QTableWidget::item {
                padding: 9px 10px;
                border-bottom: 1px solid #1d2a38;
            }
            QTableWidget::item:selected {
                background: #1b3a2a;
                color: #ffffff;
            }
            QHeaderView::section {
                background: #172232;
                color: #ffffff;
                padding: 10px 8px;
                border: 0;
                border-right: 1px solid #263647;
                font-weight: 700;
            }
            QScrollBar:vertical, QScrollBar:horizontal {
                background: #0b1118;
                border: 0;
                width: 12px;
                height: 12px;
            }
            QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
                background: #314359;
                border-radius: 6px;
                min-height: 30px;
                min-width: 30px;
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
            QPushButton#PrimaryButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1ed760, stop:1 #d8b86f);
                border-color: #60df8a;
                color: #06100a;
                font-weight: 700;
            }
            QPushButton#DangerButton {
                border-color: #6d3131;
                background: #2a1719;
                color: #ffd4d4;
            }
            QPushButton#DangerButton:hover {
                border-color: #d65a5a;
                background: #3a1d20;
            }
            QPushButton#SuccessButton {
                border-color: #2f6b48;
                background: #102418;
                color: #c8f7d8;
            }
            QPushButton#SuccessButton:hover {
                border-color: #1ed760;
                background: #143321;
            }
            """
        )


def main() -> int:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setWindowIcon(QIcon(resource_path("assets/brand_mark.png")))
    window = LicenseStudioWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
