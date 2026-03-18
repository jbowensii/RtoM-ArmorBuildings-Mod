"""Tab — New Armor: add armor recipes, view/delete saved items, build."""

from __future__ import annotations

import json
import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup, QCheckBox, QComboBox, QFormLayout,
    QGridLayout, QGroupBox, QHBoxLayout, QLabel, QMessageBox,
    QPushButton, QRadioButton, QSplitter, QVBoxLayout, QWidget,
)

from src.armor.mod_utils import missing_armor_recipes, dt_item_recipes_handle
from src.gui.shared import (
    add_material_row, build_combined, collect_materials,
    create_item_list_pane, delete_per_item, refresh_item_list,
    remove_material_row,
)


class ArmorAdderTab(QWidget):
    """New Armor tab with left item list and right form."""

    CRAFTING_STATIONS = {
        "CraftingStation_BasicForge": "Forge",
        "CraftingStation_AdvancedForge": "Khuzdul Forge",
        "CraftingStation_Workbench": "Workbench",
        "CraftingStation_FabricStation": "Loom",
        "CraftingStation_LegendayElvishForge": "Great Forge of Narvi",
        "CraftingStation_FloodedForge": "Great Belegost Forge",
        "CraftingStation_NogrodForge": "Great Forge of Nogrod",
        "CraftingStation_DurinForge": "Great Forge of Durin",
        "CraftingStation_MithrilForge": "Great Mithril Forge",
    }

    def __init__(self, tobis_json_dir: str, templates_dir: str,
                 game_extract_dir: str, tobis_mod_dir: str,
                 items: dict, unlock_requirements: dict) -> None:
        super().__init__()
        self.tobis_json_dir = tobis_json_dir
        self.templates_dir = templates_dir
        self.game_extract_dir = game_extract_dir
        self.tobis_mod_dir = tobis_mod_dir
        self.items = items
        self.unlock_requirements = unlock_requirements
        self.unlock_type = "UnlockRequiredItems"
        self.visible_unlock_map: dict[str, str] = {}
        self.materials_widgets: list = []
        self.station_checkboxes: list[QCheckBox] = []
        self.missing_armor = missing_armor_recipes(templates_dir, tobis_json_dir)
        self._setup_ui()

    def _setup_ui(self) -> None:
        outer = QHBoxLayout()

        # Left pane
        left_widget, self.build_btn, self.item_list, self.delete_btn = \
            create_item_list_pane("Saved Armor Recipes:")
        self.build_btn.clicked.connect(
            lambda: build_combined(self, self.tobis_json_dir,
                                   self.game_extract_dir, self.tobis_mod_dir)
        )
        self.item_list.currentItemChanged.connect(self._on_item_selected)
        self.delete_btn.clicked.connect(self._delete_selected)

        # Right pane: form
        right = QVBoxLayout()

        self.armor_combo = QComboBox()
        self.armor_combo.addItems([list(d.keys())[0] for d in self.missing_armor])

        cs_group = QGroupBox("Crafting Stations")
        cs_layout = QGridLayout()
        for i, (_tag, name) in enumerate(self.CRAFTING_STATIONS.items()):
            cb = QCheckBox(name)
            self.station_checkboxes.append(cb)
            cs_layout.addWidget(cb, i // 2, i % 2)
        cs_group.setLayout(cs_layout)

        self.mat_layout = QVBoxLayout()
        btn_row = QHBoxLayout()
        add_btn = QPushButton("Add Material")
        add_btn.clicked.connect(
            lambda: add_material_row(self.mat_layout, self.materials_widgets,
                                     self.items, parent=self)
        )
        rm_btn = QPushButton("Remove Material")
        rm_btn.clicked.connect(
            lambda: remove_material_row(self.mat_layout, self.materials_widgets,
                                        parent=self)
        )
        btn_row.addWidget(add_btn)
        btn_row.addWidget(rm_btn)

        unlock_group = QGroupBox("Unlock Conditions")
        u_layout = QVBoxLayout()
        u_btn = QHBoxLayout()
        self.radio_item = QRadioButton("Discover Item")
        self.radio_item.setChecked(True)
        self.radio_item.clicked.connect(self._update_unlock_items)
        self.radio_construction = QRadioButton("Discover Construction")
        self.radio_construction.clicked.connect(self._update_unlock_constructions)
        self.btn_group = QButtonGroup()
        self.btn_group.addButton(self.radio_item)
        self.btn_group.addButton(self.radio_construction)
        u_btn.addWidget(self.radio_item)
        u_btn.addWidget(self.radio_construction)
        u_layout.addLayout(u_btn)
        self.unlock_combo = QComboBox()
        u_layout.addWidget(self.unlock_combo)
        unlock_group.setLayout(u_layout)

        save_btn = QPushButton("Save Armor")
        save_btn.clicked.connect(self._save)

        form = QFormLayout()
        form.addRow("Armor Name:", self.armor_combo)
        form.addRow(cs_group)
        right.addLayout(form)
        right.addWidget(QLabel("Materials (max 6):"))
        right.addLayout(self.mat_layout)
        right.addLayout(btn_row)
        right.addWidget(unlock_group)
        right.addWidget(save_btn)

        right_widget = QWidget()
        right_widget.setLayout(right)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        outer.addWidget(splitter)
        self.setLayout(outer)

        add_material_row(self.mat_layout, self.materials_widgets, self.items)
        self._update_unlock_items()
        refresh_item_list(self.item_list, self.tobis_json_dir, "DT_ItemRecipes")

    # ── Item list callbacks ─────────────────────────────────────────
    def _on_item_selected(self, current, _previous) -> None:
        """Display info about the selected armor recipe."""
        if not current:
            return
        # Selection just highlights — no form population for armor

    def _delete_selected(self) -> None:
        tag = delete_per_item(
            self, self.item_list, self.tobis_json_dir, ["DT_ItemRecipes"],
        )
        if tag:
            refresh_item_list(
                self.item_list, self.tobis_json_dir, "DT_ItemRecipes",
            )
            self._refresh_missing()
            QMessageBox.information(self, "Deleted", f"'{tag}' removed.")

    def _refresh_missing(self) -> None:
        """Refresh the missing armor dropdown."""
        self.missing_armor = missing_armor_recipes(
            self.templates_dir, self.tobis_json_dir,
        )
        self.armor_combo.clear()
        self.armor_combo.addItems([list(d.keys())[0] for d in self.missing_armor])

    # ── Form callbacks ──────────────────────────────────────────────
    def _update_unlock_items(self) -> None:
        self.unlock_type = "UnlockRequiredItems"
        self._populate_unlock()

    def _update_unlock_constructions(self) -> None:
        self.unlock_type = "UnlockRequiredConstructions"
        self._populate_unlock()

    def _populate_unlock(self) -> None:
        self.unlock_combo.clear()
        self.visible_unlock_map.clear()
        for tag, name in self.unlock_requirements.get(self.unlock_type, {}).items():
            self.visible_unlock_map[name] = tag
            self.unlock_combo.addItem(name)

    def _save(self) -> None:
        if not any(cb.isChecked() for cb in self.station_checkboxes):
            QMessageBox.warning(self, "No Station", "Select at least one crafting station.")
            return

        idx = self.armor_combo.currentIndex()
        armor_name = self.armor_combo.currentText()
        armor_tag = self.missing_armor[idx].get(armor_name)

        materials = collect_materials(self.materials_widgets)
        stations = [
            tag for tag, name in self.CRAFTING_STATIONS.items()
            if any(cb.isChecked() and cb.text() == name for cb in self.station_checkboxes)
        ]

        sel = self.unlock_combo.currentText()
        unlock_req = self.visible_unlock_map.get(sel, sel)

        dt_item_recipes_handle(
            self.tobis_json_dir, self.templates_dir, armor_tag,
            stations, materials, self.unlock_type, unlock_req,
        )

        self._refresh_missing()
        refresh_item_list(self.item_list, self.tobis_json_dir, "DT_ItemRecipes")
        QMessageBox.information(self, "Saved", f"Armor recipe '{armor_tag}' added.")
