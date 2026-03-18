"""Tab 1 — New Construction Adder (from RtoM-Moding-Tool constructionUI.py)."""

from __future__ import annotations

import json
import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup, QComboBox, QCompleter, QFormLayout, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QListWidget, QMessageBox, QPushButton,
    QRadioButton, QSpinBox, QSplitter, QVBoxLayout, QWidget,
)

from src.construction.mod_utils import (
    architecture_handle, dt_constructions_handle, dt_construction_recipes_handle,
)
from src.utils.json_split_combine import combine_all


class ConstructionAdderTab(QWidget):
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

    # ── UI ─────────────────────────────────────────────────────────
    def _setup_ui(self) -> None:
        outer = QHBoxLayout()

        # ── Left pane: Build button + item list ──
        left = QVBoxLayout()

        self.build_btn = QPushButton("Build Combined Files")
        self.build_btn.setStyleSheet("font-weight: bold; padding: 8px;")
        self.build_btn.clicked.connect(self._build_combined)
        left.addWidget(self.build_btn)

        left.addWidget(QLabel("Saved Constructions:"))
        self.item_list = QListWidget()
        self.item_list.currentItemChanged.connect(self._on_item_selected)
        left.addWidget(self.item_list)

        self.delete_btn = QPushButton("Delete Selected")
        self.delete_btn.clicked.connect(self._delete_selected)
        left.addWidget(self.delete_btn)

        left_widget = QWidget()
        left_widget.setLayout(left)
        left_widget.setMaximumWidth(280)

        # ── Right pane: form ──
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
        add_btn.clicked.connect(self._add_material)
        rm_btn = QPushButton("Remove Material")
        rm_btn.clicked.connect(self._remove_material)
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

        # ── Splitter ──
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        outer.addWidget(splitter)
        self.setLayout(outer)

        self._add_material()
        self._update_unlock_items()
        self._refresh_item_list()

    # ── Item list ───────────────────────────────────────────────────
    def _refresh_item_list(self) -> None:
        """Reload the list of per-item construction files."""
        self.item_list.clear()
        dt_dir = os.path.join(self.tobis_json_dir, "DT_Constructions")
        if os.path.isdir(dt_dir):
            for fname in sorted(os.listdir(dt_dir)):
                if fname.endswith(".json"):
                    self.item_list.addItem(fname[:-5])

    def _on_item_selected(self, current, _previous) -> None:
        """Load and display the selected per-item file in the form."""
        if not current:
            return
        tag = current.text()

        # Load from DT_Constructions per-item file
        dt_path = os.path.join(
            self.tobis_json_dir, "DT_Constructions", f"{tag}.json",
        )
        if not os.path.isfile(dt_path):
            return

        with open(dt_path, "r", encoding="utf-8") as f:
            dt_data = json.load(f)

        row = dt_data.get("Row", {})
        self.tag_display.setText(row.get("Name", tag))

        # Try to extract display name from Architecture file
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

        # Extract asset path from row
        try:
            asset = row["Value"][3]["Value"]["AssetPath"]["AssetName"]
            # Strip the _C suffix
            if asset.endswith("_C"):
                asset = asset.rsplit(".", 1)[0]
            self.asset_input.setText(asset)
        except (KeyError, IndexError, TypeError):
            pass

    def _delete_selected(self) -> None:
        """Delete the selected item's per-item files."""
        current = self.item_list.currentItem()
        if not current:
            QMessageBox.warning(self, "No Selection", "Select an item to delete.")
            return

        tag = current.text()
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Delete '{tag}' from all construction tables?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        for table in ("DT_Constructions", "DT_ConstructionRecipes", "Architecture"):
            path = os.path.join(self.tobis_json_dir, table, f"{tag}.json")
            if os.path.isfile(path):
                os.remove(path)

        self._refresh_item_list()
        QMessageBox.information(self, "Deleted", f"'{tag}' removed.")

    def _build_combined(self) -> None:
        """Combine per-item files into TobisMod/json_data/."""
        output = os.path.join(self.tobis_mod_dir, "json_data")
        try:
            results = combine_all(
                self.tobis_json_dir, self.game_extract_dir, output,
            )
            total = sum(results.values())
            detail = ", ".join(f"{k}: {v}" for k, v in results.items())
            QMessageBox.information(
                self, "Build Complete",
                f"Combined {total} items into TobisMod/json_data/.\n\n{detail}",
            )
        except Exception as exc:
            QMessageBox.critical(self, "Build Failed", str(exc))

    # ── Slots ──────────────────────────────────────────────────────
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

    def _add_material(self) -> None:
        if len(self.materials_widgets) >= 6:
            QMessageBox.warning(self, "Limit", "Max 6 materials.")
            return
        row = QHBoxLayout()
        cat_cb = QComboBox()
        cat_cb.addItems(list(self.items.keys()))
        name_cb = QComboBox()
        name_cb.setEditable(True)
        visible_map: dict[str, str] = {}

        def _update(category: str) -> None:
            tags = self.items.get(category, {})
            name_cb.clear()
            visible_map.clear()
            names = []
            for t, n in tags.items():
                visible_map[n] = t
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
        self.materials_widgets.append((name_cb, count, visible_map))

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
        user_name = self.user_name.text().strip()
        name = self.name_input.text().strip()
        desc = self.desc_input.text().strip()
        asset = self.asset_input.text().strip()
        if not name or not desc or not asset:
            QMessageBox.warning(self, "Empty Fields", "Please fill all fields.")
            return

        materials = []
        for name_w, count_w, vmap in self.materials_widgets:
            vis = name_w.currentText().strip()
            materials.append((vmap.get(vis, vis), count_w.value()))

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

        self._refresh_item_list()
        QMessageBox.information(self, "Saved", f"Construction '{unique}' added.")
