"""Shared field-value helpers for autocomplete and widget creation.

Loads pre-built field-value indexes from data/field_values/ and provides
factory functions for QComboBox widgets with autocomplete.
"""

from __future__ import annotations

import json
import os

from PySide6.QtWidgets import QComboBox, QCompleter

# Resolved once at import time — points to data/field_values/
_FIELD_VALUES_DIR = os.path.normpath(os.path.join(
    os.path.dirname(__file__), os.pardir, os.pardir, "data", "field_values",
))


def load_field_values(table: str) -> dict:
    """Load the field-value index for *table* (e.g. "DT_Weapons").

    Returns a dict mapping field names to ``{"type": ..., "values": [...]}``.
    Returns an empty dict if the file is missing.
    """
    path = os.path.join(_FIELD_VALUES_DIR, f"{table}_fields.json")
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    return {}


def load_string_table() -> dict:
    """Load the string-table lookup (tag → {name, description}).

    Parsed from Localization/en/Game.po and cached as JSON.
    """
    path = os.path.join(_FIELD_VALUES_DIR, "string_table_lookup.json")
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    return {}


def enum_short_values(field_data: dict) -> list[str]:
    """Extract short enum names (after '::') from a field-value entry.

    Example: "EBuildProcess::DualMode" → "DualMode"
    """
    return sorted({
        v.rsplit("::", maxsplit=1)[-1]
        for v in field_data.get("values", [])
    })


def make_combo(
    values: list[str], editable: bool = True,
) -> QComboBox:
    """Create a QComboBox pre-populated with *values* and autocomplete."""
    combo = QComboBox()
    combo.setEditable(editable)
    combo.addItems(values)
    if editable and values:
        combo.setCompleter(QCompleter(values))
    return combo
