"""Generic item-adder tab for any item table with optional recipe editing.

Provides New/Save/Delete workflow: New creates an empty template on the
right pane, Save writes the per-item JSON using the Name Tag as filename.
"""
# pylint: disable=too-many-lines
from __future__ import annotations

import copy
import json
import os
import re

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QCompleter, QFormLayout, QGridLayout, QGroupBox,
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


def _collect_from_dict(  # pylint: disable=too-many-branches
    obj: dict, names: dict,
) -> None:
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


def humanize_station_label(row_name: str, display_names: dict) -> str:
    """Return a friendly UI label for a CraftingStations RowName.

    Uses the field-values display_names map when present, otherwise strips
    the CraftingStation_ prefix and inserts spaces before capital letters.
    Also normalises the typo'd "Legenday" → "Legendary" used by some rows.
    """
    if row_name in display_names:
        return display_names[row_name]
    bare = row_name.replace("CraftingStation_", "").replace("Legenday", "Legendary")
    return re.sub(r"(?<!^)(?=[A-Z])", " ", bare)


def make_station_struct(row_name: str) -> dict:
    """Build a single MorConstructionRowHandle entry for CraftingStations."""
    return {
        "$type": "UAssetAPI.PropertyTypes.Structs.StructPropertyData, UAssetAPI",
        "StructType": "MorConstructionRowHandle",
        "SerializeNone": True,
        "StructGUID": "{00000000-0000-0000-0000-000000000000}",
        "SerializationControl": "NoExtension",
        "Operation": "None",
        "Name": "CraftingStations",
        "ArrayIndex": 0,
        "IsZero": False,
        "PropertyTagFlags": "None",
        "PropertyTagExtensions": "NoExtension",
        "Value": [
            {
                "$type": "UAssetAPI.PropertyTypes.Objects.NamePropertyData, UAssetAPI",
                "Name": "RowName",
                "ArrayIndex": 0,
                "IsZero": False,
                "PropertyTagFlags": "None",
                "PropertyTagExtensions": "NoExtension",
                "Value": row_name,
            }
        ],
    }


def extract_station_row_names(row_value_array: list) -> list[str]:
    """Pull the list of crafting-station RowNames from a recipe row's Value."""
    for entry in row_value_array:
        if entry.get("Name") != "CraftingStations":
            continue
        names = []
        for sub in entry.get("Value", []) or []:
            if not isinstance(sub, dict):
                continue
            for field in sub.get("Value", []) or []:
                if isinstance(field, dict) and field.get("Name") == "RowName":
                    val = field.get("Value")
                    if isinstance(val, str) and val:
                        names.append(val)
                    break
        return names
    return []


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
        self.desc_string: QLineEdit | None = None
        self.mat_layout: QVBoxLayout | None = None
        self._material_picker: MaterialPicker | None = None
        self._unlock_picker: UnlockPicker | None = None
        self._station_checkboxes: dict[str, QCheckBox] = {}
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
        """Build the Basic Info group: Pack Name, Name, Name Tag, Description."""
        group = QGroupBox("Basic Info")
        form = QFormLayout()

        # Pack name — editable with autocomplete
        pack_vals = self._item_fv.get("PackNames", {}).get("values", [])
        self.pack_name = QLineEdit()
        self.pack_name.setPlaceholderText("Pack name (e.g., Tobi)")
        if pack_vals:
            self.pack_name.setCompleter(QCompleter(sorted(pack_vals)))

        # Name — read-only, shows "display name (game name)" or just game name
        self.name_input = QLineEdit()
        self.name_input.setReadOnly(True)

        # Name Tag — the game row name, used as the JSON filename
        self.tag_display = QLineEdit()
        self.tag_display.setPlaceholderText("No spaces, e.g. Mereak_Battleaxe")
        self.tag_display.textChanged.connect(self._sanitize_tag)

        # Description — editable, string table path (e.g. Weapons.Battleaxe.Mereak.Description)
        self.desc_input = QLineEdit()
        self.desc_input.setPlaceholderText("String table path, e.g. Tag.Description")

        # Description String — read-only, shows resolved text or "NOT FOUND"
        self.desc_string = QLineEdit()
        self.desc_string.setReadOnly(True)

        for label, widget in [
            ("Pack Name", self.pack_name),
            ("Name", self.name_input),
            ("Name Tag", self.tag_display),
            ("Description", self.desc_input),
            ("Description String", self.desc_string),
        ]:
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
        self._build_crafting_stations_group(layout)
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

    def _build_crafting_stations_group(self, parent: QVBoxLayout) -> None:
        """Build a 2-column QGroupBox of QCheckBoxes for CraftingStations.

        Auto-populated from data/field_values/DT_ItemRecipes_fields.json so
        every station the game ships (forges, furnaces, hearths, kitchens,
        breweries, loom, mill, etc.) is selectable without manual mapping.
        """
        fv = self._recipe_fv.get("CraftingStations.RowName", {})
        row_names = list(fv.get("values", []))
        if not row_names:
            return
        display_names = fv.get("display_names", {})
        # Sort by user-facing label so the grid reads alphabetically
        labelled = sorted(
            ((humanize_station_label(rn, display_names), rn) for rn in row_names),
            key=lambda pair: pair[0].lower(),
        )
        group = QGroupBox("Crafting Stations")
        grid = QGridLayout()
        cols = 2
        for idx, (label, row_name) in enumerate(labelled):
            cb = QCheckBox(label)
            self._station_checkboxes[row_name] = cb
            grid.addWidget(cb, idx // cols, idx % cols)
        group.setLayout(grid)
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
        """Clear the form and populate with template defaults.

        Instead of blanking all fields, loads the template's default values
        into the widgets so that sane defaults (Item.Scrap, None, -6, etc.)
        are preserved when saving.
        """
        # Deselect list so we're in "new" mode
        self.item_list.clearSelection()
        self.item_list.setCurrentItem(None)
        # Clear basic info
        self.pack_name.clear()
        self.name_input.clear()
        self.tag_display.clear()
        self.desc_input.clear()
        self.desc_string.clear()
        self.desc_string.setStyleSheet("")
        # Reset master selector (e.g. Weapon Type)
        if self._master_combo:
            self._master_combo.setCurrentIndex(0)
        self._weapon_type_tag = ""
        # Load template defaults into item field widgets
        if self._item_template:
            self._load_fields_into_widgets(
                self._item_template.get("Value", []), self._item_widgets)
        # Load template defaults into recipe field widgets
        if self._recipe_template:
            template_values = self._recipe_template.get("Value", [])
            self._load_fields_into_widgets(template_values, self._recipe_widgets)
            self._apply_stations_from_values(template_values)
            if self.cfg.recipe_has_materials and self._material_picker:
                self._material_picker.load_from_values(template_values)
        else:
            self._clear_recipe_fields()

    # Tables that require a Broken_ duplicate when saving
    _BROKEN_VARIANT_TABLES = frozenset({"DT_Weapons", "DT_Tools"})

    # ── Save item ────────────────────────────────────────────────

    def _save(self) -> None:
        """Save the current form as a per-item JSON file.

        Uses the Name Tag as the filename. Creates both the item file
        and (if applicable) the recipe file. For DT_Weapons and DT_Tools,
        also creates a Broken_ variant with the same fields.
        """
        tag = self.tag_display.text().strip()
        if not tag:
            QMessageBox.warning(self, "Missing Tag",
                                "Enter a Name Tag before saving.")
            return

        # Save item per-item file
        self._save_item_file(tag)

        # Auto-create Broken_ variant for weapons and tools
        if self.cfg.item_table in self._BROKEN_VARIANT_TABLES:
            broken_tag = f"Broken_{tag}" if not tag.startswith("Broken_") else tag
            if broken_tag != tag:
                self._save_broken_variant(tag, broken_tag)

        # Save recipe per-item file (if this tab has recipes)
        if self.cfg.recipe_table and self._recipe_template:
            self._save_recipe_file(tag)

        refresh_item_list(
            self.item_list, self.tobis_json_dir, self.cfg.item_table)
        QMessageBox.information(self, "Saved", f"'{tag}' saved.")

    # Vanilla string table key prefixes per table type
    _ST_KEY_PREFIX = {
        "DT_Weapons": "Weapons",
        "DT_Armor": "Armor",
        "DT_Tools": "Tools",
        "DT_Items": "Items",
        "DT_Ores": "Items",
    }

    def _make_string_key(self, tag: str, suffix: str) -> str:
        """Build a vanilla-style string table key.

        Follows the game's convention per table type:
        - Weapons: Weapons.{WeaponType}.{AuthorName}.{suffix}
          e.g. Weapons.Battleaxe.Balin.Name
        - Armor: Armor.{Pack}.{Piece}.{suffix}
        - Tools: Tools.{ToolType}.{AuthorName}.{suffix}
        - Items/Ores: Items.{Tag}.{suffix}

        Falls back to "{tag}.{suffix}" if the table has no known pattern.
        """
        prefix = self._ST_KEY_PREFIX.get(self.cfg.item_table, "")
        if not prefix:
            return f"{tag}.{suffix}"

        # For weapons, use the weapon type from the master selector
        if self.cfg.item_table == "DT_Weapons" and self._master_combo:
            weapon_type = self._master_combo.currentText()
            if weapon_type and weapon_type != "(select)":
                # Extract the author/name part from tag
                # e.g. "Balin_Battleaxe" → "Balin", "Mereak_Battleaxe" → "Mereak"
                parts = tag.split("_")
                # Remove "Broken" prefix if present
                if parts[0] == "Broken" and len(parts) > 1:
                    author = "_".join(parts[1:-1]) if len(parts) > 2 else parts[1]
                    return f"Weapons.{weapon_type}.{author}.Broken.{suffix}"
                author = "_".join(parts[:-1]) if len(parts) > 1 else tag
                return f"Weapons.{weapon_type}.{author}.{suffix}"

        # Generic: Prefix.{tag_parts_joined_by_dots}.{suffix}
        parts = tag.replace("_", ".")
        return f"{prefix}.{parts}.{suffix}"

    def _save_item_file(self, tag: str) -> None:
        """Write the item per-item JSON from template + form values."""
        if not self._item_template:
            QMessageBox.warning(self, "No Template",
                                f"No template found for {self.cfg.item_table}.")
            return

        row = copy.deepcopy(self._item_template)
        row["Name"] = tag

        # Set DisplayName and Description string table keys
        # Follows vanilla key patterns per table type
        display_key = self._make_string_key(tag, "Name")
        desc_path = self.desc_input.text().strip() if self.desc_input else ""
        if not desc_path:
            desc_path = self._make_string_key(tag, "Description")
        for entry in row.get("Value", []):
            if entry.get("Name") == "DisplayName":
                entry["Value"] = display_key
            elif entry.get("Name") == "Description":
                entry["Value"] = desc_path

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

    def _save_broken_variant(  # pylint: disable=too-many-branches,too-many-statements
        self, _original_tag: str, broken_tag: str,
    ) -> None:
        """Create a Broken_ variant of a weapon or tool.

        The broken variant duplicates the original but with:
        - Name/tag: Broken_{original}
        - Actor path: insert _Broken before the .ClassName suffix
        - Damage: 5, Speed: 1.0, Durability: -1 (standard broken stats)
        - Tags.Tags: only the UI tag (no weapon type tag)
        """
        if not self._item_template:
            return

        row = copy.deepcopy(self._item_template)
        row["Name"] = broken_tag

        # Set DisplayName and Description using vanilla key pattern
        display_key = self._make_string_key(broken_tag, "Name")
        desc_key = self._make_string_key(broken_tag, "Description")
        for entry in row.get("Value", []):
            if entry.get("Name") == "DisplayName":
                entry["Value"] = display_key
            elif entry.get("Name") == "Description":
                entry["Value"] = desc_key

        # Apply the same widget values as the original
        self._apply_widgets_to_row(row, self._item_widgets)

        # Override Actor path: insert _Broken before the _C suffix
        # e.g. /Game/.../EQ_Sword.EQ_Sword_C → /Game/.../EQ_Sword_Broken.EQ_Sword_Broken_C
        for entry in row.get("Value", []):
            if entry.get("Name") == "Actor":
                # Actor is a SoftObjectPath dict after _apply_widgets_to_row
                val = entry.get("Value")
                if isinstance(val, dict):
                    asset = val.get("AssetPath", {}).get("AssetName", "")
                elif isinstance(val, str):
                    asset = val
                else:
                    asset = ""
                if asset and "." in asset:
                    pkg, cls = asset.rsplit(".", maxsplit=1)
                    if cls.endswith("_C"):
                        base = cls[:-2]
                        broken_asset = f"{pkg}_Broken.{base}_Broken_C"
                    else:
                        broken_asset = f"{pkg}_Broken.{cls}"
                    # Always write as proper SoftObjectPath dict
                    entry["Value"] = {
                        "$type": "UAssetAPI.PropertyTypes.Objects"
                                 ".FSoftObjectPath, UAssetAPI",
                        "AssetPath": {
                            "$type": "UAssetAPI.PropertyTypes.Objects"
                                     ".FTopLevelAssetPath, UAssetAPI",
                            "PackageName": None,
                            "AssetName": broken_asset,
                        },
                        "SubPathString": None,
                    }

            # Override standard broken stats
            elif entry.get("Name") == "Damage":
                entry["Value"] = 5
            elif entry.get("Name") == "Speed":
                entry["Value"] = 1.0
            elif entry.get("Name") == "Durability":
                entry["Value"] = -1

        # Tags: only the UI tag (no weapon type tag)
        # The master selector sets Tags.Tags to [UI_tag] then _inject_extra_tag
        # adds the weapon type tag. For broken, we just want [UI_tag].
        for entry in row.get("Value", []):
            if entry.get("Name") == "Tags":
                try:
                    inner = entry["Value"][0]
                    tag_list = inner.get("Value", [])
                    if isinstance(tag_list, list):
                        # Keep only UI tags (UI.Weapon.*), remove weapon type tags
                        ui_tags = [t for t in tag_list
                                   if t.startswith("UI.")]
                        inner["Value"] = ui_tags if ui_tags else tag_list[:1]
                except (KeyError, IndexError, TypeError):
                    pass
                break

        namemap = self._build_namemap(row)
        if broken_tag not in namemap:
            namemap.append(broken_tag)

        item_data = {
            "NameMap": namemap,
            "Imports": [],
            "Row": row,
        }

        out_dir = os.path.join(self.tobis_json_dir, self.cfg.item_table)
        os.makedirs(out_dir, exist_ok=True)
        path = os.path.join(out_dir, f"{broken_tag}.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(item_data, fh, indent=4, ensure_ascii=False)

    # ResultItemHandle prefix per item table (singular form)
    _RESULT_ITEM_PREFIX = {
        "DT_Weapons": "Weapon",
        "DT_Armor": "Armor",
        "DT_Tools": "Tool",
        "DT_Items": "Item",
    }

    def _save_recipe_file(self, tag: str) -> None:
        """Write the recipe per-item JSON from template + form values."""
        row = copy.deepcopy(self._recipe_template)
        row["Name"] = tag

        # Set ResultItemHandle.RowName with correct prefix
        # e.g. Weapon.Mereak_Battleaxe, Armor.BearGuild_Gloves_T4
        prefix = self._RESULT_ITEM_PREFIX.get(self.cfg.item_table, "Item")
        result_handle = f"{prefix}.{tag}"
        for entry in row.get("Value", []):
            if entry.get("Name") == "ResultItemHandle":
                for sub in entry.get("Value", []):
                    if isinstance(sub, dict) and sub.get("Name") == "RowName":
                        sub["Value"] = result_handle
                        break
                break

        # Apply recipe widget values
        self._apply_widgets_to_row(row, self._recipe_widgets)

        # Apply Crafting Stations checkboxes
        self._apply_stations_to_row(row)

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

        Supports dotted field names (e.g. "DamageType.TagName" or
        "InitialRepairCost.MaterialHandle.RowName") by recursively
        walking into nested struct/array Value entries.
        """
        for entry in row.get("Value", []):
            name = entry.get("Name")
            # Direct match
            if name in widgets:
                self._apply_widget_to_entry(entry, widgets[name])
                continue
            # Dotted match — recurse into nested structs
            for wname, widget in widgets.items():
                if not wname.startswith(f"{name}."):
                    continue
                remainder = wname[len(name) + 1:]  # e.g. "MaterialHandle.RowName"
                self._apply_nested(entry, remainder, widget)

    def _apply_nested(self, entry: dict, path: str, widget) -> None:
        """Walk into nested Value arrays to find and set a dotted field.

        path may be "TagName" (1 level) or "MaterialHandle.RowName" (2+ levels).
        Handles both struct Value lists and array Value lists (walks into [0]).
        """
        val = entry.get("Value")
        if isinstance(val, list):
            for sub in val:
                if not isinstance(sub, dict):
                    continue
                sub_name = sub.get("Name", "")
                if "." in path:
                    first, rest = path.split(".", maxsplit=1)
                    if sub_name == first:
                        self._apply_nested(sub, rest, widget)
                        return
                elif sub_name == path:
                    self._apply_widget_to_entry(sub, widget)
                    return

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
            elif "GameplayTagContainer" in dtype:
                # Tags are stored as a list of strings — set as single-element list
                # Additional tags (e.g. WeaponTypeTag) are injected separately
                entry["Value"] = [text] if text else []
            else:
                entry["Value"] = text
        elif isinstance(widget, QLineEdit):
            text = widget.text().strip()
            if isinstance(entry.get("Value"), dict):
                # Value is already a SoftObjectPath dict — update AssetName
                try:
                    entry["Value"]["AssetPath"]["AssetName"] = text
                except (KeyError, TypeError):
                    entry["Value"] = text
            elif "SoftObjectProperty" in dtype and text:
                # Template has placeholder (0) — construct proper SoftObjectPath
                entry["Value"] = {
                    "$type": "UAssetAPI.PropertyTypes.Objects.FSoftObjectPath, UAssetAPI",
                    "AssetPath": {
                        "$type": "UAssetAPI.PropertyTypes.Objects.FTopLevelAssetPath, UAssetAPI",
                        "PackageName": None,
                        "AssetName": text,
                    },
                    "SubPathString": None,
                }
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

    def _apply_stations_to_row(self, row: dict) -> None:
        """Rebuild the CraftingStations array from the checkbox group."""
        if not self._station_checkboxes:
            return
        checked = [
            row_name for row_name, cb in self._station_checkboxes.items()
            if cb.isChecked()
        ]
        for entry in row.get("Value", []):
            if entry.get("Name") == "CraftingStations":
                entry["Value"] = [make_station_struct(rn) for rn in checked]
                return

    def _apply_stations_from_values(self, values: list) -> None:
        """Set checkbox state from a recipe row's Value array."""
        if not self._station_checkboxes:
            return
        active = set(extract_station_row_names(values))
        for row_name, cb in self._station_checkboxes.items():
            cb.setChecked(row_name in active)

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

    def _on_item_selected(  # pylint: disable=too-many-branches
        self, current, _previous,
    ) -> None:
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

        # Name — show "display name (game name)" if found, else just game name
        display = self._display_names.get(tag, "")
        if not display:
            st = self._string_table.get(tag)
            if st:
                display = st.get("name", "")
        if display:
            self.name_input.setText(f"{display} ({tag})")
        else:
            self.name_input.setText(tag)

        # Description — show the string table path from the JSON
        desc_path = ""
        for entry in row.get("Value", []):
            if entry.get("Name") == "Description" and isinstance(
                entry.get("Value"), str
            ):
                desc_path = entry["Value"]
                break
        self.desc_input.setText(desc_path)

        # Description String — resolve from string table or show NOT FOUND
        st = self._string_table.get(tag)
        desc_text = st.get("description", "") if st else ""
        if desc_text:
            self.desc_string.setText(desc_text)
            self.desc_string.setStyleSheet("")
        else:
            self.desc_string.setText("STRING NOT FOUND IN STRING TABLE")
            self.desc_string.setStyleSheet("font-weight: bold; color: red;")
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
        self._apply_stations_from_values(vals)
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
        for cb in self._station_checkboxes.values():
            cb.setChecked(False)
        if self.cfg.recipe_has_materials and self._material_picker:
            self._material_picker.clear_all()
            self._material_picker.add_row()

    def _load_fields_into_widgets(self, values: list,
                                  widgets: dict[str, QWidget]) -> None:
        """Set each widget's value from its corresponding JSON entry.

        Supports dotted field names (e.g. "DamageType.TagName" or
        "InitialRepairCost.MaterialHandle.RowName") by recursively
        walking into nested struct/array Value entries.
        """
        for entry in values:
            fname = entry.get("Name")
            # Direct match
            if fname in widgets:
                self._set_widget(widgets[fname], entry)
                continue
            # Dotted match — recurse into nested structs
            for wname, widget in widgets.items():
                if not wname.startswith(f"{fname}."):
                    continue
                remainder = wname[len(fname) + 1:]
                found = self._find_nested(entry, remainder)
                if found is not None:
                    self._set_widget(widget, found)

    def _find_nested(self, entry: dict, path: str) -> dict | None:
        """Walk into nested Value arrays to find a dotted field entry."""
        val = entry.get("Value")
        if isinstance(val, list):
            for sub in val:
                if not isinstance(sub, dict):
                    continue
                sub_name = sub.get("Name", "")
                if "." in path:
                    first, rest = path.split(".", maxsplit=1)
                    if sub_name == first:
                        return self._find_nested(sub, rest)
                elif sub_name == path:
                    return sub
        return None

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
