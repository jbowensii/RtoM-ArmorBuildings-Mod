"""Tab 7 — Sync (repo <-> staging)."""

from __future__ import annotations

import traceback

from PySide6.QtWidgets import (
    QHBoxLayout, QMessageBox, QPushButton, QTextEdit,
    QVBoxLayout, QWidget,
)

from src.gui.log_panel import StdoutCapture


class SyncTab(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout()

        btn_row = QHBoxLayout()
        export_btn = QPushButton("Export (repo -> staging)")
        export_btn.clicked.connect(self._export)
        import_btn = QPushButton("Import (staging -> repo)")
        import_btn.clicked.connect(self._import)
        check_btn = QPushButton("Check differences")
        check_btn.clicked.connect(self._check)
        btn_row.addWidget(export_btn)
        btn_row.addWidget(import_btn)
        btn_row.addWidget(check_btn)

        self.output = QTextEdit()
        self.output.setReadOnly(True)

        layout.addLayout(btn_row)
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
        except Exception:
            self.output.append(traceback.format_exc())
            QMessageBox.critical(self, "Error", f"{label} failed. See output.")

    def _export(self) -> None:
        from src.sync import sync_export
        self._run(sync_export, "Sync Export")

    def _import(self) -> None:
        from src.sync import sync_import
        self._run(sync_import, "Sync Import")

    def _check(self) -> None:
        from src.sync import sync_check
        self._run(sync_check, "Sync Check")
