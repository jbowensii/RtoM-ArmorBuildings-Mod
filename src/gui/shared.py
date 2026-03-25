"""Shared GUI helpers used by multiple tabs.

Provides reusable widgets and methods for material pickers, item list
panes, and the Build Combined Files action.
"""

from __future__ import annotations

import os
from PySide6.QtWidgets import (
    QComboBox, QCompleter, QHBoxLayout, QLabel, QListWidget,
    QMessageBox, QPushButton, QSpinBox, QVBoxLayout, QWidget,
)

from src.construction.mod_utils import advanced_bannister_post_stone_unlock
from src.utils.json_handler import load_json, save_json
from src.utils.json_split_combine import combine_all


# ---------------------------------------------------------------------------
# Build Combined Files (Combine + Restore + Update Mod)
# ---------------------------------------------------------------------------

# Constructions removed in game patch 1.2 that need unlock restoration
_RESTORE_CONSTRUCTIONS = [
    "Elder_Archway_A", "Advanced_Column_Wood_A", "Advanced_Column_Wood_D",
    "Advanced_Fence_Wood_1m", "Advanced_Fence_Wood", "Crude_Column",
    "Elder_Wall_E", "Scaffolding_Platform_Open", "Elder_Wall_A_Crown",
    "Elder_Wall_Short_A", "Elder_Window_B", "Elder_Window_A",
    "Elder_Wall_Thin_A_Crown", "Elder_Wall_Thin_B", "Elder_Archway_C",
    "Elder_Wall_B_Crown", "Elder_Wall_D", "Advanced_Column_Wood_B",
    "Elder_Wall_E_Crown", "Elder_Archway_Corner",
    "Scaffolding_Platform_1x1x3", "Elder_Wall_Short_B", "Elder_Wall_B",
    "Elder_Window_C", "Elder_Wall_A", "Elder_Wall_C", "Elder_Wall_Thin_A",
    "Scaffolding_Platform_1x3x3", "Elder_Archway_Vertical",
    "Elder_Archway_Horizontal_Large", "Elder_Wall_Corner_Crown",
    "Advanced_Stairs_Railing_1m_V2", "Advanced_Bannister_Post_Stone",
]


def _restore_constructions(building_dir: str) -> int:
    """Restore constructions removed in patch 1.2. Returns count restored."""
    recipes_path = os.path.join(building_dir, "DT_ConstructionRecipes.json")
    if not os.path.isfile(recipes_path):
        return 0
    data = load_json(recipes_path)
    count = 0
    for recipe in data["Exports"][0]["Table"]["Data"]:
        name = recipe.get("Name")
        if name in _RESTORE_CONSTRUCTIONS:
            for prop in recipe["Value"]:
                if prop.get("Name") == "DefaultUnlocks":
                    try:
                        prop["Value"][0]["Value"] = (
                            "EMorRecipeUnlockType::DiscoverDependencies"
                        )
                        if name == "Advanced_Bannister_Post_Stone":
                            prop["Value"][3] = advanced_bannister_post_stone_unlock()
                        count += 1
                    except (KeyError, IndexError, TypeError):
                        continue
    save_json(recipes_path, data)
    return count


def _update_mod_imports(building_dir: str, data_dir: str) -> None:
    """Apply string table imports to DT_Constructions."""
    constr_path = os.path.join(building_dir, "DT_Constructions.json")
    if not os.path.isfile(constr_path):
        return
    constr = load_json(constr_path)

    imports_path = os.path.join(data_dir, "Imports.json")
    if not os.path.isfile(imports_path):
        return
    st_imports = load_json(imports_path)
    arch_st = st_imports["Imports"][0:4]

    moded_len = len(constr["Imports"])
    serial_deps: list[int] = []
    for i, imp in enumerate(arch_st):
        if imp["OuterIndex"] < 0:
            imp["OuterIndex"] = -(moded_len + i)
            serial_deps.append(imp["OuterIndex"] - 1)

    constr["Imports"].extend(arch_st)
    if "SerializationBeforeCreateDependencies" in constr["Exports"][0]:
        constr["Exports"][0]["SerializationBeforeCreateDependencies"].extend(
            serial_deps
        )
    save_json(constr_path, constr)


def build_combined(
    parent: QWidget,
    tobis_json_dir: str,
    game_extract_dir: str,
    tobis_mod_dir: str,
    data_dir: str | None = None,
) -> None:
    """Combine all per-item files, restore 1.2 constructions, apply imports."""
    output = os.path.join(tobis_mod_dir, "json_data")
    try:
        # Step 1: Combine per-item files with vanilla base
        results = combine_all(tobis_json_dir, game_extract_dir, output)
        total = sum(results.values())
        detail = ", ".join(f"{k}: {v}" for k, v in results.items())

        # Step 2: Restore constructions removed in patch 1.2
        building_dir = os.path.join(
            output, "Moria", "Content", "Tech", "Data", "Building",
        )
        restored = _restore_constructions(building_dir)

        # Step 3: Apply string table imports to DT_Constructions
        if data_dir is None:
            data_dir = os.path.join(
                os.path.dirname(tobis_json_dir.rstrip(os.sep)),
            )
        _update_mod_imports(building_dir, data_dir)

        msg = (
            f"Combined {total} items into TobisMod/json_data/.\n"
            f"Restored {restored} patch-1.2 constructions.\n"
            f"Applied string table imports.\n\n{detail}"
        )
        QMessageBox.information(parent, "Build Complete", msg)
    except Exception as exc:  # noqa: BLE001
        QMessageBox.critical(parent, "Build Failed", str(exc))


# ---------------------------------------------------------------------------
# Item List Pane (left side of adder tabs)
# ---------------------------------------------------------------------------

def create_item_list_pane(
    label_text: str = "Saved Items:",
) -> tuple[QWidget, QPushButton, QListWidget, QPushButton]:
    """Create a left-pane widget with Build button, item list, and Delete button.

    Returns:
        (container_widget, build_button, list_widget, delete_button)
    """
    layout = QVBoxLayout()

    build_btn = QPushButton("Build Combined Files")
    build_btn.setStyleSheet("font-weight: bold; padding: 8px;")
    layout.addWidget(build_btn)

    layout.addWidget(QLabel(label_text))
    item_list = QListWidget()
    layout.addWidget(item_list)

    delete_btn = QPushButton("Delete Selected")
    layout.addWidget(delete_btn)

    widget = QWidget()
    widget.setLayout(layout)
    widget.setMaximumWidth(280)
    return widget, build_btn, item_list, delete_btn


def refresh_item_list(
    item_list: QListWidget,
    tobis_json_dir: str,
    table_name: str,
) -> None:
    """Reload a QListWidget from per-item files in a Tobis_json subdirectory."""
    item_list.clear()
    dt_dir = os.path.join(tobis_json_dir, table_name)
    if os.path.isdir(dt_dir):
        for fname in sorted(os.listdir(dt_dir)):
            if fname.endswith(".json"):
                item_list.addItem(fname[:-5])


def delete_per_item(
    parent: QWidget,
    item_list: QListWidget,
    tobis_json_dir: str,
    tables: list[str],
) -> str | None:
    """Delete the selected item's per-item file(s) with confirmation.

    Args:
        parent: Parent widget for dialogs.
        item_list: The QListWidget to get selection from.
        tobis_json_dir: Root of Tobis_json directory.
        tables: List of table subdirectories to delete from
                (e.g. ["DT_Constructions", "DT_ConstructionRecipes", "Architecture"]).

    Returns:
        The deleted tag name, or None if cancelled.
    """
    current = item_list.currentItem()
    if not current:
        QMessageBox.warning(parent, "No Selection", "Select an item to delete.")
        return None

    tag = current.text()
    reply = QMessageBox.question(
        parent, "Confirm Delete",
        f"Delete '{tag}'?",
        QMessageBox.Yes | QMessageBox.No,
    )
    if reply != QMessageBox.Yes:
        return None

    for table in tables:
        path = os.path.join(tobis_json_dir, table, f"{tag}.json")
        if os.path.isfile(path):
            os.remove(path)

    return tag


# ---------------------------------------------------------------------------
# Material Picker
# ---------------------------------------------------------------------------

def add_material_row(
    mat_layout: QVBoxLayout,
    materials_widgets: list,
    items: dict,
    max_materials: int = 6,
    parent: QWidget | None = None,
) -> bool:
    """Add a material picker row (category + name + count).

    Returns True if added, False if at max.
    """
    if len(materials_widgets) >= max_materials:
        if parent:
            QMessageBox.warning(parent, "Limit", f"Max {max_materials} materials.")
        return False

    row = QHBoxLayout()
    cat_cb = QComboBox()
    cat_cb.addItems(list(items.keys()))
    name_cb = QComboBox()
    name_cb.setEditable(True)
    vmap: dict[str, str] = {}

    def _update(category: str) -> None:
        tags = items.get(category, {})
        name_cb.clear()
        vmap.clear()
        names = []
        for t, n in tags.items():
            vmap[n] = t
            names.append(n)
        names.sort()
        name_cb.addItems(names)
        name_cb.setCompleter(QCompleter(names))

    cat_cb.currentTextChanged.connect(_update)
    _update(cat_cb.currentText())

    count = QSpinBox()
    count.setRange(1, 999)

    row.addWidget(cat_cb)
    row.addWidget(name_cb)
    row.addWidget(QLabel("x"))
    row.addWidget(count)
    mat_layout.addLayout(row)
    materials_widgets.append((name_cb, count, vmap))
    return True


def remove_material_row(
    mat_layout: QVBoxLayout,
    materials_widgets: list,
    parent: QWidget | None = None,
) -> bool:
    """Remove the last material picker row.

    Returns True if removed, False if at minimum.
    """
    if len(materials_widgets) <= 1:
        if parent:
            QMessageBox.warning(parent, "Minimum", "At least one material required.")
        return False

    idx = mat_layout.count() - 1
    item = mat_layout.itemAt(idx)
    if item and item.layout():
        while item.layout().count():
            w = item.layout().takeAt(0).widget()
            if w:
                w.setParent(None)
        mat_layout.removeItem(item.layout())
    materials_widgets.pop()
    return True


def collect_materials(materials_widgets: list) -> list[tuple[str, int]]:
    """Extract (tag, count) pairs from the material widgets."""
    materials = []
    for name_w, count_w, vmap in materials_widgets:
        vis = name_w.currentText().strip()
        materials.append((vmap.get(vis, vis), count_w.value()))
    return materials
