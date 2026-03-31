"""Tab configurations for all item types.

Defines the TabConfig dataclass and per-table configs that drive the
generic ItemAdderTab.  Each config declares which fields to display,
their widget types, and whether materials/unlocks are included.

Field tuples: (field_name, widget_type)
  widget_type: "enum", "bool", "int", "float", "tags", "asset", "text"
  Dotted names (e.g. "DamageType.TagName") reach into nested structs.
"""

from __future__ import annotations

from dataclasses import dataclass, field


# ── Configuration dataclass ──────────────────────────────────────

@dataclass
class TabConfig:
    """Describes what an item tab should display and edit."""

    tab_label: str                      # e.g. "New Weapon"
    item_table: str                     # e.g. "DT_Weapons"
    item_struct_label: str              # e.g. "DT_Weapons"
    recipe_table: str | None = None     # e.g. "DT_ItemRecipes" or None
    recipe_struct_label: str | None = None

    # Fields to show as editable in the item section
    # Each tuple: (field_name, widget_type)
    # widget_type: "enum", "bool", "int", "float", "tags", "asset"
    item_fields: list[tuple[str, str]] = field(default_factory=list)

    # Fields to show as editable in the recipe section
    recipe_fields: list[tuple[str, str]] = field(default_factory=list)

    # Whether recipe has materials and unlock sections
    recipe_has_materials: bool = False
    recipe_has_unlocks: bool = False

    # Optional master-selector that auto-fills multiple fields.
    # Dict of { "SelectorLabel": { "Choice": { "field": "value", ...}, ...} }
    # Fields listed here become read-only, driven by the selector.
    master_selector: dict | None = None


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
        # Identity
        ("Actor", "asset"),             # Blueprint path to 3D model
        ("Icon", "asset"),              # UI icon texture path
        ("Tags.Tags", "tags"),          # UI.Armor.Helmet.Tier3, etc.
        # Combat stats
        ("Durability", "int"),
        ("DamageReduction", "float"),
        ("DamageProtection", "float"),
        ("DamageModifiers.RowName", "tags"),  # CorrosiveDamage, etc.
        # Repair
        ("InitialRepairCost.MaterialHandle.RowName", "tags"),
        ("InitialRepairCost.Count", "int"),
        # Skills
        ("SkillsGranted.SkillsGranted", "tags"),
        ("SkillsRequired.SkillsRequired", "tags"),
        # Cosmetic
        ("CosmeticOwner.RowName", "tags"),
        ("CosmeticConvertCost.RowName", "tags"),
        ("CosmeticAchievement.RowName", "tags"),
        ("ItemSetRowHandle.RowName", "tags"),
        # General
        ("Portability", "enum"),
        ("MaxStackSize", "int"),
        ("SlotSize", "int"),
        ("BaseTradeValue", "float"),
        ("EnabledState", "enum"),
    ],
    recipe_fields=_ITEM_RECIPE_FIELDS,
    recipe_has_materials=True,
    recipe_has_unlocks=True,
)

# ── Weapons ──────────────────────────────────────────────────────

# Weapon Type master-selector: auto-fills DamageType, UI Tag, and Weapon Type Tag.
# NOTE: Mattock/Maul tags are intentionally inverted — this is a known game bug
# that we must replicate for compatibility.
_WEAPON_TYPE_RULES = {
    "Weapon Type": {
        "Axe": {
            "DamageType.TagName": "Damage.Slashing.Axe.1h",
            "Tags.Tags": "UI.Weapon.1h",
            "WeaponTypeTag": "Item.Weapon.WarAxe",
        },
        "Sword": {
            "DamageType.TagName": "Damage.Slashing.Sword.1h",
            "Tags.Tags": "UI.Weapon.1h",
            "WeaponTypeTag": "Item.Weapon.Sword.1h",
        },
        "Maul": {
            "DamageType.TagName": "Damage.Bludgeon.Hammer.1h",
            "Tags.Tags": "UI.Weapon.1h",
            "WeaponTypeTag": "Item.Weapon.Mattock",  # Inverted on purpose!
        },
        "Spear": {
            "DamageType.TagName": "Damage.Piercing.Spear",
            "Tags.Tags": "UI.Weapon.1h",
            "WeaponTypeTag": "Item.Weapon.Spear",
        },
        "Battleaxe": {
            "DamageType.TagName": "Damage.Slashing.Axe.2h",
            "Tags.Tags": "UI.Weapon.2h",
            "WeaponTypeTag": "Item.Weapon.Battleaxe",
        },
        "Greatsword": {
            "DamageType.TagName": "Damage.Slashing.Sword.2h",
            "Tags.Tags": "UI.Weapon.2h",
            "WeaponTypeTag": "Item.Weapon.Sword.2h",
        },
        "Halberd": {
            "DamageType.TagName": "Damage.Slashing.Halberd",
            "Tags.Tags": "UI.Weapon.2h",
            "WeaponTypeTag": "Item.Weapon.Halberd",
        },
        "Mattock": {
            "DamageType.TagName": "Damage.Bludgeon.Hammer.2h",
            "Tags.Tags": "UI.Weapon.2h",
            "WeaponTypeTag": "Item.Weapon.Hammer",  # Inverted on purpose!
        },
    },
}

WEAPON_CONFIG = TabConfig(
    tab_label="New Weapon",
    item_table="DT_Weapons",
    item_struct_label="DT_Weapons",
    recipe_table="DT_ItemRecipes",
    recipe_struct_label="DT_ItemRecipes (Weapon Recipe)",
    master_selector=_WEAPON_TYPE_RULES,
    item_fields=[
        # Identity
        ("Actor", "asset"),             # Blueprint path to 3D model
        ("Icon", "asset"),              # UI icon texture path
        ("DamageType.TagName", "tags"),  # Auto-filled by Weapon Type
        ("Tags.Tags", "tags"),           # Auto-filled by Weapon Type
        # Combat stats
        ("Damage", "int"),
        ("Speed", "float"),
        ("Tier", "int"),
        ("ArmorPenetration", "float"),
        ("BlockDamageReduction", "float"),
        ("StaminaCost", "float"),
        ("EnergyCost", "float"),
        ("Durability", "int"),
        # Repair
        ("InitialRepairCost.MaterialHandle.RowName", "tags"),
        ("InitialRepairCost.Count", "int"),
        # Skills
        ("SkillsRequired.SkillsRequired", "tags"),
        # Cosmetic
        ("CosmeticConvertCost.RowName", "tags"),
        ("ItemSetRowHandle.RowName", "tags"),
        # General
        ("Portability", "enum"),
        ("MaxStackSize", "int"),
        ("SlotSize", "int"),
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
        # Identity
        ("Actor", "asset"),             # Blueprint path to 3D model
        ("Icon", "asset"),              # UI icon texture path
        ("Tags.Tags", "tags"),           # Item.Tool.Pickaxe, UI.Tool, etc.
        ("CompatibleToolTags.CompatibleToolTags", "tags"),
        # Stats
        ("Durability", "int"),
        ("DurabilityDecayWhileEquipped", "float"),
        ("CarveHits", "int"),
        ("NpcMiningRate", "float"),
        ("StaminaCost", "float"),
        ("EnergyCost", "float"),
        # Repair
        ("InitialRepairCost.MaterialHandle.RowName", "tags"),
        ("InitialRepairCost.Count", "int"),
        # Skills
        ("SkillsRequired.SkillsRequired", "tags"),
        # Cosmetic
        ("CosmeticConvertCost.RowName", "tags"),
        ("ItemSetRowHandle.RowName", "tags"),
        # General
        ("Portability", "enum"),
        ("MaxStackSize", "int"),
        ("SlotSize", "int"),
        ("BaseTradeValue", "float"),
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
        # Identity
        ("Actor", "asset"),             # Blueprint path
        ("Icon", "asset"),              # UI icon texture
        ("Tags.Tags", "tags"),           # UI.Materials, Item.BasicGather, etc.
        # Skills
        ("SkillsRequired.SkillsRequired", "tags"),
        # Cosmetic
        ("CosmeticConvertCost.RowName", "tags"),
        ("ItemSetRowHandle.RowName", "tags"),
        # General
        ("Portability", "enum"),
        ("MaxStackSize", "int"),
        ("SlotSize", "int"),
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
        ("RequiredTags.RequiredTags", "tags"),  # Flora.GrowthStage, etc.
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
        ("Tags.Tags", "tags"),           # Item.Mineral.Stone, UI.Materials, etc.
        ("Portability", "enum"),
        ("MaxStackSize", "int"),
        ("BaseTradeValue", "float"),
        ("EnabledState", "enum"),
    ],
)
