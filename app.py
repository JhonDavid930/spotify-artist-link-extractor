"""Application entry point.

Copyright (c) 2026 Jhon David (art. David Appleton).
All rights reserved.
"""

from __future__ import annotations

import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow, resource_path


def main() -> int:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setWindowIcon(QIcon(resource_path("assets/brand_mark.png")))
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
