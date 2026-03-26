"""Tab 5 — Localization pipeline (PO/CSV conversion + pak build)."""

from __future__ import annotations

import traceback

from PySide6.QtWidgets import (
    QGroupBox, QHBoxLayout, QMessageBox, QPushButton,
    QTextEdit, QVBoxLayout, QWidget,
)

from src.gui.log_panel import StdoutCapture


class LocalizationTab(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout()

        # PO -> CSV
        g1 = QGroupBox("Export PO -> CSV (for translators)")
        l1 = QHBoxLayout()
        btn1 = QPushButton("Run Export")
        btn1.clicked.connect(self._po_to_csv)
        l1.addWidget(btn1)
        g1.setLayout(l1)

        # CSV -> PO
        g2 = QGroupBox("Import CSV -> PO (merge translations)")
        l2 = QHBoxLayout()
        btn2 = QPushButton("Run Import")
        btn2.clicked.connect(self._csv_to_po)
        l2.addWidget(btn2)
        g2.setLayout(l2)

        # Build pak
        g3 = QGroupBox("Build Localization Pak")
        l3 = QHBoxLayout()
        btn3 = QPushButton("Run Build")
        btn3.clicked.connect(self._build_pak)
        l3.addWidget(btn3)
        g3.setLayout(l3)

        self.output = QTextEdit()
        self.output.setReadOnly(True)

        layout.addWidget(g1)
        layout.addWidget(g2)
        layout.addWidget(g3)
        layout.addWidget(self.output)
        self.setLayout(layout)

    def _run(self, func, label: str) -> None:
        self.output.clear()
        self.output.append(f"--- {label} ---")
        try:
            with StdoutCapture(self.output):
                func()
            self.output.append("--- Done ---")
        except SystemExit:
            self.output.append("--- Operation exited ---")
        except Exception:  # pylint: disable=broad-exception-caught
            self.output.append(traceback.format_exc())
            QMessageBox.critical(self, "Error", f"{label} failed. See output.")

    def _po_to_csv(self) -> None:
        from src.localization.po_to_csv import run
        self._run(run, "PO -> CSV Export")

    def _csv_to_po(self) -> None:
        from src.localization.csv_to_po import run
        self._run(run, "CSV -> PO Import")

    def _build_pak(self) -> None:
        from src.packaging.pak_locres import run
        self._run(run, "Build Localization Pak")
