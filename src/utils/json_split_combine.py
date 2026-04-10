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
# Disabled-state helpers
# ---------------------------------------------------------------------------

def _is_disabled(row: dict) -> bool:
    """Return True if the row's EnabledState property is Disabled."""
    for prop in row.get("Value", []):
        if prop.get("Name") == "EnabledState":
            return "Disabled" in str(prop.get("Value", ""))
    return False


def collect_disabled_tags(source_dir: str) -> set[str]:
    """Scan per-item files in *source_dir* and return tags marked Disabled.

    Also includes ``Broken_{tag}`` variants so broken weapons/tools are
    skipped alongside their disabled base items.
    """
    if not os.path.isdir(source_dir):
        return set()
    disabled: set[str] = set()
    for fname in sorted(os.listdir(source_dir)):
        if not fname.endswith(".json"):
            continue
        try:
            item = _load(os.path.join(source_dir, fname))
        except (OSError, json.JSONDecodeError):
            continue
        row = item.get("Row", {})
        if not _is_disabled(row):
            continue
        tag = row.get("Name") or fname[:-5]
        disabled.add(tag)
        # Also skip the Broken_ variant if it exists
        if not tag.startswith("Broken_"):
            disabled.add(f"Broken_{tag}")
    return disabled


# ---------------------------------------------------------------------------
# Combine
# ---------------------------------------------------------------------------

def combine_dt_file(
    source_dir: str,
    shell_path: str,
    output_path: str,
    has_imports: bool = False,
    skip_tags: set[str] | None = None,
) -> int:
    """Combine per-item files back into a single DataTable JSON.

    Args:
        source_dir: Directory containing per-item JSON files.
        shell_path: Path to the vanilla base JSON (from game_extract).
        output_path: Where to write the combined file.
        has_imports: If True, merge and reindex Imports (DT_Constructions).
        skip_tags: Optional set of row names (tags) to exclude from the
            combined output. Rows whose own EnabledState is Disabled are
            always skipped.

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

    skip = set(skip_tags) if skip_tags else set()
    base_import_count = len(data.get("Imports", []))
    accumulated = 0
    namemap_set = set(data.get("NameMap", []))
    count = 0

    for fname in files:
        item = _load(os.path.join(source_dir, fname))
        row = item["Row"]
        tag = row.get("Name") or fname[:-5]

        # Skip if tag is in caller's skip set or the row is Disabled
        if tag in skip or _is_disabled(row):
            log.info("Skipping disabled row: %s", tag)
            continue

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
#
# Order matters: item tables are processed BEFORE recipe tables so the
# combine_all() orchestrator can collect disabled item tags and pass them
# to the recipe combiners (skip recipes whose result is disabled).
_COMBINE_MAP = [
    ("Architecture", None, {"is_arch": True}),
    # Item tables first
    ("DT_Constructions",
     "Moria/Content/Tech/Data/Building/DT_Constructions",
     {"has_imports": True, "is_item": True}),
    ("DT_Armor", "Moria/Content/Tech/Data/Items/DT_Armor",
     {"is_item": True}),
    ("DT_Weapons", "Moria/Content/Tech/Data/Items/DT_Weapons",
     {"is_item": True}),
    ("DT_Items", "Moria/Content/Tech/Data/Items/DT_Items",
     {"is_item": True}),
    ("DT_Tools", "Moria/Content/Tech/Data/Items/DT_Tools",
     {"is_item": True}),
    ("DT_Loot", "Moria/Content/Character/AI/DT_Loot", {}),
    ("DT_Ores", "Moria/Content/Tech/Data/Items/DT_Ores", {}),
    ("DT_CategoryTags", "Moria/Content/Tech/Data/DT_CategoryTags", {}),
    # Recipe tables last — receive the collected skip set
    ("DT_ConstructionRecipes",
     "Moria/Content/Tech/Data/Building/DT_ConstructionRecipes",
     {"is_recipe": True}),
    ("DT_ItemRecipes",
     "Moria/Content/Tech/Data/Items/DT_ItemRecipes",
     {"is_recipe": True}),
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

    # Disabled tags collected from item tables are passed to recipe tables
    # so recipes for disabled items are also skipped from the combined output.
    disabled_tags: set[str] = set()

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
            results[table_name] = combine_architecture_file(
                source, arch_shell, output)
            continue

        shell = os.path.join(uassetgui_dir, f"{game_path}.json")
        output = os.path.join(output_dir, f"{game_path}.json")

        if not os.path.isfile(shell):
            log.warning(
                "Vanilla base not found: %s — skipping %s", shell, table_name)
            results[table_name] = 0
            continue

        # Collect disabled tags from item tables BEFORE combining so they
        # can be skipped and forwarded to recipe tables.
        if opts.get("is_item"):
            table_disabled = collect_disabled_tags(source)
            disabled_tags.update(table_disabled)
            if table_disabled:
                log.info("%s: skipping %d disabled item(s)",
                         table_name, len(table_disabled))
            # Pass the table's own disabled set so Broken_ variants in the
            # same table (not themselves disabled) are also skipped.
            skip = table_disabled
        elif opts.get("is_recipe"):
            # Recipe tables use the full accumulated skip set
            skip = disabled_tags
        else:
            skip = None

        results[table_name] = combine_dt_file(
            source, shell, output,
            has_imports=opts.get("has_imports", False),
            skip_tags=skip,
        )

    return results
