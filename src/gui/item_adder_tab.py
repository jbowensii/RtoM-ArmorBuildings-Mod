"""Generic item tab — works for any item table + optional recipe table.

Provides a left-pane item list and right-pane scrollable form with:
  - Read-only basic info (Pack Name, Name, Tag, Description)
  - Editable item fields (enums, bools, ints, floats via field config)
  - Optional recipe section (materials, unlock conditions)
  - Autocomplete from field_values index files
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QButtonGroup, QCheckBox, QComboBox, QCompleter,
    QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QPushButton, QRadioButton, QScrollArea, QSpinBox,
    QSplitter, QStyle, QVBoxLayout, QWidget,
)

from src.gui.shared import (
    build_combined, create_item_list_pane, delete_per_item, refresh_item_list,
)

_FIELD_VALUES_DIR = os.path.join(
    os.path.dirname(__file__), os.pardir, os.pardir, "data", "field_values",
)


# ── Configuration dataclass ──────────────────────────────────────

@dataclass
class TabConfig:
    """Describes what an item tab should display and edit."""

    tab_label: str                      # e.g. "New Weapon"
    item_table: str                     # e.g. "DT_Weapons"
    item_struct_label: str              # e.g. "DT_Weapons"
    recipe_table: str | None = None     # e.g. "DT_ItemRecipes" or None
    recipe_struct_label: str | None = None

    # Fields to show as editable in the item section
    # Each tuple: (field_name, widget_type)
    # widget_type: "enum", "bool", "int", "float", "tags", "asset"
    item_fields: list[tuple[str, str]] = field(default_factory=list)

    # Fields to show as editable in the recipe section
    recipe_fields: list[tuple[str, str]] = field(default_factory=list)

    # Whether recipe has materials and unlock sections
    recipe_has_materials: bool = False
    recipe_has_unlocks: bool = False


# ── Helpers ──────────────────────────────────────────────────────

def _load_field_values(table: str) -> dict:
    path = os.path.join(_FIELD_VALUES_DIR, f"{table}_fields.json")
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _load_string_table() -> dict:
    path = os.path.join(_FIELD_VALUES_DIR, "string_table_lookup.json")
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _enum_short_values(field_data: dict) -> list[str]:
    return sorted({v.split("::")[-1] for v in field_data.get("values", [])})


def _make_combo(values: list[str], editable: bool = True) -> QComboBox:
    cb = QComboBox()
    cb.setEditable(editable)
    cb.addItems(values)
    if editable and values:
        cb.setCompleter(QCompleter(values))
    return cb


# ── Generic Item Adder Tab ───────────────────────────────────────

class ItemAdderTab(QWidget):
    """Generic tab for viewing/editing any item table + optional recipe."""

    def __init__(self, cfg: TabConfig,
                 tobis_json_dir: str, templates_dir: str,
                 game_extract_dir: str, tobis_mod_dir: str,
                 data_dir: str | None = None,
                 items_index: dict | None = None,
                 unlock_requirements: dict | None = None) -> None:
        super().__init__()
        self.cfg = cfg
        self.tobis_json_dir = tobis_json_dir
        self.templates_dir = templates_dir
        self.game_extract_dir = game_extract_dir
        self.tobis_mod_dir = tobis_mod_dir
        self.data_dir = data_dir
        self.items_index = items_index or {}
        self.unlock_requirements = unlock_requirements or {}
        self.unlock_type = "UnlockRequiredItems"
        self.visible_unlock_map: dict[str, str] = {}
        self.materials_widgets: list = []

        # Editable widget references (field_name → widget)
        self._item_widgets: dict[str, QWidget] = {}
        self._recipe_widgets: dict[str, QWidget] = {}

        # Load field values for autocomplete
        self._item_fv = _load_field_values(cfg.item_table)
        self._recipe_fv = (
            _load_field_values(cfg.recipe_table) if cfg.recipe_table else {}
        )
        self._string_table = _load_string_table()

        self._setup_ui()

    # ── UI Setup ─────────────────────────────────────────────────
    def _setup_ui(self) -> None:
        outer = QHBoxLayout()

        # Left pane
        left_widget, self.build_btn, self.item_list, self.delete_btn = \
            create_item_list_pane(f"Saved {self.cfg.item_table} items:")
        self.build_btn.clicked.connect(
            lambda: build_combined(self, self.tobis_json_dir,
                                   self.game_extract_dir, self.tobis_mod_dir,
                                   self.data_dir)
        )
        self.item_list.currentItemChanged.connect(self._on_item_selected)
        self.delete_btn.clicked.connect(self._delete_selected)

        # Right pane
        right = QVBoxLayout()
        self._build_basic_info(right)
        self._build_item_fields(right)
        if self.cfg.recipe_table:
            self._build_recipe_fields(right)

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

        if self.cfg.recipe_has_materials:
            self._add_material_row()
        if self.cfg.recipe_has_unlocks:
            self._update_unlock_items()
        refresh_item_list(
            self.item_list, self.tobis_json_dir, self.cfg.item_table,
        )

    def _build_basic_info(self, parent: QVBoxLayout) -> None:
        group = QGroupBox("Basic Info")
        form = QFormLayout()

        # Pack name with autocomplete
        pack_values = self._item_fv.get("PackNames", {}).get("values", [])
        self.pack_name = QLineEdit()
        self.pack_name.setPlaceholderText("Pack name (e.g., Tobi)")
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
        parent.addWidget(group)

    def _build_item_fields(self, parent: QVBoxLayout) -> None:
        if not self.cfg.item_fields:
            return
        group = QGroupBox(self.cfg.item_struct_label)
        form = QFormLayout()

        for field_name, widget_type in self.cfg.item_fields:
            widget = self._create_field_widget(
                field_name, widget_type, self._item_fv,
            )
            self._item_widgets[field_name] = widget
            form.addRow(field_name, widget)

        group.setLayout(form)
        parent.addWidget(group)

    def _build_recipe_fields(self, parent: QVBoxLayout) -> None:
        group = QGroupBox(self.cfg.recipe_struct_label or self.cfg.recipe_table)
        layout = QVBoxLayout()

        # Enum/int/float/bool fields
        if self.cfg.recipe_fields:
            form = QFormLayout()
            for field_name, widget_type in self.cfg.recipe_fields:
                widget = self._create_field_widget(
                    field_name, widget_type, self._recipe_fv,
                )
                self._recipe_widgets[field_name] = widget
                form.addRow(field_name, widget)
            layout.addLayout(form)

        # Bool fields as checkboxes in rows
        bool_fields = [
            (fn, wt) for fn, wt in self.cfg.recipe_fields if wt == "bool"
        ]
        # (already added above via form, no need for separate checkbox rows)

        # Materials section
        if self.cfg.recipe_has_materials:
            layout.addWidget(QLabel("Required Materials (max 6):"))
            self.mat_layout = QVBoxLayout()
            layout.addLayout(self.mat_layout)
            add_btn = QPushButton("Add Material")
            add_btn.clicked.connect(self._add_material_row)
            layout.addWidget(add_btn)

        # Unlock section
        if self.cfg.recipe_has_unlocks:
            layout.addWidget(QLabel("Unlock Conditions (DefaultUnlocks):"))
            btn_layout = QHBoxLayout()
            self.radio_item = QRadioButton("Discover Item")
            self.radio_item.setChecked(True)
            self.radio_item.clicked.connect(self._update_unlock_items)
            self.radio_construction = QRadioButton("Discover Construction")
            self.radio_construction.clicked.connect(
                self._update_unlock_constructions
            )
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
        parent.addWidget(group)

    # ── Widget factory ───────────────────────────────────────────
    def _create_field_widget(self, field_name: str, widget_type: str,
                             field_values: dict) -> QWidget:
        fv = field_values.get(field_name, {})
        values = fv.get("values", [])

        if widget_type == "enum":
            short = _enum_short_values(fv) or values
            return _make_combo(short, editable=False)

        if widget_type == "bool":
            cb = QCheckBox()
            return cb

        if widget_type == "int":
            sb = QSpinBox()
            sb.setRange(-99999, 99999)
            # Set a sensible default from values
            if values:
                try:
                    sb.setValue(int(values[0]))
                except (ValueError, IndexError):
                    pass
            return sb

        if widget_type == "float":
            le = QLineEdit()
            le.setPlaceholderText("0.0")
            if values:
                le.setCompleter(QCompleter(values))
            return le

        if widget_type == "tags":
            return _make_combo(sorted(values), editable=True)

        if widget_type == "asset":
            le = QLineEdit()
            if values:
                le.setCompleter(QCompleter(sorted(values)))
            return le

        # Default: text with completer
        le = QLineEdit()
        if values:
            le.setCompleter(QCompleter(sorted(values)))
        return le

    # ── Material helpers ─────────────────────────────────────────
    def _add_material_row(self) -> None:
        if len(self.materials_widgets) >= 6:
            QMessageBox.warning(self, "Limit", "Max 6 materials.")
            return

        mat_values = self._recipe_fv.get(
            "DefaultRequiredMaterials.MaterialHandle.RowName", {},
        ).get("values", [])

        row = QHBoxLayout()
        cat_cb = QComboBox()
        cat_cb.addItems(sorted(self.items_index.keys()))
        name_cb = QComboBox()
        name_cb.setEditable(True)
        vmap: dict[str, str] = {}

        def _update(category: str) -> None:
            tags = self.items_index.get(category, {})
            name_cb.clear()
            vmap.clear()
            names = []
            for t, n in tags.items():
                vmap[n] = t
                names.append(n)
            names.sort()
            name_cb.addItems(names)
            all_values = sorted(set(names + mat_values))
            name_cb.setCompleter(QCompleter(all_values))

        cat_cb.currentTextChanged.connect(_update)
        _update(cat_cb.currentText())

        count = QSpinBox()
        count.setRange(1, 999)

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
        trash_btn.clicked.connect(
            lambda _, r=row, e=entry: self._remove_specific_material(r, e)
        )

    def _remove_specific_material(self, row_layout, entry) -> None:
        if len(self.materials_widgets) <= 1:
            QMessageBox.warning(self, "Minimum", "At least one material.")
            return
        while row_layout.count():
            w = row_layout.takeAt(0).widget()
            if w:
                w.setParent(None)
        self.mat_layout.removeItem(row_layout)
        if entry in self.materials_widgets:
            self.materials_widgets.remove(entry)

    def _clear_all_material_rows(self) -> None:
        while self.materials_widgets:
            idx = self.mat_layout.count() - 1
            item = self.mat_layout.itemAt(idx)
            if item and item.layout():
                while item.layout().count():
                    w = item.layout().takeAt(0).widget()
                    if w:
                        w.setParent(None)
                self.mat_layout.removeItem(item.layout())
            self.materials_widgets.pop()

    # ── Unlock helpers ───────────────────────────────────────────
    def _update_unlock_items(self) -> None:
        self.unlock_type = "UnlockRequiredItems"
        self._populate_unlock_combo()

    def _update_unlock_constructions(self) -> None:
        self.unlock_type = "UnlockRequiredConstructions"
        self._populate_unlock_combo()

    def _populate_unlock_combo(self) -> None:
        self.unlock_combo.clear()
        self.visible_unlock_map.clear()
        for tag, name in self.unlock_requirements.get(
            self.unlock_type, {}
        ).items():
            self.visible_unlock_map[name] = tag
            self.unlock_combo.addItem(name)
        key = f"DefaultUnlocks.{self.unlock_type}.RowName"
        extra = self._recipe_fv.get(key, {}).get("values", [])
        if extra:
            all_items = sorted(set(
                list(self.visible_unlock_map.keys()) + extra
            ))
            self.unlock_combo.setCompleter(QCompleter(all_items))

    # ── Item selection ───────────────────────────────────────────
    def _on_item_selected(self, current, _previous) -> None:
        if not current:
            return
        tag = current.text()

        # Load item JSON
        dt_path = os.path.join(
            self.tobis_json_dir, self.cfg.item_table, f"{tag}.json",
        )
        if not os.path.isfile(dt_path):
            return
        with open(dt_path, "r", encoding="utf-8") as f:
            dt_data = json.load(f)
        row = dt_data.get("Row", {})
        self.tag_display.setText(row.get("Name", tag))

        # Pack name from tag
        tag_parts = tag.split("_")
        for i, part in enumerate(tag_parts):
            if "Pack" in part:
                self.pack_name.setText("_".join(tag_parts[:i + 1]))
                break

        # Name & Description from string table or row text fields
        st_entry = self._string_table.get(tag)
        if st_entry:
            self.name_input.setText(st_entry.get("name", ""))
            self.desc_input.setText(st_entry.get("description", ""))
        else:
            self._load_text_from_row(row.get("Value", []))

        # Load item fields into widgets
        item_vals = row.get("Value", [])
        self._load_fields_into_widgets(item_vals, self._item_widgets)

        # Load recipe if applicable
        if self.cfg.recipe_table:
            recipe_path = os.path.join(
                self.tobis_json_dir, self.cfg.recipe_table, f"{tag}.json",
            )
            if os.path.isfile(recipe_path):
                with open(recipe_path, "r", encoding="utf-8") as f:
                    recipe_data = json.load(f)
                recipe_vals = recipe_data.get("Row", {}).get("Value", [])
                self._load_fields_into_widgets(recipe_vals, self._recipe_widgets)
                if self.cfg.recipe_has_materials:
                    self._load_materials(recipe_vals)
                if self.cfg.recipe_has_unlocks:
                    self._load_unlocks(recipe_vals)

    def _load_text_from_row(self, values: list) -> None:
        """Try to extract DisplayName/Description from row values."""
        for entry in values:
            name = entry.get("Name", "")
            val = entry.get("Value", "")
            if name == "DisplayName" and isinstance(val, str):
                self.name_input.setText(val)
            elif name == "Description" and isinstance(val, str):
                self.desc_input.setText(val)

    def _load_fields_into_widgets(self, values: list,
                                  widgets: dict[str, QWidget]) -> None:
        for entry in values:
            field_name = entry.get("Name")
            if field_name not in widgets:
                continue
            widget = widgets[field_name]
            val = entry.get("Value")
            t = entry.get("$type", "")

            if isinstance(widget, QCheckBox):
                widget.setChecked(bool(val))
            elif isinstance(widget, QSpinBox):
                try:
                    widget.setValue(int(val))
                except (ValueError, TypeError):
                    pass
            elif isinstance(widget, QComboBox):
                if "EnumProperty" in t:
                    short = str(val).split("::")[-1] if "::" in str(val) else str(val)
                    idx = widget.findText(short)
                    if idx >= 0:
                        widget.setCurrentIndex(idx)
                    else:
                        widget.setCurrentText(short)
                elif isinstance(val, list):
                    # Tags
                    try:
                        tags = val[0].get("Value", []) if val else []
                        if tags:
                            widget.setCurrentText(tags[0])
                    except (KeyError, IndexError, TypeError, AttributeError):
                        pass
                else:
                    widget.setCurrentText(str(val) if val else "")
            elif isinstance(widget, QLineEdit):
                if isinstance(val, dict):
                    try:
                        widget.setText(val["AssetPath"]["AssetName"])
                    except (KeyError, TypeError):
                        widget.setText(str(val))
                else:
                    widget.setText(str(val) if val is not None else "")

    def _load_materials(self, values: list) -> None:
        for entry in values:
            if entry.get("Name") == "DefaultRequiredMaterials":
                mats = entry.get("Value", [])
                self._clear_all_material_rows()
                for mat in mats:
                    mat_vals = mat.get("Value", [])
                    mat_name = ""
                    count = 1
                    for fld in mat_vals:
                        if fld.get("Name") == "MaterialHandle":
                            try:
                                mat_name = fld["Value"][0]["Value"]
                            except (KeyError, IndexError, TypeError):
                                pass
                        elif fld.get("Name") == "Count":
                            count = fld.get("Value", 1)
                    self._add_material_row()
                    if self.materials_widgets:
                        name_w, count_w, vmap = self.materials_widgets[-1]
                        found = False
                        for display, t in vmap.items():
                            if t == mat_name:
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
        for entry in values:
            if entry.get("Name") == "DefaultUnlocks":
                for fld in entry.get("Value", []):
                    if fld.get("Name") == "UnlockRequiredItems":
                        items = fld.get("Value", [])
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
                    elif fld.get("Name") == "UnlockRequiredConstructions":
                        items = fld.get("Value", [])
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
        tables = [self.cfg.item_table]
        if self.cfg.recipe_table:
            tables.append(self.cfg.recipe_table)
        tag = delete_per_item(
            self, self.item_list, self.tobis_json_dir, tables,
        )
        if tag:
            refresh_item_list(
                self.item_list, self.tobis_json_dir, self.cfg.item_table,
            )
            QMessageBox.information(self, "Deleted", f"'{tag}' removed.")
