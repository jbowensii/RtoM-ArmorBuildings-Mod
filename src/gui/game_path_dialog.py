"""First-run dialog for selecting the game installation path."""

from __future__ import annotations

import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup, QDialog, QFileDialog, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QPushButton, QRadioButton, QVBoxLayout,
)

from src.config import Config
from src.utils.game_extractor import detect_game_paths


class GamePathDialog(QDialog):
    """Modal dialog that prompts the user to select a game install path."""

    def __init__(self, cfg: Config, parent=None) -> None:
        super().__init__(parent)
        self.cfg = cfg
        self.setWindowTitle("Game Installation Path")
        self.setMinimumWidth(550)
        self.setModal(True)

        self._detected = detect_game_paths()
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout()

        title = QLabel("Select your Return to Moria installation:")
        title.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(title)

        self.radio_group = QButtonGroup(self)

        # Steam option
        self.radio_steam = QRadioButton("Steam")
        steam_path = next((p for p, t in self._detected if t == "Steam"), "")
        if steam_path:
            self.radio_steam.setText(f"Steam  —  {steam_path}")
            self.radio_steam.setProperty("path", steam_path)
        else:
            self.radio_steam.setText("Steam  (not detected)")
            self.radio_steam.setEnabled(False)
            self.radio_steam.setProperty("path", "")
        self.radio_group.addButton(self.radio_steam)
        layout.addWidget(self.radio_steam)

        # Epic Games option
        self.radio_epic = QRadioButton("Epic Games")
        epic_path = next((p for p, t in self._detected if t == "Epic Games"), "")
        if epic_path:
            self.radio_epic.setText(f"Epic Games  —  {epic_path}")
            self.radio_epic.setProperty("path", epic_path)
        else:
            self.radio_epic.setText("Epic Games  (not detected)")
            self.radio_epic.setEnabled(False)
            self.radio_epic.setProperty("path", "")
        self.radio_group.addButton(self.radio_epic)
        layout.addWidget(self.radio_epic)

        # Custom option
        self.radio_custom = QRadioButton("Custom path")
        self.radio_custom.setProperty("path", "")
        self.radio_group.addButton(self.radio_custom)
        layout.addWidget(self.radio_custom)

        custom_row = QHBoxLayout()
        self.custom_edit = QLineEdit()
        self.custom_edit.setPlaceholderText("Browse to game installation folder...")
        self.custom_edit.setEnabled(False)
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse)
        custom_row.addWidget(self.custom_edit)
        custom_row.addWidget(browse_btn)
        layout.addLayout(custom_row)

        self.radio_custom.toggled.connect(
            lambda checked: self.custom_edit.setEnabled(checked)
        )

        # Pre-select first detected path
        if self._detected:
            first_type = self._detected[0][1]
            if first_type == "Steam":
                self.radio_steam.setChecked(True)
            else:
                self.radio_epic.setChecked(True)
        else:
            self.radio_custom.setChecked(True)

        # Buttons
        btn_row = QHBoxLayout()
        ok_btn = QPushButton("OK")
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self._accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addStretch()
        btn_row.addWidget(ok_btn)
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

        self.setLayout(layout)

    def _browse(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self, "Select Game Installation Folder"
        )
        if path:
            self.custom_edit.setText(path)

    def _get_selected_path(self) -> tuple[str, str]:
        """Return (path, type) for the selected option."""
        if self.radio_steam.isChecked():
            return (self.radio_steam.property("path"), "Steam")
        if self.radio_epic.isChecked():
            return (self.radio_epic.property("path"), "Epic Games")
        return (self.custom_edit.text().strip(), "Custom")

    def _accept(self) -> None:
        path, install_type = self._get_selected_path()
        if not path:
            QMessageBox.warning(self, "No Path", "Please select a game installation path.")
            return

        paks_dir = os.path.join(path, "Moria", "Content", "Paks")
        if not os.path.isdir(paks_dir):
            QMessageBox.warning(
                self, "Invalid Path",
                f"Could not find game paks at:\n{paks_dir}\n\n"
                "Please select the folder containing the game installation.",
            )
            return

        self.cfg.set_game_path(path, install_type)
        self.accept()
