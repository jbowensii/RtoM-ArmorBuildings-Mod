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
        # Convert raw tag autocomplete values to "Display Name (tag)" format
        self._display_names = load_item_display_names()
        raw_ac = autocomplete_values or []
        self._ac_values = sorted({
            f"{self._display_names[v]} ({v})" if v in self._display_names else v
            for v in raw_ac
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
            labels = []
            for tag, display in tags.items():
                # Show as "Display Name (tag)" for clarity
                label = f"{display} ({tag})"
                vmap[label] = tag
                labels.append(label)
            labels.sort()
            name_cb.addItems(labels)
            all_vals = sorted(set(labels + self._ac_values))
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
        """Return [(material_tag, count), ...] from current rows.

        Resolves "Display Name (tag)" back to just the tag.
        """
        materials = []
        for name_cb, count_sb, vmap, _ in self._rows:
            display = name_cb.currentText().strip()
            tag = vmap.get(display, display)
            # Handle "Display Name (tag)" format — extract tag from parens
            if tag == display and "(" in display and display.endswith(")"):
                tag = display.rsplit("(", maxsplit=1)[-1].rstrip(")")
            materials.append((tag, count_sb.value()))
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
                        # Fall back to "Display Name (tag)" format
                        if mat_name in self._display_names:
                            label = f"{self._display_names[mat_name]} ({mat_name})"
                        else:
                            label = mat_name
                        name_cb.setCurrentText(label)
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
