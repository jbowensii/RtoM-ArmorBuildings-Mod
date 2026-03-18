"""Combine per-item JSON files with vanilla game data into full DataTables.

Per-item source files live in ``data/Tobis_json/{table}/{tag}.json``.
Vanilla base data comes from ``data/game_extract/uassetgui/{game_path}.json``.
Combined output goes to ``TobisMod/json_data/{game_path}.json``.
"""

from __future__ import annotations

import copy
import json
import logging
import os
from typing import Any

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(path: str, data: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    log.info("Wrote %s", path)


# ---------------------------------------------------------------------------
# Combine
# ---------------------------------------------------------------------------

def combine_dt_file(
    source_dir: str,
    shell_path: str,
    output_path: str,
    has_imports: bool = False,
) -> int:
    """Combine per-item files back into a single DataTable JSON.

    Args:
        source_dir: Directory containing per-item JSON files.
        shell_path: Path to the vanilla base JSON (from game_extract).
        output_path: Where to write the combined file.
        has_imports: If True, merge and reindex Imports (DT_Constructions).

    Returns:
        Number of items combined.
    """
    if not os.path.isdir(source_dir):
        log.warning("Source dir does not exist: %s", source_dir)
        return 0

    data = _load(shell_path)
    files = sorted(f for f in os.listdir(source_dir) if f.endswith(".json"))

    if not files:
        # No per-item files — just copy the vanilla base as-is
        _save(output_path, data)
        return 0

    base_import_count = len(data.get("Imports", []))
    accumulated = 0
    namemap_set = set(data.get("NameMap", []))
    count = 0

    for fname in files:
        item = _load(os.path.join(source_dir, fname))
        row = item["Row"]
        item_namemap = item.get("NameMap", [])
        item_imports = item.get("Imports", [])

        # Merge NameMap (deduplicate)
        for nm in item_namemap:
            if nm not in namemap_set:
                data["NameMap"].append(nm)
                namemap_set.add(nm)

        if has_imports and item_imports:
            # Assign real indices
            pkg_new_pos = base_import_count + accumulated  # 0-based position
            tex_new_pos = pkg_new_pos + 1

            pkg_import = copy.deepcopy(item_imports[0])
            tex_import = copy.deepcopy(item_imports[1])

            # Package OuterIndex stays 0
            pkg_import["OuterIndex"] = 0
            # Texture2D OuterIndex points to its Package (1-based negative)
            tex_import["OuterIndex"] = -(pkg_new_pos + 1)

            data["Imports"].append(pkg_import)
            data["Imports"].append(tex_import)

            # Fix Icon value in the row
            for prop in row.get("Value", []):
                if (prop.get("Name") == "Icon"
                        and isinstance(prop.get("Value"), int)):
                    prop["Value"] = -(tex_new_pos + 1)
                    break

            accumulated += len(item_imports)

        data["Exports"][0]["Table"]["Data"].append(row)
        count += 1

    _save(output_path, data)
    log.info("Combined %d items into %s", count, output_path)
    return count


def combine_architecture_file(
    source_dir: str,
    shell_path: str,
    output_path: str,
) -> int:
    """Combine per-item Architecture files back into a single string table.

    Returns:
        Number of items combined.
    """
    if not os.path.isdir(source_dir):
        log.warning("Source dir does not exist: %s", source_dir)
        return 0

    data = _load(shell_path)
    files = sorted(f for f in os.listdir(source_dir) if f.endswith(".json"))
    count = 0

    for fname in files:
        item = _load(os.path.join(source_dir, fname))
        data["Exports"][0]["Table"]["Value"].extend(item.get("Entries", []))
        count += 1

    _save(output_path, data)
    log.info("Combined %d architecture items into %s", count, output_path)
    return count


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

# Mapping: table_name → (game_path for vanilla base, combine options)
_COMBINE_MAP = [
    ("Architecture", None, {"is_arch": True}),
    ("DT_Constructions", "Moria/Content/Tech/Data/Building/DT_Constructions", {"has_imports": True}),
    ("DT_ConstructionRecipes", "Moria/Content/Tech/Data/Building/DT_ConstructionRecipes", {}),
    ("DT_ItemRecipes", "Moria/Content/Tech/Data/Items/DT_ItemRecipes", {}),
]


def combine_all(
    tobis_json_dir: str,
    game_extract_dir: str,
    output_dir: str,
) -> dict[str, int]:
    """Combine all per-item files into their respective combined outputs.

    For each table, the vanilla base is read from
    ``game_extract_dir/uassetgui/{game_path}.json`` and per-item rows from
    ``tobis_json_dir/{table_name}/``.  Output goes to
    ``output_dir/{game_path}.json`` (matching the game path structure).

    Architecture has no vanilla base (empty scaffold generated in-memory).

    Args:
        tobis_json_dir: Root of per-item files (data/Tobis_json/).
        game_extract_dir: Root of extracted game files (data/game_extract/).
        output_dir: Root of combined output (TobisMod/json_data/).

    Returns:
        Dict mapping table name → number of items combined.
    """
    results: dict[str, int] = {}
    uassetgui_dir = os.path.join(game_extract_dir, "uassetgui")

    for table_name, game_path, opts in _COMBINE_MAP:
        source = os.path.join(tobis_json_dir, table_name)

        if opts.get("is_arch"):
            # Architecture has no vanilla base — use empty scaffold
            arch_shell = os.path.join(tobis_json_dir, "_architecture_shell.json")
            if not os.path.isfile(arch_shell):
                empty_arch = {
                    "$type": "UAssetAPI.UAsset, UAssetAPI",
                    "Info": "Serialized with UAssetAPI",
                    "NameMap": [],
                    "Exports": [{"Table": {"Value": []}}],
                }
                os.makedirs(os.path.dirname(arch_shell), exist_ok=True)
                _save(arch_shell, empty_arch)

            output = os.path.join(
                output_dir, "Moria", "Content", "Tech", "Data",
                "Building", "Architecture.json",
            )
            results[table_name] = combine_architecture_file(source, arch_shell, output)
        else:
            shell = os.path.join(uassetgui_dir, f"{game_path}.json")
            output = os.path.join(output_dir, f"{game_path}.json")

            if not os.path.isfile(shell):
                log.warning("Vanilla base not found: %s — skipping %s", shell, table_name)
                results[table_name] = 0
                continue

            results[table_name] = combine_dt_file(
                source, shell, output,
                has_imports=opts.get("has_imports", False),
            )

    return results
