"""
colour_variants — Auto-link colour-variant armour recipes to base items.

The game supports a ``DiscoverDependencies`` unlock type: a colour
variant (e.g. ``Khazad_White_Chest``) unlocks automatically when the
player discovers the base item (``Khazad_Chest``).  Setting this up
manually for every ``_White_``, ``_Black_``, and ``_Gold_`` variant is
tedious, so this module automates it.

Workflow
--------
1. Load ``DT_ItemRecipes.json`` — the master recipe DataTable.
2. Load ``UnlockRequiredItems.json`` — a small template snippet.
3. For every recipe containing a colour tag in its name:

   a. Derive the base name by stripping the colour tag.
   b. Switch ``UnlockType`` from ``Manual`` → ``DiscoverDependencies``.
   c. Insert a deep-copy of the template pointing to the base recipe.

4. Save the modified JSON back to disk.

.. note::
   UAssetAPI serialises DataTable properties as ordered arrays, so we
   access fields by numeric index.  Positions are stable within a game
   version but may shift after a game update.
"""

from __future__ import annotations

import copy
import json
import os
import re
import sys

from src.config import cfg

# Colour tags that identify variant recipes
COLOUR_TAGS: list[str] = ["_White_", "_Black_", "_Gold_"]

_COLOUR_RE = re.compile(r"_(White|Black|Gold)_")


def clean_name(name: str) -> str:
    """Strip the colour tag from an item name to get the base name.

    Example::

        >>> clean_name("Khazad_White_Chest")
        'Khazad_Chest'
    """
    return _COLOUR_RE.sub("_", name)


def is_colour_variant(name: str) -> bool:
    """Return ``True`` if *name* contains a colour tag."""
    return any(tag in name for tag in COLOUR_TAGS)


def patch_recipe(
    item: dict,
    template: dict,
) -> str | None:
    """Patch a single colour-variant recipe row in-place.

    Args:
        item:     One row from the DataTable ``Data`` array.
        template: Deep-copy source for the dependency structure.

    Returns:
        The raw item name if patched, or ``None`` if skipped.
    """
    # ── Read the item reference name ──
    try:
        raw_name: str = item["Value"][0]["Value"][0]["Value"]
    except (IndexError, KeyError, TypeError):
        return None

    if not is_colour_variant(raw_name):
        return None

    base_name = clean_name(raw_name)

    # ── Switch unlock type: Manual → DiscoverDependencies ──
    try:
        unlock_type = item["Value"][12]["Value"][0]["Value"]
        if unlock_type == "EMorRecipeUnlockType::Manual":
            item["Value"][12]["Value"][0]["Value"] = (
                "EMorRecipeUnlockType::DiscoverDependencies"
            )
    except (IndexError, KeyError):
        print(f"[colour_variants] WARNING: Could not modify UnlockType for {raw_name}")

    # ── Insert dependency template pointing to the base recipe ──
    try:
        new_obj = copy.deepcopy(template)
        new_obj["Value"][0]["Value"][0]["Value"] = base_name
        item["Value"][12]["Value"][3] = new_obj
    except (IndexError, KeyError, TypeError):
        print(f"[colour_variants] WARNING: Could not set RequiredRecipe for {raw_name}")

    return raw_name


def run(
    recipes_path: str | None = None,
    template_path: str | None = None,
) -> int:
    """Execute the colour-variant patching pass.

    All arguments are optional — defaults come from ``config.ini``.

    Returns:
        Number of recipes patched.
    """
    if recipes_path is None:
        recipes_path = cfg.path(
            "modified-json", "Moria", "Content", "Tech", "Data",
            "Items", "DT_ItemRecipes.json",
        )
    if template_path is None:
        template_path = cfg.path("modified-json", "UnlockRequiredItems.json")

    # ── Validate inputs ──
    for label, path in [("Recipes", recipes_path), ("Template", template_path)]:
        if not os.path.isfile(path):
            print(
                f"[colour_variants] ERROR: {label} not found: {path}",
                file=sys.stderr,
            )
            sys.exit(1)

    # ── Step 1: Load data ──
    with open(recipes_path, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    with open(template_path, "r", encoding="utf-8") as fh:
        template = json.load(fh)

    exports = data.get("Exports", [])
    if not exports:
        print("[colour_variants] ERROR: No 'Exports' in recipe JSON.", file=sys.stderr)
        sys.exit(1)

    table_data = exports[0].get("Table", {}).get("Data", [])

    # ── Step 2: Patch every colour-variant row ──
    patched = 0
    for item in table_data:
        if patch_recipe(item, template) is not None:
            patched += 1

    # ── Step 3: Save ──
    with open(recipes_path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)

    print(f"Done — patched {patched} colour-variant recipes.")
    return patched


def main() -> None:
    """CLI entry point."""
    run()


if __name__ == "__main__":
    main()
