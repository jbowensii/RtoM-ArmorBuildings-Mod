"""Shared GUI helpers — build pipeline, item list pane, and list management.

The build pipeline combines per-item JSON files with vanilla game data,
restores constructions removed in patch 1.2, and applies string table
imports to all DataTables (DT_Constructions, DT_Armor, DT_Weapons,
DT_Tools, DT_Items).
"""

from __future__ import annotations

import os

from PySide6.QtWidgets import (
    QLabel, QListWidget, QMessageBox, QPushButton, QVBoxLayout, QWidget,
)

from src.construction.mod_utils import advanced_bannister_post_stone_unlock
from src.utils.json_handler import load_json, save_json
from src.utils.json_split_combine import combine_all


# ---------------------------------------------------------------------------
# Build Combined Files (Combine + Restore + Update Mod)
# ---------------------------------------------------------------------------

# 32 constructions removed in game patch 1.2 that need their unlock type
# changed from Manual back to DiscoverDependencies so players can craft them.
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


def _find_prop(values: list, name: str) -> dict | None:
    """Return the first property dict in *values* whose Name matches."""
    for prop in values:
        if prop.get("Name") == name:
            return prop
    return None


def _restore_constructions(building_dir: str) -> int:
    """Restore constructions removed in patch 1.2.

    Sets DefaultUnlocks.UnlockType to DiscoverDependencies for each
    recipe matching _RESTORE_CONSTRUCTIONS.  Returns count restored.
    """
    recipes_path = os.path.join(building_dir, "DT_ConstructionRecipes.json")
    if not os.path.isfile(recipes_path):
        return 0
    data = load_json(recipes_path)
    count = 0
    for recipe in data["Exports"][0]["Table"]["Data"]:
        name = recipe.get("Name")
        if name not in _RESTORE_CONSTRUCTIONS:
            continue
        unlock = _find_prop(recipe["Value"], "DefaultUnlocks")
        if unlock is None:
            continue
        try:
            unlock["Value"][0]["Value"] = (
                "EMorRecipeUnlockType::DiscoverDependencies"
            )
            if name == "Advanced_Bannister_Post_Stone":
                unlock["Value"][3] = advanced_bannister_post_stone_unlock()
            count += 1
        except (KeyError, IndexError, TypeError):
            continue
    save_json(recipes_path, data)
    return count


def _append_string_table_imports(
    json_path: str, st_entries: list[dict],
) -> None:
    """Append string table Package+StringTable import pairs to a DataTable JSON.

    For each pair, the Package entry has OuterIndex=0 (no parent). The
    StringTable entry's OuterIndex is reindexed to point to its Package
    entry using negative 1-based indexing into the Imports array.
    The StringTable's position is then added to
    Exports[0].SerializationBeforeCreateDependencies.

    Args:
        json_path: Path to the combined DataTable JSON.
        st_entries: List of import dicts (Package + StringTable pairs)
                    with placeholder OuterIndex values.
    """
    import copy
    if not os.path.isfile(json_path):
        return
    data = load_json(json_path)

    # Deep-copy so we don't mutate the source for the next call
    entries = copy.deepcopy(st_entries)

    moded_len = len(data["Imports"])
    serial_deps: list[int] = []
    for i, imp in enumerate(entries):
        if imp["ClassName"] != "Package" and imp["OuterIndex"] < 0:
            # Point to the Package entry we're about to append
            imp["OuterIndex"] = -(moded_len + i)
            # StringTable position (1-based negative) goes into serial deps
            serial_deps.append(-(moded_len + i + 1))

    data["Imports"].extend(entries)
    if "SerializationBeforeCreateDependencies" in data["Exports"][0]:
        data["Exports"][0][
            "SerializationBeforeCreateDependencies"
        ].extend(serial_deps)
    save_json(json_path, data)


def _update_all_mod_imports(output_dir: str, data_dir: str) -> None:
    """Apply string table imports to all DataTables that reference mod strings.

    - DT_Constructions: ST_Mod_Architecture + ST_Mod_Interactables (entries 0-3)
    - DT_Armor, DT_Weapons, DT_Tools, DT_Items: ST_Mod_Items (entries 6-7)

    Import entries are read from data/Imports.json.
    """
    imports_path = os.path.join(data_dir, "Imports.json")
    if not os.path.isfile(imports_path):
        return
    st_imports = load_json(imports_path)
    all_imports = st_imports.get("Imports", [])

    # Constructions need Architecture + Interactables string tables
    arch_interactables = all_imports[0:4]
    building_dir = os.path.join(
        output_dir, "Moria", "Content", "Tech", "Data", "Building",
    )
    _append_string_table_imports(
        os.path.join(building_dir, "DT_Constructions.json"),
        arch_interactables,
    )

    # Armor, Weapons, Tools, Items need ST_Mod_Items
    items_st = all_imports[6:8]
    items_dir = os.path.join(
        output_dir, "Moria", "Content", "Tech", "Data", "Items",
    )
    for table in ("DT_Armor", "DT_Weapons", "DT_Tools", "DT_Items"):
        _append_string_table_imports(
            os.path.join(items_dir, f"{table}.json"),
            items_st,
        )


def build_combined(  # pylint: disable=broad-exception-caught
    parent: QWidget,
    tobis_json_dir: str,
    game_extract_dir: str,
    tobis_mod_dir: str,
    data_dir: str | None = None,
) -> None:
    """Run the full build pipeline: combine → restore → import-fix.

    Steps:
      1. Combine per-item Tobis_json/ files with vanilla game extract.
      2. Restore 32 constructions disabled in game patch 1.2.
      3. Append string table imports to all DataTables:
         - DT_Constructions: ST_Mod_Architecture + ST_Mod_Interactables
         - DT_Armor/Weapons/Tools/Items: ST_Mod_Items
    """
    output = os.path.join(tobis_mod_dir, "json_data")
    try:
        results = combine_all(tobis_json_dir, game_extract_dir, output)
        total = sum(results.values())
        detail = ", ".join(f"{k}: {v}" for k, v in results.items())

        building_dir = os.path.join(
            output, "Moria", "Content", "Tech", "Data", "Building",
        )
        restored = _restore_constructions(building_dir)

        if data_dir is None:
            data_dir = os.path.dirname(tobis_json_dir.rstrip(os.sep))
        _update_all_mod_imports(output, data_dir)

        msg = (
            f"Combined {total} items into TobisMod/json_data/.\n"
            f"Restored {restored} patch-1.2 constructions.\n"
            f"Applied string table imports.\n\n{detail}"
        )
        QMessageBox.information(parent, "Build Complete", msg)
    except Exception as exc:
        QMessageBox.critical(parent, "Build Failed", str(exc))


# ---------------------------------------------------------------------------
# Item List Pane (left side of adder tabs)
# ---------------------------------------------------------------------------

def create_item_list_pane(
    label_text: str = "Saved Items:",
) -> tuple[QWidget, QPushButton, QListWidget, QPushButton]:
    """Create a left-pane widget with Build button, item list, and Delete.

    Returns (container_widget, build_button, list_widget, delete_button).
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
    item_list: QListWidget, tobis_json_dir: str, table_name: str,
) -> None:
    """Reload a QListWidget from per-item JSON files in a subdirectory."""
    item_list.clear()
    dt_dir = os.path.join(tobis_json_dir, table_name)
    if os.path.isdir(dt_dir):
        for fname in sorted(os.listdir(dt_dir)):
            if fname.endswith(".json"):
                item_list.addItem(fname[:-5])


def delete_per_item(
    parent: QWidget, item_list: QListWidget,
    tobis_json_dir: str, tables: list[str],
) -> str | None:
    """Delete the selected item's per-item file(s) with confirmation.

    Removes matching JSON files from each table subdirectory.
    Returns the deleted tag name, or None if cancelled.
    """
    current = item_list.currentItem()
    if not current:
        QMessageBox.warning(parent, "No Selection", "Select an item.")
        return None

    tag = current.text()
    reply = QMessageBox.question(
        parent, "Confirm Delete", f"Delete '{tag}'?",
        QMessageBox.Yes | QMessageBox.No,
    )
    if reply != QMessageBox.Yes:
        return None

    for table in tables:
        path = os.path.join(tobis_json_dir, table, f"{tag}.json")
        if os.path.isfile(path):
            os.remove(path)
    return tag
