"""Armor recipe logic — refactored from RtoM-Moding-Tool armorModUtils.py.

All path construction uses explicit *saves_dir* and *data_dir* parameters.
"""

from __future__ import annotations

import copy
import logging
import os

from src.utils.json_handler import load_json, save_json

log = logging.getLogger(__name__)


def missing_armor_recipes(templates_dir: str, tobis_mod_dir: str, tobis_json_dir: str) -> list[dict]:
    """Return a list of ``{display_name: tag}`` dicts for armors without recipes."""
    dt_path = os.path.join(
        tobis_mod_dir, "UpdateMods", "MoreArmor", "DT_ItemRecipes.json"
    )
    armor_path = os.path.join(templates_dir, "MoreArmor", "Armor.json")

    dt = load_json(dt_path)
    armor = load_json(armor_path)

    recipe_names = {
        r.get("Name")
        for r in dt.get("Exports", [{}])[0].get("Table", {}).get("Data", [])
    }

    # Also check per-item files in Tobis_json
    js_dir = os.path.join(tobis_json_dir, "DT_ItemRecipes")
    per_item_names: set[str] = set()
    if os.path.isdir(js_dir):
        for fname in os.listdir(js_dir):
            if fname.endswith(".json"):
                per_item_names.add(fname[:-5])

    missing = []
    for tag, name in armor.items():
        if tag not in recipe_names and tag not in per_item_names:
            missing.append({name: tag})
    return missing


def dt_item_recipes_handle(
    tobis_json_dir: str,
    templates_dir: str,
    armor_tag: str,
    crafting_stations: list[str],
    materials: list[tuple[str, int]],
    unlock_option: str,
    unlock_requirement: str,
) -> None:
    """Write a per-item DT_ItemRecipes file for an armor recipe."""
    tpl = load_json(os.path.join(templates_dir, "MoreArmor", "ItemRecipeTemplate.json"))
    cs_tpl = load_json(os.path.join(templates_dir, "MoreArmor", "CraftingStationTemplate.json"))
    mat_tpl = load_json(os.path.join(templates_dir, "MoreArmor", "RequiredMaterialTemplate.json"))
    dummy = load_json(os.path.join(templates_dir, "MoreArmor", "DumyStructs.json"))
    unlock_structs = load_json(os.path.join(templates_dir, "MoreArmor", "UnlockRequirementsStructs.json"))

    tpl["Name"] = armor_tag
    tpl["Value"][0]["Value"][0]["Value"] = f"Armor.{armor_tag}"

    tpl["Value"][3]["Value"] = crafting_stations_array(crafting_stations, cs_tpl)
    tpl["Value"][8]["Value"] = crafting_materials_array(materials, mat_tpl)
    unlock_conditions(tpl, unlock_option, unlock_requirement, unlock_structs, dummy)

    item_data = {
        "NameMap": [armor_tag, f"Armor.{armor_tag}"],
        "Imports": [],
        "Row": tpl,
    }

    out_dir = os.path.join(tobis_json_dir, "DT_ItemRecipes")
    os.makedirs(out_dir, exist_ok=True)
    save_json(os.path.join(out_dir, f"{armor_tag}.json"), item_data)
    log.info("DT_ItemRecipes: added %s", armor_tag)


def crafting_stations_array(
    stations: list[str], template: dict
) -> list[dict]:
    """Build crafting-station array from tag list."""
    result = []
    for tag in stations:
        entry = copy.deepcopy(template)
        entry["Value"][0]["Value"] = tag
        result.append(entry)
    return result


def crafting_materials_array(
    materials: list[tuple[str, int]], template: dict
) -> list[dict]:
    """Build required-materials array."""
    result = []
    for tag, count in materials:
        entry = copy.deepcopy(template)
        entry["Value"][0]["Value"][0]["Value"] = tag
        entry["Value"][2]["Value"] = count
        result.append(entry)
    return result


def unlock_conditions(
    recipe_tpl: dict,
    option: str,
    requirement: str,
    unlock_structs: dict,
    dummy_structs: dict,
) -> None:
    """Set unlock conditions on an item recipe template in-place."""
    if option == "UnlockRequiredItems":
        req = copy.deepcopy(unlock_structs["UnlockRequiredItems"])
        req["Value"][0]["Value"][0]["Value"] = requirement
        recipe_tpl["Value"][12]["Value"][3] = req
        recipe_tpl["Value"][12]["Value"][4] = dummy_structs["UnlockRequiredConstructions"]
    else:
        req = copy.deepcopy(unlock_structs["UnlockRequiredConstructions"])
        req["Value"][0]["Value"][0]["Value"] = requirement
        recipe_tpl["Value"][12]["Value"][3] = dummy_structs["UnlockRequiredItems"]
        recipe_tpl["Value"][12]["Value"][4] = req


def sandbox_exclusive_items() -> list[dict]:
    """Return the hardcoded list of sandbox-exclusive items."""
    return [
        {"Tag": "Spear_1h_t1_TU2", "UnlockOption": "UnlockRequiredConstructions", "UnlockRequirement": "CraftingStation_BasicForge"},
        {"Tag": "WarAxe_1h_t2", "UnlockOption": "UnlockRequiredConstructions", "UnlockRequirement": "CraftingStation_FurnaceUpgrade"},
        {"Tag": "WarAxe_1h_t3", "UnlockOption": "UnlockRequiredConstructions", "UnlockRequirement": "CraftingStation_FloodedForge"},
        {"Tag": "Battleaxe_2h_t2", "UnlockOption": "UnlockRequiredConstructions", "UnlockRequirement": "CraftingStation_ForgeUpgrade_GemCutter"},
        {"Tag": "Halberd_2h_t2", "UnlockOption": "UnlockRequiredConstructions", "UnlockRequirement": "CraftingStation_AdvancedForge"},
        {"Tag": "Sword_2h_t2", "UnlockOption": "UnlockRequiredConstructions", "UnlockRequirement": "CraftingStation_AdvancedForge"},
        {"Tag": "Battleaxe_2h_t4", "UnlockOption": "UnlockRequiredConstructions", "UnlockRequirement": "CraftingStation_MithrilForge"},
        {"Tag": "FamousElvenSword", "UnlockOption": "UnlockRequiredConstructions", "UnlockRequirement": "CraftingStation_LegendayElvishForge"},
        {"Tag": "Amazing_Set_HelmetArmor", "UnlockOption": "UnlockRequiredItems", "UnlockRequirement": "Item.Hide"},
        {"Tag": "Wonderful_Set_HelmetArmor", "UnlockOption": "UnlockRequiredItems", "UnlockRequirement": "Item.Hide"},
        {"Tag": "SouthernmostFireProof_Set_HelmetArmor", "UnlockOption": "UnlockRequiredItems", "UnlockRequirement": "Item.Hide"},
        {"Tag": "BlueMountainsHunter_Set_TorsoArmor", "UnlockOption": "UnlockRequiredItems", "UnlockRequirement": "Item.Hide"},
        {"Tag": "BlueMountainsHunter_Set_BootsArmor", "UnlockOption": "UnlockRequiredItems", "UnlockRequirement": "Item.Hide"},
        {"Tag": "RangeBonus_Set_GlovesArmor", "UnlockOption": "UnlockRequiredItems", "UnlockRequirement": "Item.Hide"},
        {"Tag": "BowmansGloves", "UnlockOption": "UnlockRequiredItems", "UnlockRequirement": "Item.Hide"},
        {"Tag": "AntiColdTorso", "UnlockOption": "UnlockRequiredItems", "UnlockRequirement": "Item.BoltsOfCloth"},
        {"Tag": "AntiColdBoots", "UnlockOption": "UnlockRequiredItems", "UnlockRequirement": "Item.BoltsOfCloth"},
        {"Tag": "AntiColdGloves", "UnlockOption": "UnlockRequiredItems", "UnlockRequirement": "Item.BoltsOfCloth"},
        {"Tag": "AntiColdHelm", "UnlockOption": "UnlockRequiredItems", "UnlockRequirement": "Item.BoltsOfCloth"},
        {"Tag": "Nogrod_Set_TorsoArmor", "UnlockOption": "UnlockRequiredConstructions", "UnlockRequirement": "CraftingStation_NogrodForge"},
        {"Tag": "Nogrod_Set_GlovesArmor", "UnlockOption": "UnlockRequiredConstructions", "UnlockRequirement": "CraftingStation_NogrodForge"},
    ]
