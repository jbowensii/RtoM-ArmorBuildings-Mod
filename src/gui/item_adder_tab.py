"""Generic item-adder tab for any item table with optional recipe editing."""
from __future__ import annotations

import json
import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QCompleter, QFormLayout, QGroupBox,
    QLabel, QLineEdit, QMessageBox, QPushButton, QScrollArea,
    QSpinBox, QSplitter, QVBoxLayout, QWidget,
)

from src.gui.field_helpers import (
    enum_short_values, load_field_values, load_string_table, make_combo,
)
from src.gui.material_picker import MaterialPicker
from src.gui.shared import (
    build_combined, create_item_list_pane, delete_per_item, refresh_item_list,
)
from src.gui.tab_configs import TabConfig
from src.gui.unlock_picker import UnlockPicker

class ItemAdderTab(QWidget):
    """Generic tab for viewing/editing any item table plus optional recipe."""

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
        self.delete_btn: QPushButton | None = None
        self.pack_name: QLineEdit | None = None
        self.name_input: QLineEdit | None = None
        self.tag_display: QLineEdit | None = None
        self.desc_input: QLineEdit | None = None
        self.mat_layout: QVBoxLayout | None = None
        self._material_picker: MaterialPicker | None = None
        self._unlock_picker: UnlockPicker | None = None
        # Field-value indexes for autocomplete
        self._item_fv = load_field_values(cfg.item_table)
        self._recipe_fv = (
            load_field_values(cfg.recipe_table) if cfg.recipe_table else {}
        )
        self._string_table = load_string_table()
        self._setup_ui()

    def _setup_ui(self) -> None:
        outer = QVBoxLayout()
        left_widget, self.build_btn, self.item_list, self.delete_btn = \
            create_item_list_pane(f"Saved {self.cfg.item_table} items:")
        self.build_btn.clicked.connect(
            lambda: build_combined(
                self, self.tobis_json_dir, self.game_extract_dir,
                self.tobis_mod_dir, self.data_dir))
        self.item_list.currentItemChanged.connect(self._on_item_selected)
        self.delete_btn.clicked.connect(self._delete_selected)
        right = QVBoxLayout()
        self._build_basic_info(right)
        self._build_item_fields(right)
        if self.cfg.recipe_table:
            self._build_recipe_fields(right)
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
        """Pack name (editable) + read-only name / tag / description."""
        group = QGroupBox("Basic Info")
        form = QFormLayout()
        pack_vals = self._item_fv.get("PackNames", {}).get("values", [])
        self.pack_name = QLineEdit()
        self.pack_name.setPlaceholderText("Pack name (e.g., Tobi)")
        if pack_vals:
            self.pack_name.setCompleter(QCompleter(sorted(pack_vals)))
        self.name_input = QLineEdit()
        self.name_input.setReadOnly(True)
        self.tag_display = QLineEdit()
        self.tag_display.setReadOnly(True)
        self.desc_input = QLineEdit()
        self.desc_input.setReadOnly(True)
        for label, widget in [("Pack Name", self.pack_name),
                              ("Name", self.name_input),
                              ("Name Tag", self.tag_display),
                              ("Description", self.desc_input)]:
            form.addRow(label, widget)
        group.setLayout(form)
        parent.addWidget(group)

    def _build_item_fields(self, parent: QVBoxLayout) -> None:
        """Editable widgets for each configured item field."""
        if not self.cfg.item_fields:
            return
        group = QGroupBox(self.cfg.item_struct_label)
        form = QFormLayout()
        for name, wtype in self.cfg.item_fields:
            w = self._create_field_widget(name, wtype, self._item_fv)
            self._item_widgets[name] = w
            form.addRow(name, w)
        group.setLayout(form)
        parent.addWidget(group)

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
        parts = tag.split("_")
        for i, part in enumerate(parts):
            if "Pack" in part:
                self.pack_name.setText("_".join(parts[:i + 1]))
                break
        st = self._string_table.get(tag)
        if st:
            self.name_input.setText(st.get("name", ""))
            self.desc_input.setText(st.get("description", ""))
        else:
            for entry in row.get("Value", []):
                n, v = entry.get("Name", ""), entry.get("Value", "")
                if n == "DisplayName" and isinstance(v, str):
                    self.name_input.setText(v)
                elif n == "Description" and isinstance(v, str):
                    self.desc_input.setText(v)
        self._load_fields_into_widgets(row.get("Value", []), self._item_widgets)
        if self.cfg.recipe_table:
            self._load_recipe(tag)

    def _load_recipe(self, tag: str) -> None:
        """Load recipe JSON and populate recipe widgets / materials / unlocks."""
        path = os.path.join(
            self.tobis_json_dir, self.cfg.recipe_table, f"{tag}.json")
        if not os.path.isfile(path):
            return
        with open(path, "r", encoding="utf-8") as fh:
            vals = json.load(fh).get("Row", {}).get("Value", [])
        self._load_fields_into_widgets(vals, self._recipe_widgets)
        if self.cfg.recipe_has_materials and self._material_picker:
            self._material_picker.load_from_values(vals)
        if self.cfg.recipe_has_unlocks and self._unlock_picker:
            self._unlock_picker.load_from_values(vals)

    def _load_fields_into_widgets(self, values: list,
                                  widgets: dict[str, QWidget]) -> None:
        """Set each widget's value from its corresponding JSON entry."""
        for entry in values:
            fname = entry.get("Name")
            if fname not in widgets:
                continue
            w, val = widgets[fname], entry.get("Value")
            if isinstance(w, QCheckBox):
                w.setChecked(bool(val))
            elif isinstance(w, QSpinBox):
                try:
                    w.setValue(int(val))
                except (ValueError, TypeError):
                    pass
            elif isinstance(w, QComboBox):
                self._set_combo(w, val, entry.get("$type", ""))
            elif isinstance(w, QLineEdit):
                self._set_lineedit(w, val)

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
