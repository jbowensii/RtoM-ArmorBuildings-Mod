"""Reusable material-picker widget manager.

Manages a dynamic list of material rows (category + name + count + trash)
used by construction and item tabs for DT recipe editing.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QApplication, QComboBox, QCompleter, QHBoxLayout, QLabel,
    QMessageBox, QPushButton, QSpinBox, QStyle, QVBoxLayout, QWidget,
)

from src.gui.field_helpers import load_item_display_names


class MaterialPicker:
    """Dynamic list of material-picker rows (max 6).

    Each row has: category combo, name combo (with autocomplete),
    count spinner, and a trash button to remove that row.
    """

    MAX_ROWS = 6

    def __init__(
        self, parent: QWidget, layout: QVBoxLayout,
        items_index: dict, autocomplete_values: list[str] | None = None,
    ) -> None:
        self._parent = parent
        self._layout = layout
        self._items_index = items_index
        # Convert raw tag autocomplete values to display names where possible
        self._display_names = load_item_display_names()
        raw_ac = autocomplete_values or []
        self._ac_values = sorted({
            self._display_names.get(v, v) for v in raw_ac
        })
        self._rows: list[tuple[QComboBox, QSpinBox, dict, QHBoxLayout]] = []

    # -- Public API --------------------------------------------------------

    @property
    def count(self) -> int:
        """Number of material rows currently displayed."""
        return len(self._rows)

    def add_row(self) -> None:
        """Add a material row. Warns if already at MAX_ROWS."""
        if len(self._rows) >= self.MAX_ROWS:
            QMessageBox.warning(
                self._parent, "Limit", f"Max {self.MAX_ROWS} materials.",
            )
            return

        row = QHBoxLayout()
        cat_cb = QComboBox()
        cat_cb.addItems(sorted(self._items_index.keys()))
        name_cb = QComboBox()
        name_cb.setEditable(True)
        vmap: dict[str, str] = {}

        def _on_category(category: str) -> None:
            tags = self._items_index.get(category, {})
            name_cb.clear()
            vmap.clear()
            names = []
            for tag, display in tags.items():
                vmap[display] = tag
                names.append(display)
            names.sort()
            name_cb.addItems(names)
            all_vals = sorted(set(names + self._ac_values))
            name_cb.setCompleter(QCompleter(all_vals))

        cat_cb.currentTextChanged.connect(_on_category)
        _on_category(cat_cb.currentText())

        count_sb = QSpinBox()
        count_sb.setRange(1, 999)

        # Per-row trash button
        trash = QPushButton()
        icon = QApplication.style().standardIcon(QStyle.SP_TrashIcon)
        if icon.isNull():
            trash.setText("\u2715")
        else:
            trash.setIcon(icon)
        trash.setFixedWidth(30)
        trash.setToolTip("Remove this material")

        row.addWidget(cat_cb)
        row.addWidget(name_cb)
        row.addWidget(QLabel("x"))
        row.addWidget(count_sb)
        row.addWidget(trash)
        self._layout.addLayout(row)

        entry = (name_cb, count_sb, vmap, row)
        self._rows.append(entry)
        trash.clicked.connect(lambda _, e=entry: self._remove(e))

    def clear_all(self) -> None:
        """Remove every material row (used before loading saved data)."""
        while self._rows:
            self._remove_force(self._rows[-1])

    def collect(self) -> list[tuple[str, int]]:
        """Return [(material_tag, count), ...] from current rows."""
        materials = []
        for name_cb, count_sb, vmap, _ in self._rows:
            display = name_cb.currentText().strip()
            materials.append((vmap.get(display, display), count_sb.value()))
        return materials

    def load_from_values(self, values: list) -> None:
        """Populate rows from a DefaultRequiredMaterials JSON array."""
        for entry in values:
            if entry.get("Name") != "DefaultRequiredMaterials":
                continue
            mats = entry.get("Value", [])
            self.clear_all()
            for mat in mats:
                mat_name, count = _parse_material(mat)
                self.add_row()
                if self._rows:
                    name_cb, count_sb, vmap, _ = self._rows[-1]
                    # Try display name first, fall back to raw tag
                    found = False
                    for display, tag in vmap.items():
                        if tag == mat_name:
                            name_cb.setCurrentText(display)
                            found = True
                            break
                    if not found:
                        # Fall back to global display name, then raw tag
                        friendly = self._display_names.get(mat_name, mat_name)
                        name_cb.setCurrentText(friendly)
                    count_sb.setValue(count)
            if not mats:
                self.add_row()
            return
        # No DefaultRequiredMaterials found — add one empty row
        self.add_row()

    # -- Private -----------------------------------------------------------

    def _remove(self, entry: tuple) -> None:
        """Remove a specific row (with minimum-1 guard)."""
        if len(self._rows) <= 1:
            QMessageBox.warning(
                self._parent, "Minimum", "At least one material required.",
            )
            return
        self._remove_force(entry)

    def _remove_force(self, entry: tuple) -> None:
        """Remove a row without minimum check."""
        _, _, _, row_layout = entry
        while row_layout.count():
            widget = row_layout.takeAt(0).widget()
            if widget:
                widget.setParent(None)
        self._layout.removeItem(row_layout)
        if entry in self._rows:
            self._rows.remove(entry)


def _parse_material(mat: dict) -> tuple[str, int]:
    """Extract (material_tag, count) from a MorRequiredRecipeMaterial struct."""
    mat_name = ""
    count = 1
    for field in mat.get("Value", []):
        if field.get("Name") == "MaterialHandle":
            try:
                mat_name = field["Value"][0]["Value"]
            except (KeyError, IndexError, TypeError):
                pass
        elif field.get("Name") == "Count":
            count = field.get("Value", 1)
    return mat_name, count
