"""Reusable unlock-condition picker widget.

Manages the Discover Item / Discover Construction radio buttons and
the unlock-requirement combo box used by construction and item recipe tabs.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QButtonGroup, QComboBox, QCompleter, QHBoxLayout, QLabel,
    QRadioButton, QVBoxLayout,
)


class UnlockPicker:
    """Radio-toggle + combo for selecting unlock conditions.

    Supports loading saved unlock data from DT recipe JSON values.
    """

    def __init__(
        self, parent_layout: QVBoxLayout,
        unlock_requirements: dict,
        recipe_fv: dict | None = None,
        fv_key_prefix: str = "DefaultUnlocks",
    ) -> None:
        self._reqs = unlock_requirements
        self._recipe_fv = recipe_fv or {}
        self._fv_prefix = fv_key_prefix
        self._type = "UnlockRequiredItems"
        self._visible_map: dict[str, str] = {}  # display_name → tag

        # Build widgets
        parent_layout.addWidget(QLabel("Unlock Conditions (DefaultUnlocks):"))

        btn_row = QHBoxLayout()
        self._radio_item = QRadioButton("Discover Item")
        self._radio_item.setChecked(True)
        self._radio_item.clicked.connect(self._select_items)
        self._radio_constr = QRadioButton("Discover Construction")
        self._radio_constr.clicked.connect(self._select_constructions)

        group = QButtonGroup(self._radio_item)
        group.addButton(self._radio_item)
        group.addButton(self._radio_constr)
        # Keep a reference so Qt doesn't garbage-collect
        self._btn_group = group

        btn_row.addWidget(self._radio_item)
        btn_row.addWidget(self._radio_constr)
        parent_layout.addLayout(btn_row)

        self._combo = QComboBox()
        self._combo.setEditable(True)
        parent_layout.addWidget(self._combo)

        self._populate()

    # -- Public API --------------------------------------------------------

    @property
    def unlock_type(self) -> str:
        """Current unlock type: 'UnlockRequiredItems' or 'UnlockRequiredConstructions'."""
        return self._type

    @property
    def selected_tag(self) -> str:
        """Resolved tag for the selected unlock requirement."""
        display = self._combo.currentText()
        return self._visible_map.get(display, display)

    def load_from_values(self, values: list) -> None:
        """Populate from a DefaultUnlocks JSON struct."""
        for entry in values:
            if entry.get("Name") != "DefaultUnlocks":
                continue
            for field in entry.get("Value", []):
                if field.get("Name") == "UnlockRequiredItems":
                    items = field.get("Value", [])
                    if items:
                        self._radio_item.setChecked(True)
                        self._select_items()
                        self._set_combo_from_tag(items)
                        return
                elif field.get("Name") == "UnlockRequiredConstructions":
                    items = field.get("Value", [])
                    if items:
                        self._radio_constr.setChecked(True)
                        self._select_constructions()
                        self._set_combo_from_tag(items)
                        return
            return

    # -- Private -----------------------------------------------------------

    def _select_items(self) -> None:
        self._type = "UnlockRequiredItems"
        self._populate()

    def _select_constructions(self) -> None:
        self._type = "UnlockRequiredConstructions"
        self._populate()

    def _populate(self) -> None:
        """Refresh the combo with current unlock type's options."""
        self._combo.clear()
        self._visible_map.clear()
        for tag, name in self._reqs.get(self._type, {}).items():
            self._visible_map[name] = tag
            self._combo.addItem(name)
        # Add autocomplete from field values
        key = f"{self._fv_prefix}.{self._type}.RowName"
        extra = self._recipe_fv.get(key, {}).get("values", [])
        if extra:
            all_items = sorted(set(
                list(self._visible_map.keys()) + extra
            ))
            self._combo.setCompleter(QCompleter(all_items))

    def _set_combo_from_tag(self, items: list) -> None:
        """Set combo selection from a JSON UnlockRequired* array."""
        try:
            tag = items[0]["Value"][0]["Value"]
        except (KeyError, IndexError, TypeError):
            return
        for display, stored_tag in self._visible_map.items():
            if stored_tag == tag:
                self._combo.setCurrentText(display)
                return
        self._combo.setCurrentText(tag)
