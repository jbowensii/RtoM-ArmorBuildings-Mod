"""Tab 4 — Armor Recipes Maintain Mod (from armorUpdaterUI.py)."""

from __future__ import annotations

import copy
import os
import re

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QMessageBox, QPushButton, QVBoxLayout, QWidget,
)

from src.armor.mod_utils import sandbox_exclusive_items, unlock_conditions
from src.gui.shared import build_combined
from src.utils.json_handler import load_json, save_json


class ArmorUpdaterTab(QWidget):
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

        # Path to DT_ItemRecipes in TobisMod/json_data/
        self._recipes_path = os.path.join(
            tobis_mod_dir, "json_data",
            "Moria", "Content", "Tech", "Data", "Items", "DT_ItemRecipes.json",
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

        self.restore_btn = QPushButton("Restore Shayar, Amzul and Masharuz armors")
        self.restore_btn.setFixedSize(300, 150)
        self.restore_btn.clicked.connect(self._restore_bwg)

        self.sandbox_btn = QPushButton("Sandbox to Campaign Items")
        self.sandbox_btn.setFixedSize(300, 150)
        self.sandbox_btn.setEnabled(False)
        self.sandbox_btn.clicked.connect(self._sandbox_to_campaign)

        layout.addWidget(self.build_btn, alignment=Qt.AlignHCenter)
        layout.addWidget(self.restore_btn, alignment=Qt.AlignHCenter)
        layout.addWidget(self.sandbox_btn, alignment=Qt.AlignHCenter)
        self.setLayout(layout)

    @staticmethod
    def _clean_name(name: str) -> str:
        return re.sub(r"_(White|Black|Gold)_", "_", name)

    def _build_combined(self) -> None:
        """Combine per-item Tobis_json/ files into TobisMod/json_data/."""
        build_combined(self, self.tobis_json_dir,
                       self.game_extract_dir, self.tobis_mod_dir)

    def _restore_bwg(self) -> None:
        """Restore BWG colour variants directly in json_data/."""
        tpl_path = os.path.join(
            self.templates_dir, "MoreArmor", "UnlockRequiredItems.json",
        )

        dt = load_json(self._recipes_path)
        tpl = load_json(tpl_path)

        for item in dt.get("Exports", [{}])[0].get("Table", {}).get("Data", []):
            try:
                raw = item["Value"][0]["Value"][0]["Value"]
            except (IndexError, KeyError, TypeError):
                continue
            if any(c in raw for c in ("_White_", "_Black_", "_Gold_")):
                base = self._clean_name(raw)
                try:
                    if item["Value"][14]["Value"][0]["Value"] == "EMorRecipeUnlockType::Manual":
                        item["Value"][14]["Value"][0]["Value"] = "EMorRecipeUnlockType::DiscoverDependencies"
                except (IndexError, KeyError):
                    pass
                try:
                    obj = copy.deepcopy(tpl)
                    obj["Value"][0]["Value"][0]["Value"] = base
                    item["Value"][14]["Value"][3] = obj
                except (IndexError, KeyError, TypeError):
                    pass

        save_json(self._recipes_path, dt)
        QMessageBox.information(self, "Success", "Shayar, Amzul and Masharuz armors restored.")
        self.restore_btn.setEnabled(False)
        self.sandbox_btn.setEnabled(True)

    def _sandbox_to_campaign(self) -> None:
        """Unlock sandbox-exclusive items for campaign directly in json_data/."""
        u_structs = load_json(os.path.join(
            self.templates_dir, "MoreArmor", "UnlockRequirementsStructs.json",
        ))
        dummy = load_json(os.path.join(
            self.templates_dir, "MoreArmor", "DumyStructs.json",
        ))

        dt = load_json(self._recipes_path)
        recipes = dt.get("Exports", [{}])[0].get("Table", {}).get("Data", [])

        for item in sandbox_exclusive_items():
            for recipe in recipes:
                if recipe.get("Name") == item["Tag"]:
                    if recipe["Value"][12]["Value"][0]["Value"] != "EMorRecipeUnlockType::DiscoverDependencies":
                        recipe["Value"][12]["Value"][0]["Value"] = "EMorRecipeUnlockType::DiscoverDependencies"
                        unlock_conditions(recipe, item["UnlockOption"], item["UnlockRequirement"], u_structs, dummy)
                    if recipe["Value"][15]["Value"] != "ERowEnabledState::Live":
                        recipe["Value"][15]["Value"] = "ERowEnabledState::Live"

        save_json(self._recipes_path, dt)
        QMessageBox.information(self, "Success", "Sandbox items unlocked for campaign.")
        self.sandbox_btn.setEnabled(False)
        self.restore_btn.setEnabled(True)
