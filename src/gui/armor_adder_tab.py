"""Tab 3 — New Armor Adder (from armorAdderUI.py)."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup, QCheckBox, QComboBox, QCompleter, QFormLayout,
    QGridLayout, QGroupBox, QHBoxLayout, QLabel, QMessageBox,
    QPushButton, QRadioButton, QSpinBox, QVBoxLayout, QWidget,
)

from src.armor.mod_utils import missing_armor_recipes, dt_item_recipes_handle


class ArmorAdderTab(QWidget):
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

    def __init__(self, tobis_json_dir: str, templates_dir: str, items: dict,
                 unlock_requirements: dict) -> None:
        super().__init__()
        self.tobis_json_dir = tobis_json_dir
        self.templates_dir = templates_dir
        self.items = items
        self.unlock_requirements = unlock_requirements
        self.unlock_type = "UnlockRequiredItems"
        self.visible_unlock_map: dict[str, str] = {}
        self.materials_widgets: list = []
        self.station_checkboxes: list[QCheckBox] = []
        self.missing_armor = []  # populated after extraction
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout()

        self.armor_combo = QComboBox()
        self.armor_combo.addItems([list(d.keys())[0] for d in self.missing_armor])

        # Crafting stations
        cs_group = QGroupBox("Crafting Stations")
        cs_layout = QGridLayout()
        for i, (tag, name) in enumerate(self.CRAFTING_STATIONS.items()):
            cb = QCheckBox(name)
            self.station_checkboxes.append(cb)
            cs_layout.addWidget(cb, i // 2, i % 2)
        cs_group.setLayout(cs_layout)

        # Materials
        self.mat_layout = QVBoxLayout()
        btn_row = QHBoxLayout()
        add_btn = QPushButton("Add Material")
        add_btn.clicked.connect(self._add_material)
        rm_btn = QPushButton("Remove Material")
        rm_btn.clicked.connect(self._remove_material)
        btn_row.addWidget(add_btn)
        btn_row.addWidget(rm_btn)

        # Unlock conditions
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
        layout.addLayout(form)
        layout.addWidget(QLabel("Materials (max 6):"))
        layout.addLayout(self.mat_layout)
        layout.addLayout(btn_row)
        layout.addWidget(unlock_group)
        layout.addWidget(save_btn)
        self.setLayout(layout)
        self._add_material()
        self._update_unlock_items()

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

    def _add_material(self) -> None:
        if len(self.materials_widgets) >= 6:
            QMessageBox.warning(self, "Limit", "Max 6 materials.")
            return
        row = QHBoxLayout()
        cat_cb = QComboBox()
        cat_cb.addItems(list(self.items.keys()))
        name_cb = QComboBox()
        name_cb.setEditable(True)
        vmap: dict[str, str] = {}

        def _update(cat: str) -> None:
            tags = self.items.get(cat, {})
            name_cb.clear()
            vmap.clear()
            names = []
            for t, n in tags.items():
                vmap[n] = t
                names.append(n)
            names.sort()
            name_cb.addItems(names)
            name_cb.setCompleter(QCompleter(names))

        cat_cb.currentTextChanged.connect(_update)
        _update(cat_cb.currentText())
        count = QSpinBox()
        count.setRange(1, 999)
        row.addWidget(cat_cb)
        row.addWidget(name_cb)
        row.addWidget(QLabel("x"))
        row.addWidget(count)
        self.mat_layout.addLayout(row)
        self.materials_widgets.append((name_cb, count, vmap))

    def _remove_material(self) -> None:
        if len(self.materials_widgets) <= 1:
            QMessageBox.warning(self, "Minimum", "At least one material required.")
            return
        idx = self.mat_layout.count() - 1
        item = self.mat_layout.itemAt(idx)
        if item and item.layout():
            while item.layout().count():
                w = item.layout().takeAt(0).widget()
                if w:
                    w.setParent(None)
            self.mat_layout.removeItem(item.layout())
        self.materials_widgets.pop()

    def _save(self) -> None:
        if not any(cb.isChecked() for cb in self.station_checkboxes):
            QMessageBox.warning(self, "No Station", "Select at least one crafting station.")
            return

        idx = self.armor_combo.currentIndex()
        armor_name = self.armor_combo.currentText()
        armor_tag = self.missing_armor[idx].get(armor_name)

        materials = []
        for name_w, count_w, vmap in self.materials_widgets:
            vis = name_w.currentText().strip()
            materials.append((vmap.get(vis, vis), count_w.value()))

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

        self.missing_armor = missing_armor_recipes(
            self.templates_dir, "", self.tobis_json_dir,
        )
        self.armor_combo.clear()
        self.armor_combo.addItems([list(d.keys())[0] for d in self.missing_armor])
        QMessageBox.information(self, "Saved", f"Armor recipe '{armor_tag}' added.")
