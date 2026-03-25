"""Tab — New Construction: add constructions, view/delete saved items, build."""

from __future__ import annotations

import json
import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QButtonGroup, QCheckBox, QComboBox, QCompleter,
    QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QPushButton, QRadioButton, QScrollArea, QSpinBox,
    QSplitter, QStyle, QVBoxLayout, QWidget,
)

from src.construction.mod_utils import (
    architecture_handle, dt_constructions_handle, dt_construction_recipes_handle,
)
from src.gui.shared import (
    build_combined, create_item_list_pane, delete_per_item, refresh_item_list,
)

# Field value files for autocomplete
_FIELD_VALUES_DIR = os.path.join(
    os.path.dirname(__file__), os.pardir, os.pardir, "data", "field_values",
)


def _load_field_values(table: str) -> dict:
    """Load field values JSON for autocomplete."""
    path = os.path.join(_FIELD_VALUES_DIR, f"{table}_fields.json")
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _load_string_table() -> dict:
    """Load string table lookup (tag → {name, description})."""
    path = os.path.join(_FIELD_VALUES_DIR, "string_table_lookup.json")
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _enum_short_values(field_data: dict) -> list[str]:
    """Extract short enum names (after ::) from field_data."""
    return sorted({v.split("::")[-1] for v in field_data.get("values", [])})


def _make_combo(values: list[str], editable: bool = True) -> QComboBox:
    """Create a QComboBox with autocomplete."""
    cb = QComboBox()
    cb.setEditable(editable)
    cb.addItems(values)
    if editable:
        cb.setCompleter(QCompleter(values))
    return cb


class ConstructionAdderTab(QWidget):
    """New Construction tab with left item list and right form."""

    def __init__(self, tobis_json_dir: str, templates_dir: str,
                 game_extract_dir: str, tobis_mod_dir: str,
                 items: dict, category_tags: dict,
                 unlock_requirements: dict,
                 data_dir: str | None = None) -> None:
        super().__init__()
        self.tobis_json_dir = tobis_json_dir
        self.templates_dir = templates_dir
        self.game_extract_dir = game_extract_dir
        self.tobis_mod_dir = tobis_mod_dir
        self.data_dir = data_dir
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

        # Load field values for autocomplete
        self._const_fields = _load_field_values("DT_Constructions")
        self._recipe_fields = _load_field_values("DT_ConstructionRecipes")
        self._string_table = _load_string_table()

        self._setup_ui()

    # ── UI Setup ─────────────────────────────────────────────────
    def _setup_ui(self) -> None:
        outer = QHBoxLayout()

        # Left pane
        left_widget, self.build_btn, self.item_list, self.delete_btn = \
            create_item_list_pane("Saved Constructions:")
        self.build_btn.clicked.connect(
            lambda: build_combined(self, self.tobis_json_dir,
                                   self.game_extract_dir, self.tobis_mod_dir,
                                   self.data_dir)
        )
        self.item_list.currentItemChanged.connect(self._on_item_selected)
        self.delete_btn.clicked.connect(self._delete_selected)

        # Right pane — scrollable form
        right = QVBoxLayout()
        self._build_basic_info(right)
        self._build_construction_fields(right)
        self._build_recipe_fields(right)

        save_btn = QPushButton("Save Construction")
        save_btn.setStyleSheet("font-weight: bold; padding: 8px;")
        save_btn.clicked.connect(self._save)
        right.addWidget(save_btn)

        right.addStretch()

        right_inner = QWidget()
        right_inner.setLayout(right)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(right_inner)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_widget)
        splitter.addWidget(scroll)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        outer.addWidget(splitter)
        self.setLayout(outer)

        self._add_material_row()
        self._update_unlock_items()
        refresh_item_list(self.item_list, self.tobis_json_dir, "DT_Constructions")

    def _build_basic_info(self, parent_layout: QVBoxLayout) -> None:
        group = QGroupBox("Basic Info")
        form = QFormLayout()

        # Pack Name with autocomplete from existing packs
        pack_values = self._const_fields.get("PackNames", {}).get("values", [])
        self.pack_name = QLineEdit()
        self.pack_name.setPlaceholderText("Enter your pack name (e.g., Tobi)")
        if pack_values:
            self.pack_name.setCompleter(QCompleter(sorted(pack_values)))

        self.name_input = QLineEdit()
        self.name_input.setReadOnly(True)
        self.tag_display = QLineEdit()
        self.tag_display.setReadOnly(True)
        self.desc_input = QLineEdit()
        self.desc_input.setReadOnly(True)

        form.addRow("Pack Name", self.pack_name)
        form.addRow("Name", self.name_input)
        form.addRow("Name Tag", self.tag_display)
        form.addRow("Description", self.desc_input)

        group.setLayout(form)
        parent_layout.addWidget(group)

    def _build_construction_fields(self, parent_layout: QVBoxLayout) -> None:
        group = QGroupBox("DT_Constructions")
        form = QFormLayout()

        # Asset Path with autocomplete
        actor_values = self._const_fields.get("Actor", {}).get("values", [])
        self.asset_input = QLineEdit()
        self.asset_input.setPlaceholderText("/Game/Items/Breakables/...")
        if actor_values:
            self.asset_input.setCompleter(QCompleter(actor_values))

        # Category Tags
        tag_values = self._const_fields.get("Tags", {}).get("values", [])
        self.cat_main = QComboBox()
        self.cat_main.addItems(self.main_categories)
        self.cat_main.currentTextChanged.connect(self._update_subcategories)
        self.cat_sub = QComboBox()
        self._update_subcategories(self.cat_main.currentText())

        # EnabledState
        enabled_values = _enum_short_values(
            self._const_fields.get("EnabledState", {}))
        if not enabled_values:
            enabled_values = ["Live", "Disabled"]
        self.const_enabled = _make_combo(enabled_values, editable=False)

        form.addRow("Asset Path", self.asset_input)
        form.addRow("Main Category", self.cat_main)
        form.addRow("Sub Category", self.cat_sub)
        if tag_values:
            self.tags_combo = _make_combo(tag_values)
            form.addRow("Gameplay Tags", self.tags_combo)
        form.addRow("EnabledState", self.const_enabled)

        group.setLayout(form)
        parent_layout.addWidget(group)

    def _build_recipe_fields(self, parent_layout: QVBoxLayout) -> None:
        group = QGroupBox("DT_ConstructionRecipes")
        layout = QVBoxLayout()

        # Enum fields
        form = QFormLayout()

        rf = self._recipe_fields
        self.build_process = _make_combo(
            _enum_short_values(rf.get("BuildProcess", {})) or ["DualMode"],
            editable=False)
        self.location_req = _make_combo(
            _enum_short_values(rf.get("LocationRequirement", {}))
            or ["Anywhere", "Base"], editable=False)
        self.placement_type = _make_combo(
            _enum_short_values(rf.get("PlacementType", {}))
            or ["FreePlacement", "SnapGrid"], editable=False)
        self.foundation_rule = _make_combo(
            _enum_short_values(rf.get("FoundationRule", {}))
            or ["Always", "FreePlaced", "Never"], editable=False)
        self.monument_type = _make_combo(
            _enum_short_values(rf.get("MonumentType", {})) or ["None"],
            editable=False)
        recipe_enabled_vals = _enum_short_values(
            rf.get("EnabledState", {}))
        if not recipe_enabled_vals:
            recipe_enabled_vals = ["Live", "Disabled"]
        self.recipe_enabled = _make_combo(recipe_enabled_vals, editable=False)

        form.addRow("BuildProcess", self.build_process)
        form.addRow("LocationRequirement", self.location_req)
        form.addRow("PlacementType", self.placement_type)
        form.addRow("FoundationRule", self.foundation_rule)
        form.addRow("MonumentType", self.monument_type)
        form.addRow("EnabledState", self.recipe_enabled)
        layout.addLayout(form)

        # Boolean fields — checkboxes in rows
        bool_layout = QVBoxLayout()

        row1 = QHBoxLayout()
        self.cb_on_wall = QCheckBox("On Wall")
        self.cb_on_floor = QCheckBox("On Floor")
        self.cb_on_floor.setChecked(True)
        self.cb_place_water = QCheckBox("Place On Water")
        self.cb_override_rot = QCheckBox("Override Rotation")
        row1.addWidget(self.cb_on_wall)
        row1.addWidget(self.cb_on_floor)
        row1.addWidget(self.cb_place_water)
        row1.addWidget(self.cb_override_rot)
        bool_layout.addLayout(row1)

        row2 = QHBoxLayout()
        self.cb_auto_foundation = QCheckBox("Auto Foundation")
        self.cb_inherit_stability = QCheckBox("Inherit Foundation Stability")
        self.cb_allow_refunds = QCheckBox("Allow Refunds")
        self.cb_allow_refunds.setChecked(True)
        row2.addWidget(self.cb_auto_foundation)
        row2.addWidget(self.cb_inherit_stability)
        row2.addWidget(self.cb_allow_refunds)
        bool_layout.addLayout(row2)

        layout.addLayout(bool_layout)

        # --- Required Materials (part of recipe) ---
        layout.addWidget(QLabel("Required Materials (max 6):"))
        self.mat_layout = QVBoxLayout()
        layout.addLayout(self.mat_layout)

        add_btn = QPushButton("Add Material")
        add_btn.clicked.connect(self._add_material_row)
        layout.addWidget(add_btn)

        # --- Unlock Conditions (part of recipe) ---
        unlock_label = QLabel("Unlock Conditions (DefaultUnlocks):")
        layout.addWidget(unlock_label)

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
        layout.addLayout(btn_layout)

        self.unlock_combo = QComboBox()
        self.unlock_combo.setEditable(True)
        layout.addWidget(self.unlock_combo)

        group.setLayout(layout)
        parent_layout.addWidget(group)

    # ── Material helpers ─────────────────────────────────────────
    def _add_material_row(self) -> None:
        if len(self.materials_widgets) >= 6:
            QMessageBox.warning(self, "Limit", "Max 6 materials.")
            return

        # Get autocomplete values from field_values
        mat_values = self._recipe_fields.get(
            "DefaultRequiredMaterials.MaterialHandle", {},
        ).get("values", [])

        row = QHBoxLayout()
        cat_cb = QComboBox()
        cat_cb.addItems(sorted(self.items.keys()))
        name_cb = QComboBox()
        name_cb.setEditable(True)
        vmap: dict[str, str] = {}

        def _update(category: str) -> None:
            tags = self.items.get(category, {})
            name_cb.clear()
            vmap.clear()
            names = []
            for t, n in tags.items():
                vmap[n] = t
                names.append(n)
            names.sort()
            name_cb.addItems(names)
            # Combine item names + raw material tags for completer
            all_values = sorted(set(names + mat_values))
            name_cb.setCompleter(QCompleter(all_values))

        cat_cb.currentTextChanged.connect(_update)
        _update(cat_cb.currentText())

        count = QSpinBox()
        count.setRange(1, 999)

        # Trash button to remove this specific row
        trash_btn = QPushButton()
        trash_icon = QApplication.style().standardIcon(QStyle.SP_TrashIcon)
        if trash_icon.isNull():
            trash_btn.setText("\u2715")
        else:
            trash_btn.setIcon(trash_icon)
        trash_btn.setFixedWidth(30)
        trash_btn.setToolTip("Remove this material")

        row.addWidget(cat_cb)
        row.addWidget(name_cb)
        row.addWidget(QLabel("x"))
        row.addWidget(count)
        row.addWidget(trash_btn)
        self.mat_layout.addLayout(row)
        entry = (name_cb, count, vmap)
        self.materials_widgets.append(entry)

        # Connect trash button — capture the row layout and entry
        trash_btn.clicked.connect(lambda _, r=row, e=entry: self._remove_specific_material(r, e))

    def _remove_specific_material(self, row_layout: QHBoxLayout,
                                  entry: tuple) -> None:
        """Remove a specific material row by its layout and widget entry."""
        if len(self.materials_widgets) <= 1:
            QMessageBox.warning(self, "Minimum", "At least one material required.")
            return
        # Remove widgets from the layout
        while row_layout.count():
            w = row_layout.takeAt(0).widget()
            if w:
                w.setParent(None)
        self.mat_layout.removeItem(row_layout)
        if entry in self.materials_widgets:
            self.materials_widgets.remove(entry)

    def _clear_all_material_rows(self) -> None:
        """Remove all material rows (used when loading a saved item)."""
        while self.materials_widgets:
            entry = self.materials_widgets[-1]
            idx = self.mat_layout.count() - 1
            item = self.mat_layout.itemAt(idx)
            if item and item.layout():
                while item.layout().count():
                    w = item.layout().takeAt(0).widget()
                    if w:
                        w.setParent(None)
                self.mat_layout.removeItem(item.layout())
            self.materials_widgets.pop()

    # ── Item list callbacks ──────────────────────────────────────
    def _on_item_selected(self, current, _previous) -> None:
        """Load and display the selected construction in all form fields."""
        if not current:
            return
        tag = current.text()

        # Load DT_Constructions
        dt_path = os.path.join(
            self.tobis_json_dir, "DT_Constructions", f"{tag}.json",
        )
        if not os.path.isfile(dt_path):
            return
        with open(dt_path, "r", encoding="utf-8") as f:
            dt_data = json.load(f)
        row = dt_data.get("Row", {})
        self.tag_display.setText(row.get("Name", tag))

        # Extract pack name from tag (e.g., "100BuildingsPack_Item_A" → "100BuildingsPack")
        tag_parts = tag.split("_")
        for i, part in enumerate(tag_parts):
            if "Pack" in part:
                self.pack_name.setText("_".join(tag_parts[:i + 1]))
                break

        # Name & Description — try string table first, then Architecture file
        st_entry = self._string_table.get(tag)
        if st_entry:
            self.name_input.setText(st_entry.get("name", ""))
            self.desc_input.setText(st_entry.get("description", ""))
        else:
            arch_path = os.path.join(
                self.tobis_json_dir, "Architecture", f"{tag}.json",
            )
            if os.path.isfile(arch_path):
                with open(arch_path, "r", encoding="utf-8") as f:
                    arch = json.load(f)
                for arch_entry in arch.get("Entries", []):
                    if arch_entry[0].endswith(".Name"):
                        self.name_input.setText(arch_entry[1])
                    elif arch_entry[0].endswith(".Description"):
                        self.desc_input.setText(arch_entry[1])

        # DT_Constructions fields
        const_vals = row.get("Value", [])
        self._load_asset(const_vals)
        self._load_const_tags(const_vals)
        self._load_enum_combo(const_vals, "EnabledState", self.const_enabled)

        # Load DT_ConstructionRecipes
        recipe_path = os.path.join(
            self.tobis_json_dir, "DT_ConstructionRecipes", f"{tag}.json",
        )
        if os.path.isfile(recipe_path):
            with open(recipe_path, "r", encoding="utf-8") as f:
                recipe_data = json.load(f)
            recipe_vals = recipe_data.get("Row", {}).get("Value", [])
            self._load_recipe_fields(recipe_vals)

    def _load_asset(self, values: list) -> None:
        for entry in values:
            if entry.get("Name") == "Actor":
                try:
                    asset = entry["Value"]["AssetPath"]["AssetName"]
                    if asset.endswith("_C"):
                        asset = asset.rsplit(".", 1)[0]
                    self.asset_input.setText(asset)
                except (KeyError, TypeError):
                    pass
                return

    def _load_const_tags(self, values: list) -> None:
        for entry in values:
            if entry.get("Name") == "Tags":
                try:
                    tags = entry["Value"][0]["Value"]
                    if tags and hasattr(self, "tags_combo"):
                        self.tags_combo.setCurrentText(tags[0])
                except (KeyError, IndexError, TypeError):
                    pass
                return

    @staticmethod
    def _load_enum_combo(values: list, field_name: str,
                         combo: QComboBox) -> None:
        for entry in values:
            if entry.get("Name") == field_name:
                val = entry.get("Value", "")
                short = val.split("::")[-1] if "::" in val else val
                idx = combo.findText(short)
                if idx >= 0:
                    combo.setCurrentIndex(idx)
                return

    @staticmethod
    def _load_bool_check(values: list, field_name: str,
                         checkbox: QCheckBox) -> None:
        for entry in values:
            if entry.get("Name") == field_name:
                checkbox.setChecked(bool(entry.get("Value", False)))
                return

    def _load_recipe_fields(self, values: list) -> None:
        """Populate all recipe form fields from loaded JSON values."""
        self._load_enum_combo(values, "BuildProcess", self.build_process)
        self._load_enum_combo(values, "LocationRequirement", self.location_req)
        self._load_enum_combo(values, "PlacementType", self.placement_type)
        self._load_enum_combo(values, "FoundationRule", self.foundation_rule)
        self._load_enum_combo(values, "MonumentType", self.monument_type)
        self._load_enum_combo(values, "EnabledState", self.recipe_enabled)

        self._load_bool_check(values, "bOnWall", self.cb_on_wall)
        self._load_bool_check(values, "bOnFloor", self.cb_on_floor)
        self._load_bool_check(values, "bPlaceOnWater", self.cb_place_water)
        self._load_bool_check(values, "bOverrideRotation", self.cb_override_rot)
        self._load_bool_check(values, "bAutoFoundation", self.cb_auto_foundation)
        self._load_bool_check(values, "bInheritAutoFoundationStability",
                              self.cb_inherit_stability)
        self._load_bool_check(values, "bAllowRefunds", self.cb_allow_refunds)

        # Load materials
        self._load_materials(values)

        # Load unlock info
        self._load_unlocks(values)

    def _load_materials(self, values: list) -> None:
        """Load DefaultRequiredMaterials into the material rows."""
        for entry in values:
            if entry.get("Name") == "DefaultRequiredMaterials":
                mats = entry.get("Value", [])
                # Clear existing rows
                self._clear_all_material_rows()
                # Add rows for each material
                for mat in mats:
                    mat_vals = mat.get("Value", [])
                    mat_name = ""
                    count = 1
                    for field in mat_vals:
                        if field.get("Name") == "MaterialHandle":
                            try:
                                mat_name = field["Value"][0]["Value"]
                            except (KeyError, IndexError, TypeError):
                                pass
                        elif field.get("Name") == "Count":
                            count = field.get("Value", 1)
                    self._add_material_row()
                    if self.materials_widgets:
                        name_w, count_w, vmap = self.materials_widgets[-1]
                        # Try to find by display name first
                        found = False
                        for display, tag in vmap.items():
                            if tag == mat_name:
                                name_w.setCurrentText(display)
                                found = True
                                break
                        if not found:
                            name_w.setCurrentText(mat_name)
                        count_w.setValue(count)
                if not mats:
                    self._add_material_row()
                return
        self._add_material_row()

    def _load_unlocks(self, values: list) -> None:
        """Load DefaultUnlocks into the unlock radio/combo."""
        for entry in values:
            if entry.get("Name") == "DefaultUnlocks":
                unlock_vals = entry.get("Value", [])
                for field in unlock_vals:
                    if field.get("Name") == "UnlockRequiredItems":
                        items = field.get("Value", [])
                        if items:
                            self.radio_item.setChecked(True)
                            self._update_unlock_items()
                            try:
                                tag = items[0]["Value"][0]["Value"]
                                for display, t in self.visible_unlock_map.items():
                                    if t == tag:
                                        self.unlock_combo.setCurrentText(display)
                                        return
                                self.unlock_combo.setCurrentText(tag)
                            except (KeyError, IndexError, TypeError):
                                pass
                            return
                    elif field.get("Name") == "UnlockRequiredConstructions":
                        items = field.get("Value", [])
                        if items:
                            self.radio_construction.setChecked(True)
                            self._update_unlock_constructions()
                            try:
                                tag = items[0]["Value"][0]["Value"]
                                for display, t in self.visible_unlock_map.items():
                                    if t == tag:
                                        self.unlock_combo.setCurrentText(display)
                                        return
                                self.unlock_combo.setCurrentText(tag)
                            except (KeyError, IndexError, TypeError):
                                pass
                            return
                return

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

    # ── Form callbacks ───────────────────────────────────────────
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
        # Add autocomplete from field_values
        key = f"DefaultUnlocks.{self.unlock_type}"
        extra = self._recipe_fields.get(key, {}).get("values", [])
        if extra:
            all_items = sorted(set(
                list(self.visible_unlock_map.keys()) + extra
            ))
            self.unlock_combo.setCompleter(QCompleter(all_items))

    # ── Collect recipe overrides ─────────────────────────────────
    def _collect_recipe_overrides(self) -> dict:
        """Collect all recipe field values from the form."""
        return {
            "BuildProcess": self.build_process.currentText(),
            "LocationRequirement": self.location_req.currentText(),
            "PlacementType": self.placement_type.currentText(),
            "FoundationRule": self.foundation_rule.currentText(),
            "MonumentType": self.monument_type.currentText(),
            "bOnWall": self.cb_on_wall.isChecked(),
            "bOnFloor": self.cb_on_floor.isChecked(),
            "bPlaceOnWater": self.cb_place_water.isChecked(),
            "bOverrideRotation": self.cb_override_rot.isChecked(),
            "bAutoFoundation": self.cb_auto_foundation.isChecked(),
            "bInheritAutoFoundationStability": self.cb_inherit_stability.isChecked(),
            "bAllowRefunds": self.cb_allow_refunds.isChecked(),
            "EnabledState": self.recipe_enabled.currentText(),
        }

    def _collect_materials(self) -> list[tuple[str, int]]:
        """Extract (tag, count) pairs from the material widgets."""
        materials = []
        for name_w, count_w, vmap in self.materials_widgets:
            vis = name_w.currentText().strip()
            materials.append((vmap.get(vis, vis), count_w.value()))
        return materials

    # ── Rename support ───────────────────────────────────────────
    def _rename_item(self, old_tag: str, new_tag: str) -> None:
        """Rename per-item JSON files from old_tag to new_tag."""
        tables = ["DT_Constructions", "DT_ConstructionRecipes", "Architecture"]
        for table in tables:
            old_path = os.path.join(self.tobis_json_dir, table, f"{old_tag}.json")
            new_path = os.path.join(self.tobis_json_dir, table, f"{new_tag}.json")
            if os.path.isfile(old_path):
                os.rename(old_path, new_path)

    # ── Save ─────────────────────────────────────────────────────
    def _save(self) -> None:
        pack_name = self.pack_name.text().strip()
        name = self.name_input.text().strip()
        desc = self.desc_input.text().strip()
        asset = self.asset_input.text().strip()
        if not name or not desc or not asset:
            QMessageBox.warning(self, "Empty Fields", "Please fill all fields.")
            return

        materials = self._collect_materials()
        cat_key = f"{self.cat_main.currentText()}.{self.cat_sub.currentText()}"
        cat_tag = self.category_tags_raw.get(cat_key, "")

        # If user edited the Name Tag, use that directly; otherwise generate
        custom_tag = self.tag_display.text().strip()
        selected = self.item_list.currentItem()
        old_tag = selected.text() if selected else None

        if custom_tag and old_tag and custom_tag != old_tag:
            # User renamed — rename existing files first
            self._rename_item(old_tag, custom_tag)
            unique = custom_tag
        elif custom_tag and not old_tag:
            # User provided a custom tag for a new item
            unique = custom_tag
        else:
            tag = f"{pack_name}Pack_{name.title().replace(' ', '')}"
            unique = architecture_handle(tag, name, desc, self.tobis_json_dir)

        self.tag_display.setText(unique)

        # Always write Architecture entry
        arch_dir = os.path.join(self.tobis_json_dir, "Architecture")
        os.makedirs(arch_dir, exist_ok=True)
        arch_data = {
            "Entries": [
                [f"{unique}.Name", name],
                [f"{unique}.Description", desc],
            ]
        }
        arch_path = os.path.join(arch_dir, f"{unique}.json")
        with open(arch_path, "w", encoding="utf-8") as f:
            json.dump(arch_data, f, indent=2)

        dt_constructions_handle(
            unique, asset, cat_tag,
            self.tobis_json_dir, self.templates_dir, pack_name,
        )
        sel = self.unlock_combo.currentText()
        unlock_req = self.visible_unlock_map.get(sel, sel)
        recipe_overrides = self._collect_recipe_overrides()
        dt_construction_recipes_handle(
            unique, self.tobis_json_dir, self.templates_dir,
            cat_key, materials, self.unlock_type, unlock_req,
            recipe_overrides=recipe_overrides,
        )
        refresh_item_list(self.item_list, self.tobis_json_dir, "DT_Constructions")
        QMessageBox.information(self, "Saved", f"Construction '{unique}' saved.")
