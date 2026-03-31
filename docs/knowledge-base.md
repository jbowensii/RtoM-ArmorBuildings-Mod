# RtoM Mod Tools — Knowledge Base

## Table of Contents

- [Overview](#overview)
- [Application Tabs](#application-tabs)
- [Architecture](#architecture)
- [Directory Layout](#directory-layout)
- [Data Tables Explained](#data-tables-explained)
- [Per-Item Files](#per-item-files)
- [Display Names and String Tables](#display-names-and-string-tables)
- [Field Value Indexes](#field-value-indexes)
- [Templates](#templates)
- [First Run and Game Extraction](#first-run-and-game-extraction)
- [Build Process](#build-process)
- [Construction Workflow](#construction-workflow)
- [Armor, Weapon, Tool, and Item Workflow](#armor-weapon-tool-and-item-workflow)
- [Loot and Ore Workflow](#loot-and-ore-workflow)
- [Localization Pipeline](#localization-pipeline)
- [Color Variants](#color-variants)
- [Configuration](#configuration)
- [File Formats](#file-formats)
- [Import Index System](#import-index-system)
- [String Table Import System](#string-table-import-system)
- [External Toolchain](#external-toolchain)
- [Build and Release Pipeline](#build-and-release-pipeline)
- [Mod Pack Registry](#mod-pack-registry)
- [Glossary](#glossary)

---

## Overview

RtoM Mod Tools is a PySide6 desktop application for managing the **Secrets of Khazad-Dum** mod
for *The Lord of the Rings: Return to Moria*. The mod adds cosmetic armour sets, weapons,
tools, items, loot tables, and 28+ building/construction packs to the game.

The tool manages **11 game DataTables** through a tabbed GUI interface. Each tab lets you
browse existing items, view their properties, and edit recipe/crafting data. A single
"Build Combined Files" button merges everything into the final mod files.

**Current version:** 3.1.1
**Pylint score:** 10.00/10
**Automated tests:** 83 passing

---

## Application Tabs

The application has 9 tabs, each serving a different purpose:

### Item Editing Tabs (with recipes)

These tabs display a left-side item list and a right-side scrollable form. When you select
an item from the list, the form populates with its properties from the DataTable and its
matching recipe from DT_ItemRecipes (or DT_ConstructionRecipes for constructions).

| Tab | Item Table | Recipe Table | Description |
|-----|-----------|-------------|-------------|
| **New Construction** | DT_Constructions | DT_ConstructionRecipes | Buildings, decorations, walls, floors, scaffolding. Has unique fields like PlacementType, FoundationRule, OnWall/OnFloor flags. |
| **New Armor** | DT_Armor | DT_ItemRecipes | Helmets, gloves, chest pieces, boots. Armor-specific fields: Durability, DamageReduction, DamageProtection. |
| **New Weapon** | DT_Weapons | DT_ItemRecipes | Swords, axes, hammers, shields, spears. Weapon-specific fields: Damage, Speed, Tier, ArmorPenetration, BlockDamageReduction. |
| **New Tool** | DT_Tools | DT_ItemRecipes | Picks, hammers, chisels, torches. Tool-specific fields: CarveHits, DurabilityDecayWhileEquipped, NpcMiningRate. |
| **New Item** | DT_Items | DT_ItemRecipes | Materials and resources (wood, ingots, cloth, food ingredients). Fields: MaxStackSize, BaseTradeValue, Portability. |

### Item Editing Tabs (without recipes)

These items do not have crafting recipes — they appear in the game through other means
(drop tables, mining, etc.).

| Tab | Item Table | Description |
|-----|-----------|-------------|
| **New Loot** | DT_Loot | Drop tables for breakables and creatures. Defines what items drop, with what chance, and in what quantity. Fields: DropChance, MinQuantity, MaxQuantity, RequiredTags. |
| **New Ore** | DT_Ores | Ores and minerals obtained from mining. Fields: Portability, MaxStackSize, BaseTradeValue. Has a unique Mineral field linking to the voxel baking system. |

### Pipeline Tabs

| Tab | Description |
|-----|-------------|
| **Localization** | Converts PO translation files to CSV and back, then packages them into .pak format using UnrealPak. Supports English (source), German, Spanish, and French. |
| **Color Variants** | Auto-links Black, White, and Gold colour variants of armor sets to their base recipes. Sets the unlock type to DiscoverDependencies so crafting one variant unlocks the others. |

---

## Architecture

The application is a Python package. When installed via the installer, it lives at
`%LOCALAPPDATA%\RtoMModTools\`. During development, it runs from the repository root.

### Source Code Modules

| Module | Lines | Purpose |
|--------|-------|---------|
| `main.py` | ~30 | Entry point — first-run checks, launches GUI |
| `src/__init__.py` | ~14 | App name and version constants |
| `src/config.py` | ~160 | Config singleton — reads config.ini, resolves all paths |

### GUI Modules

| Module | Lines | Purpose |
|--------|-------|---------|
| `src/gui/main_window.py` | ~104 | Main window with tabbed interface, loads shared data |
| `src/gui/construction_adder_tab.py` | ~464 | Custom New Construction tab (left list + right form) |
| `src/gui/item_adder_tab.py` | ~300 | Generic tab class for Armor/Weapon/Tool/Item/Loot/Ore |
| `src/gui/tab_configs.py` | ~170 | TabConfig dataclass and per-table field configurations |
| `src/gui/shared.py` | ~175 | Build pipeline, item list pane, refresh/delete helpers |
| `src/gui/field_helpers.py` | ~65 | Field-value loading, enum extraction, combo factories |
| `src/gui/material_picker.py` | ~170 | MaterialPicker class — dynamic material rows with trash icons |
| `src/gui/unlock_picker.py` | ~130 | UnlockPicker class — radio toggle + searchable combo |
| `src/gui/game_path_dialog.py` | ~137 | First-run game path selection dialog |
| `src/gui/extraction_dialog.py` | ~134 | Extraction progress dialog with background worker |
| `src/gui/localization_tab.py` | ~79 | Localization pipeline tab |
| `src/gui/recipes_tab.py` | ~46 | Color Variants tab |
| `src/gui/log_panel.py` | ~52 | Stdout capture and logging panel |

### Backend Modules

| Module | Lines | Purpose |
|--------|-------|---------|
| `src/construction/mod_utils.py` | ~280 | Per-item file creation for constructions (templates, imports, recipes) |
| `src/utils/json_split_combine.py` | ~228 | Combine per-item files with vanilla base into full DataTables |
| `src/utils/game_extractor.py` | ~230 | Game file extraction via retoc + UAssetGUI |
| `src/utils/json_handler.py` | ~30 | JSON load/save with error handling and logging |
| `src/recipes/colour_variants.py` | ~167 | Auto-link BWG colour variants |
| `src/localization/` | ~100 | PO/CSV conversion modules (po_parser, po_to_csv, csv_to_po) |
| `src/packaging/pak_locres.py` | ~105 | Pak file packaging via UnrealPak |

### How the Generic Tab System Works

Most tabs use the same generic `ItemAdderTab` class, configured by a `TabConfig` dataclass.
Each config specifies:

- Which DataTable to browse (e.g., `DT_Weapons`)
- Which recipe table to pair it with (e.g., `DT_ItemRecipes`, or `None` for Loot/Ores)
- Which fields to display as editable widgets (enums, bools, ints, floats)
- Whether to show materials and unlock sections

This means adding a new tab for a new DataTable only requires adding a new `TabConfig` entry
in `tab_configs.py` — no new GUI code needed.

The **New Construction** tab is a custom implementation because constructions have unique
requirements: they create three per-item files (Architecture + DT_Constructions +
DT_ConstructionRecipes), use a different recipe table, and have construction-specific
fields (PlacementType, FoundationRule, etc.).

---

## Directory Layout

```
RtoMModTools/                           (installed at %LOCALAPPDATA%\RtoMModTools\)
|
+-- RtoMModTools.exe                    The application executable
+-- config.ini                          Configuration (created on first run)
|
+-- utilities/                          External tools shipped with installer
|   +-- retoc.exe                       Extracts .uasset from IoStore paks
|   +-- UAssetGUI.exe                   Converts .uasset to/from JSON
|   +-- oo2core_9_win64.dll             Compression library required by retoc
|
+-- data/
|   +-- extraction_manifest.ini         Defines which DataTables to extract from the game
|   +-- Imports.json                    String table import definitions (8 entries)
|   |
|   +-- templates/                      [shipped with installer]
|   |   +-- MoreBuildings/              Tobi's construction templates
|   |   |   +-- ConstructionTemplate.json
|   |   |   +-- ConstructionRecipeTemplate.json
|   |   |   +-- constructionsImportTemplates.json
|   |   |   +-- ItemTemplate.json       (material row template)
|   |   |   +-- Items.json              (category → tag → display name index)
|   |   |   +-- CategoryTags.json       (building categories)
|   |   |   +-- CategoryFlags.json      (placement flags per category)
|   |   |   +-- DumyStructs.json        (empty struct placeholders)
|   |   |   +-- UnlockRequirementsStructs.json
|   |   |   +-- UnlockRequirementsItemsConstructions.json
|   |   +-- MoreArmor/                  Tobi's armor templates
|   |   |   +-- ItemRecipeTemplate.json
|   |   |   +-- Armor.json              (armor tag → display name mapping)
|   |   |   +-- CraftingStationTemplate.json
|   |   |   +-- RequiredMaterialTemplate.json
|   |   |   +-- DumyStructs.json
|   |   |   +-- UnlockRequirementsStructs.json
|   |   |   +-- UnlockRequirementsItemsConstructions.json
|   |   +-- ConstructiondDT/            Single-row DataTable templates
|   |   +-- RtoMMoreBuildings_P/        More Buildings plugin templates
|   |   +-- generated/                  Auto-generated row templates
|   |       +-- DT_Armor_template.json
|   |       +-- DT_Weapons_template.json
|   |       +-- DT_Tools_template.json
|   |       +-- DT_Items_template.json
|   |       +-- DT_Loot_template.json
|   |       +-- DT_Ores_template.json
|   |       +-- DT_ItemRecipes_template.json
|   |
|   +-- field_values/                   [autocomplete indexes, shipped with installer]
|   |   +-- DT_Constructions_fields.json      (10 fields, 1100+ values)
|   |   +-- DT_ConstructionRecipes_fields.json (43 fields)
|   |   +-- DT_Armor_fields.json              (26 fields)
|   |   +-- DT_Weapons_fields.json            (28 fields)
|   |   +-- DT_Tools_fields.json              (26 fields)
|   |   +-- DT_Items_fields.json              (15 fields)
|   |   +-- DT_Loot_fields.json               (7 fields)
|   |   +-- DT_Ores_fields.json               (16 fields)
|   |   +-- DT_ItemRecipes_fields.json        (28 fields)
|   |   +-- string_table_lookup.json          (tag → name + description, 2111 entries)
|   |   +-- item_display_names.json           (tag → display name, 1521 entries)
|   |
|   +-- game_extract/                   [generated on first run, NOT shipped]
|   |   +-- retoc/                      .uasset/.uexp intermediates
|   |   |   +-- Moria/Content/...
|   |   +-- uassetgui/                  Vanilla JSON DataTables
|   |       +-- Moria/Content/Tech/Data/Building/
|   |       |   +-- DT_Constructions.json
|   |       |   +-- DT_ConstructionRecipes.json
|   |       +-- Moria/Content/Tech/Data/Items/
|   |       |   +-- DT_Armor.json
|   |       |   +-- DT_Weapons.json
|   |       |   +-- DT_Tools.json
|   |       |   +-- DT_Items.json
|   |       |   +-- DT_Ores.json
|   |       |   +-- DT_ItemRecipes.json
|   |       |   +-- DT_Consumables.json
|   |       +-- Moria/Content/Tech/Data/
|   |       |   +-- DT_CategoryTags.json
|   |       |   +-- StringTables/       (4 vanilla string table JSONs)
|   |       |       +-- Items.json
|   |       |       +-- Architecture.json
|   |       |       +-- Interactables.json
|   |       |       +-- CategoryTags.json
|   |       +-- Moria/Content/Character/AI/
|   |           +-- DT_Loot.json
|   |
|   +-- Tobis_json/                     [per-item source files, shipped with installer]
|       +-- Architecture/               String table entries (name + description)
|       +-- DT_Constructions/           246 construction definitions
|       +-- DT_ConstructionRecipes/     245 construction recipes
|       +-- DT_Armor/                   4 armor definitions
|       +-- DT_ItemRecipes/             42 item recipes (armor, weapons, tools)
|       +-- DT_Weapons/                 9 weapon definitions
|       +-- DT_Tools/                   2 tool definitions
|       +-- DT_Items/                   5 item definitions
|       +-- DT_Loot/                    63 loot table entries
|       +-- DT_CategoryTags/            5 custom category tags
|       +-- _architecture_shell.json    Empty scaffold for Architecture combine
|
+-- TobisMod/
|   +-- json_data/                      [build output — combined DataTables]
|       +-- Moria/Content/...           Final mod JSON files
|
+-- Localization/
    +-- en/, de/, es/, fr/              Translation files (.po, .csv)
    +-- ModLocalization/                Packaged .locres files + Paklist.txt
```

### What Gets Shipped vs Generated

- **Shipped with installer:** templates, field_values, Tobis_json, utilities, Imports.json
- **Generated on first run:** game_extract (4.8 GB of vanilla game data, extracted via retoc + UAssetGUI)
- **Generated on Build:** TobisMod/json_data (combined mod files)

The game_extract directory is NOT included in the installer because it's 4.8 GB of vanilla
game data. It's re-extracted from the player's game installation on first run.

---

## Data Tables Explained

Return to Moria stores game data in Unreal Engine 4 DataTables. Each DataTable is a typed
table where every row has a unique name (the "tag") and a set of typed properties.

The mod tool works with 11 DataTables:

### Building Tables

| Table | Rows (vanilla) | Rows (mod) | What It Stores |
|-------|---------------|------------|----------------|
| **DT_Constructions** | 854 | 246 | Building definitions: display name, description, icon, actor blueprint, category tags, enabled state |
| **DT_ConstructionRecipes** | 814 | 245 | Building recipes: materials needed, placement rules (wall/floor/water), foundation rules, unlock conditions |

These two tables are paired by row name — `DT_Constructions.GraniteWall_A` has a matching
`DT_ConstructionRecipes.GraniteWall_A` that defines how to craft it.

### Item Tables

| Table | Rows (vanilla) | Rows (mod) | What It Stores |
|-------|---------------|------------|----------------|
| **DT_Armor** | 156 | 4 | Armor pieces: durability, damage protection, damage reduction, equipment effects |
| **DT_Weapons** | 158 | 9 | Weapons: damage, speed, tier, armor penetration, block damage reduction, stamina cost |
| **DT_Tools** | 41 | 2 | Tools: carve hits, compatible tool tags, durability decay, NPC mining rate |
| **DT_Items** | 131 | 5 | Materials/resources: stack size, trade value, portability |
| **DT_Ores** | 41 | 0 | Ores/minerals: same fields as items, plus a Mineral voxel reference |

### Recipe Table (shared)

| Table | Rows (vanilla) | Rows (mod) | What It Stores |
|-------|---------------|------------|----------------|
| **DT_ItemRecipes** | 390 | 42 | Crafting recipes for ALL items (armor, weapons, tools, items): crafting stations, required materials, craft time, unlock conditions |

DT_ItemRecipes is shared across Armor, Weapons, Tools, and Items. A recipe row's
`ResultItemHandle.RowName` points to the item it crafts.

### Other Tables

| Table | Rows (vanilla) | Rows (mod) | What It Stores |
|-------|---------------|------------|----------------|
| **DT_Loot** | 370 | 63 | Drop tables: item handle, min/max quantity, drop chance, required tags |
| **DT_CategoryTags** | (many) | 5 | Building category definitions for the construction UI |
| **DT_Consumables** | (many) | 0 | Consumable items (extracted but not currently modded) |

---

## Per-Item Files

Instead of editing one giant DataTable JSON directly, the mod tool stores each custom item
as its own small JSON file in `data/Tobis_json/{table}/{tag}.json`. This makes it easy to
add, remove, or share individual items.

### Per-Item File Structure (DataTable Row)

Every per-item file for a DataTable row has this structure:

```json
{
    "NameMap": ["TagName", "/Game/path/to/asset", ...],
    "Imports": [
        { "Package import for icon texture..." },
        { "Texture2D import for icon..." }
    ],
    "Row": {
        "$type": "UAssetAPI.PropertyTypes.Structs.StructPropertyData, UAssetAPI",
        "StructType": "MorConstructionDefinition",
        "Name": "TobiPack_AleKeg_A",
        "Value": [
            { "Name": "DisplayName", "Value": "TobiPack_AleKeg_A.Name", ... },
            { "Name": "Description", "Value": "TobiPack_AleKeg_A.Description", ... },
            { "Name": "Actor", "Value": { "AssetPath": { "AssetName": "/Game/..." } } },
            ...
        ]
    }
}
```

- **NameMap** — String identifiers used by this item (tags, asset paths). Merged into the
  combined file's NameMap during Build.
- **Imports** — External asset references (Package + Texture2D for icons). Only present for
  DT_Constructions; empty `[]` for all other tables.
- **Row** — The actual DataTable row. The `Value` array contains typed property entries,
  each with a `Name` field and a `Value` field.

### Per-Item File Structure (Architecture / String Table)

Construction display names and descriptions are stored in a separate string table called
Architecture. Each per-item Architecture file has this simple structure:

```json
{
    "Entries": [
        ["TobiPack_AleKeg_A.Name", "Ale Keg"],
        ["TobiPack_AleKeg_A.Description", "A keg of finest dwarven ale"]
    ]
}
```

### Tag Naming Convention

Item tags must contain **no spaces** — use underscores. The GUI auto-replaces spaces
with underscores as you type.

For constructions, tags follow the pattern: `{PackName}_{ItemName}_{Letter}`
- **PackName** — The contributor's pack name (e.g., TobiPack, AradrenPack)
- **ItemName** — A human-readable item name in TitleCase (e.g., GraniteWall, AleKeg)
- **Letter** — An auto-assigned suffix (A-Z) to ensure uniqueness

For weapons, tools, and other items, tags follow: `{Name}_{Type}`
- Example: `Mereak_Battleaxe`, `Restoration_Hammer_Tobi`, `CeibaCutting`

Examples: `TobiPack_AleKeg_A`, `100BuildingsPack_GimlisMap_A`, `Mereak_Battleaxe`

The Pack Name field has autocomplete from 33 known packs (unified across all tabs).

---

## Display Names and String Tables

The game stores human-readable item names in String Tables, not in the DataTables themselves.
Each DataTable row's `DisplayName` field contains a reference like
`Items.Items.Leather.Name` that points to the string table entry "Leather".

### How Display Names Are Resolved

The mod tool extracts 4 vanilla string tables from the game via retoc + UAssetGUI:

| String Table | Location | Contains |
|-------------|----------|----------|
| Items | `/Game/Tech/Data/StringTables/Items` | Names and descriptions for all items, armor, weapons, tools, ores |
| Architecture | `/Game/Tech/Data/StringTables/Architecture` | Names and descriptions for vanilla constructions |
| Interactables | `/Game/Tech/Data/StringTables/Interactables` | Names for crafting stations and interactive objects |
| CategoryTags | `/Game/Tech/Data/StringTables/CategoryTags` | Building category display names |

Additionally, the mod's own string table entries come from `Localization/en/Game.po`,
which uses the format:

```
msgctxt "ST_Mod_Architecture,100BuildingsPack_GimlisMap_A.Name"
msgid "Gimli's Map"
msgstr "Gimli's Map"
```

### Display Name Index Files

All display names are compiled into two JSON index files:

1. **`data/field_values/item_display_names.json`** — Maps 1,521 item tags to their
   display names. Used by the material picker to show "Leather (Item.Leather)" format.

2. **`data/field_values/string_table_lookup.json`** — Maps tags to both name and
   description. Used when selecting an item from the left-side list to populate the
   Basic Info section.

These indexes are built by the `scripts/extract_field_values.py` script from both
vanilla string tables and the mod's Game.po file.

---

## Field Value Indexes

Every editable field in every DataTable has a pre-built autocomplete index stored in
`data/field_values/{table}_fields.json`. These indexes power the dropdown menus and
type-ahead autocomplete in the GUI.

### How They're Built

The `scripts/extract_field_values.py` script scans two sources:

1. **Per-item files** in `data/Tobis_json/{table}/` — All custom mod items
2. **Vanilla game extract** in `data/game_extract/uassetgui/` — All original game items

For each field in each row, it collects every unique value and stores them sorted:

```json
{
    "BuildProcess": {
        "type": "enum",
        "values": ["EBuildProcess::DualMode"]
    },
    "DefaultRequiredMaterials.MaterialHandle.RowName": {
        "type": "name",
        "values": ["Consumable.CaveHoney", "Item.BronzeIngot", "Item.Leather", ...]
    },
    "bOnWall": {
        "type": "bool",
        "values": ["false", "true"]
    }
}
```

### Field Types

| Type | Widget | Example |
|------|--------|---------|
| `enum` | Dropdown combo (non-editable) | BuildProcess, PlacementType, EnabledState |
| `bool` | Checkbox | bOnWall, bOnFloor, bAllowRefunds |
| `int` | Spin box | Damage, Durability, MaxStackSize |
| `float` | Text field with completer | DamageReduction, DropChance, CraftTimeSeconds |
| `name` | Combo with autocomplete | MaterialHandle.RowName, UnlockRequiredItems.RowName |
| `asset` | Text field with autocomplete | Actor (1,093 known asset paths) |
| `tags` | Combo with autocomplete | Gameplay tag strings |
| `text` | Read-only display | DisplayName, Description |

### Field Counts Per Table

| Table | Fields Indexed |
|-------|---------------|
| DT_Constructions | 10 |
| DT_ConstructionRecipes | 43 |
| DT_Armor | 26 |
| DT_Weapons | 28 |
| DT_Tools | 26 |
| DT_Items | 15 |
| DT_Loot | 7 |
| DT_Ores | 16 |
| DT_ItemRecipes | 28 |

---

## Templates

Templates are JSON structures that define the "shape" of a new DataTable row. When you save
a new item, the tool copies a template, fills in your values, and writes it as a per-item file.

### Tobi's Validated Templates (MoreBuildings/ and MoreArmor/)

These were created by Tobi (the mod author) and are known to produce correct game data:

- **ConstructionTemplate.json** — Blank DT_Constructions row
- **ConstructionRecipeTemplate.json** — Blank DT_ConstructionRecipes row
- **ItemRecipeTemplate.json** — Blank DT_ItemRecipes row for armor
- **constructionsImportTemplates.json** — Package + Texture2D import structures
- **ItemTemplate.json** — Single material entry for a recipe
- **CategoryFlags.json** — Placement flags (OnWall, OnFloor, etc.) per building category

### Generated Templates (generated/)

For tables without Tobi-provided templates, row templates were auto-generated from existing
per-item files or vanilla game data. These have the correct UAssetAPI structure but haven't
been manually validated:

- DT_Armor_template.json, DT_Weapons_template.json, DT_Tools_template.json
- DT_Items_template.json, DT_Loot_template.json, DT_Ores_template.json
- DT_ItemRecipes_template.json

---

## First Run and Game Extraction

When the application launches for the first time (or when `data/game_extract/` is missing):

1. **Game Path Dialog** — A dialog asks the user to select their game installation. It
   auto-detects Steam and Epic Games install locations. The path is saved to
   `config.ini [Game] InstallPath`.

2. **Extraction** — The tool uses `retoc` to extract .uasset files from the game's
   IoStore pak archives, then `UAssetGUI` to convert them to JSON. The extraction
   manifest (`data/extraction_manifest.ini`) defines 11 DataTables to extract.

3. **String Tables** — 4 vanilla string tables (Items, Architecture, Interactables,
   CategoryTags) are also extracted to support display name resolution.

Extraction only runs when files are missing. It takes about 2-3 minutes. The extracted
files total about 4.8 GB (which is why they're not shipped with the installer).

### Extraction Manifest

The manifest (`data/extraction_manifest.ini`) uses INI format with one section per table:

```ini
[DT_Constructions]
stem = DT_Constructions
game_path = Moria/Content/Tech/Data/Building/DT_Constructions
shell_group = MoreBuildings
has_imports = true
```

- **stem** — Filter string passed to `retoc --filter`
- **game_path** — Where the file ends up (relative to game_extract/)
- **shell_group** — (optional) Which template group this belongs to
- **has_imports** — (optional) Whether icon import handling is needed

---

## Build Process

The **Build Combined Files** button runs a three-step pipeline that transforms per-item
source files into the final mod DataTables.

### Step 1: Combine Per-Item Files with Vanilla Base

For each of the 11 DataTables in the combine map:

1. Load the vanilla game JSON from `data/game_extract/uassetgui/{game_path}.json`.
   This is the original, unmodified game data.

2. Read all per-item JSON files from `data/Tobis_json/{table}/` (sorted alphabetically
   by filename to ensure consistent ordering).

3. For each per-item file:
   - Merge its `NameMap` entries into the combined file (deduplicated)
   - For DT_Constructions: recalculate Import indices for icon references
     (Package + Texture2D pairs are renumbered based on their position)
   - Append the `Row` to the DataTable's `Exports[0].Table.Data[]` array

4. Write the combined result to `TobisMod/json_data/{game_path}.json`

Architecture is special — it has no vanilla base (it's a mod-only string table) so it
uses an empty scaffold and just concatenates all per-item entries.

### Step 2: Restore Patch 1.2 Constructions

Game patch 1.2 removed 32 construction recipes by changing their unlock type to `Manual`
(which makes them uncraftable). The build pipeline restores these by:

1. Loading `TobisMod/json_data/.../DT_ConstructionRecipes.json`
2. Finding each of the 32 affected recipes by name
3. Setting their `DefaultUnlocks.UnlockType` to `DiscoverDependencies`
4. Special case: `Advanced_Bannister_Post_Stone` gets a custom unlock struct
   requiring `Ore.Granite`

### Step 3: Apply String Table Imports

For the game to resolve mod display names, each DataTable needs import references to the
mod's string tables. The build pipeline appends these from `data/Imports.json`:

| DataTable | String Tables Added |
|-----------|-------------------|
| DT_Constructions | ST_Mod_Architecture + ST_Mod_Interactables (4 import entries) |
| DT_Armor | ST_Mod_Items (2 import entries) |
| DT_Weapons | ST_Mod_Items (2 import entries) |
| DT_Tools | ST_Mod_Items (2 import entries) |
| DT_Items | ST_Mod_Items (2 import entries) |

See [String Table Import System](#string-table-import-system) for the technical details
of how import indices are calculated.

### Build Output

After the build, `TobisMod/json_data/` contains 11 combined DataTable JSON files ready
for conversion back to .uasset format:

```
TobisMod/json_data/
+-- Moria/Content/Tech/Data/Building/
|   +-- DT_Constructions.json         (854 vanilla + 246 custom rows)
|   +-- DT_ConstructionRecipes.json   (814 vanilla + 245 custom rows)
|   +-- Architecture.json             (mod-only string table)
+-- Moria/Content/Tech/Data/Items/
|   +-- DT_Armor.json                 (156 + 4 rows)
|   +-- DT_Weapons.json               (158 + 9 rows)
|   +-- DT_Tools.json                 (41 + 2 rows)
|   +-- DT_Items.json                 (131 + 5 rows)
|   +-- DT_Ores.json                  (41 + 0 rows)
|   +-- DT_ItemRecipes.json           (390 + 42 rows)
+-- Moria/Content/Tech/Data/
|   +-- DT_CategoryTags.json          (+ 5 custom categories)
+-- Moria/Content/Character/AI/
    +-- DT_Loot.json                   (370 + 63 rows)
```

---

## Construction Workflow

Adding a new construction creates **three per-item files**:

1. **Architecture file** (`Tobis_json/Architecture/{tag}.json`) — Display name and
   description for the string table.

2. **DT_Constructions file** (`Tobis_json/DT_Constructions/{tag}.json`) — The construction
   definition with asset path, icon, category tags, and enabled state.

3. **DT_ConstructionRecipes file** (`Tobis_json/DT_ConstructionRecipes/{tag}.json`) — The
   crafting recipe with materials, placement flags, foundation rules, and unlock conditions.

### Construction-Specific Fields

The New Construction tab has fields not found in other tabs:

**DT_Constructions fields:**
- Asset Path — Blueprint path to the in-game 3D model
- Main/Sub Category — Building UI categories (e.g., Deco > Furniture)
- Gameplay Tags — Classification tags
- EnabledState — Live or Disabled

**DT_ConstructionRecipes fields:**
- BuildProcess — DualMode (the only known value)
- LocationRequirement — Anywhere or Base
- PlacementType — FreePlacement or SnapGrid
- FoundationRule — Always, FreePlaced, or Never
- MonumentType — None, or a specific monument type
- Placement checkboxes: On Wall, On Floor, Place On Water, Override Rotation
- Foundation checkboxes: Auto Foundation, Inherit Foundation Stability, Allow Refunds

### Category Flags

When you select a building category (e.g., "Walls", "Furniture", "Banners"), the recipe
fields are auto-populated from `CategoryFlags.json`. For example, "Banners" sets
OnWall=true, OnFloor=false, PlacementType=FreePlacement. You can override these after
the category is selected.

---

## Armor, Weapon, Tool, and Item Workflow

### Common Workflow (all four types)

Each tab has the same left/right pane layout:

**Left pane:**
- **Build Combined Files** button — runs the full pipeline
- Scrollable item list showing all per-item files
- **New** button — clears the form for a new entry
- **Delete** button — removes the selected item and its associated files

**Right pane (scrollable):**
- **Basic Info** — Pack Name (editable with autocomplete from 33 known packs),
  Name, Name Tag (no spaces — auto-replaces with underscores), Description
- **Item fields** — All editable properties for the DataTable (see per-tab details below)
- **Recipe fields** — DT_ItemRecipes properties (if this item type has recipes)
- **Save** button — writes per-item JSON using the Name Tag as the filename

### Creating a New Item

1. Click **New** on the left pane to clear the form
2. Enter the **Pack Name** (e.g., "Tobi")
3. Enter the **Name Tag** — no spaces allowed, use underscores (e.g., `Mereak_Battleaxe`)
4. Fill in the item-specific fields
5. Fill in the recipe fields (materials, unlock conditions)
6. Click **Save** — creates the per-item JSON files in `Tobis_json/`

### NameMap Generation

When saving, the tool automatically builds a complete NameMap for each per-item file
by walking the JSON structure and collecting all referenced strings (field names, enum
values, struct types, property type names, asset paths, gameplay tags). This matches
the format expected by UAssetAPI and the game engine. String table references
(ST_Mod_Items) are added later during the Build Combined step.

### Weapon-Specific: Weapon Type Selector

The New Weapon tab has a **Weapon Type** master-selector dropdown that auto-fills
three fields when you select a weapon type:

| Weapon Type | DamageType | UI Tag | Weapon Type Tag |
|-------------|-----------|--------|-----------------|
| Axe | Damage.Slashing.Axe.1h | UI.Weapon.1h | Item.Weapon.WarAxe |
| Sword | Damage.Slashing.Sword.1h | UI.Weapon.1h | Item.Weapon.Sword.1h |
| Maul | Damage.Bludgeon.Hammer.1h | UI.Weapon.1h | Item.Weapon.Mattock* |
| Spear | Damage.Piercing.Spear | UI.Weapon.1h | Item.Weapon.Spear |
| Battleaxe | Damage.Slashing.Axe.2h | UI.Weapon.2h | Item.Weapon.Battleaxe |
| Greatsword | Damage.Slashing.Sword.2h | UI.Weapon.2h | Item.Weapon.Sword.2h |
| Halberd | Damage.Slashing.Halberd | UI.Weapon.2h | Item.Weapon.Halberd |
| Mattock | Damage.Bludgeon.Hammer.2h | UI.Weapon.2h | Item.Weapon.Hammer* |

*Mattock and Maul weapon type tags are intentionally inverted. This is a known game
bug that we must replicate for compatibility.

The DamageType and Tags fields become read-only when driven by the Weapon Type selector.
Both the UI tag and the Weapon Type tag are injected into the Tags gameplay tag container.
When loading an existing weapon, the selector auto-detects the weapon type from DamageType.

### Weapon and Tool: Broken Variants

When saving a **weapon** (DT_Weapons) or **tool** (DT_Tools), the tool automatically
creates a **Broken_ variant** with identical fields. For example, saving `Mereak_Battleaxe`
also creates `Broken_Mereak_Battleaxe`. This is required because the game uses broken
variants as the degraded state of weapons and tools.

- The broken variant has the same tag with `Broken_` prepended
- No recipe is created for the broken variant (broken items are not craftable)
- If you're saving an item that already starts with `Broken_`, no duplicate is created
- Both files appear in the left pane after save

### Per-Tab Field Details

**DT_Armor (20 fields):** Actor, Icon, Tags, Durability, DamageReduction,
DamageProtection, DamageModifiers, InitialRepairCost (material + count),
SkillsGranted, SkillsRequired, CosmeticOwner, CosmeticConvertCost,
CosmeticAchievement, ItemSetRowHandle, Portability, MaxStackSize, SlotSize,
BaseTradeValue, EnabledState

**DT_Weapons (22 fields):** Weapon Type selector + Actor, Icon, DamageType, Tags,
Damage, Speed, Tier, ArmorPenetration, BlockDamageReduction, StaminaCost,
EnergyCost, Durability, InitialRepairCost, SkillsRequired, CosmeticConvertCost,
ItemSetRowHandle, Portability, MaxStackSize, SlotSize, BaseTradeValue, EnabledState

**DT_Tools (20 fields):** Actor, Icon, Tags, CompatibleToolTags, Durability,
DurabilityDecayWhileEquipped, CarveHits, NpcMiningRate, StaminaCost, EnergyCost,
InitialRepairCost, SkillsRequired, CosmeticConvertCost, ItemSetRowHandle,
Portability, MaxStackSize, SlotSize, BaseTradeValue, EnabledState

**DT_Items (11 fields):** Actor, Icon, Tags, SkillsRequired, CosmeticConvertCost,
ItemSetRowHandle, Portability, MaxStackSize, SlotSize, BaseTradeValue, EnabledState

### Recipe Fields (DT_ItemRecipes)

All four types share the same recipe table. The recipe fields shown are:

- **ResultItemCount** — How many items the recipe produces
- **CraftTimeSeconds** — How long crafting takes
- **bCanBePinned** — Whether the recipe can be pinned to the HUD
- **bNpcOnlyRecipe** — Whether only NPCs can use this recipe
- **EnabledState** — Live, Disabled, or DevelopmentOnly

Plus the materials section (up to 6 materials with per-row trash icons, category
and name autocomplete showing "Display Name (tag)" format, and count spinner)
and the unlock conditions (Discover Item or Discover Construction radio toggle
with searchable combo).

### Items Without Recipes

Some items (like CeibaWood or CeibaCutting) exist in DT_Items but have no matching
recipe in DT_ItemRecipes. When you select such an item, the recipe section clears
to defaults so stale data from the previous selection doesn't persist.

---

## Loot and Ore Workflow

### Loot (DT_Loot)

Loot entries define drop tables — what items can drop from breakables, creatures, or
environmental objects. There is no crafting recipe. Fields:

- **DropChance** — Probability (0.0 to 1.0) that this item drops
- **MinQuantity** / **MaxQuantity** — Range of how many drop
- **RequiredTags** — Gameplay tags that must be present for this drop to occur
- **EnabledState** — Live or Disabled

### Ores (DT_Ores)

Ores define minable minerals. They're similar to regular items but have a unique
**Mineral** field that links to the voxel/mining system. There is no crafting recipe.
Currently there are no custom ore per-item files — only the 41 vanilla entries exist.

---

## Localization Pipeline

The Localization tab provides three operations:

1. **PO to CSV** — Converts `.po` translation files (used by translators) to `.csv`
   format (used by the game's localization system)

2. **CSV to PO** — Converts back from CSV to PO for editing

3. **Build Localization Pak** — Packages the localization files into a `.pak` file
   using UnrealPak. This pak file is what gets installed alongside the mod.

Supported languages: English (source), German, Spanish, French.

Translation files are in `Localization/{lang}/Game.po`. The PO format includes
context strings like `ST_Mod_Architecture,TobiPack_AleKeg_A.Name` to identify
which string table entry each translation belongs to.

---

## Color Variants

The Color Variants tab has one button: **Patch Colour-Variant Recipes**.

It automatically links Black, White, and Gold armour variants to their base items.
For example, if there's a "Shayar Helmet" with White, Black, and Gold variants,
this patch sets all three variants' unlock type to `DiscoverDependencies` so that
discovering any one variant unlocks the recipe for all of them.

The patch operates on `DT_ItemRecipes` by:
1. Finding recipes with `_White_`, `_Black_`, or `_Gold_` in their name
2. Extracting the base item name (stripping the colour suffix)
3. Setting the unlock type and base unlock requirement

---

## Configuration

`config.ini` is created on first run. Available settings:

| Section | Key | Default | Purpose |
|---------|-----|---------|---------|
| [General] | Debug | false | Enable verbose debug logging |
| [Paths] | ProjectRoot | (auto) | Repository root directory |
| [Paths] | UE4Root | (auto) | UE4.27 installation (needed for UnrealPak) |
| [Localization] | SourcePO | Localization/en/Game.po | Source translation file |
| [Localization] | TargetLang | fr | Target language for translation |
| [Localization] | PakFileName | (auto) | Output pak filename |
| [Game] | InstallPath | (set on first run) | Game installation path |
| [Game] | InstallType | (set on first run) | Steam, Epic Games, or Custom |
| [ModTool] | DataDir | data | Root data directory |

---

## File Formats

All JSON files use the UAssetAPI serialization format. Understanding this format is
essential for working with the mod tool.

### DataTable JSON Structure

```json
{
    "$type": "UAssetAPI.UAsset, UAssetAPI",
    "Info": "Serialized with UAssetAPI",
    "NameMap": ["string1", "string2", ...],
    "Imports": [
        { "$type": "UAssetAPI.Import, UAssetAPI", "ObjectName": "...", ... }
    ],
    "Exports": [
        {
            "Table": {
                "Data": [
                    { "Name": "RowName", "Value": [...properties...] },
                    ...
                ]
            },
            "SerializationBeforeCreateDependencies": [-5, -7, ...],
            ...
        }
    ]
}
```

- **NameMap** — All string identifiers used in the file
- **Imports** — External asset references (Packages, Textures, StringTables)
- **Exports[0].Table.Data** — Array of DataTable rows
- **SerializationBeforeCreateDependencies** — Indices of Imports that must be loaded
  before the DataTable can be created

### Property Types

Each property in a row's `Value` array has a `$type` field indicating its type:

| $type | Name | Stores |
|-------|------|--------|
| `EnumPropertyData` | Enum | `"EBuildProcess::DualMode"` |
| `BoolPropertyData` | Bool | `true` / `false` |
| `IntPropertyData` | Integer | `42` |
| `FloatPropertyData` | Float | `3.14` |
| `TextPropertyData` | Text | String table reference |
| `NamePropertyData` | Name | String identifier |
| `ObjectPropertyData` | Object | Negative index into Imports |
| `SoftObjectPropertyData` | Asset | `{ "AssetPath": { "AssetName": "/Game/..." } }` |
| `ArrayPropertyData` | Array | `[ ...elements... ]` |
| `StructPropertyData` | Struct | `{ "Value": [ ...properties... ] }` |
| `GameplayTagContainerPropertyData` | Tags | `["Tag.SubTag.Name", ...]` |

### Architecture JSON Structure (String Table)

```json
{
    "$type": "UAssetAPI.UAsset, UAssetAPI",
    "Exports": [
        {
            "Table": {
                "TableNamespace": "",
                "Value": [
                    ["TobiPack_AleKeg_A.Name", "Ale Keg"],
                    ["TobiPack_AleKeg_A.Description", "A keg of ale"],
                    ...
                ]
            }
        }
    ]
}
```

---

## Import Index System

Imports use **negative 1-based indices**. This is one of the trickiest parts of the
UAssetAPI format and is critical to understand for the build pipeline.

### How It Works

The `Imports` array is referenced using negative numbers starting at -1:

```
Imports[0]  →  referenced as -1
Imports[1]  →  referenced as -2
Imports[2]  →  referenced as -3
...
Imports[N]  →  referenced as -(N+1)
```

For example, if a construction's `Icon` field has value `-1647`, the icon texture is
at `Imports[1646]` (absolute value minus one gives the 0-based index).

### Package + Texture2D Pairs

Each construction icon requires two Import entries:

1. **Package** — Points to the texture's package path. `OuterIndex = 0` (no parent).
2. **Texture2D** — The actual texture. `OuterIndex` points to its Package entry.

During the Build step, when per-item files are appended to the vanilla base, these
indices are recalculated because the Import array grows:

```
If vanilla has 1000 imports and we add item at position 1000:
  Package goes at index 1000 → referenced as -1001
  Texture2D goes at index 1001 → OuterIndex = -1001 (points to Package)
  Icon value = -1002 (points to Texture2D)
```

---

## String Table Import System

For the game to resolve mod display names (like "Gimli's Map" for tag
`100BuildingsPack_GimlisMap_A`), each combined DataTable needs Import entries
that reference the mod's string tables.

### How It Works

The string table imports are defined in `data/Imports.json` as Package + StringTable
pairs. During the build pipeline's Step 3, these are appended to each DataTable's
Imports array.

For each pair:
1. The **Package** entry is appended with `OuterIndex = 0` (no parent)
2. The **StringTable** entry's `OuterIndex` is recalculated to point to its Package
3. The StringTable's position (negative 1-based) is added to
   `SerializationBeforeCreateDependencies` so the game loads it before the DataTable

### Example

If `DT_Armor` has 23 existing imports and we append the ST_Mod_Items pair:

```
Package goes at Imports[23]    → OuterIndex = 0 (no parent)
StringTable goes at Imports[24] → OuterIndex = -24 (points to Package at [23])
SerializationBeforeCreateDependencies gets -25 (StringTable position)
```

### Which Tables Get Which String Tables

```
data/Imports.json entries:
  [0-1]  ST_Mod_Architecture      → applied to DT_Constructions
  [2-3]  ST_Mod_Interactables     → applied to DT_Constructions
  [4-5]  ST_Mod_Effects           → (reserved, not currently applied)
  [6-7]  ST_Mod_Items             → applied to DT_Armor, DT_Weapons, DT_Tools, DT_Items
```

The build pipeline deep-copies each import pair before reindexing, so the same source
entries can safely be applied to multiple DataTables with different Import array sizes.

---

## External Toolchain

| Tool | Purpose | Command |
|------|---------|---------|
| **retoc** | Extract .uasset from IoStore paks | `retoc to-legacy --version UE4_27 --filter {stem} {paks_dir} {output}` |
| **UAssetGUI** | Convert .uasset to JSON | `UAssetGUI tojson {input} {output} VER_UE4_27` |
| **UnrealPak** | Package localization .pak files | `UnrealPak {output.pak} -create={paklist} -compress` |
| **Inno Setup** | Build Windows installer | `ISCC.exe /DMyAppVersion={ver} RtoMModTools.iss` |
| **PyInstaller** | Build standalone .exe | `pyinstaller build/RtoMModTools.spec --noconfirm` |

**Important version strings:** retoc uses `UE4_27` while UAssetGUI uses `VER_UE4_27`.
These are different strings and using the wrong one will produce errors.

---

## Build and Release Pipeline

The release build is managed by `build/build_release.py` and creates both a standalone
exe and a Windows installer.

### Build Steps

1. **Sync Export** — Copies localization files to `build/staging/`
2. **PyInstaller** — Builds `RtoMModTools.exe` (single-file, ~46 MB)
3. **Copy to Release** — Places exe in `release/`
4. **Inno Setup** — Compiles `RtoMModTools_Setup_v{version}.exe` installer (~52 MB)

### What the Installer Packages

The Inno Setup installer bundles:
- The PyInstaller exe (which embeds all Python code and PySide6)
- `utilities/` (retoc, UAssetGUI, oo2core DLL)
- `data/templates/` (all template files)
- `data/field_values/` (all autocomplete indexes)
- `data/Tobis_json/` (all per-item source files)
- `data/extraction_manifest.ini` and `data/Imports.json`
- `Localization/` files
- `assets/icons/` (app icon)

**Not included:** `data/game_extract/` (4.8 GB, regenerated from user's game on first run)

### Known Build Issue

OneDrive file locking can cause `PermissionError` during the sync step. If this happens,
retry with `--skip-sync` to reuse existing staging files:

```bash
python build/build_release.py --skip-sync
```

---

## Mod Pack Registry

The mod includes 26+ building/construction packs from various contributors:

| Pack | Contributor | Items |
|------|------------|-------|
| 100BuildingsPack | Various | Gimli's Map, Granite barriers/walls, Guard Statue, lanterns, Telchar Forge |
| AradrenPack | Aradren | Column bases, capitals, shafts, wall variants |
| CeibaPack | — | Ceiba wood constructions |
| CurvedPack | — | Curved wall variants |
| DrainPumpPack | — | Drain pump construction |
| GlitteringCavesLampsPack | — | Glittering Caves themed lamps |
| GrumniPack | Grumni | Archways, various constructions |
| JuboPack | Jubo | Various constructions |
| KelaerielPack | Kelaeriel | Various constructions |
| KingdomBannersPack | — | Kingdom-themed banners |
| MereakPack | Mereak | Battle axes, constructions |
| MithrilWallsPack | — | Mithril wall variants |
| OlfahrPack | Olfahr | Various constructions |
| RailingsPack | — | Railing variants |
| SeraniPack | Serani | Various constructions |
| SilverWallsPack | — | Silver wall variants |
| StreetLampPack | — | Street lamp variants |
| TobiDurinPack | Tobi | Durin-themed constructions |
| TobiFloorPack | Tobi | Floor variants |
| TobiPack | Tobi | General constructions (ale kegs, crafting stations, etc.) |
| UzbadPack | Uzbad | Various constructions |
| VasePack | — | Decorative vases |
| ZetaPack | Zeta | Various constructions |

---

## Glossary

| Term | Definition |
|------|-----------|
| **DataTable** | UE4 data structure storing typed rows. Each row has a unique name (tag) and typed properties. Exported as JSON by UAssetGUI. |
| **IoStore** | UE4 packaging format (.ucas/.utoc/.pak). The game ships data in this format. Extracted to legacy .uasset by retoc. |
| **Per-item file** | A single JSON file in `Tobis_json/` representing one custom item. Contains NameMap, Imports, and Row. |
| **Vanilla base** | The original, unmodified game DataTable JSON from `game_extract/uassetgui/`. Used as the starting point for Build. |
| **Combined file** | Build output — vanilla base with all custom per-item rows appended. Written to `TobisMod/json_data/`. |
| **String table** | UE4 asset mapping keys to localized text. Used for display names and descriptions. |
| **Tag** | The unique row name for an item (e.g., `TobiPack_AleKeg_A`). Used as the filename for per-item files. |
| **NameMap** | Array of string identifiers in a UAsset file. All strings used by the asset must be in this array. |
| **Imports** | Array of external asset references in a UAsset file. Referenced by negative 1-based indices. |
| **BWG** | Black/White/Gold — colour variants of cosmetic armour sets. |
| **retoc** | Tool for converting between IoStore and legacy UE4 asset formats. Version string: `UE4_27`. |
| **UAssetGUI** | Tool for converting between .uasset binary and JSON text. Version string: `VER_UE4_27`. |
| **MaterialPicker** | GUI component for selecting crafting materials with category, display name, count, and per-row delete. |
| **UnlockPicker** | GUI component for selecting unlock conditions (Discover Item or Discover Construction). |
| **TabConfig** | Dataclass that defines which fields a generic item tab displays. Adding a new tab only requires a new TabConfig. |
| **Field values** | Pre-built autocomplete indexes in `data/field_values/`. One JSON file per DataTable. |
| **Architecture** | The mod's string table for construction display names and descriptions. Not a vanilla game table. |
