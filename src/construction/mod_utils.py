"""Construction recipe logic — refactored from RtoM-Moding-Tool modUtils.py.

All path construction uses explicit *saves_dir* and *data_dir* parameters
instead of relative ``../`` navigation.
"""

from __future__ import annotations

import copy
import logging
import os
from string import ascii_uppercase

from src.utils.json_handler import load_json, save_json

log = logging.getLogger(__name__)


def gen_unique_tag(base_tag: str, exports: list) -> str:
    """Return the first unused A-Z suffix for *base_tag*."""
    existing = {
        entry[0] for entry in exports
        if isinstance(entry, list) and len(entry) == 2
    }
    for letter in ascii_uppercase:
        candidate = f"{base_tag}_{letter}.Name"
        if candidate not in existing:
            return letter
    raise ValueError(
        f"Could not generate a unique name for '{base_tag}' (A-Z depleted)"
    )


def architecture_handle(
    tag: str, name: str, description: str, saves_dir: str
) -> str:
    """Add name/description entries to Architecture.json; return unique tag."""
    path = os.path.join(
        saves_dir, "newObjects", "MoreBuildings", "Architecture.json"
    )
    data = load_json(path)
    exports = data["Exports"][0]["Table"]["Value"]

    letter = gen_unique_tag(tag, exports)
    unique_tag = f"{tag}_{letter}"

    exports.append([f"{unique_tag}.Name", name])
    exports.append([f"{unique_tag}.Description", description])

    save_json(path, data)
    log.info("Architecture: added %s", unique_tag)
    return unique_tag


def dt_constructions_handle(
    unique_tag: str,
    asset_path: str,
    category_tag: str,
    saves_dir: str,
    data_dir: str,
    user_name: str,
) -> None:
    """Add a construction entry to DT_Constructions.json."""
    new_path = os.path.join(
        saves_dir, "newObjects", "MoreBuildings", "DT_Constructions.json"
    )
    template_path = os.path.join(
        data_dir, "MoreBuildings", "ConstructionTemplate.json"
    )
    import_template_path = os.path.join(
        data_dir, "MoreBuildings", "constructionsImportTemplates.json"
    )

    dt = load_json(new_path)
    template = load_json(template_path)
    import_template = load_json(import_template_path)

    blueprint = asset_path.split("/")[-1]
    texture_name = f"T_UI_BuildIcon_{unique_tag}"
    icon_path = f"/Game/Mods/{user_name}Pack/Constructions/Icons/{texture_name}"

    # Fill template
    template["Name"] = unique_tag
    template["Value"][0]["Value"] = f"{unique_tag}.Name"
    template["Value"][1]["Value"] = f"{unique_tag}.Description"
    template["Value"][3]["Value"]["AssetPath"]["AssetName"] = (
        f"{asset_path}.{blueprint}_C"
    )
    template["Value"][4]["Value"][0]["Value"][0]["Value"]["AssetPath"][
        "AssetName"
    ] = f"{asset_path}.{blueprint}_C"
    template["Value"][5]["Value"][0]["Value"].append(category_tag)

    pkg_loc = -1 - len(dt["Imports"])
    template["Value"][2]["Value"] = pkg_loc - 1

    dt["NameMap"].extend([
        unique_tag, asset_path, f"{asset_path}.{blueprint}_C",
        texture_name, icon_path,
    ])
    dt["Exports"][0]["Table"]["Data"].append(template)

    # Imports
    pkg_import = import_template["Package"].copy()
    pkg_import["ObjectName"] = icon_path

    tex_import = import_template["Texture2D"].copy()
    tex_import["ObjectName"] = texture_name
    tex_import["OuterIndex"] = pkg_loc

    dt["Imports"].append(pkg_import)
    dt["Imports"].append(tex_import)

    save_json(new_path, dt)
    log.info("DT_Constructions: added %s", unique_tag)


def dt_construction_recipes_handle(
    unique_tag: str,
    saves_dir: str,
    data_dir: str,
    category_tag: str,
    required_items: list,
    unlock_option: str,
    unlock_requirement: str,
) -> None:
    """Add a construction recipe entry to DT_ConstructionRecipes.json."""
    recipe_tpl = load_json(
        os.path.join(data_dir, "MoreBuildings", "ConstructionRecipeTemplate.json")
    )
    item_tpl = load_json(
        os.path.join(data_dir, "MoreBuildings", "ItemTemplate.json")
    )
    dummy = load_json(
        os.path.join(data_dir, "MoreBuildings", "DumyStructs.json")
    )
    flags_data = load_json(
        os.path.join(data_dir, "MoreBuildings", "CategoryFlags.json")
    )
    unlock_structs = load_json(
        os.path.join(data_dir, "MoreBuildings", "UnlockRequirementsStructs.json")
    )

    new_path = os.path.join(
        saves_dir, "newObjects", "MoreBuildings", "DT_ConstructionRecipes.json"
    )
    dt = load_json(new_path)
    dt["NameMap"].append(unique_tag)

    item_array = []
    for item_tag, count in required_items:
        new_item = copy.deepcopy(item_tpl)
        new_item["Value"][0]["Value"][0]["Value"] = item_tag
        new_item["Value"][2]["Value"] = count
        item_array.append(new_item)
        dt["NameMap"].append(item_tag)

    flags = flags_data.get(category_tag)
    if not flags and "." in category_tag:
        _, sub = category_tag.split(".", 1)
        flags = flags_data.get(sub)

    recipe_tpl["Name"] = unique_tag
    recipe_tpl["Value"][0]["Value"][0]["Value"] = unique_tag
    recipe_tpl["Value"][2]["Value"] = flags[0]
    recipe_tpl["Value"][3]["Value"] = flags[1]
    recipe_tpl["Value"][4]["Value"] = flags[2]
    recipe_tpl["Value"][5]["Value"] = flags[3]
    recipe_tpl["Value"][9]["Value"] = flags[4]
    recipe_tpl["Value"][10]["Value"] = flags[5]
    recipe_tpl["Value"][11]["Value"] = flags[6]
    recipe_tpl["Value"][16]["Value"] = item_array

    if unlock_option == "UnlockRequiredItems":
        req = unlock_structs["UnlockRequiredItems"].copy()
        req["Value"][0]["Value"][0]["Value"] = unlock_requirement
        recipe_tpl["Value"][20]["Value"][3] = req
        recipe_tpl["Value"][20]["Value"][4] = dummy["UnlockRequiredConstructions"]
    else:
        req = unlock_structs["UnlockRequiredConstructions"].copy()
        req["Value"][0]["Value"][0]["Value"] = unlock_requirement
        recipe_tpl["Value"][20]["Value"][3] = dummy["UnlockRequiredItems"]
        recipe_tpl["Value"][20]["Value"][4] = req

    dt["Exports"][0]["Table"]["Data"].append(recipe_tpl)
    save_json(new_path, dt)
    log.info("DT_ConstructionRecipes: added %s", unique_tag)


def advanced_bannister_post_stone_unlock() -> dict:
    """Return the unlock struct for Advanced_Bannister_Post_Stone."""
    return {
        "$type": "UAssetAPI.PropertyTypes.Objects.ArrayPropertyData, UAssetAPI",
        "ArrayType": "StructProperty",
        "Name": "UnlockRequiredItems",
        "ArrayIndex": 0,
        "IsZero": False,
        "PropertyTagFlags": "None",
        "PropertyTagExtensions": "NoExtension",
        "Value": [{
            "$type": "UAssetAPI.PropertyTypes.Structs.StructPropertyData, UAssetAPI",
            "StructType": "MorAnyItemRowHandle",
            "SerializeNone": True,
            "StructGUID": "{00000000-0000-0000-0000-000000000000}",
            "SerializationControl": "NoExtension",
            "Operation": "None",
            "Name": "UnlockRequiredItems",
            "ArrayIndex": 0,
            "IsZero": False,
            "PropertyTagFlags": "None",
            "PropertyTagExtensions": "NoExtension",
            "Value": [{
                "$type": "UAssetAPI.PropertyTypes.Objects.NamePropertyData, UAssetAPI",
                "Name": "RowName",
                "ArrayIndex": 0,
                "IsZero": False,
                "PropertyTagFlags": "None",
                "PropertyTagExtensions": "NoExtension",
                "Value": "Ore.Granite",
            }],
        }],
    }
