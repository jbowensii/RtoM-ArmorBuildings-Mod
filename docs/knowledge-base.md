# RtoM Mod Tools — Knowledge Base

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Directory Layout](#directory-layout)
- [First Run & Game Extraction](#first-run--game-extraction)
- [Construction Workflow](#construction-workflow)
- [Armor Workflow](#armor-workflow)
- [Build Process](#build-process)
- [Maintainer Tabs](#maintainer-tabs)
- [Localization Pipeline](#localization-pipeline)
- [Configuration](#configuration)
- [File Formats](#file-formats)
- [External Toolchain](#external-toolchain)
- [Mod Pack Registry](#mod-pack-registry)
- [Glossary](#glossary)

---

## Overview

RtoM Mod Tools is a PySide6 desktop application for managing the **Secrets of Khazad-Dum** mod for *The Lord of the Rings: Return to Moria*. The mod adds cosmetic armour sets and 28+ building/construction packs to the game.

The tool provides:

- **New Construction** — Add custom constructions with materials, categories, and unlock conditions
- **New Armor** — Add custom armor recipes with crafting stations and materials
- **Buildings Maintainer** — Restore 1.2-removed constructions, apply string table imports
- **Armor Maintainer** — Restore BWG colour variants, unlock sandbox items for campaign
- **Localization** — PO/CSV conversion and pak packaging
- **Recipes** — Auto-link colour variants to base recipes

---

## Architecture

The application is a Python package installed to `%LOCALAPPDATA%\RtoMModTools\`.

| Module | Purpose |
|--------|---------|
| `main.py` | Entry point — first-run checks, launches GUI |
| `src/config.py` | Config singleton — reads config.ini, exposes all paths |
| `src/gui/main_window.py` | Main window with tabbed interface |
| `src/gui/shared.py` | Shared GUI helpers — material pickers, item list, build action |
| `src/gui/construction_adder_tab.py` | New Construction tab |
| `src/gui/armor_adder_tab.py` | New Armor tab |
| `src/gui/construction_updater_tab.py` | Buildings Maintainer tab |
| `src/gui/armor_updater_tab.py` | Armor Maintainer tab |
| `src/gui/game_path_dialog.py` | First-run game path selection |
| `src/gui/extraction_dialog.py` | Extraction progress dialog |
| `src/construction/mod_utils.py` | Construction per-item file writers |
| `src/armor/mod_utils.py` | Armor per-item file writers |
| `src/utils/json_split_combine.py` | Combine per-item files with vanilla base |
| `src/utils/game_extractor.py` | Game file extraction via retoc + UAssetGUI |
| `src/utils/json_handler.py` | JSON load/save utilities |
| `src/recipes/colour_variants.py` | Auto-link BWG colour variants |
| `src/localization/` | PO/CSV conversion modules |
| `src/packaging/pak_locres.py` | Pak file packaging |

---

## Directory Layout

Installed application directory (`%LOCALAPPDATA%\RtoMModTools\`):

```
RtoMModTools/
+-- RtoMModTools.exe
+-- config.ini
+-- utilities/
|   +-- retoc.exe
|   +-- UAssetGUI.exe
|   +-- oo2core_9_win64.dll
+-- data/
|   +-- extraction_manifest.ini
|   +-- Imports.json
|   +-- templates/                  [shipped with installer]
|   |   +-- MoreBuildings/          Construction JSON templates
|   |   +-- MoreArmor/              Armor JSON templates
|   |   +-- ConstructiondDT/        Single-row DT templates
|   |   +-- RtoMMoreBuildings_P/    More Buildings plugin
|   +-- game_extract/               [generated on first run]
|   |   +-- retoc/                  .uasset/.uexp intermediates
|   |   |   +-- Moria/Content/...
|   |   +-- uassetgui/              Vanilla JSON DataTables
|   |       +-- Moria/Content/Tech/Data/Building/
|   |       +-- Moria/Content/Tech/Data/Items/
|   |       +-- Moria/Content/Character/AI/
|   +-- Tobis_json/                 [per-item source files]
|       +-- Architecture/           Name/description pairs
|       +-- DT_Constructions/       Construction definitions
|       +-- DT_ConstructionRecipes/ Construction recipes
|       +-- DT_ItemRecipes/         Armor recipes
+-- TobisMod/
|   +-- json_data/                  [build output]
|       +-- Moria/Content/...       Combined DataTables
+-- localization/
    +-- en/, de/, es/, fr/
    +-- ModLocalization/
```

---

## First Run & Game Extraction

On first launch:

1. **Game Path Dialog** — Select game installation (Steam, Epic Games, or custom path). Auto-detects known install locations. Saved to `config.ini [Game]`.

2. **Extraction** — Uses `retoc` to extract .uasset files from the game's IoStore paks, then `UAssetGUI` to convert them to JSON. The manifest (`data/extraction_manifest.ini`) defines 11 DataTables to extract.

Extracted files serve as the vanilla baseline for the Build step. Extraction only runs when files are missing — it won't re-extract on subsequent launches unless the user deletes `data/game_extract/`.

### Extracted DataTables

- DT_Constructions, DT_ConstructionRecipes (Building)
- DT_ItemRecipes, DT_Armor, DT_Weapons, DT_Items, DT_Consumables, DT_Ores, DT_Tools (Items)
- DT_CategoryTags (Tech Data)
- DT_Loot (Character/AI)

---

## Construction Workflow

Adding a new construction creates **three per-item files**:

1. `Tobis_json/Architecture/{tag}.json` — Display name and description
2. `Tobis_json/DT_Constructions/{tag}.json` — Definition (asset path, icon, category, imports)
3. `Tobis_json/DT_ConstructionRecipes/{tag}.json` — Recipe (materials, flags, unlock condition)

Tag format: `{UserName}Pack_{Name}_{Letter}` where the letter (A-Z) is auto-assigned as the first unused suffix.

### Per-Item File Format (DT row)

```json
{
    "NameMap": ["TobiPack_AleKeg", "/Game/path/..."],
    "Imports": [{"Package..."}, {"Texture2D..."}],
    "Row": { "Name": "TobiPack_AleKeg", "Value": [...] }
}
```

- `NameMap` — String identifiers relevant to this item
- `Imports` — Package + Texture2D imports for the icon (DT_Constructions only; empty `[]` for recipes)
- `Row` — The DataTable row object

### Per-Item File Format (Architecture)

```json
{
    "Entries": [
        ["TobiPack_AleKeg.Name", "Ale Keg"],
        ["TobiPack_AleKeg.Description", "A keg of ale"]
    ]
}
```

---

## Armor Workflow

Adding a new armor recipe creates **one per-item file**:

- `Tobis_json/DT_ItemRecipes/{armor_tag}.json`

Available armor tags come from `data/templates/MoreArmor/Armor.json`. Items that already have per-item files are excluded from the dropdown.

---

## Build Process

Clicking **Build Combined Files** runs `combine_all()`:

1. For each table (Architecture, DT_Constructions, DT_ConstructionRecipes, DT_ItemRecipes):
   - Load the vanilla base from `game_extract/uassetgui/{game_path}.json`
   - Read all per-item files from `Tobis_json/{table}/` (sorted alphabetically)
   - Merge NameMap entries (deduplicated)
   - Append each row to the DataTable
   - For DT_Constructions: recalculate Import indices for icon references
2. Write combined output to `TobisMod/json_data/{game_path}.json`

Architecture uses an empty scaffold (no vanilla base) since it's a mod-only string table.

---

## Maintainer Tabs

After Build, the Maintainer tabs apply game-specific patches directly to `TobisMod/json_data/`:

### Buildings Maintainer

1. **Restore Constructions** — Re-enables 33 constructions removed in game patch 1.2 by changing their unlock type to `DiscoverDependencies`
2. **Update Mod** — Applies string table imports to DT_Constructions for the mod's Architecture string table

### Armor Maintainer

1. **Restore BWG** — Re-enables White/Black/Gold colour variants by changing unlock type and setting dependency references
2. **Sandbox to Campaign** — Unlocks 21 sandbox-exclusive items for campaign mode

---

## Localization Pipeline

1. **PO to CSV** — Converts PO translation files to CSV format for the game
2. **CSV to PO** — Converts back for translator editing
3. **Pak Locres** — Packages localization CSVs into .pak format using UnrealPak

Supported languages: English (source), German, Spanish, French.

---

## Configuration

`config.ini` sections:

| Section | Key | Purpose |
|---------|-----|---------|
| [General] | Debug | Enable debug logging (true/false) |
| [Paths] | ProjectRoot | Repository root directory |
| [Paths] | UE4Root | UE4.27 installation directory |
| [Localization] | SourcePO, TargetLang, PakFileName | Localization settings |
| [Game] | InstallPath | Game installation path (set on first run) |
| [Game] | InstallType | Steam, Epic Games, or Custom |
| [ModTool] | DataDir | Root data directory (default: data) |

---

## File Formats

All JSON files use the UAssetAPI serialization format. Key structures:

- **DataTable** — `Exports[0].Table.Data[]` is an array of row objects, each with a `Name` field as the unique key
- **Architecture (String Table)** — `Exports[0].Table.Value[]` is an array of `[key, value]` pairs
- **NameMap** — Array of string identifiers used by the asset
- **Imports** — Array of external asset references (Packages, Textures) linked via negative indices

### Import Index System

Imports use 1-based negative indices. For example, `Icon: -1647` means the icon texture is at import position `abs(-1647) - 1 = 1646` (0-based). Each construction has a Package import (OuterIndex=0) and a Texture2D import (OuterIndex pointing to its Package). During the Build/combine step, these indices are recalculated as items are appended to the vanilla base.

---

## External Toolchain

| Tool | Purpose | Command |
|------|---------|---------|
| retoc | Extract .uasset from IoStore paks | `retoc to-legacy --version UE4_27 --filter {stem} {paks_dir} {output}` |
| UAssetGUI | Convert .uasset to JSON | `UAssetGUI tojson {input} {output} VER_UE4_27` |
| UnrealPak | Package localization .pak files | Via `src/packaging/pak_locres.py` |

**Important:** retoc uses `UE4_27` while UAssetGUI uses `VER_UE4_27` — the version prefix differs between tools.

---

## Mod Pack Registry

The mod includes 28+ building/construction packs from various contributors:

- 100BuildingsPack
- AradrenPack
- BearGuildPack
- CeibaPack
- CurvedPack
- DrainPumpPack
- FungalPack
- GlitteringCavesLampsPack
- JuboPack
- KelaerielPack
- KingdomBannersPack
- KingsWeaponsPack
- MereakPack (+ MereakAxePack)
- MithrilWallsPack
- NoobDelux_Banner
- OlfahrPack
- RailingsPack
- SeraniPack
- SilverWallsPack
- StreetLampPack
- TobiDoorsPack
- TobiDurinPack
- TobiFloorPack
- TobiPack
- UzbadPack
- VasePack
- ZetaPack

---

## Glossary

| Term | Definition |
|------|-----------|
| **DataTable** | UE4 data structure storing typed rows. Exported as JSON by UAssetGUI. |
| **IoStore** | UE4 packaging format (.ucas/.utoc). Extracted to legacy .uasset by retoc. |
| **Per-item file** | Single JSON file in `Tobis_json/` representing one custom construction or armor recipe. |
| **Vanilla base** | Extracted game DataTable JSON from `game_extract/uassetgui/`. Used as the starting point for Build. |
| **Combined file** | Build output — vanilla base + all per-item rows merged into one file at `TobisMod/json_data/`. |
| **BWG** | Black/White/Gold — colour variants of cosmetic armour sets. |
| **retoc** | Tool for converting between IoStore and legacy UE4 asset formats. Uses `UE4_27`. |
| **UAssetGUI** | Tool for converting between .uasset binary and JSON text format. Uses `VER_UE4_27`. |
| **Shell** | Legacy term for vanilla-only base file. Now refers to the extracted game JSON in `game_extract/uassetgui/`. |
