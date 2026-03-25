"""Tab configurations for all item types.

Each config defines which fields to display and how.
Field tuples: (field_name, widget_type)
  widget_type: "enum", "bool", "int", "float", "tags", "asset", "text"
"""

from src.gui.item_adder_tab import TabConfig

# ── Shared recipe fields (DT_ItemRecipes) ────────────────────────

_ITEM_RECIPE_FIELDS = [
    ("ResultItemCount", "int"),
    ("CraftTimeSeconds", "float"),
    ("bCanBePinned", "bool"),
    ("bNpcOnlyRecipe", "bool"),
    ("EnabledState", "enum"),
]

# ── Armor ────────────────────────────────────────────────────────

ARMOR_CONFIG = TabConfig(
    tab_label="New Armor",
    item_table="DT_Armor",
    item_struct_label="DT_Armor",
    recipe_table="DT_ItemRecipes",
    recipe_struct_label="DT_ItemRecipes (Armor Recipe)",
    item_fields=[
        ("Durability", "int"),
        ("DamageReduction", "float"),
        ("DamageProtection", "float"),
        ("Portability", "enum"),
        ("MaxStackSize", "int"),
        ("BaseTradeValue", "float"),
        ("EnabledState", "enum"),
    ],
    recipe_fields=_ITEM_RECIPE_FIELDS,
    recipe_has_materials=True,
    recipe_has_unlocks=True,
)

# ── Weapons ──────────────────────────────────────────────────────

WEAPON_CONFIG = TabConfig(
    tab_label="New Weapon",
    item_table="DT_Weapons",
    item_struct_label="DT_Weapons",
    recipe_table="DT_ItemRecipes",
    recipe_struct_label="DT_ItemRecipes (Weapon Recipe)",
    item_fields=[
        ("Damage", "int"),
        ("Speed", "float"),
        ("Tier", "int"),
        ("ArmorPenetration", "float"),
        ("BlockDamageReduction", "float"),
        ("StaminaCost", "float"),
        ("EnergyCost", "float"),
        ("Durability", "int"),
        ("Portability", "enum"),
        ("MaxStackSize", "int"),
        ("BaseTradeValue", "float"),
        ("EnabledState", "enum"),
    ],
    recipe_fields=_ITEM_RECIPE_FIELDS,
    recipe_has_materials=True,
    recipe_has_unlocks=True,
)

# ── Tools ────────────────────────────────────────────────────────

TOOL_CONFIG = TabConfig(
    tab_label="New Tool",
    item_table="DT_Tools",
    item_struct_label="DT_Tools",
    recipe_table="DT_ItemRecipes",
    recipe_struct_label="DT_ItemRecipes (Tool Recipe)",
    item_fields=[
        ("Durability", "int"),
        ("DurabilityDecayWhileEquipped", "float"),
        ("CarveHits", "int"),
        ("StaminaCost", "float"),
        ("EnergyCost", "float"),
        ("Portability", "enum"),
        ("MaxStackSize", "int"),
        ("EnabledState", "enum"),
    ],
    recipe_fields=_ITEM_RECIPE_FIELDS,
    recipe_has_materials=True,
    recipe_has_unlocks=True,
)

# ── Items (materials/resources) ──────────────────────────────────

ITEM_CONFIG = TabConfig(
    tab_label="New Item",
    item_table="DT_Items",
    item_struct_label="DT_Items",
    recipe_table="DT_ItemRecipes",
    recipe_struct_label="DT_ItemRecipes (Item Recipe)",
    item_fields=[
        ("Portability", "enum"),
        ("MaxStackSize", "int"),
        ("BaseTradeValue", "float"),
        ("EnabledState", "enum"),
    ],
    recipe_fields=_ITEM_RECIPE_FIELDS,
    recipe_has_materials=True,
    recipe_has_unlocks=True,
)

# ── Loot (drop tables — no recipe) ──────────────────────────────

LOOT_CONFIG = TabConfig(
    tab_label="New Loot",
    item_table="DT_Loot",
    item_struct_label="DT_Loot",
    recipe_table=None,
    item_fields=[
        ("DropChance", "float"),
        ("MinQuantity", "int"),
        ("MaxQuantity", "int"),
        ("EnabledState", "enum"),
    ],
)

# ── Ores (no recipe) ────────────────────────────────────────────

ORE_CONFIG = TabConfig(
    tab_label="New Ore",
    item_table="DT_Ores",
    item_struct_label="DT_Ores",
    recipe_table=None,
    item_fields=[
        ("Portability", "enum"),
        ("MaxStackSize", "int"),
        ("BaseTradeValue", "float"),
        ("EnabledState", "enum"),
    ],
)
