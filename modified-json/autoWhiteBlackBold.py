"""
autoWhiteBlackBold.py — Auto-link colour-variant armour recipes to their
                        base recipe for discovery-based unlocking.

Workflow
--------
The game has a recipe unlock type called "DiscoverDependencies" which
means a colour variant (e.g. Khazad_White_Chest) automatically unlocks
when the player discovers the base item (Khazad_Chest).  Setting this
up manually for every _White_, _Black_, and _Gold_ variant is tedious
and error-prone, so this script automates it:

1. Load DT_ItemRecipes.json — the master recipe data-table exported
   from UAssetGUI in UAssetAPI JSON format.
2. Load the UnlockRequiredItems.json template — a small JSON snippet
   that defines the "required recipe" dependency structure.
3. For every recipe whose item name contains _White_, _Black_, or
   _Gold_:
   a. Derive the base item name by stripping the colour tag.
   b. Change UnlockType from Manual → DiscoverDependencies.
   c. Insert a deep-copy of the template with the base item name so
      the game knows *which* recipe to depend on.
4. Save the modified DT_ItemRecipes.json back to disk.

Note: The JSON structure uses numeric array indices because UAssetAPI
serialises UE4 DataTable properties as ordered arrays, not named
fields.  Index positions are stable for a given game version but may
shift after a game update — check the export if things break.
"""

import copy
import json
import os
import re
import sys

# ── Add project root to path so we can import the shared config loader ──
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config_loader import cfg

# ── Colour tags that identify variant recipes ──
COLOUR_TAGS = ["_White_", "_Black_", "_Gold_"]


def clean_name(name: str) -> str:
    """Strip colour tags to get the base item name.

    Example: 'Khazad_White_Chest' → 'Khazad_Chest'
    """
    return re.sub(r"_(White|Black|Gold)_", "_", name)


def main():
    # ── Resolve file paths from config ──
    recipes_path = cfg.path(
        "modified-json", "Moria", "Content", "Tech", "Data", "Items",
        "DT_ItemRecipes.json",
    )
    template_path = cfg.path("modified-json", "UnlockRequiredItems.json")

    # ── Validate inputs ──
    for label, path in [("Recipes", recipes_path), ("Template", template_path)]:
        if not os.path.isfile(path):
            print(f"[ERROR] {label} file not found: {path}", file=sys.stderr)
            sys.exit(1)

    # ─────────────────────────────────────────────────────────────────
    # Step 1: Load the master recipe table and the dependency template.
    # ─────────────────────────────────────────────────────────────────
    with open(recipes_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    with open(template_path, "r", encoding="utf-8") as f:
        template_obj = json.load(f)

    # Navigate to the DataTable rows inside the UAssetAPI export
    exports = data.get("Exports", [])
    if not exports:
        print("[ERROR] No 'Exports' found in recipe JSON.", file=sys.stderr)
        sys.exit(1)

    table_data = exports[0].get("Table", {}).get("Data", [])

    # ─────────────────────────────────────────────────────────────────
    # Step 2: Iterate every recipe row and patch colour variants.
    # ─────────────────────────────────────────────────────────────────
    patched_count = 0

    for item in table_data:
        # Extract the item reference name from the row
        try:
            raw_name = item["Value"][0]["Value"][0]["Value"]
        except (IndexError, KeyError, TypeError):
            print("[WARNING] Could not read item name from a row — skipping.")
            continue

        # Only process colour-variant items
        if not any(tag in raw_name for tag in COLOUR_TAGS):
            continue

        # (a) Derive the base item name
        base_name = clean_name(raw_name)

        # (b) Switch unlock type: Manual → DiscoverDependencies
        try:
            unlock_type = item["Value"][12]["Value"][0]["Value"]
            if unlock_type == "EMorRecipeUnlockType::Manual":
                item["Value"][12]["Value"][0]["Value"] = (
                    "EMorRecipeUnlockType::DiscoverDependencies"
                )
        except (IndexError, KeyError):
            print(f"[WARNING] Could not modify UnlockType for {raw_name}")

        # (c) Insert the dependency template pointing to the base recipe
        try:
            new_obj = copy.deepcopy(template_obj)
            new_obj["Value"][0]["Value"][0]["Value"] = base_name
            item["Value"][12]["Value"][3] = new_obj
        except (IndexError, KeyError, TypeError):
            print(f"[WARNING] Could not set RequiredRecipe for {raw_name}")

        patched_count += 1

    # ─────────────────────────────────────────────────────────────────
    # Step 3: Save the modified recipe table.
    # ─────────────────────────────────────────────────────────────────
    with open(recipes_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    print(f"Done — patched {patched_count} colour-variant recipes.")


if __name__ == "__main__":
    main()
