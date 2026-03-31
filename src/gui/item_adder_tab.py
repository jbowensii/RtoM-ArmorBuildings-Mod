"""Generic item-adder tab for any item table with optional recipe editing.

Provides New/Save/Delete workflow: New creates an empty template on the
right pane, Save writes the per-item JSON using the Name Tag as filename.
"""
from __future__ import annotations

import copy
import json
import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QCompleter, QFormLayout, QGroupBox,
    QLabel, QLineEdit, QMessageBox, QPushButton, QScrollArea,
    QSpinBox, QSplitter, QVBoxLayout, QWidget,
)

from src.gui.field_helpers import (
    enum_short_values, load_field_values, load_item_display_names,
    load_string_table, make_combo,
)
from src.gui.material_picker import MaterialPicker
from src.gui.shared import (
    build_combined, create_item_list_pane, delete_per_item, refresh_item_list,
)
from src.gui.tab_configs import TabConfig
from src.gui.unlock_picker import UnlockPicker


# Property type short names that UAssetAPI requires in the NameMap
_PROP_TYPE_NAMES = frozenset({
    "ArrayProperty", "BoolProperty", "ByteProperty", "EnumProperty",
    "FloatProperty", "IntProperty", "MapProperty", "NameProperty",
    "ObjectProperty", "SoftObjectProperty", "StructProperty",
    "TextProperty",
})


def _collect_namemap_strings(obj, names: dict) -> None:
    """Recursively walk a JSON structure and collect NameMap strings."""
    if isinstance(obj, dict):
        _collect_from_dict(obj, names)
    elif isinstance(obj, list):
        for item in obj:
            if isinstance(item, str) and item:
                names[item] = None
            else:
                _collect_namemap_strings(item, names)


def _collect_from_dict(obj: dict, names: dict) -> None:
    """Collect NameMap-relevant strings from a single JSON dict."""
    # Extract property type short name from $type
    dtype = obj.get("$type", "")
    if dtype:
        short = dtype.split(".")[-1].split(",")[0]
        if short.endswith("Data"):
            short = short[:-4]
        if short in _PROP_TYPE_NAMES:
            names[short] = None

    # Collect string-valued metadata fields
    for key in ("Name", "StructType", "EnumType", "InnerType",
                "ArrayType", "ClassName", "ClassPackage", "TableId"):
        val = obj.get(key)
        if isinstance(val, str) and val:
            names[val] = None

    # Collect Value (string, list, or dict)
    val = obj.get("Value")
    if isinstance(val, str) and val:
        names[val] = None
    elif isinstance(val, (list, dict)):
        _collect_namemap_strings(val, names)

    # Collect asset paths
    asset_path = obj.get("AssetPath", {})
    if isinstance(asset_path, dict):
        asset = asset_path.get("AssetName", "")
        if asset:
            names[asset] = None

    # Collect ObjectName
    obj_name = obj.get("ObjectName")
    if isinstance(obj_name, str) and obj_name:
        names[obj_name] = None

    # Recurse into remaining sub-structures
    for key, child in obj.items():
        if key in ("Value", "AssetPath", "ObjectName", "$type"):
            continue
        if isinstance(child, (list, dict)):
            _collect_namemap_strings(child, names)


class ItemAdderTab(QWidget):
    """Generic tab for viewing/editing any item table plus optional recipe.

    Driven by a TabConfig that specifies which fields to display, which
    recipe table to pair with, and whether materials/unlocks are shown.
    """

    def __init__(
        self, cfg: TabConfig,
        tobis_json_dir: str, templates_dir: str,
        game_extract_dir: str, tobis_mod_dir: str,
        data_dir: str | None = None,
        items_index: dict | None = None,
        unlock_requirements: dict | None = None,
    ) -> None:
        super().__init__()
        self.cfg = cfg
        self.tobis_json_dir = tobis_json_dir
        self.templates_dir = templates_dir
        self.game_extract_dir = game_extract_dir
        self.tobis_mod_dir = tobis_mod_dir
        self.data_dir = data_dir
        self.items_index = items_index or {}
        self.unlock_requirements = unlock_requirements or {}
        # Widget maps populated during UI build
        self._item_widgets: dict[str, QWidget] = {}
        self._recipe_widgets: dict[str, QWidget] = {}
        # Pre-init all widget attrs to None (fixes W0201)
        self.build_btn: QPushButton | None = None
        self.item_list = None
        self.new_btn: QPushButton | None = None
        self.delete_btn: QPushButton | None = None
        self.pack_name: QLineEdit | None = None
        self.name_input: QLineEdit | None = None
        self.tag_display: QLineEdit | None = None
        self.desc_input: QLineEdit | None = None
        self.mat_layout: QVBoxLayout | None = None
        self._material_picker: MaterialPicker | None = None
        self._unlock_picker: UnlockPicker | None = None
        self._master_combo: QComboBox | None = None
        self._master_rules: dict | None = None
        self._master_driven_fields: set[str] = set()
        self._weapon_type_tag: str = ""
        # Field-value indexes for autocomplete
        self._item_fv = load_field_values(cfg.item_table)
        self._recipe_fv = (
            load_field_values(cfg.recipe_table) if cfg.recipe_table else {}
        )
        self._string_table = load_string_table()
        self._display_names = load_item_display_names()
        # Load templates for saving new items
        self._item_template = self._load_template(cfg.item_table)
        self._recipe_template = (
            self._load_template("DT_ItemRecipes")
            if cfg.recipe_table else None
        )
        self._setup_ui()

    # ── Template loading ─────────────────────────────────────────

    def _load_template(self, table: str) -> dict:
        """Load a row template for creating new per-item files."""
        # Try generated templates first, then MoreArmor
        for subdir in ("generated", "MoreArmor"):
            path = os.path.join(
                self.templates_dir, subdir, f"{table}_template.json",
            )
            if os.path.isfile(path):
                with open(path, "r", encoding="utf-8") as fh:
                    return json.load(fh)
        return {}

    # ── UI Setup ─────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        outer = QVBoxLayout()
        left_widget, self.build_btn, self.item_list, self.new_btn, \
            self.delete_btn = \
            create_item_list_pane(f"Saved {self.cfg.item_table} items:")
        self.build_btn.clicked.connect(
            lambda: build_combined(
                self, self.tobis_json_dir, self.game_extract_dir,
                self.tobis_mod_dir, self.data_dir))
        self.item_list.currentItemChanged.connect(self._on_item_selected)
        self.new_btn.clicked.connect(self._new_item)
        self.delete_btn.clicked.connect(self._delete_selected)

        right = QVBoxLayout()
        self._build_basic_info(right)
        self._build_item_fields(right)
        if self.cfg.recipe_table:
            self._build_recipe_fields(right)

        # Save button at the bottom of the right pane
        save_btn = QPushButton("Save")
        save_btn.setStyleSheet("font-weight: bold; padding: 8px;")
        save_btn.clicked.connect(self._save)
        right.addWidget(save_btn)

        right.addStretch()
        right_w = QWidget()
        right_w.setLayout(right)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(right_w)
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_widget)
        splitter.addWidget(scroll)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        outer.addWidget(splitter)
        self.setLayout(outer)
        refresh_item_list(
            self.item_list, self.tobis_json_dir, self.cfg.item_table)

    def _build_basic_info(self, parent: QVBoxLayout) -> None:
        """Pack name (editable) + editable name / tag / description."""
        group = QGroupBox("Basic Info")
        form = QFormLayout()
        # Pack name with unified autocomplete
        pack_vals = self._item_fv.get("PackNames", {}).get("values", [])
        self.pack_name = QLineEdit()
        self.pack_name.setPlaceholderText("Pack name (e.g., Tobi)")
        if pack_vals:
            self.pack_name.setCompleter(QCompleter(sorted(pack_vals)))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Display name")
        self.tag_display = QLineEdit()
        self.tag_display.setPlaceholderText("No spaces, e.g. Mereak_Battleaxe")
        self.tag_display.textChanged.connect(self._sanitize_tag)
        self.desc_input = QLineEdit()
        self.desc_input.setPlaceholderText("Description")
        for label, widget in [("Pack Name", self.pack_name),
                              ("Name", self.name_input),
                              ("Name Tag", self.tag_display),
                              ("Description", self.desc_input)]:
            form.addRow(label, widget)
        group.setLayout(form)
        parent.addWidget(group)

    def _build_item_fields(self, parent: QVBoxLayout) -> None:
        """Editable widgets for each configured item field.

        If the config has a master_selector, a combo is placed at the top
        that auto-fills the linked fields and makes them read-only.
        """
        if not self.cfg.item_fields:
            return
        group = QGroupBox(self.cfg.item_struct_label)
        layout = QVBoxLayout()

        # Master selector (e.g. Weapon Type → auto-fills DamageType, Tags)
        if self.cfg.master_selector:
            self._build_master_selector(layout)

        form = QFormLayout()
        for name, wtype in self.cfg.item_fields:
            w = self._create_field_widget(name, wtype, self._item_fv)
            # Disable fields driven by the master selector
            if name in self._master_driven_fields:
                w.setEnabled(False)
            self._item_widgets[name] = w
            form.addRow(name, w)
        layout.addLayout(form)
        group.setLayout(layout)
        parent.addWidget(group)

    def _build_master_selector(self, layout: QVBoxLayout) -> None:
        """Build a master combo that auto-fills multiple linked fields."""
        for label, choices in self.cfg.master_selector.items():
            # Collect which fields this selector drives
            for fields in choices.values():
                self._master_driven_fields.update(fields.keys())
            self._master_rules = choices

            form = QFormLayout()
            self._master_combo = QComboBox()
            self._master_combo.addItems(["(select)"] + list(choices.keys()))
            self._master_combo.currentTextChanged.connect(
                self._on_master_changed)
            form.addRow(label, self._master_combo)
            layout.addLayout(form)

    def _on_master_changed(self, selection: str) -> None:
        """Auto-fill linked fields when the master selector changes."""
        if not self._master_rules or selection == "(select)":
            return
        fields = self._master_rules.get(selection, {})
        for field_name, value in fields.items():
            # WeaponTypeTag is stored but not a visible widget
            if field_name == "WeaponTypeTag":
                self._weapon_type_tag = value
                continue
            widget = self._item_widgets.get(field_name)
            if widget is None:
                continue
            if isinstance(widget, QComboBox):
                idx = widget.findText(value)
                if idx >= 0:
                    widget.setCurrentIndex(idx)
                else:
                    widget.setCurrentText(value)
            elif isinstance(widget, QLineEdit):
                widget.setText(value)

    def _reverse_lookup_master(self, values: list) -> None:
        """Set the master combo by matching existing item data to rules."""
        if not self._master_rules or not self._master_combo:
            return
        # Try to match DamageType.TagName to a weapon type
        damage_type = ""
        for entry in values:
            if entry.get("Name") == "DamageType":
                try:
                    damage_type = entry["Value"][0]["Value"]
                except (KeyError, IndexError, TypeError):
                    pass
                break
        if not damage_type:
            return
        for weapon_type, fields in self._master_rules.items():
            if fields.get("DamageType.TagName") == damage_type:
                self._master_combo.setCurrentText(weapon_type)
                self._weapon_type_tag = fields.get("WeaponTypeTag", "")
                return

    def _build_recipe_fields(self, parent: QVBoxLayout) -> None:
        """Recipe fields, materials (MaterialPicker), unlocks (UnlockPicker)."""
        group = QGroupBox(self.cfg.recipe_struct_label or self.cfg.recipe_table)
        layout = QVBoxLayout()
        if self.cfg.recipe_fields:
            form = QFormLayout()
            for name, wtype in self.cfg.recipe_fields:
                w = self._create_field_widget(name, wtype, self._recipe_fv)
                self._recipe_widgets[name] = w
                form.addRow(name, w)
            layout.addLayout(form)
        if self.cfg.recipe_has_materials:
            layout.addWidget(QLabel("Required Materials (max 6):"))
            self.mat_layout = QVBoxLayout()
            layout.addLayout(self.mat_layout)
            mat_ac = self._recipe_fv.get(
                "DefaultRequiredMaterials.MaterialHandle.RowName", {},
            ).get("values", [])
            self._material_picker = MaterialPicker(
                self, self.mat_layout, self.items_index, mat_ac)
            self._material_picker.add_row()
            add_btn = QPushButton("Add Material")
            add_btn.clicked.connect(self._material_picker.add_row)
            layout.addWidget(add_btn)
        if self.cfg.recipe_has_unlocks:
            unlock_box = QVBoxLayout()
            self._unlock_picker = UnlockPicker(
                unlock_box, self.unlock_requirements, self._recipe_fv)
            layout.addLayout(unlock_box)
        group.setLayout(layout)
        parent.addWidget(group)

    def _create_field_widget(self, field_name: str, widget_type: str,
                             fv_index: dict) -> QWidget:
        """Return a widget for *widget_type* with autocomplete values."""
        fv = fv_index.get(field_name, {})
        vals = fv.get("values", [])
        if widget_type == "enum":
            return make_combo(enum_short_values(fv) or vals, editable=False)
        if widget_type == "bool":
            return QCheckBox()
        if widget_type == "int":
            sb = QSpinBox()
            sb.setRange(-99999, 99999)
            if vals:
                try:
                    sb.setValue(int(vals[0]))
                except (ValueError, IndexError):
                    pass
            return sb
        if widget_type == "tags":
            return make_combo(sorted(vals), editable=True)
        # float / asset / text — QLineEdit with optional completer
        le = QLineEdit()
        if widget_type == "float":
            le.setPlaceholderText("0.0")
        if vals:
            le.setCompleter(QCompleter(sorted(vals)))
        return le

    # ── NameMap builder ───────────────────────────────────────

    @staticmethod
    def _build_namemap(row: dict) -> list[str]:
        """Walk a row and collect every string that should be in NameMap.

        UAssetAPI requires all referenced strings (field names, enum values,
        struct types, tag strings, asset paths, property type names, etc.)
        to be present in the NameMap for the asset to be valid.
        """
        names: dict[str, None] = {}  # ordered set (preserves insertion order)
        _collect_namemap_strings(row, names)

        # Always include standard UAsset entries
        for std in ("None", "Object", "Package", "StringTable",
                    "GameplayTag", "GameplayTagContainer"):
            names[std] = None

        # Filter out UAssetAPI internal strings and GUIDs
        return [n for n in names
                if not n.startswith("UAssetAPI.")
                and not n.startswith("{00000000")
                and n != "NoExtension"]

    # ── Tag validation ─────────────────────────────────────────

    def _sanitize_tag(self, text: str) -> None:
        """Auto-replace spaces with underscores in the Name Tag field."""
        if " " in text:
            cursor_pos = self.tag_display.cursorPosition()
            cleaned = text.replace(" ", "_")
            self.tag_display.setText(cleaned)
            self.tag_display.setCursorPosition(cursor_pos)

    # ── New item ─────────────────────────────────────────────────

    def _new_item(self) -> None:
        """Clear the form for a new item entry."""
        # Deselect list so we're in "new" mode
        self.item_list.clearSelection()
        self.item_list.setCurrentItem(None)
        # Clear basic info
        self.pack_name.clear()
        self.name_input.clear()
        self.tag_display.clear()
        self.desc_input.clear()
        # Reset master selector (e.g. Weapon Type)
        if self._master_combo:
            self._master_combo.setCurrentIndex(0)
        self._weapon_type_tag = ""
        # Reset item field widgets to defaults
        for widget in self._item_widgets.values():
            if isinstance(widget, QCheckBox):
                widget.setChecked(False)
            elif isinstance(widget, QSpinBox):
                widget.setValue(0)
            elif isinstance(widget, QComboBox):
                widget.setCurrentIndex(0)
            elif isinstance(widget, QLineEdit):
                widget.clear()
        # Reset recipe widgets
        self._clear_recipe_fields()

    # ── Save item ────────────────────────────────────────────────

    def _save(self) -> None:
        """Save the current form as a per-item JSON file.

        Uses the Name Tag as the filename. Creates both the item file
        and (if applicable) the recipe file.
        """
        tag = self.tag_display.text().strip()
        if not tag:
            QMessageBox.warning(self, "Missing Tag",
                                "Enter a Name Tag before saving.")
            return

        # Save item per-item file
        self._save_item_file(tag)

        # Save recipe per-item file (if this tab has recipes)
        if self.cfg.recipe_table and self._recipe_template:
            self._save_recipe_file(tag)

        refresh_item_list(
            self.item_list, self.tobis_json_dir, self.cfg.item_table)
        QMessageBox.information(self, "Saved", f"'{tag}' saved.")

    def _save_item_file(self, tag: str) -> None:
        """Write the item per-item JSON from template + form values."""
        if not self._item_template:
            QMessageBox.warning(self, "No Template",
                                f"No template found for {self.cfg.item_table}.")
            return

        row = copy.deepcopy(self._item_template)
        row["Name"] = tag

        # Apply widget values to the template row
        self._apply_widgets_to_row(row, self._item_widgets)

        # Inject weapon type tag into the Tags array (alongside UI tag)
        if self._weapon_type_tag:
            self._inject_extra_tag(row, "Tags", self._weapon_type_tag)

        namemap = self._build_namemap(row)
        # Ensure tag is in the NameMap
        if tag not in namemap:
            namemap.append(tag)

        item_data = {
            "NameMap": namemap,
            "Imports": [],
            "Row": row,
        }

        out_dir = os.path.join(self.tobis_json_dir, self.cfg.item_table)
        os.makedirs(out_dir, exist_ok=True)
        path = os.path.join(out_dir, f"{tag}.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(item_data, fh, indent=4, ensure_ascii=False)

    def _save_recipe_file(self, tag: str) -> None:
        """Write the recipe per-item JSON from template + form values."""
        row = copy.deepcopy(self._recipe_template)
        row["Name"] = tag

        # Apply recipe widget values
        self._apply_widgets_to_row(row, self._recipe_widgets)

        # Apply materials from picker
        if self.cfg.recipe_has_materials and self._material_picker:
            materials = self._material_picker.collect()
            self._apply_materials_to_row(row, materials)

        namemap = self._build_namemap(row)
        if tag not in namemap:
            namemap.append(tag)

        item_data = {
            "NameMap": namemap,
            "Imports": [],
            "Row": row,
        }

        out_dir = os.path.join(self.tobis_json_dir, self.cfg.recipe_table)
        os.makedirs(out_dir, exist_ok=True)
        path = os.path.join(out_dir, f"{tag}.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(item_data, fh, indent=4, ensure_ascii=False)

    def _apply_widgets_to_row(self, row: dict,
                              widgets: dict[str, QWidget]) -> None:
        """Write widget values back into a template row's Value array.

        Supports dotted field names (e.g. "DamageType.TagName") by walking
        into nested struct Value arrays.
        """
        for entry in row.get("Value", []):
            name = entry.get("Name")
            # Direct match
            if name in widgets:
                self._apply_widget_to_entry(entry, widgets[name])
                continue
            # Dotted match — find child entry inside struct
            for wname, widget in widgets.items():
                if not wname.startswith(f"{name}."):
                    continue
                child_name = wname.split(".", maxsplit=1)[1]
                for sub in entry.get("Value", []):
                    if isinstance(sub, dict) and sub.get("Name") == child_name:
                        self._apply_widget_to_entry(sub, widget)
                        break

    def _apply_widget_to_entry(  # pylint: disable=too-many-branches
        self, entry: dict, widget: QWidget,
    ) -> None:
        """Write a single widget's value into a JSON property entry."""
        dtype = entry.get("$type", "")
        if isinstance(widget, QCheckBox):
            entry["Value"] = widget.isChecked()
        elif isinstance(widget, QSpinBox):
            entry["Value"] = widget.value()
        elif isinstance(widget, QComboBox):
            text = widget.currentText()
            if "EnumProperty" in dtype:
                enum_type = entry.get("EnumType", "")
                if enum_type and "::" not in text:
                    text = f"{enum_type}::{text}"
                entry["Value"] = text
            else:
                entry["Value"] = text
        elif isinstance(widget, QLineEdit):
            text = widget.text().strip()
            if isinstance(entry.get("Value"), dict):
                try:
                    entry["Value"]["AssetPath"]["AssetName"] = text
                except (KeyError, TypeError):
                    entry["Value"] = text
            elif "FloatProperty" in dtype:
                try:
                    entry["Value"] = float(text) if text else 0.0
                except ValueError:
                    entry["Value"] = text
            else:
                entry["Value"] = text

    @staticmethod
    def _inject_extra_tag(row: dict, field_name: str, tag: str) -> None:
        """Append an extra gameplay tag to a Tags-type field's value array.

        Used to inject WeaponTypeTag alongside the UI tag set by the combo.
        """
        for entry in row.get("Value", []):
            if entry.get("Name") != field_name:
                continue
            try:
                tag_list = entry["Value"][0]["Value"]
                if isinstance(tag_list, list) and tag not in tag_list:
                    tag_list.append(tag)
            except (KeyError, IndexError, TypeError):
                pass
            return

    @staticmethod
    def _apply_materials_to_row(row: dict,
                                materials: list[tuple[str, int]]) -> None:
        """Write material list into the DefaultRequiredMaterials field."""
        for entry in row.get("Value", []):
            if entry.get("Name") != "DefaultRequiredMaterials":
                continue
            # Build material array from the template's DummyStruct
            dummy = entry.get("DummyStruct")
            mat_array = []
            for mat_tag, count in materials:
                if not mat_tag:
                    continue
                mat_entry = copy.deepcopy(dummy) if dummy else {
                    "Value": [
                        {"Name": "MaterialHandle", "Value": [
                            {"Name": "RowName", "Value": ""}
                        ]},
                        {"Name": "WildcardHandle", "Value": [
                            {"Name": "RowName", "Value": "None"}
                        ]},
                        {"Name": "Count", "Value": 0},
                    ]
                }
                # Set material tag and count
                for field in mat_entry.get("Value", []):
                    if field.get("Name") == "MaterialHandle":
                        try:
                            field["Value"][0]["Value"] = mat_tag
                        except (KeyError, IndexError, TypeError):
                            pass
                    elif field.get("Name") == "Count":
                        field["Value"] = count
                mat_array.append(mat_entry)
            entry["Value"] = mat_array
            return

    # ── Item selection ───────────────────────────────────────────

    def _on_item_selected(self, current, _previous) -> None:
        """Load item (and recipe) when the user clicks a list entry."""
        if not current:
            return
        tag = current.text()
        dt_path = os.path.join(
            self.tobis_json_dir, self.cfg.item_table, f"{tag}.json")
        if not os.path.isfile(dt_path):
            return
        with open(dt_path, "r", encoding="utf-8") as fh:
            row = json.load(fh).get("Row", {})
        self.tag_display.setText(row.get("Name", tag))
        # Extract pack name from tag
        parts = tag.split("_")
        for i, part in enumerate(parts):
            if "Pack" in part:
                self.pack_name.setText("_".join(parts[:i + 1]))
                break
        # Name & description from string table or display names
        st = self._string_table.get(tag)
        if st:
            self.name_input.setText(st.get("name", ""))
            self.desc_input.setText(st.get("description", ""))
        elif tag in self._display_names:
            self.name_input.setText(self._display_names[tag])
            self.desc_input.clear()
        else:
            for entry in row.get("Value", []):
                n, v = entry.get("Name", ""), entry.get("Value", "")
                if n == "DisplayName" and isinstance(v, str):
                    self.name_input.setText(v)
                elif n == "Description" and isinstance(v, str):
                    self.desc_input.setText(v)
        item_values = row.get("Value", [])
        self._load_fields_into_widgets(item_values, self._item_widgets)
        # Reverse-lookup master selector (e.g. Weapon Type from DamageType)
        if self.cfg.master_selector:
            self._reverse_lookup_master(item_values)
        if self.cfg.recipe_table:
            self._load_recipe(tag)

    def _load_recipe(self, tag: str) -> None:
        """Load recipe JSON and populate recipe widgets / materials / unlocks."""
        path = os.path.join(
            self.tobis_json_dir, self.cfg.recipe_table, f"{tag}.json")
        if not os.path.isfile(path):
            self._clear_recipe_fields()
            return
        with open(path, "r", encoding="utf-8") as fh:
            vals = json.load(fh).get("Row", {}).get("Value", [])
        self._load_fields_into_widgets(vals, self._recipe_widgets)
        if self.cfg.recipe_has_materials and self._material_picker:
            self._material_picker.load_from_values(vals)
        if self.cfg.recipe_has_unlocks and self._unlock_picker:
            self._unlock_picker.load_from_values(vals)

    def _clear_recipe_fields(self) -> None:
        """Reset all recipe widgets to defaults."""
        for widget in self._recipe_widgets.values():
            if isinstance(widget, QCheckBox):
                widget.setChecked(False)
            elif isinstance(widget, QSpinBox):
                widget.setValue(0)
            elif isinstance(widget, QComboBox):
                widget.setCurrentIndex(0)
            elif isinstance(widget, QLineEdit):
                widget.clear()
        if self.cfg.recipe_has_materials and self._material_picker:
            self._material_picker.clear_all()
            self._material_picker.add_row()

    def _load_fields_into_widgets(self, values: list,
                                  widgets: dict[str, QWidget]) -> None:
        """Set each widget's value from its corresponding JSON entry.

        Supports dotted field names (e.g. "DamageType.TagName") for nested
        struct fields — walks into the struct's Value array to find the child.
        """
        for entry in values:
            fname = entry.get("Name")
            # Direct match
            if fname in widgets:
                self._set_widget(widgets[fname], entry)
                continue
            # Dotted match — e.g. "DamageType" entry with widget "DamageType.TagName"
            for wname, widget in widgets.items():
                if not wname.startswith(f"{fname}."):
                    continue
                child_name = wname.split(".", maxsplit=1)[1]
                for sub in entry.get("Value", []):
                    if isinstance(sub, dict) and sub.get("Name") == child_name:
                        self._set_widget(widget, sub)
                        break

    def _set_widget(self, widget: QWidget, entry: dict) -> None:
        """Set a single widget's value from a JSON property entry."""
        val = entry.get("Value")
        if isinstance(widget, QCheckBox):
            widget.setChecked(bool(val))
        elif isinstance(widget, QSpinBox):
            try:
                widget.setValue(int(val))
            except (ValueError, TypeError):
                pass
        elif isinstance(widget, QComboBox):
            self._set_combo(widget, val, entry.get("$type", ""))
        elif isinstance(widget, QLineEdit):
            self._set_lineedit(widget, val)

    @staticmethod
    def _set_combo(widget: QComboBox, val, dtype: str) -> None:
        """Set combo from JSON value (enum, tag-array, or plain text)."""
        if "EnumProperty" in dtype:
            short = str(val).rsplit("::", maxsplit=1)[-1]
            idx = widget.findText(short)
            if idx >= 0:
                widget.setCurrentIndex(idx)
            else:
                widget.setCurrentText(short)
        elif isinstance(val, list):
            try:
                tags = val[0].get("Value", []) if val else []
                if tags:
                    widget.setCurrentText(tags[0])
            except (KeyError, IndexError, TypeError, AttributeError):
                pass
        else:
            widget.setCurrentText(str(val) if val else "")

    @staticmethod
    def _set_lineedit(widget: QLineEdit, val) -> None:
        """Set line-edit from JSON value (asset dict or scalar)."""
        if isinstance(val, dict):
            try:
                widget.setText(val["AssetPath"]["AssetName"])
            except (KeyError, TypeError):
                widget.setText(str(val))
        else:
            widget.setText(str(val) if val is not None else "")

    def _delete_selected(self) -> None:
        """Delete the selected item (and its recipe) from disk."""
        tables = [self.cfg.item_table]
        if self.cfg.recipe_table:
            tables.append(self.cfg.recipe_table)
        tag = delete_per_item(
            self, self.item_list, self.tobis_json_dir, tables)
        if tag:
            refresh_item_list(
                self.item_list, self.tobis_json_dir, self.cfg.item_table)
            QMessageBox.information(self, "Deleted", f"'{tag}' removed.")
