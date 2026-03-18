"""Split combined UAsset JSON files into per-item files and combine them back.

The *split* functions extract individual rows from large DataTable JSON files
exported by UAssetAPI, writing one file per item.  The *combine* functions
reassemble those per-item files into the combined format the game expects.

Directory layout (relative to saves_dir)::

    json_source/
        MoreBuildings/
            Architecture/{tag}.json
            DT_Constructions/{tag}.json
            DT_ConstructionRecipes/{tag}.json
        MoreArmor/
            DT_ItemRecipes/{tag}.json

    newObjects/          <-- generated output (combined files)
        MoreBuildings/
            Architecture.json
            DT_Constructions.json
            DT_ConstructionRecipes.json
        MoreArmor/
            DT_ItemRecipes.json
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


def _relevant_namemap(row_json_str: str, namemap: list[str]) -> list[str]:
    """Return NameMap entries that appear anywhere in the serialised row."""
    return [nm for nm in namemap if nm in row_json_str]


# ---------------------------------------------------------------------------
# Split
# ---------------------------------------------------------------------------

def split_dt_file(
    combined_path: str,
    output_dir: str,
    prefix_filter: str = "TobiPack_",
    has_imports: bool = False,
) -> int:
    """Split a DataTable JSON into per-item files.

    Args:
        combined_path: Path to the combined DT JSON file.
        output_dir: Directory to write per-item files to.
        prefix_filter: Only extract rows whose Name starts with this.
        has_imports: If True (DT_Constructions), also extract per-item Imports.

    Returns:
        Number of items extracted.
    """
    data = _load(combined_path)
    rows = data["Exports"][0]["Table"]["Data"]
    namemap = data.get("NameMap", [])
    imports = data.get("Imports", [])
    count = 0

    for row in rows:
        name = row.get("Name", "")
        if not name.startswith(prefix_filter):
            continue

        row_str = json.dumps(row)
        item_namemap = _relevant_namemap(row_str, namemap)
        item_imports: list[dict] = []

        if has_imports:
            # Find Icon ObjectPropertyData — Value[2] for constructions
            icon_idx = None
            for prop in row.get("Value", []):
                if (prop.get("Name") == "Icon"
                        and prop.get("$type", "").endswith("ObjectPropertyData, UAssetAPI")
                        and isinstance(prop.get("Value"), int)
                        and prop["Value"] < 0):
                    icon_idx = prop["Value"]
                    break

            if icon_idx is not None:
                # Texture2D is at abs(icon_idx) - 1, Package is its OuterIndex
                tex_pos = abs(icon_idx) - 1
                tex_import = imports[tex_pos]
                pkg_pos = abs(tex_import["OuterIndex"]) - 1
                pkg_import = imports[pkg_pos]
                # Store with placeholder indices — combine will recalculate
                pkg_copy = copy.deepcopy(pkg_import)
                tex_copy = copy.deepcopy(tex_import)
                pkg_copy["OuterIndex"] = 0  # Package always has OuterIndex 0
                tex_copy["OuterIndex"] = -1  # placeholder: "first of my pair"
                item_imports = [pkg_copy, tex_copy]

        item_data = {
            "NameMap": item_namemap,
            "Imports": item_imports,
            "Row": row,
        }
        _save(os.path.join(output_dir, f"{name}.json"), item_data)
        count += 1

    log.info("Split %d items from %s", count, combined_path)
    return count


def split_architecture_file(
    combined_path: str,
    output_dir: str,
    prefix_filter: str = "TobiPack_",
) -> int:
    """Split Architecture.json string table into per-item files.

    Returns:
        Number of items extracted.
    """
    data = _load(combined_path)
    entries = data["Exports"][0]["Table"]["Value"]

    # Group by prefix: "Tag.Name" / "Tag.Description" → group by Tag
    groups: dict[str, list[list]] = {}
    for entry in entries:
        if not isinstance(entry, list) or len(entry) != 2:
            continue
        key = entry[0]  # e.g. "TobiPack_AleKeg.Name"
        dot = key.rfind(".")
        if dot < 0:
            continue
        prefix = key[:dot]
        if not prefix.startswith(prefix_filter):
            continue
        groups.setdefault(prefix, []).append(entry)

    count = 0
    for prefix, group_entries in groups.items():
        item_data = {"Entries": group_entries}
        _save(os.path.join(output_dir, f"{prefix}.json"), item_data)
        count += 1

    log.info("Split %d architecture items from %s", count, combined_path)
    return count


def generate_shell(
    combined_path: str,
    shell_path: str,
    prefix_filter: str = "TobiPack_",
    has_imports: bool = False,
    is_architecture: bool = False,
) -> None:
    """Create a shell template by stripping prefix_filter rows from a combined file."""
    data = _load(combined_path)

    if is_architecture:
        entries = data["Exports"][0]["Table"]["Value"]
        data["Exports"][0]["Table"]["Value"] = [
            e for e in entries
            if not (isinstance(e, list) and len(e) == 2
                    and e[0].split(".")[0].startswith(prefix_filter))
        ]
        _save(shell_path, data)
        log.info("Generated architecture shell: %s", shell_path)
        return

    rows = data["Exports"][0]["Table"]["Data"]

    # Collect names of rows to remove
    remove_names = {r["Name"] for r in rows if r.get("Name", "").startswith(prefix_filter)}

    if has_imports:
        # Collect import indices to remove
        remove_import_positions: set[int] = set()
        for row in rows:
            if row.get("Name", "") not in remove_names:
                continue
            for prop in row.get("Value", []):
                if (prop.get("Name") == "Icon"
                        and isinstance(prop.get("Value"), int)
                        and prop["Value"] < 0):
                    tex_pos = abs(prop["Value"]) - 1
                    tex_imp = data["Imports"][tex_pos]
                    pkg_pos = abs(tex_imp["OuterIndex"]) - 1
                    remove_import_positions.add(tex_pos)
                    remove_import_positions.add(pkg_pos)

        # Remove imports (rebuild list excluding removed positions)
        old_imports = data["Imports"]
        new_imports = []
        # Build old→new index mapping for remaining imports
        old_to_new: dict[int, int] = {}
        for i, imp in enumerate(old_imports):
            if i not in remove_import_positions:
                old_to_new[i] = len(new_imports)
                new_imports.append(imp)

        # Fix OuterIndex references in remaining imports
        for imp in new_imports:
            oi = imp.get("OuterIndex", 0)
            if oi < 0:
                old_pos = abs(oi) - 1
                if old_pos in old_to_new:
                    imp["OuterIndex"] = -(old_to_new[old_pos] + 1)

        # Fix Icon references in remaining rows
        for row in rows:
            if row.get("Name", "") in remove_names:
                continue
            for prop in row.get("Value", []):
                if (prop.get("Name") == "Icon"
                        and isinstance(prop.get("Value"), int)
                        and prop["Value"] < 0):
                    old_pos = abs(prop["Value"]) - 1
                    if old_pos in old_to_new:
                        prop["Value"] = -(old_to_new[old_pos] + 1)

        # Fix SerializationBeforeCreateDependencies
        serial_deps = data["Exports"][0].get("SerializationBeforeCreateDependencies", [])
        new_serial = []
        for dep in serial_deps:
            if dep < 0:
                old_pos = abs(dep) - 1
                if old_pos in old_to_new:
                    new_serial.append(-(old_to_new[old_pos] + 1))
            else:
                new_serial.append(dep)
        data["Exports"][0]["SerializationBeforeCreateDependencies"] = new_serial

        data["Imports"] = new_imports

    # Remove matching rows
    data["Exports"][0]["Table"]["Data"] = [
        r for r in rows if r.get("Name", "") not in remove_names
    ]

    # Clean NameMap: remove entries only used by removed rows
    remaining_str = json.dumps(data["Exports"][0]["Table"]["Data"]) + json.dumps(data.get("Imports", []))
    data["NameMap"] = [nm for nm in data["NameMap"] if nm in remaining_str]

    _save(shell_path, data)
    log.info("Generated shell: %s (%d rows removed)", shell_path, len(remove_names))


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
        shell_path: Path to the shell template (vanilla-only base).
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
        # No per-item files — just copy the shell as-is
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
                # Create empty architecture scaffold
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


def split_all(
    modified_json_dir: str,
    json_source_dir: str,
    shells_dir: str,
    prefix_filter: str = "TobiPack_",
) -> dict[str, int]:
    """Split existing combined files and generate shells.

    This is a one-time migration helper. It reads the full combined files
    from *modified_json_dir*, extracts prefix_filter rows into
    *json_source_dir*, and generates vanilla-only shells in *shells_dir*.

    Args:
        modified_json_dir: Root containing the full combined files.
        json_source_dir: Where to write per-item files.
        shells_dir: Where to write shell templates.
        prefix_filter: Row name prefix to extract.

    Returns:
        Dict mapping table name → number of items extracted.
    """
    # File locations within modified_json_dir
    sources = {
        ("MoreBuildings", "DT_Constructions"): os.path.join(
            modified_json_dir, "Moria", "Content", "Tech", "Data", "Building", "DT_Constructions.json"
        ),
        ("MoreBuildings", "DT_ConstructionRecipes"): os.path.join(
            modified_json_dir, "Moria", "Content", "Tech", "Data", "Building", "DT_ConstructionRecipes.json"
        ),
        ("MoreArmor", "DT_ItemRecipes"): os.path.join(
            modified_json_dir, "Moria", "Content", "Tech", "Data", "Items", "DT_ItemRecipes.json"
        ),
    }

    results: dict[str, int] = {}

    for (mod_group, table_name), src_path in sources.items():
        if not os.path.isfile(src_path):
            log.warning("Source not found: %s", src_path)
            results[table_name] = 0
            continue

        has_imports = table_name == "DT_Constructions"
        out_dir = os.path.join(json_source_dir, mod_group, table_name)
        shell_path = os.path.join(shells_dir, mod_group, f"{table_name}.json")

        # Generate shell (strips prefix_filter rows)
        generate_shell(src_path, shell_path, prefix_filter, has_imports=has_imports)

        # Split rows into per-item files
        results[table_name] = split_dt_file(
            src_path, out_dir, prefix_filter, has_imports=has_imports
        )

    # Architecture shell — create an empty one since it doesn't exist in modified-json
    arch_shell_path = os.path.join(shells_dir, "MoreBuildings", "Architecture.json")
    if not os.path.isfile(arch_shell_path):
        empty_arch = {
            "$type": "UAssetAPI.UAsset, UAssetAPI",
            "Info": "Serialized with UAssetAPI",
            "NameMap": [],
            "Exports": [{
                "Table": {
                    "Value": []
                }
            }],
        }
        _save(arch_shell_path, empty_arch)
        log.info("Created empty Architecture shell: %s", arch_shell_path)

    results["Architecture"] = 0
    return results
