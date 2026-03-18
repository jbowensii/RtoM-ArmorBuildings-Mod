"""Tab 4 — Armor Recipes Maintain Mod (from armorUpdaterUI.py)."""

from __future__ import annotations

import copy
import os
import re

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QLabel, QMessageBox, QPushButton, QVBoxLayout, QWidget,
)

from src.armor.mod_utils import sandbox_exclusive_items, unlock_conditions
from src.utils.json_handler import load_json, save_json


class ArmorUpdaterTab(QWidget):
    def __init__(self, saves_dir: str, data_dir: str) -> None:
        super().__init__()
        self.saves_dir = saves_dir
        self.data_dir = data_dir
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout()

        self.restore_btn = QPushButton("Restore Shayar, Amzul and Masharuz armors")
        self.restore_btn.setFixedSize(300, 150)
        self.restore_btn.clicked.connect(self._restore_bwg)

        self.sandbox_btn = QPushButton("Sandbox to Campaign Items")
        self.sandbox_btn.setFixedSize(300, 150)
        self.sandbox_btn.setEnabled(False)
        self.sandbox_btn.clicked.connect(self._sandbox_to_campaign)

        self.cosmetic_btn = QPushButton("Add Cosmetic Armors")
        self.cosmetic_btn.setFixedSize(300, 150)
        self.cosmetic_btn.setEnabled(False)
        self.cosmetic_btn.clicked.connect(self._add_cosmetic)

        layout.addWidget(self.restore_btn, alignment=Qt.AlignHCenter)
        layout.addWidget(self.sandbox_btn, alignment=Qt.AlignHCenter)
        layout.addWidget(self.cosmetic_btn, alignment=Qt.AlignHCenter)
        self.setLayout(layout)

    @staticmethod
    def _clean_name(name: str) -> str:
        return re.sub(r"_(White|Black|Gold)_", "_", name)

    def _restore_bwg(self) -> None:
        src_path = os.path.join(self.saves_dir, "UpdateMods", "MoreArmor", "DT_ItemRecipes.json")
        tpl_path = os.path.join(self.data_dir, "MoreArmor", "UnlockRequiredItems.json")
        dst_path = os.path.join(self.saves_dir, "UpdateMods", "MoreArmor", "moded", "DT_ItemRecipes.json")

        dt = load_json(src_path)
        tpl = load_json(tpl_path)

        for item in dt.get("Exports", [{}])[0].get("Table", {}).get("Data", []):
            try:
                raw = item["Value"][0]["Value"][0]["Value"]
            except (IndexError, KeyError, TypeError):
                continue
            if any(c in raw for c in ("_White_", "_Black_", "_Gold_")):
                base = self._clean_name(raw)
                try:
                    if item["Value"][12]["Value"][0]["Value"] == "EMorRecipeUnlockType::Manual":
                        item["Value"][12]["Value"][0]["Value"] = "EMorRecipeUnlockType::DiscoverDependencies"
                except (IndexError, KeyError):
                    pass
                try:
                    obj = copy.deepcopy(tpl)
                    obj["Value"][0]["Value"][0]["Value"] = base
                    item["Value"][12]["Value"][3] = obj
                except (IndexError, KeyError, TypeError):
                    pass

        save_json(dst_path, dt)
        QMessageBox.information(self, "Success", "Shayar, Amzul and Masharuz armors restored.")
        self.restore_btn.setEnabled(False)
        self.sandbox_btn.setEnabled(True)

    def _sandbox_to_campaign(self) -> None:
        moded_path = os.path.join(self.saves_dir, "UpdateMods", "MoreArmor", "moded", "DT_ItemRecipes.json")
        u_structs = load_json(os.path.join(self.data_dir, "MoreArmor", "UnlockRequirementsStructs.json"))
        dummy = load_json(os.path.join(self.data_dir, "MoreArmor", "DumyStructs.json"))

        dt = load_json(moded_path)
        recipes = dt.get("Exports", [{}])[0].get("Table", {}).get("Data", [])

        for item in sandbox_exclusive_items():
            for recipe in recipes:
                if recipe.get("Name") == item["Tag"]:
                    if recipe["Value"][12]["Value"][0]["Value"] != "EMorRecipeUnlockType::DiscoverDependencies":
                        recipe["Value"][12]["Value"][0]["Value"] = "EMorRecipeUnlockType::DiscoverDependencies"
                        unlock_conditions(recipe, item["UnlockOption"], item["UnlockRequirement"], u_structs, dummy)
                    if recipe["Value"][13]["Value"] != "ERowEnabledState::Live":
                        recipe["Value"][13]["Value"] = "ERowEnabledState::Live"

        save_json(moded_path, dt)
        QMessageBox.information(self, "Success", "Sandbox items unlocked for campaign.")
        self.sandbox_btn.setEnabled(False)
        self.cosmetic_btn.setEnabled(True)

    def _add_cosmetic(self) -> None:
        moded_path = os.path.join(self.saves_dir, "UpdateMods", "MoreArmor", "moded", "DT_ItemRecipes.json")
        new_path = os.path.join(self.saves_dir, "newObjects", "MoreArmor", "DT_ItemRecipes.json")

        dt = load_json(moded_path)
        new_dt = load_json(new_path)

        dt["NameMap"].extend(new_dt["NameMap"])
        dt["Exports"][0]["Table"]["Data"].extend(new_dt["Exports"][0]["Table"]["Data"])

        save_json(moded_path, dt)
        QMessageBox.information(self, "Success", "Cosmetic armor recipes added.")
        self.cosmetic_btn.setEnabled(False)
        self.restore_btn.setEnabled(True)
