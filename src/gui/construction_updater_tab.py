"""Tab 2 — More Buildings Maintain Mod (from constructionUpdater.py)."""

from __future__ import annotations

import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QLabel, QMessageBox, QPushButton, QVBoxLayout, QWidget,
)

from src.construction.mod_utils import advanced_bannister_post_stone_unlock
from src.utils.json_handler import load_json, save_json


class ConstructionUpdaterTab(QWidget):
    def __init__(self, saves_dir: str, data_dir: str) -> None:
        super().__init__()
        self.saves_dir = saves_dir
        self.data_dir = data_dir
        self._setup_ui()

    def _path(self, category: str, filename: str) -> str:
        base = {
            "vanilla": os.path.join(self.saves_dir, "UpdateMods", "MoreBuildings"),
            "new": os.path.join(self.saves_dir, "newObjects", "MoreBuildings"),
            "moded": os.path.join(self.saves_dir, "UpdateMods", "MoreBuildings", "moded"),
            "restore": os.path.join(self.saves_dir, "UpdateMods", "RestoreBuildings"),
        }[category]
        return os.path.abspath(os.path.join(base, filename))

    def _setup_ui(self) -> None:
        layout = QVBoxLayout()
        self.restore_btn = QPushButton("Restore Constructions")
        self.restore_btn.setFixedSize(300, 150)
        self.restore_btn.clicked.connect(self._restore)
        self.restore_btn.setToolTip("Restore constructions removed in the 1.2 update.")

        self.update_btn = QPushButton("Update Mod")
        self.update_btn.setFixedSize(300, 150)
        self.update_btn.setEnabled(False)
        self.update_btn.clicked.connect(self._update_mod)
        self.update_btn.setToolTip("Merge new constructions into the mod.")

        layout.addWidget(self.restore_btn, alignment=Qt.AlignHCenter)
        layout.addWidget(self.update_btn, alignment=Qt.AlignHCenter)
        self.setLayout(layout)

    def _restore(self) -> None:
        data = load_json(self._path("vanilla", "DT_ConstructionRecipes.json"))
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

        save_json(self._path("moded", "DT_ConstructionRecipes.json"), data)
        save_json(self._path("restore", "DT_ConstructionRecipes.json"), data)
        QMessageBox.information(self, "Done", "Constructions removed in 1.2 have been restored.")
        self.restore_btn.setEnabled(False)
        self.update_btn.setEnabled(True)

    def _update_mod(self) -> None:
        arch = load_json(self._path("vanilla", "Architecture.json"))
        recipes = load_json(self._path("moded", "DT_ConstructionRecipes.json"))
        constr = load_json(self._path("vanilla", "DT_Constructions.json"))

        new_arch = load_json(self._path("new", "Architecture.json"))
        new_recipes = load_json(self._path("new", "DT_ConstructionRecipes.json"))
        new_constr = load_json(self._path("new", "DT_Constructions.json"))

        st_imports = load_json(os.path.join(self.data_dir, "Imports.json"))
        arch_st = st_imports["Imports"][0:4]

        # Architecture
        arch["Exports"][0]["Table"]["Value"].extend(new_arch["Exports"][0]["Table"]["Value"])

        # Constructions — fix import indices
        vanilla_len = len(constr["Imports"])
        serial_deps: list[int] = []
        for imp in new_constr["Imports"]:
            if imp["OuterIndex"] < 0:
                imp["OuterIndex"] = -(vanilla_len + abs(imp["OuterIndex"]))
                serial_deps.append(imp["OuterIndex"] - 1)

        for item in new_constr["Exports"][0]["Table"]["Data"]:
            for prop in item["Value"]:
                if prop["$type"] == "UAssetAPI.PropertyTypes.Objects.ObjectPropertyData, UAssetAPI":
                    if isinstance(prop.get("Value"), int) and prop["Value"] < 0:
                        prop["Value"] = -(vanilla_len + abs(prop["Value"]))

        constr["NameMap"].extend(new_constr["NameMap"])
        constr["Exports"][0]["Table"]["Data"].extend(new_constr["Exports"][0]["Table"]["Data"])
        constr["Imports"].extend(new_constr["Imports"])

        moded_len = len(constr["Imports"])
        for i, imp in enumerate(arch_st):
            if imp["OuterIndex"] < 0:
                imp["OuterIndex"] = -(moded_len + i)
                serial_deps.append(imp["OuterIndex"] - 1)

        constr["Imports"].extend(arch_st)
        constr["Exports"][0]["SerializationBeforeCreateDependencies"].extend(serial_deps)

        # Recipes
        for nm in new_recipes["NameMap"]:
            if nm not in recipes["NameMap"]:
                recipes["NameMap"].append(nm)
        recipes["Exports"][0]["Table"]["Data"].extend(new_recipes["Exports"][0]["Table"]["Data"])

        save_json(self._path("moded", "Architecture.json"), arch)
        save_json(self._path("moded", "DT_ConstructionRecipes.json"), recipes)
        save_json(self._path("moded", "DT_Constructions.json"), constr)
        QMessageBox.information(self, "Done", "More Buildings mod files have been created.")
        self.restore_btn.setEnabled(True)
        self.update_btn.setEnabled(False)
