#!/usr/bin/env python3
"""Scan all per-item JSON files and vanilla extract to collect unique field values."""

import json
import os
from pathlib import Path
from collections import defaultdict

BASE = Path(r"c:/Users/johnb/OneDrive/Documents/Projects/RtoM-ArmorBuildings-Mod")

# Source directories
SOURCES = {
    "DT_Constructions": {
        "per_item_dir": BASE / "data/Tobis_json/DT_Constructions",
        "vanilla_file": BASE / "data/game_extract/uassetgui/Moria/Content/Tech/Data/Building/DT_Constructions.json",
        "output_file": BASE / "data/field_values/DT_Constructions_fields.json",
    },
    "DT_ConstructionRecipes": {
        "per_item_dir": BASE / "data/Tobis_json/DT_ConstructionRecipes",
        "vanilla_file": BASE / "data/game_extract/uassetgui/Moria/Content/Tech/Data/Building/DT_ConstructionRecipes.json",
        "output_file": BASE / "data/field_values/DT_ConstructionRecipes_fields.json",
    },
}


def classify_type(type_str):
    """Map $type string to a simple type label."""
    if "EnumPropertyData" in type_str:
        return "enum"
    if "BoolPropertyData" in type_str:
        return "bool"
    if "SoftObjectPropertyData" in type_str:
        return "asset"
    if "TextPropertyData" in type_str:
        return "text"
    if "ObjectPropertyData" in type_str:
        return "object"
    if "ArrayPropertyData" in type_str:
        return "array"
    if "FloatPropertyData" in type_str:
        return "float"
    if "IntPropertyData" in type_str:
        return "int"
    if "GameplayTagContainerPropertyData" in type_str:
        return "tags"
    if "StructPropertyData" in type_str:
        return "struct"
    if "NamePropertyData" in type_str:
        return "name"
    return "unknown"


def extract_material_rownames(material_entries):
    """Extract MaterialHandle RowName values from DefaultRequiredMaterials entries."""
    rownames = []
    for entry in material_entries:
        if not isinstance(entry, dict):
            continue
        # Each entry is a MorRequiredRecipeMaterial struct with Value array
        for sub_field in entry.get("Value", []):
            if not isinstance(sub_field, dict):
                continue
            if sub_field.get("Name") == "MaterialHandle":
                # MaterialHandle is a struct with Value containing RowName
                for inner in sub_field.get("Value", []):
                    if isinstance(inner, dict) and inner.get("Name") == "RowName":
                        val = inner.get("Value")
                        if val and val != "None":
                            rownames.append(str(val))
            elif sub_field.get("Name") == "WildcardHandle":
                for inner in sub_field.get("Value", []):
                    if isinstance(inner, dict) and inner.get("Name") == "RowName":
                        val = inner.get("Value")
                        if val and val != "None":
                            rownames.append(f"Wildcard:{val}")
            elif sub_field.get("Name") == "Count":
                # We collect count values too
                rownames.append(f"Count:{sub_field.get('Value')}")
    return rownames


def extract_unlock_values(unlock_struct_value):
    """Extract values from a DefaultUnlocks/SandboxUnlocks struct Value array."""
    results = {"UnlockType": [], "UnlockRequiredItems": [], "NumFragments": [],
               "UnlockRequiredFragments": [], "UnlockRequiredConstructions": []}
    for field in unlock_struct_value:
        if not isinstance(field, dict):
            continue
        name = field.get("Name", "")
        if name == "UnlockType":
            val = field.get("Value")
            if val:
                results["UnlockType"].append(str(val))
        elif name == "NumFragments":
            val = field.get("Value")
            if val is not None:
                results["NumFragments"].append(val)
        elif name == "UnlockRequiredItems":
            for item_struct in field.get("Value", []):
                if isinstance(item_struct, dict):
                    for inner in item_struct.get("Value", []):
                        if isinstance(inner, dict) and inner.get("Name") == "RowName":
                            val = inner.get("Value")
                            if val and val != "None":
                                results["UnlockRequiredItems"].append(str(val))
        elif name == "UnlockRequiredFragments":
            for item_struct in field.get("Value", []):
                if isinstance(item_struct, dict):
                    for inner in item_struct.get("Value", []):
                        if isinstance(inner, dict) and inner.get("Name") == "RowName":
                            val = inner.get("Value")
                            if val and val != "None":
                                results["UnlockRequiredFragments"].append(str(val))
        elif name == "UnlockRequiredConstructions":
            for item_struct in field.get("Value", []):
                if isinstance(item_struct, dict):
                    for inner in item_struct.get("Value", []):
                        if isinstance(inner, dict) and inner.get("Name") == "RowName":
                            val = inner.get("Value")
                            if val and val != "None":
                                results["UnlockRequiredConstructions"].append(str(val))
    return results


def extract_handle_rownames(entries):
    """Extract RowName values from handle struct arrays (RequiredConstructions, etc.)."""
    rownames = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        for inner in entry.get("Value", []):
            if isinstance(inner, dict) and inner.get("Name") == "RowName":
                val = inner.get("Value")
                if val and val != "None":
                    rownames.append(str(val))
    return rownames


def process_field(field, fields_data):
    """Process a single field from a row's Value array, adding to fields_data."""
    if not isinstance(field, dict):
        return

    type_str = field.get("$type", "")
    name = field.get("Name", "")
    simple_type = classify_type(type_str)

    if not name:
        return

    # Handle special struct types that wrap other data
    if simple_type == "struct":
        struct_type = field.get("StructType", "")

        # GameplayTagContainer (e.g., Tags field)
        if struct_type == "GameplayTagContainer":
            if name not in fields_data:
                fields_data[name] = {"type": "tags", "values": set()}
            for inner in field.get("Value", []):
                if isinstance(inner, dict) and "GameplayTagContainerPropertyData" in inner.get("$type", ""):
                    for tag in inner.get("Value", []):
                        if tag:
                            fields_data[name]["values"].add(str(tag))
            return

        # DefaultUnlocks / SandboxUnlocks - unlock struct
        if struct_type == "MorRecipeUnlock" and name in ("DefaultUnlocks", "SandboxUnlocks"):
            prefix = name
            unlock_vals = extract_unlock_values(field.get("Value", []))
            for sub_name, vals in unlock_vals.items():
                key = f"{prefix}.{sub_name}"
                if key not in fields_data:
                    if sub_name == "UnlockType":
                        fields_data[key] = {"type": "enum", "values": set()}
                    elif sub_name == "NumFragments":
                        fields_data[key] = {"type": "int", "values": set()}
                    else:
                        fields_data[key] = {"type": "name", "values": set()}
                for v in vals:
                    fields_data[key]["values"].add(str(v))
            return

        # Handle row handles (ResultConstructionHandle, etc.)
        if struct_type in ("MorConstructionRowHandle", "MorAnyItemRowHandle",
                           "MorCategoryTagRowHandle", "MorRecipeFragmentRowHandle"):
            if name not in fields_data:
                fields_data[name] = {"type": "handle", "values": set()}
            for inner in field.get("Value", []):
                if isinstance(inner, dict) and inner.get("Name") == "RowName":
                    val = inner.get("Value")
                    if val and val != "None":
                        fields_data[name]["values"].add(str(val))
            return

        # Generic struct - skip (or recurse into it)
        return

    # EnumPropertyData
    if simple_type == "enum":
        if name not in fields_data:
            fields_data[name] = {"type": "enum", "values": set()}
        val = field.get("Value")
        if val:
            fields_data[name]["values"].add(str(val))
        return

    # BoolPropertyData
    if simple_type == "bool":
        if name not in fields_data:
            fields_data[name] = {"type": "bool", "values": set()}
        val = field.get("Value")
        fields_data[name]["values"].add(str(val).lower())
        return

    # SoftObjectPropertyData
    if simple_type == "asset":
        if name not in fields_data:
            fields_data[name] = {"type": "asset", "values": set()}
        val = field.get("Value")
        if isinstance(val, dict):
            asset_path = val.get("AssetPath", {})
            asset_name = asset_path.get("AssetName", "")
            if asset_name:
                fields_data[name]["values"].add(asset_name)
        return

    # TextPropertyData
    if simple_type == "text":
        if name not in fields_data:
            fields_data[name] = {"type": "text", "values": set()}
        val = field.get("Value")
        if val:
            fields_data[name]["values"].add(str(val))
        # Also collect TableId if present
        table_id = field.get("TableId")
        if table_id:
            key = f"{name}.TableId"
            if key not in fields_data:
                fields_data[key] = {"type": "text", "values": set()}
            fields_data[key]["values"].add(str(table_id))
        return

    # ObjectPropertyData
    if simple_type == "object":
        if name not in fields_data:
            fields_data[name] = {"type": "object", "values": set()}
        val = field.get("Value")
        if val is not None:
            fields_data[name]["values"].add(str(val))
        return

    # FloatPropertyData
    if simple_type == "float":
        if name not in fields_data:
            fields_data[name] = {"type": "float", "values": set()}
        val = field.get("Value")
        if val is not None:
            fields_data[name]["values"].add(str(val))
        return

    # IntPropertyData
    if simple_type == "int":
        if name not in fields_data:
            fields_data[name] = {"type": "int", "values": set()}
        val = field.get("Value")
        if val is not None:
            fields_data[name]["values"].add(str(val))
        return

    # ArrayPropertyData
    if simple_type == "array":
        arr_name = name
        arr_values = field.get("Value", [])

        # DefaultRequiredMaterials / SandboxRequiredMaterials
        if arr_name in ("DefaultRequiredMaterials", "SandboxRequiredMaterials"):
            key_mat = f"{arr_name}.MaterialHandle"
            key_wild = f"{arr_name}.WildcardHandle"
            key_count = f"{arr_name}.Count"
            if key_mat not in fields_data:
                fields_data[key_mat] = {"type": "name", "values": set()}
            if key_wild not in fields_data:
                fields_data[key_wild] = {"type": "name", "values": set()}
            if key_count not in fields_data:
                fields_data[key_count] = {"type": "int", "values": set()}
            for entry in arr_values:
                if not isinstance(entry, dict):
                    continue
                for sub_field in entry.get("Value", []):
                    if not isinstance(sub_field, dict):
                        continue
                    if sub_field.get("Name") == "MaterialHandle":
                        for inner in sub_field.get("Value", []):
                            if isinstance(inner, dict) and inner.get("Name") == "RowName":
                                val = inner.get("Value")
                                if val and val != "None":
                                    fields_data[key_mat]["values"].add(str(val))
                    elif sub_field.get("Name") == "WildcardHandle":
                        for inner in sub_field.get("Value", []):
                            if isinstance(inner, dict) and inner.get("Name") == "RowName":
                                val = inner.get("Value")
                                if val and val != "None":
                                    fields_data[key_wild]["values"].add(str(val))
                    elif sub_field.get("Name") == "Count":
                        val = sub_field.get("Value")
                        if val is not None:
                            fields_data[key_count]["values"].add(str(val))
            return

        # DefaultRequiredConstructions / SandboxRequiredConstructions
        if arr_name in ("DefaultRequiredConstructions", "SandboxRequiredConstructions"):
            if arr_name not in fields_data:
                fields_data[arr_name] = {"type": "name", "values": set()}
            for rn in extract_handle_rownames(arr_values):
                fields_data[arr_name]["values"].add(rn)
            return

        # BackwardCompatibilityActors - array of SoftObjectPath structs
        if arr_name == "BackwardCompatibilityActors":
            if arr_name not in fields_data:
                fields_data[arr_name] = {"type": "asset", "values": set()}
            for entry in arr_values:
                if not isinstance(entry, dict):
                    continue
                for inner in entry.get("Value", []):
                    if isinstance(inner, dict):
                        val = inner.get("Value")
                        if isinstance(val, dict):
                            asset_name = val.get("AssetPath", {}).get("AssetName", "")
                            if asset_name:
                                fields_data[arr_name]["values"].add(asset_name)
            return

        # Generic array - just note it exists
        if arr_name not in fields_data:
            fields_data[arr_name] = {"type": "array", "values": set()}
        fields_data[arr_name]["values"].add(f"[{len(arr_values)} entries]")
        return

    # GameplayTagContainerPropertyData (can appear directly)
    if simple_type == "tags":
        if name not in fields_data:
            fields_data[name] = {"type": "tags", "values": set()}
        for tag in field.get("Value", []):
            if tag:
                fields_data[name]["values"].add(str(tag))
        return

    # NamePropertyData
    if simple_type == "name":
        if name not in fields_data:
            fields_data[name] = {"type": "name", "values": set()}
        val = field.get("Value")
        if val and val != "None":
            fields_data[name]["values"].add(str(val))
        return


def process_row(row_value, fields_data):
    """Process a single row's Value array."""
    if not isinstance(row_value, list):
        return
    for field in row_value:
        process_field(field, fields_data)


def process_per_item_dir(directory, fields_data):
    """Process all per-item JSON files in a directory."""
    count = 0
    for json_file in sorted(directory.glob("*.json")):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            row = data.get("Row", {})
            row_value = row.get("Value", [])
            process_row(row_value, fields_data)
            count += 1
        except Exception as e:
            print(f"  ERROR processing {json_file.name}: {e}")
    return count


def process_vanilla_extract(vanilla_file, fields_data):
    """Process a vanilla game extract DataTable JSON."""
    count = 0
    try:
        with open(vanilla_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Structure: Exports[0].Table.Data = [row1, row2, ...]
        exports = data.get("Exports", [])
        for export in exports:
            table = export.get("Table", {})
            rows = table.get("Data", [])
            for row in rows:
                row_value = row.get("Value", [])
                process_row(row_value, fields_data)
                count += 1
    except Exception as e:
        print(f"  ERROR processing vanilla file {vanilla_file}: {e}")
    return count


def main():
    output_dir = BASE / "data/field_values"
    output_dir.mkdir(parents=True, exist_ok=True)

    for table_name, sources in SOURCES.items():
        print(f"\n{'='*60}")
        print(f"Processing: {table_name}")
        print(f"{'='*60}")

        fields_data = {}

        # Process per-item files
        per_item_dir = sources["per_item_dir"]
        if per_item_dir.exists():
            count = process_per_item_dir(per_item_dir, fields_data)
            print(f"  Per-item files processed: {count}")
        else:
            print(f"  WARNING: Per-item directory not found: {per_item_dir}")

        # Process vanilla extract
        vanilla_file = sources["vanilla_file"]
        if vanilla_file.exists():
            count = process_vanilla_extract(vanilla_file, fields_data)
            print(f"  Vanilla rows processed: {count}")
        else:
            print(f"  WARNING: Vanilla file not found: {vanilla_file}")

        # Convert sets to sorted lists for JSON output
        output = {}
        for field_name in sorted(fields_data.keys()):
            info = fields_data[field_name]
            sorted_values = sorted(info["values"], key=lambda x: (x.replace("-", "").replace(".", "0") if x.lstrip("-").replace(".", "").isdigit() else x))
            output[field_name] = {
                "type": info["type"],
                "values": sorted_values,
            }

        # Write output
        output_file = sources["output_file"]
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        print(f"  Output written to: {output_file}")

        # Print summary
        print(f"\n  {'Field Name':<45} {'Type':<8} {'# Values'}")
        print(f"  {'-'*45} {'-'*8} {'-'*8}")
        for field_name in sorted(output.keys()):
            info = output[field_name]
            print(f"  {field_name:<45} {info['type']:<8} {len(info['values'])}")

        # Print detailed values for key fields
        print(f"\n  --- Detailed values ---")
        for field_name in sorted(output.keys()):
            info = output[field_name]
            vals = info["values"]
            if len(vals) <= 30:
                print(f"\n  {field_name} ({info['type']}, {len(vals)} values):")
                for v in vals:
                    print(f"    - {v}")
            else:
                print(f"\n  {field_name} ({info['type']}, {len(vals)} values): [showing first 15]")
                for v in vals[:15]:
                    print(f"    - {v}")
                print(f"    ... and {len(vals) - 15} more")


if __name__ == "__main__":
    main()
