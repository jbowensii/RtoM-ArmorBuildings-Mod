"""Progress dialog for extracting game DataTable files."""

from __future__ import annotations

import logging
import os
from typing import Any

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QDialog, QLabel, QMessageBox, QProgressBar, QPushButton, QVBoxLayout,
)

from src.config import Config
from src.utils.game_extractor import extract_all

log = logging.getLogger(__name__)


class _ExtractWorker(QThread):
    """Background thread that runs the extraction pipeline."""

    progress = Signal(str, int, int)  # message, current, total
    finished = Signal(dict)           # results dict
    error = Signal(str)               # error message

    def __init__(
        self,
        cfg: Config,
        manifest: list[dict[str, Any]],
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.cfg = cfg
        self.manifest = manifest

    def run(self) -> None:  # pylint: disable=broad-exception-caught
        """Run the extraction pipeline in a background thread."""
        try:
            retoc = os.path.join(self.cfg.utilities_dir, "retoc.exe")
            uassetgui = os.path.join(self.cfg.utilities_dir, "UAssetGUI.exe")

            results = extract_all(
                paks_dir=self.cfg.game_paks_dir,
                retoc_exe=retoc,
                uassetgui_exe=uassetgui,
                game_extract_dir=self.cfg.game_extract_dir,
                manifest=self.manifest,
                progress=self.progress.emit,
            )
            self.finished.emit(results)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            log.exception("Extraction failed")
            self.error.emit(str(exc))


class ExtractionProgressDialog(QDialog):
    """Modal dialog showing extraction progress."""

    def __init__(
        self,
        cfg: Config,
        manifest: list[dict[str, Any]],
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.cfg = cfg
        self.manifest = manifest
        self.setWindowTitle("Extracting Game Files")
        self.setMinimumWidth(500)
        self.setModal(True)

        self._setup_ui()
        self._start()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout()

        title = QLabel("Extracting game DataTables...")
        title.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(title)

        self.status_label = QLabel("Preparing...")
        layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, len(self.manifest))
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        self.count_label = QLabel("")
        layout.addWidget(self.count_label)

        self.close_btn = QPushButton("Cancel")
        self.close_btn.clicked.connect(self.reject)
        layout.addWidget(self.close_btn)

        self.setLayout(layout)

    def _start(self) -> None:
        self.worker = _ExtractWorker(self.cfg, self.manifest, self)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_progress(self, message: str, current: int, total: int) -> None:
        self.status_label.setText(message)
        self.progress_bar.setValue(current)
        self.count_label.setText(f"{current} / {total}")

    def _on_finished(self, results: dict) -> None:
        total = len(self.manifest)
        extracted = len(results)
        self.progress_bar.setValue(total)
        self.status_label.setText("Extraction complete.")
        self.count_label.setText(f"Extracted {extracted} / {total} files.")
        self.close_btn.setText("Close")
        self.close_btn.clicked.disconnect()
        self.close_btn.clicked.connect(self.accept)

        if extracted < total:
            missing = total - extracted
            QMessageBox.warning(
                self, "Partial Extraction",
                f"{missing} file(s) could not be extracted.\n"
                "Check the log for details.",
            )

    def _on_error(self, message: str) -> None:
        self.status_label.setText("Extraction failed.")
        self.close_btn.setText("Close")
        self.close_btn.clicked.disconnect()
        self.close_btn.clicked.connect(self.reject)
        QMessageBox.critical(self, "Extraction Error", message)
