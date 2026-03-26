"""Tab 6 — Recipe automation (colour-variant patching)."""

from __future__ import annotations

import traceback

from PySide6.QtWidgets import (
    QMessageBox, QPushButton, QTextEdit, QVBoxLayout, QWidget,
)

from src.gui.log_panel import StdoutCapture


class RecipesTab(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout()

        btn = QPushButton("Patch Colour-Variant Recipes")
        btn.setFixedSize(300, 60)
        btn.clicked.connect(self._run_patch)
        btn.setToolTip("Auto-link Black/White/Gold variant recipes to their base items.")

        self.output = QTextEdit()
        self.output.setReadOnly(True)

        layout.addWidget(btn)
        layout.addWidget(self.output)
        self.setLayout(layout)

    def _run_patch(self) -> None:
        self.output.clear()
        self.output.append("--- Patching colour variants ---")
        try:
            from src.recipes.colour_variants import run
            with StdoutCapture(self.output):
                run()
            self.output.append("--- Done ---")
        except SystemExit:
            self.output.append("--- Operation exited ---")
        except Exception:  # pylint: disable=broad-exception-caught
            self.output.append(traceback.format_exc())
            QMessageBox.critical(self, "Error", "Patch failed. See output.")
