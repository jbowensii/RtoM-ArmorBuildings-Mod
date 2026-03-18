"""Tab 2 — More Buildings Maintain Mod (from constructionUpdater.py)."""

from __future__ import annotations

import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QMessageBox, QPushButton, QVBoxLayout, QWidget,
)

from src.construction.mod_utils import advanced_bannister_post_stone_unlock
from src.gui.shared import build_combined
from src.utils.json_handler import load_json, save_json


class ConstructionUpdaterTab(QWidget):
    def __init__(
        self,
        tobis_mod_dir: str,
        templates_dir: str,
        data_dir: str,
        tobis_json_dir: str,
        game_extract_dir: str,
    ) -> None:
        super().__init__()
        self.tobis_mod_dir = tobis_mod_dir
        self.templates_dir = templates_dir
        self.data_dir = data_dir
        self.tobis_json_dir = tobis_json_dir
        self.game_extract_dir = game_extract_dir

        # Paths within TobisMod/json_data/ (game path structure)
        self._building_dir = os.path.join(
            tobis_mod_dir, "json_data",
            "Moria", "Content", "Tech", "Data", "Building",
        )
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout()

        self.build_btn = QPushButton("Build Combined Files")
        self.build_btn.setFixedSize(300, 150)
        self.build_btn.clicked.connect(self._build_combined)
        self.build_btn.setToolTip(
            "Combine per-item Tobis_json/ files into TobisMod/json_data/."
        )

        self.restore_btn = QPushButton("Restore Constructions")
        self.restore_btn.setFixedSize(300, 150)
        self.restore_btn.clicked.connect(self._restore)
        self.restore_btn.setToolTip("Restore constructions removed in the 1.2 update.")

        self.update_btn = QPushButton("Update Mod")
        self.update_btn.setFixedSize(300, 150)
        self.update_btn.setEnabled(False)
        self.update_btn.clicked.connect(self._update_mod)
        self.update_btn.setToolTip("Apply import fixes and string table entries.")

        layout.addWidget(self.build_btn, alignment=Qt.AlignHCenter)
        layout.addWidget(self.restore_btn, alignment=Qt.AlignHCenter)
        layout.addWidget(self.update_btn, alignment=Qt.AlignHCenter)
        self.setLayout(layout)

    def _build_combined(self) -> None:
        """Combine per-item Tobis_json/ files into TobisMod/json_data/."""
        build_combined(self, self.tobis_json_dir,
                       self.game_extract_dir, self.tobis_mod_dir)

    def _restore(self) -> None:
        """Restore constructions removed in game patch 1.2 directly in json_data/."""
        recipes_path = os.path.join(self._building_dir, "DT_ConstructionRecipes.json")
        data = load_json(recipes_path)

        constructions = [
            "Elder_Archway_A", "Advanced_Column_Wood_A", "Advanced_Column_Wood_D",
            "Advanced_Fence_Wood_1m", "Advanced_Fence_Wood", "Crude_Column",
            "Elder_Wall_E", "Scaffolding_Platform_Open", "Elder_Wall_A_Crown",
            "Elder_Wall_Short_A", "Elder_Window_B", "Elder_Window_A",
            "Elder_Wall_Thin_A_Crown", "Elder_Wall_Thin_B", "Elder_Archway_C",
            "Elder_Wall_B_Crown", "Elder_Wall_D", "Advanced_Column_Wood_B",
            "Elder_Wall_E_Crown", "Elder_Archway_Corner",
            "Scaffolding_Platform_1x1x3", "Elder_Wall_Short_B", "Elder_Wall_B",
            "Elder_Window_C", "Elder_Wall_A", "Elder_Wall_C", "Elder_Wall_Thin_A",
            "Scaffolding_Platform_1x3x3", "Elder_Archway_Vertical",
            "Elder_Archway_Horizontal_Large", "Elder_Wall_Corner_Crown",
            "Advanced_Stairs_Railing_1m_V2", "Advanced_Bannister_Post_Stone",
        ]
        for recipe in data["Exports"][0]["Table"]["Data"]:
            name = recipe.get("Name")
            if name in constructions:
                for prop in recipe["Value"]:
                    if prop.get("Name") == "DefaultUnlocks":
                        try:
                            prop["Value"][0]["Value"] = "EMorRecipeUnlockType::DiscoverDependencies"
                            if name == "Advanced_Bannister_Post_Stone":
                                prop["Value"][3] = advanced_bannister_post_stone_unlock()
                        except (KeyError, IndexError, TypeError):
                            continue

        save_json(recipes_path, data)
        QMessageBox.information(self, "Done", "Constructions removed in 1.2 have been restored.")
        self.restore_btn.setEnabled(False)
        self.update_btn.setEnabled(True)

    def _update_mod(self) -> None:
        """Apply string table imports to DT_Constructions in json_data/."""
        constr_path = os.path.join(self._building_dir, "DT_Constructions.json")

        constr = load_json(constr_path)

        st_imports = load_json(os.path.join(self.data_dir, "Imports.json"))
        arch_st = st_imports["Imports"][0:4]

        # Add string table imports to constructions
        moded_len = len(constr["Imports"])
        serial_deps: list[int] = []
        for i, imp in enumerate(arch_st):
            if imp["OuterIndex"] < 0:
                imp["OuterIndex"] = -(moded_len + i)
                serial_deps.append(imp["OuterIndex"] - 1)

        constr["Imports"].extend(arch_st)
        if "SerializationBeforeCreateDependencies" in constr["Exports"][0]:
            constr["Exports"][0]["SerializationBeforeCreateDependencies"].extend(serial_deps)

        save_json(constr_path, constr)
        QMessageBox.information(self, "Done", "More Buildings mod files have been updated.")
        self.restore_btn.setEnabled(True)
        self.update_btn.setEnabled(False)
