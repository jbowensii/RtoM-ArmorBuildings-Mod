#!/usr/bin/env python3
"""Generate blank templates and extract unique field values for autocomplete.

Part 1: Creates data/templates/generated/{table}_template.json
Part 2: Creates data/field_values/{table}_fields.json
"""

import json
import os
import sys
import copy
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parent.parent
TOBIS = ROOT / "data" / "Tobis_json"
VANILLA_BASE = ROOT / "data" / "game_extract" / "uassetgui"

# ── Table configs ──────────────────────────────────────────────────────────
TEMPLATE_TABLES = ["DT_Weapons", "DT_Tools", "DT_Items", "DT_Loot", "DT_Ores", "DT_Armor"]

FIELD_TABLES = [
    "DT_Armor", "DT_Weapons", "DT_Tools", "DT_Items",
    "DT_Loot", "DT_Ores", "DT_ItemRecipes",
]

VANILLA_PATHS = {
    "DT_Armor":       "Moria/Content/Tech/Data/Items/DT_Armor",
    "DT_Weapons":     "Moria/Content/Tech/Data/Items/DT_Weapons",
    "DT_Tools":       "Moria/Content/Tech/Data/Items/DT_Tools",
    "DT_Items":       "Moria/Content/Tech/Data/Items/DT_Items",
    "DT_Loot":        "Moria/Content/Character/AI/DT_Loot",
    "DT_Ores":        "Moria/Content/Tech/Data/Items/DT_Ores",
    "DT_ItemRecipes": "Moria/Content/Tech/Data/Items/DT_ItemRecipes",
}


# ── Helpers ────────────────────────────────────────────────────────────────

def load_per_item_row(filepath):
    """Load a per-item JSON and return the Row dict."""
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["Row"]


def load_vanilla_rows(table):
    """Load all rows from the vanilla game extract for a table."""
    vpath = VANILLA_BASE / (VANILLA_PATHS[table] + ".json")
    if not vpath.exists():
        print(f"  WARNING: vanilla file not found: {vpath}")
        return []
    with open(vpath, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["Exports"][0]["Table"]["Data"]


def get_first_row(table):
    """Get first available row: prefer per-item file, fall back to vanilla."""
    tobis_dir = TOBIS / table
    if tobis_dir.is_dir():
        files = sorted(tobis_dir.glob("*.json"))
        if files:
            print(f"  Using per-item file: {files[0].name}")
            return load_per_item_row(files[0])
    # Fall back to vanilla
    rows = load_vanilla_rows(table)
    if rows:
        print(f"  Using vanilla row: {rows[0].get('Name', '?')}")
        return rows[0]
    return None


# ── Part 1: Template generation ───────────────────────────────────────────

def blank_value(entry):
    """Recursively blank a field entry, keeping $type and structural fields."""
    entry = copy.deepcopy(entry)
    dtype = entry.get("$type", "")

    if "IntPropertyData" in dtype:
        entry["Value"] = 0
    elif "FloatPropertyData" in dtype:
        entry["Value"] = 0.0
    elif "BoolPropertyData" in dtype:
        entry["Value"] = False
    elif "EnumPropertyData" in dtype:
        entry["Value"] = ""
    elif "TextPropertyData" in dtype:
        entry["Value"] = ""
        # Also blank text-specific fields
        for k in ["TableId", "CultureInvariantString", "SourceFmt", "SourceValue",
                   "TargetCulture", "Namespace"]:
            if k in entry:
                entry[k] = ""
    elif "NamePropertyData" in dtype:
        entry["Value"] = ""
    elif "SoftObjectPropertyData" in dtype:
        if isinstance(entry.get("Value"), dict):
            ap = entry["Value"].get("AssetPath", {})
            if "AssetName" in ap:
                ap["AssetName"] = ""
            if "PackageName" in ap:
                ap["PackageName"] = ""
            if "SubPathString" in entry["Value"]:
                entry["Value"]["SubPathString"] = ""
        else:
            entry["Value"] = ""
    elif "ObjectPropertyData" in dtype:
        entry["Value"] = 0
    elif "ArrayPropertyData" in dtype:
        entry["Value"] = []
    elif "MapPropertyData" in dtype:
        entry["Value"] = []
        if "KeysToRemove" in entry:
            entry["KeysToRemove"] = []
    elif "StructPropertyData" in dtype:
        # Recurse into struct's Value array
        if isinstance(entry.get("Value"), list):
            entry["Value"] = [blank_value(v) for v in entry["Value"]]
    elif "GameplayTagContainerPropertyData" in dtype:
        entry["Value"] = []
    else:
        # Unknown type — try to blank Value if present
        if "Value" in entry:
            v = entry["Value"]
            if isinstance(v, str):
                entry["Value"] = ""
            elif isinstance(v, bool):
                entry["Value"] = False
            elif isinstance(v, int):
                entry["Value"] = 0
            elif isinstance(v, float):
                entry["Value"] = 0.0
            elif isinstance(v, list):
                entry["Value"] = []

    return entry


def make_template(row):
    """Create a blank template from a row."""
    template = copy.deepcopy(row)
    # Blank the row name
    template["Name"] = ""
    # Blank each field in Value
    if isinstance(template.get("Value"), list):
        template["Value"] = [blank_value(v) for v in template["Value"]]
    return template


def generate_templates():
    """Part 1: Generate template files."""
    out_dir = ROOT / "data" / "templates" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    print("=" * 60)
    print("PART 1: Generating templates")
    print("=" * 60)

    for table in TEMPLATE_TABLES:
        print(f"\n{table}:")
        row = get_first_row(table)
        if row is None:
            print(f"  SKIPPED — no data found")
            continue
        template = make_template(row)
        outpath = out_dir / f"{table}_template.json"
        with open(outpath, "w", encoding="utf-8") as f:
            json.dump(template, f, indent=4, ensure_ascii=False)
        # Count fields
        n_fields = len(template.get("Value", []))
        print(f"  -> {outpath.relative_to(ROOT)}  ({n_fields} fields)")


# ── Part 2: Field value extraction ────────────────────────────────────────

def classify_type(dtype):
    """Map a $type string to a short type label."""
    if "EnumPropertyData" in dtype:
        return "enum"
    if "BoolPropertyData" in dtype:
        return "bool"
    if "SoftObjectPropertyData" in dtype:
        return "asset"
    if "TextPropertyData" in dtype:
        return "text"
    if "IntPropertyData" in dtype:
        return "int"
    if "FloatPropertyData" in dtype:
        return "float"
    if "NamePropertyData" in dtype:
        return "name"
    if "ObjectPropertyData" in dtype:
        return "object"
    if "GameplayTagContainerPropertyData" in dtype:
        return "tags"
    if "ArrayPropertyData" in dtype:
        return "array"
    if "StructPropertyData" in dtype:
        return "struct"
    if "MapPropertyData" in dtype:
        return "map"
    return "unknown"


def extract_field_values(entry, prefix="", result=None):
    """Extract field values from an entry, recursing into arrays/structs.

    Returns dict of {field_name: {"type": ..., "values": set(...)}}
    """
    if result is None:
        result = {}

    dtype = entry.get("$type", "")
    name = entry.get("Name", "")
    field_key = f"{prefix}{name}" if prefix else name
    short_type = classify_type(dtype)

    if "EnumPropertyData" in dtype:
        val = entry.get("Value", "")
        if val and val != "None":
            result.setdefault(field_key, {"type": "enum", "values": set()})
            result[field_key]["values"].add(str(val))

    elif "BoolPropertyData" in dtype:
        val = entry.get("Value", False)
        result.setdefault(field_key, {"type": "bool", "values": set()})
        result[field_key]["values"].add(str(val).lower())

    elif "SoftObjectPropertyData" in dtype:
        val = entry.get("Value")
        if isinstance(val, dict):
            ap = val.get("AssetPath", {})
            asset_name = ap.get("AssetName", "")
            if asset_name and asset_name != "None":
                result.setdefault(field_key, {"type": "asset", "values": set()})
                result[field_key]["values"].add(asset_name)
        elif isinstance(val, str) and val and val != "None":
            result.setdefault(field_key, {"type": "asset", "values": set()})
            result[field_key]["values"].add(val)

    elif "TextPropertyData" in dtype:
        val = entry.get("Value", "")
        if val and val != "None":
            result.setdefault(field_key, {"type": "text", "values": set()})
            result[field_key]["values"].add(str(val))

    elif "IntPropertyData" in dtype:
        val = entry.get("Value", 0)
        result.setdefault(field_key, {"type": "int", "values": set()})
        result[field_key]["values"].add(str(val))

    elif "FloatPropertyData" in dtype:
        val = entry.get("Value", 0.0)
        result.setdefault(field_key, {"type": "float", "values": set()})
        result[field_key]["values"].add(str(val))

    elif "NamePropertyData" in dtype:
        val = entry.get("Value", "")
        if val and val != "None":
            result.setdefault(field_key, {"type": "name", "values": set()})
            result[field_key]["values"].add(str(val))

    elif "ObjectPropertyData" in dtype:
        val = entry.get("Value", 0)
        result.setdefault(field_key, {"type": "object", "values": set()})
        result[field_key]["values"].add(str(val))

    elif "GameplayTagContainerPropertyData" in dtype:
        vals = entry.get("Value", [])
        if vals:
            result.setdefault(field_key, {"type": "tags", "values": set()})
            for tag in vals:
                if isinstance(tag, str) and tag:
                    result[field_key]["values"].add(tag)

    elif "ArrayPropertyData" in dtype:
        arr = entry.get("Value", [])
        for item in arr:
            if isinstance(item, dict):
                item_type = item.get("$type", "")
                if "StructPropertyData" in item_type:
                    # Recurse into struct children with dotted prefix
                    sub_vals = item.get("Value", [])
                    if isinstance(sub_vals, list):
                        for sub in sub_vals:
                            if isinstance(sub, dict):
                                extract_field_values(sub, prefix=f"{field_key}.", result=result)
                else:
                    # Non-struct array items (e.g., ObjectPropertyData in EquipEffects)
                    extract_field_values(item, prefix=f"{field_key}.", result=result)

    elif "StructPropertyData" in dtype:
        struct_type = entry.get("StructType", "")
        if struct_type == "GameplayTagContainer":
            # Tags container — extract tags from first child
            sub_vals = entry.get("Value", [])
            if isinstance(sub_vals, list):
                for sub in sub_vals:
                    if isinstance(sub, dict) and "GameplayTagContainerPropertyData" in sub.get("$type", ""):
                        tags = sub.get("Value", [])
                        if tags:
                            result.setdefault(field_key, {"type": "tags", "values": set()})
                            for tag in tags:
                                if isinstance(tag, str) and tag:
                                    result[field_key]["values"].add(tag)
        else:
            # Generic struct — recurse into children with dotted prefix
            sub_vals = entry.get("Value", [])
            if isinstance(sub_vals, list):
                for sub in sub_vals:
                    if isinstance(sub, dict):
                        extract_field_values(sub, prefix=f"{field_key}.", result=result)

    elif "MapPropertyData" in dtype:
        # Maps are complex; just note the field exists
        result.setdefault(field_key, {"type": "map", "values": set()})

    return result


def process_row_values(row, result):
    """Process a single row's Value array."""
    vals = row.get("Value", [])
    if not isinstance(vals, list):
        return
    for entry in vals:
        if isinstance(entry, dict):
            extract_field_values(entry, result=result)


def extract_fields():
    """Part 2: Extract field values for autocomplete."""
    out_dir = ROOT / "data" / "field_values"
    out_dir.mkdir(parents=True, exist_ok=True)
    print("\n" + "=" * 60)
    print("PART 2: Extracting field values for autocomplete")
    print("=" * 60)

    for table in FIELD_TABLES:
        print(f"\n{table}:")
        result = {}
        row_count = 0

        # 1. Per-item files
        tobis_dir = TOBIS / table
        if tobis_dir.is_dir():
            files = sorted(tobis_dir.glob("*.json"))
            for fp in files:
                try:
                    row = load_per_item_row(fp)
                    process_row_values(row, result)
                    row_count += 1
                except Exception as e:
                    print(f"  WARNING: error in {fp.name}: {e}")
            print(f"  Per-item files: {len(files)}")
        else:
            print(f"  Per-item files: 0 (no directory)")

        # 2. Vanilla extract
        if table in VANILLA_PATHS:
            rows = load_vanilla_rows(table)
            for row in rows:
                process_row_values(row, result)
                row_count += 1
            print(f"  Vanilla rows: {len(rows)}")

        print(f"  Total rows scanned: {row_count}")

        # Convert sets to sorted lists
        output = {}
        for field_name in sorted(result.keys()):
            info = result[field_name]
            vals = sorted(info["values"], key=lambda x: (x.lower() if isinstance(x, str) else x))
            output[field_name] = {
                "type": info["type"],
                "values": vals,
            }

        outpath = out_dir / f"{table}_fields.json"
        with open(outpath, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        print(f"  Fields found: {len(output)}")
        # Print field summary
        for fname, finfo in output.items():
            print(f"    {fname} ({finfo['type']}): {len(finfo['values'])} unique values")


# ── Main ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    generate_templates()
    extract_fields()
    print("\n" + "=" * 60)
    print("DONE")
    print("=" * 60)
