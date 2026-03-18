"""Tab — New Construction: add constructions, view/delete saved items, build."""

from __future__ import annotations

import json
import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup, QComboBox, QFormLayout, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton,
    QRadioButton, QSplitter, QVBoxLayout, QWidget,
)

from src.construction.mod_utils import (
    architecture_handle, dt_constructions_handle, dt_construction_recipes_handle,
)
from src.gui.shared import (
    add_material_row, build_combined, collect_materials,
    create_item_list_pane, delete_per_item, refresh_item_list,
    remove_material_row,
)


class ConstructionAdderTab(QWidget):
    """New Construction tab with left item list and right form."""

    def __init__(self, tobis_json_dir: str, templates_dir: str,
                 game_extract_dir: str, tobis_mod_dir: str,
                 items: dict, category_tags: dict,
                 unlock_requirements: dict) -> None:
        super().__init__()
        self.tobis_json_dir = tobis_json_dir
        self.templates_dir = templates_dir
        self.game_extract_dir = game_extract_dir
        self.tobis_mod_dir = tobis_mod_dir
        self.items = items
        self.materials_widgets: list = []
        self.category_tags_raw = category_tags
        self.main_categories = sorted({k.split(".")[0] for k in category_tags})
        self.sub_categories: dict[str, list[str]] = {}
        for key in category_tags:
            main, sub = key.split(".")
            self.sub_categories.setdefault(main, []).append(sub)
        self.unlock_requirements = unlock_requirements
        self.unlock_type = "UnlockRequiredItems"
        self.visible_unlock_map: dict[str, str] = {}
        self._setup_ui()

    def _setup_ui(self) -> None:
        outer = QHBoxLayout()

        # Left pane
        left_widget, self.build_btn, self.item_list, self.delete_btn = \
            create_item_list_pane("Saved Constructions:")
        self.build_btn.clicked.connect(
            lambda: build_combined(self, self.tobis_json_dir,
                                   self.game_extract_dir, self.tobis_mod_dir)
        )
        self.item_list.currentItemChanged.connect(self._on_item_selected)
        self.delete_btn.clicked.connect(self._delete_selected)

        # Right pane: form
        right = QVBoxLayout()

        self.user_name = QLineEdit()
        self.user_name.setPlaceholderText("Enter your user name (e.g., Tobi)")
        self.name_input = QLineEdit(maxLength=30)
        self.name_input.setPlaceholderText("Enter the construction name")
        self.tag_display = QLineEdit()
        self.tag_display.setEnabled(False)
        self.desc_input = QLineEdit(maxLength=60)
        self.desc_input.setPlaceholderText("Enter the construction description")
        self.asset_input = QLineEdit()
        self.asset_input.setPlaceholderText("/Game/Items/Breakables/...")

        self.cat_main = QComboBox()
        self.cat_main.addItems(self.main_categories)
        self.cat_main.currentTextChanged.connect(self._update_subcategories)
        self.cat_sub = QComboBox()
        self._update_subcategories(self.cat_main.currentText())

        form = QFormLayout()
        form.addRow("User Name", self.user_name)
        form.addRow("Name", self.name_input)
        form.addRow("Name Tag", self.tag_display)
        form.addRow("Description", self.desc_input)
        form.addRow("Asset Path", self.asset_input)
        form.addRow("Main Category", self.cat_main)
        form.addRow("Sub Category", self.cat_sub)
        right.addLayout(form)

        right.addWidget(QLabel("Materials (max 6):"))
        self.mat_layout = QVBoxLayout()
        right.addLayout(self.mat_layout)

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
        right.addLayout(btn_row)

        # Unlock conditions
        group = QGroupBox("Unlock Conditions")
        g_layout = QVBoxLayout()
        btn_layout = QHBoxLayout()
        self.radio_item = QRadioButton("Discover Item")
        self.radio_item.setChecked(True)
        self.radio_item.clicked.connect(self._update_unlock_items)
        self.radio_construction = QRadioButton("Discover Construction")
        self.radio_construction.clicked.connect(self._update_unlock_constructions)
        self.unlock_group = QButtonGroup()
        self.unlock_group.addButton(self.radio_item)
        self.unlock_group.addButton(self.radio_construction)
        btn_layout.addWidget(self.radio_item)
        btn_layout.addWidget(self.radio_construction)
        g_layout.addLayout(btn_layout)
        self.unlock_combo = QComboBox()
        g_layout.addWidget(self.unlock_combo)
        group.setLayout(g_layout)
        right.addWidget(group)

        save_btn = QPushButton("Save Construction")
        save_btn.clicked.connect(self._save)
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
        refresh_item_list(self.item_list, self.tobis_json_dir, "DT_Constructions")

    # ── Item list callbacks ─────────────────────────────────────────
    def _on_item_selected(self, current, _previous) -> None:
        """Load and display the selected construction in the form."""
        if not current:
            return
        tag = current.text()
        dt_path = os.path.join(
            self.tobis_json_dir, "DT_Constructions", f"{tag}.json",
        )
        if not os.path.isfile(dt_path):
            return
        with open(dt_path, "r", encoding="utf-8") as f:
            dt_data = json.load(f)
        row = dt_data.get("Row", {})
        self.tag_display.setText(row.get("Name", tag))

        arch_path = os.path.join(
            self.tobis_json_dir, "Architecture", f"{tag}.json",
        )
        if os.path.isfile(arch_path):
            with open(arch_path, "r", encoding="utf-8") as f:
                arch = json.load(f)
            for entry in arch.get("Entries", []):
                if entry[0].endswith(".Name"):
                    self.name_input.setText(entry[1])
                elif entry[0].endswith(".Description"):
                    self.desc_input.setText(entry[1])
        try:
            asset = row["Value"][3]["Value"]["AssetPath"]["AssetName"]
            if asset.endswith("_C"):
                asset = asset.rsplit(".", 1)[0]
            self.asset_input.setText(asset)
        except (KeyError, IndexError, TypeError):
            pass

    def _delete_selected(self) -> None:
        tag = delete_per_item(
            self, self.item_list, self.tobis_json_dir,
            ["DT_Constructions", "DT_ConstructionRecipes", "Architecture"],
        )
        if tag:
            refresh_item_list(
                self.item_list, self.tobis_json_dir, "DT_Constructions",
            )
            QMessageBox.information(self, "Deleted", f"'{tag}' removed.")

    # ── Form callbacks ──────────────────────────────────────────────
    def _update_subcategories(self, main: str) -> None:
        self.cat_sub.clear()
        self.cat_sub.addItems(self.sub_categories.get(main, []))

    def _update_unlock_items(self) -> None:
        self.unlock_type = "UnlockRequiredItems"
        self._populate_unlock_combo()

    def _update_unlock_constructions(self) -> None:
        self.unlock_type = "UnlockRequiredConstructions"
        self._populate_unlock_combo()

    def _populate_unlock_combo(self) -> None:
        self.unlock_combo.clear()
        self.visible_unlock_map.clear()
        for tag, name in self.unlock_requirements.get(self.unlock_type, {}).items():
            self.visible_unlock_map[name] = tag
            self.unlock_combo.addItem(name)

    def _save(self) -> None:
        user_name = self.user_name.text().strip()
        name = self.name_input.text().strip()
        desc = self.desc_input.text().strip()
        asset = self.asset_input.text().strip()
        if not name or not desc or not asset:
            QMessageBox.warning(self, "Empty Fields", "Please fill all fields.")
            return

        materials = collect_materials(self.materials_widgets)
        cat_key = f"{self.cat_main.currentText()}.{self.cat_sub.currentText()}"
        cat_tag = self.category_tags_raw.get(cat_key, "")
        tag = f"{user_name}Pack_{name.title().replace(' ', '')}"

        unique = architecture_handle(tag, name, desc, self.tobis_json_dir)
        self.tag_display.setText(unique)
        dt_constructions_handle(
            unique, asset, cat_tag,
            self.tobis_json_dir, self.templates_dir, user_name,
        )
        sel = self.unlock_combo.currentText()
        unlock_req = self.visible_unlock_map.get(sel, sel)
        dt_construction_recipes_handle(
            unique, self.tobis_json_dir, self.templates_dir,
            cat_key, materials, self.unlock_type, unlock_req,
        )
        refresh_item_list(self.item_list, self.tobis_json_dir, "DT_Constructions")
        QMessageBox.information(self, "Saved", f"Construction '{unique}' added.")
