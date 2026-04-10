"""Tab -- New Construction: add constructions, view/delete saved items, build.

Uses shared helpers (field_helpers, MaterialPicker, UnlockPicker) to avoid
duplicating combo-box, material-row, and unlock-picker logic.
"""

from __future__ import annotations

import json
import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QCompleter, QFormLayout, QGroupBox, QHBoxLayout,
    QLabel, QLineEdit, QMessageBox, QPushButton, QScrollArea,
    QSplitter, QVBoxLayout, QWidget,
)

from src.construction.mod_utils import (
    dt_constructions_handle, dt_construction_recipes_handle,
)
from src.gui.field_helpers import (
    enum_short_values, load_field_values, load_string_table, make_combo,
)
from src.gui.material_picker import MaterialPicker
from src.gui.shared import (
    build_combined, create_item_list_pane, delete_per_item, refresh_item_list,
)
from src.gui.unlock_picker import UnlockPicker

# Tables whose per-item files live alongside constructions
_RELATED_TABLES = ["DT_Constructions", "DT_ConstructionRecipes", "Architecture"]


class ConstructionAdderTab(QWidget):
    """New Construction tab with a left item list and right scrollable form.

    Delegates material editing to MaterialPicker and unlock selection to
    UnlockPicker, keeping only construction-specific logic here.
    """

    # pylint: disable=too-many-instance-attributes,too-few-public-methods

    def __init__(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self, tobis_json_dir: str, templates_dir: str,
        game_extract_dir: str, tobis_mod_dir: str,
        items: dict, unlock_requirements: dict,
        data_dir: str | None = None,
    ) -> None:
        super().__init__()
        self.tobis_json_dir = tobis_json_dir
        self.templates_dir = templates_dir
        self.game_extract_dir = game_extract_dir
        self.tobis_mod_dir = tobis_mod_dir
        self.data_dir = data_dir
        self.items = items
        self.unlock_requirements = unlock_requirements

        # Field-value indexes for autocomplete
        self._const_fv = load_field_values("DT_Constructions")
        self._recipe_fv = load_field_values("DT_ConstructionRecipes")
        self._string_table = load_string_table()

        # Pre-declare all widget attrs set by _setup_ui (avoids W0201)
        self.build_btn = self.item_list = self.new_btn = self.delete_btn = None
        self.pack_name = self.tag_display = None
        self.desc_input = self.desc_string = self.asset_input = None
        self.tags_combo = None
        self.const_enabled = self.build_process = self.location_req = None
        self.placement_type = self.foundation_rule = None
        self.monument_type = self.recipe_enabled = None
        self.cb_on_wall = self.cb_on_floor = self.cb_place_water = None
        self.cb_override_rot = self.cb_auto_foundation = None
        self.cb_inherit_stability = self.cb_allow_refunds = None
        self._material_picker = self._unlock_picker = None

        self._setup_ui()

    # ── UI layout ────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        """Build the two-pane layout: item list (left) and form (right)."""
        outer = QHBoxLayout()

        # Left pane -- saved construction list
        left_widget, self.build_btn, self.item_list, self.new_btn, \
            self.delete_btn = (
                create_item_list_pane("Saved Constructions:"))
        self.build_btn.clicked.connect(lambda: build_combined(
            self, self.tobis_json_dir,
            self.game_extract_dir, self.tobis_mod_dir, self.data_dir))
        self.item_list.currentItemChanged.connect(self._on_item_selected)
        self.new_btn.clicked.connect(self._new_item)
        self.delete_btn.clicked.connect(self._delete_selected)

        # Right pane -- scrollable form
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

        self._material_picker.add_row()
        refresh_item_list(self.item_list, self.tobis_json_dir, "DT_Constructions")

    def _build_basic_info(self, layout: QVBoxLayout) -> None:
        """Pack name, tag, description path, and description string fields.

        The in-game Name is not entered here — it's set in Unreal Engine.
        The Name Tag is used as the row name and to auto-generate the
        DisplayName/Description string table keys ({tag}.Name / {tag}.Description).
        """
        group = QGroupBox("Basic Info")
        form = QFormLayout()
        packs = self._const_fv.get("PackNames", {}).get("values", [])
        self.pack_name = QLineEdit()
        self.pack_name.setPlaceholderText("Enter your pack name (e.g., Tobi)")
        if packs:
            self.pack_name.setCompleter(QCompleter(sorted(packs)))
        # Name Tag — the game row name, also used as filename
        self.tag_display = QLineEdit()
        self.tag_display.setPlaceholderText("No spaces, e.g. TobiPack_AleKeg_A")
        self.tag_display.textChanged.connect(self._sanitize_tag)
        # Description — editable, string table path
        self.desc_input = QLineEdit()
        self.desc_input.setPlaceholderText(
            "String table path (auto: {tag}.Description)")
        # Description String — resolved text or "NOT FOUND"
        self.desc_string = QLineEdit()
        self.desc_string.setReadOnly(True)
        for label, widget in [
            ("Pack Name", self.pack_name),
            ("Name Tag", self.tag_display),
            ("Description", self.desc_input),
            ("Description String", self.desc_string),
        ]:
            form.addRow(label, widget)
        group.setLayout(form)
        layout.addWidget(group)

    def _build_construction_fields(self, layout: QVBoxLayout) -> None:
        """Asset path, gameplay tags, enabled state.

        The Gameplay Tags combo is the single source for the category —
        pick a UI.Construction.Category.* value directly.
        """
        group = QGroupBox("DT_Constructions")
        form = QFormLayout()
        actors = self._const_fv.get("Actor", {}).get("values", [])
        self.asset_input = QLineEdit()
        self.asset_input.setPlaceholderText("/Game/Items/Breakables/...")
        if actors:
            self.asset_input.setCompleter(QCompleter(actors))
        enabled = (enum_short_values(self._const_fv.get("EnabledState", {}))
                   or ["Live", "Disabled"])
        self.const_enabled = make_combo(enabled, editable=False)
        form.addRow("Asset Path", self.asset_input)
        tag_vals = self._const_fv.get("Tags", {}).get("values", [])
        if tag_vals:
            self.tags_combo = make_combo(tag_vals)
            form.addRow("Gameplay Tags", self.tags_combo)
        form.addRow("EnabledState", self.const_enabled)
        group.setLayout(form)
        layout.addWidget(group)

    # ── Recipe sub-group builders ────────────────────────────────

    def _build_recipe_fields(self, layout: QVBoxLayout) -> None:
        """Recipe enums, booleans, materials, and unlock conditions."""
        group = QGroupBox("DT_ConstructionRecipes")
        inner = QVBoxLayout()
        self._build_recipe_enums(inner)
        self._build_recipe_booleans(inner)
        self._build_recipe_materials(inner)
        self._build_recipe_unlocks(inner)
        group.setLayout(inner)
        layout.addWidget(group)

    def _build_recipe_enums(self, layout: QVBoxLayout) -> None:
        """BuildProcess, LocationRequirement, PlacementType, etc."""
        form = QFormLayout()
        rfv = self._recipe_fv
        self.build_process = make_combo(
            enum_short_values(rfv.get("BuildProcess", {})) or ["DualMode"],
            editable=False)
        self.location_req = make_combo(
            enum_short_values(rfv.get("LocationRequirement", {}))
            or ["Anywhere", "Base"], editable=False)
        self.placement_type = make_combo(
            enum_short_values(rfv.get("PlacementType", {}))
            or ["FreePlacement", "SnapGrid"], editable=False)
        self.foundation_rule = make_combo(
            enum_short_values(rfv.get("FoundationRule", {}))
            or ["Always", "FreePlaced", "Never"], editable=False)
        self.monument_type = make_combo(
            enum_short_values(rfv.get("MonumentType", {})) or ["None"],
            editable=False)
        self.recipe_enabled = make_combo(
            enum_short_values(rfv.get("EnabledState", {}))
            or ["Live", "Disabled"], editable=False)
        for label, combo in [("BuildProcess", self.build_process),
                             ("LocationRequirement", self.location_req),
                             ("PlacementType", self.placement_type),
                             ("FoundationRule", self.foundation_rule),
                             ("MonumentType", self.monument_type),
                             ("EnabledState", self.recipe_enabled)]:
            form.addRow(label, combo)
        layout.addLayout(form)

    def _build_recipe_booleans(self, layout: QVBoxLayout) -> None:
        """Two rows of boolean checkboxes for recipe flags."""
        self.cb_on_wall = QCheckBox("On Wall")
        self.cb_on_floor = QCheckBox("On Floor")
        self.cb_on_floor.setChecked(True)
        self.cb_place_water = QCheckBox("Place On Water")
        self.cb_override_rot = QCheckBox("Override Rotation")
        self.cb_auto_foundation = QCheckBox("Auto Foundation")
        self.cb_inherit_stability = QCheckBox("Inherit Foundation Stability")
        self.cb_allow_refunds = QCheckBox("Allow Refunds")
        self.cb_allow_refunds.setChecked(True)
        for row_cbs in ([self.cb_on_wall, self.cb_on_floor,
                         self.cb_place_water, self.cb_override_rot],
                        [self.cb_auto_foundation, self.cb_inherit_stability,
                         self.cb_allow_refunds]):
            row = QHBoxLayout()
            for cb in row_cbs:
                row.addWidget(cb)
            layout.addLayout(row)

    def _build_recipe_materials(self, layout: QVBoxLayout) -> None:
        """Material picker rows (delegated to MaterialPicker)."""
        layout.addWidget(QLabel("Required Materials (max 6):"))
        mat_layout = QVBoxLayout()
        layout.addLayout(mat_layout)
        mat_ac = self._recipe_fv.get(
            "DefaultRequiredMaterials.MaterialHandle", {}).get("values", [])
        self._material_picker = MaterialPicker(
            parent=self, layout=mat_layout,
            items_index=self.items, autocomplete_values=mat_ac)
        add_btn = QPushButton("Add Material")
        add_btn.clicked.connect(self._material_picker.add_row)
        layout.addWidget(add_btn)

    def _build_recipe_unlocks(self, layout: QVBoxLayout) -> None:
        """Unlock condition picker (delegated to UnlockPicker)."""
        self._unlock_picker = UnlockPicker(
            parent_layout=layout,
            unlock_requirements=self.unlock_requirements,
            recipe_fv=self._recipe_fv, fv_key_prefix="DefaultUnlocks")

    # ── Item selection / load ────────────────────────────────────

    def _on_item_selected(self, current, _previous) -> None:
        """Load the selected construction into all form fields."""
        if not current:
            return
        tag = current.text()
        dt_path = os.path.join(self.tobis_json_dir, "DT_Constructions", f"{tag}.json")
        if not os.path.isfile(dt_path):
            return
        with open(dt_path, "r", encoding="utf-8") as fh:
            row = json.load(fh).get("Row", {})
        self.tag_display.setText(row.get("Name", tag))
        # Infer pack name (e.g. "100BuildingsPack_Item_A" -> "100BuildingsPack")
        for i, part in enumerate(tag.split("_")):
            if "Pack" in part:
                self.pack_name.setText("_".join(tag.split("_")[: i + 1]))
                break
        self._load_name_desc(tag, row)
        const_vals = row.get("Value", [])
        self._load_asset(const_vals)
        self._load_const_tags(const_vals)
        self._load_enum_combo(const_vals, "EnabledState", self.const_enabled)
        # Recipe file — clear if missing so stale data doesn't persist
        rp = os.path.join(self.tobis_json_dir, "DT_ConstructionRecipes", f"{tag}.json")
        if os.path.isfile(rp):
            with open(rp, "r", encoding="utf-8") as fh:
                self._load_recipe_fields(json.load(fh).get("Row", {}).get("Value", []))
        else:
            self._material_picker.clear_all()
            self._material_picker.add_row()

    def _load_name_desc(self, tag: str, row: dict) -> None:
        """Set description path and description string from data.

        Description shows the string table path from the JSON.
        Description String shows the resolved text or "NOT FOUND".
        (Name is no longer shown — it's set in Unreal Engine.)
        """
        st = self._string_table.get(tag)
        # Description — string table path from the JSON row
        desc_path = ""
        for entry in row.get("Value", []):
            if entry.get("Name") == "Description" and isinstance(
                entry.get("Value"), str
            ):
                desc_path = entry["Value"]
                break
        self.desc_input.setText(desc_path)

        # Description String — resolved text or NOT FOUND
        desc_text = st.get("description", "") if st else ""
        if not desc_text:
            ap = os.path.join(self.tobis_json_dir, "Architecture", f"{tag}.json")
            if os.path.isfile(ap):
                with open(ap, "r", encoding="utf-8") as fh:
                    for entry in json.load(fh).get("Entries", []):
                        if entry[0].endswith(".Description"):
                            desc_text = entry[1]
                            break
        if desc_text:
            self.desc_string.setText(desc_text)
            self.desc_string.setStyleSheet("")
        else:
            self.desc_string.setText("STRING NOT FOUND IN STRING TABLE")
            self.desc_string.setStyleSheet("font-weight: bold; color: red;")

    def _load_asset(self, values: list) -> None:
        """Extract Actor asset path from DT_Constructions values."""
        for entry in values:
            if entry.get("Name") == "Actor":
                try:
                    asset = entry["Value"]["AssetPath"]["AssetName"]
                    if asset.endswith("_C"):
                        asset = asset.rsplit(".", maxsplit=1)[0]
                    self.asset_input.setText(asset)
                except (KeyError, TypeError):
                    pass
                return

    def _load_const_tags(self, values: list) -> None:
        """Load gameplay tags into the tags combo if present."""
        for entry in values:
            if entry.get("Name") == "Tags":
                try:
                    tags = entry["Value"][0]["Value"]
                    if tags and self.tags_combo is not None:
                        self.tags_combo.setCurrentText(tags[0])
                except (KeyError, IndexError, TypeError):
                    pass
                return

    @staticmethod
    def _load_enum_combo(values: list, name: str, combo: QComboBox) -> None:
        """Set a combo box from a JSON enum field (strips '::' prefix)."""
        for entry in values:
            if entry.get("Name") == name:
                val = entry.get("Value", "")
                short = val.rsplit("::", maxsplit=1)[-1] if "::" in val else val
                idx = combo.findText(short)
                if idx >= 0:
                    combo.setCurrentIndex(idx)
                return

    @staticmethod
    def _load_bool_check(values: list, name: str, checkbox: QCheckBox) -> None:
        """Set a checkbox from a JSON boolean field."""
        for entry in values:
            if entry.get("Name") == name:
                checkbox.setChecked(bool(entry.get("Value", False)))
                return

    def _load_recipe_fields(self, values: list) -> None:
        """Populate all recipe form fields from loaded JSON values."""
        for fname, combo in [("BuildProcess", self.build_process),
                             ("LocationRequirement", self.location_req),
                             ("PlacementType", self.placement_type),
                             ("FoundationRule", self.foundation_rule),
                             ("MonumentType", self.monument_type),
                             ("EnabledState", self.recipe_enabled)]:
            self._load_enum_combo(values, fname, combo)
        for fname, cb in [("bOnWall", self.cb_on_wall),
                          ("bOnFloor", self.cb_on_floor),
                          ("bPlaceOnWater", self.cb_place_water),
                          ("bOverrideRotation", self.cb_override_rot),
                          ("bAutoFoundation", self.cb_auto_foundation),
                          ("bInheritAutoFoundationStability", self.cb_inherit_stability),
                          ("bAllowRefunds", self.cb_allow_refunds)]:
            self._load_bool_check(values, fname, cb)
        self._material_picker.load_from_values(values)
        self._unlock_picker.load_from_values(values)

    # ── Tag validation ──────────────────────────────────────────

    def _sanitize_tag(self, text: str) -> None:
        """Auto-replace spaces with underscores in the Name Tag field."""
        if " " in text:
            pos = self.tag_display.cursorPosition()
            self.tag_display.setText(text.replace(" ", "_"))
            self.tag_display.setCursorPosition(pos)

    # ── Actions ──────────────────────────────────────────────────

    def _new_item(self) -> None:
        """Clear the form for a new construction entry."""
        self.item_list.clearSelection()
        self.item_list.setCurrentItem(None)
        self.pack_name.clear()
        self.tag_display.clear()
        self.desc_input.clear()
        self.desc_string.clear()
        self.desc_string.setStyleSheet("")
        self.asset_input.clear()
        if self.tags_combo:
            self.tags_combo.setCurrentIndex(0)
        self.const_enabled.setCurrentIndex(0)
        # Reset recipe enums to defaults
        for combo in (self.build_process, self.location_req,
                      self.placement_type, self.foundation_rule,
                      self.monument_type, self.recipe_enabled):
            if combo:
                combo.setCurrentIndex(0)
        # Reset checkboxes
        for cb in (self.cb_on_wall, self.cb_place_water, self.cb_override_rot,
                   self.cb_auto_foundation, self.cb_inherit_stability):
            if cb:
                cb.setChecked(False)
        if self.cb_on_floor:
            self.cb_on_floor.setChecked(True)
        if self.cb_allow_refunds:
            self.cb_allow_refunds.setChecked(True)
        # Reset materials and unlocks
        if self._material_picker:
            self._material_picker.clear_all()
            self._material_picker.add_row()

    def _delete_selected(self) -> None:
        """Delete the currently selected construction and its related files."""
        tag = delete_per_item(
            self, self.item_list, self.tobis_json_dir, _RELATED_TABLES)
        if tag:
            refresh_item_list(self.item_list, self.tobis_json_dir, "DT_Constructions")
            QMessageBox.information(self, "Deleted", f"'{tag}' removed.")

    def _collect_recipe_overrides(self) -> dict:
        """Gather all recipe field values from the form for saving."""
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

    def _rename_item(self, old_tag: str, new_tag: str) -> None:
        """Rename per-item JSON files from old_tag to new_tag."""
        for table in _RELATED_TABLES:
            old = os.path.join(self.tobis_json_dir, table, f"{old_tag}.json")
            new = os.path.join(self.tobis_json_dir, table, f"{new_tag}.json")
            if os.path.isfile(old):
                os.rename(old, new)

    def _save(self) -> None:
        """Collect data, write per-item JSON files.

        The Name Tag drives everything: DisplayName/Description string table
        keys are auto-generated from it. The in-game display text is handled
        in Unreal Engine, not here. The gameplay Tags combo provides the
        category tag; recipe overrides from the form cover all placement
        flags so no category lookup is needed.
        """
        pack_name = self.pack_name.text().strip()
        asset = self.asset_input.text().strip()
        custom_tag = self.tag_display.text().strip()
        if not custom_tag or not asset:
            QMessageBox.warning(
                self, "Empty Fields", "Name Tag and Asset Path are required.")
            return

        materials = self._material_picker.collect()
        # Gameplay tag is the category (e.g. UI.Construction.Category.Deco.Jars)
        cat_tag = self.tags_combo.currentText() if self.tags_combo else ""

        # Determine tag (handle renames)
        selected = self.item_list.currentItem()
        old_tag = selected.text() if selected else None
        if old_tag and custom_tag != old_tag:
            self._rename_item(old_tag, custom_tag)
        unique = custom_tag
        self.tag_display.setText(unique)

        # Architecture entry — empty display text; resolved by Unreal string table
        arch_dir = os.path.join(self.tobis_json_dir, "Architecture")
        os.makedirs(arch_dir, exist_ok=True)
        arch_path = os.path.join(arch_dir, f"{unique}.json")
        with open(arch_path, "w", encoding="utf-8") as fh:
            json.dump({"Entries": [[f"{unique}.Name", ""],
                                   [f"{unique}.Description", ""]]}, fh, indent=2)

        dt_constructions_handle(
            unique, asset, cat_tag,
            self.tobis_json_dir, self.templates_dir, pack_name)
        # Pass empty cat_key — recipe overrides cover all placement flags
        dt_construction_recipes_handle(
            unique, self.tobis_json_dir, self.templates_dir, "",
            materials, self._unlock_picker.unlock_type,
            self._unlock_picker.selected_tag,
            recipe_overrides=self._collect_recipe_overrides())

        refresh_item_list(self.item_list, self.tobis_json_dir, "DT_Constructions")
        QMessageBox.information(self, "Saved", f"Construction '{unique}' saved.")
