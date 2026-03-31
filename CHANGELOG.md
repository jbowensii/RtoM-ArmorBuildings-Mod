# Changelog

## v3.2.0 (2026-03-31)

### New Features

- **New/Save/Delete workflow** — All item tabs have New, Save, and Delete buttons.
  New clears the form, Save writes per-item JSON using the Name Tag as filename,
  Delete removes the selected item and its associated files.
- **Weapon Type master-selector** — New Weapon tab has a dropdown (Axe, Sword, Maul,
  Spear, Battleaxe, Greatsword, Halberd, Mattock) that auto-fills DamageType, UI Tag,
  and Weapon Type Tag. Driven fields become read-only.
- **Broken variant auto-creation** — Saving a weapon or tool automatically creates a
  Broken_ duplicate (e.g., saving Mereak_Battleaxe also creates Broken_Mereak_Battleaxe).
- **All fields displayed** — Every field from the game DataTables is now shown on the
  right pane with indexed autocomplete:
  - DT_Armor: 20 fields (Actor, Icon, Tags, DamageModifiers, InitialRepairCost, etc.)
  - DT_Weapons: 22 fields (DamageType, Tags, Damage, Speed, Tier, etc.)
  - DT_Tools: 20 fields (CompatibleToolTags, CarveHits, NpcMiningRate, etc.)
  - DT_Items: 11 fields (Actor, Icon, Tags, SkillsRequired, etc.)
- **Type/tag dropdowns** — Gameplay tag dropdowns on all tabs (Armor 34 tags, Weapons 23,
  Tools 36, Items 25, Loot 159, Ores 8) plus CompatibleToolTags and DamageType.
- **Unified PackNames** — 33 pack names indexed across all 9 tabs with autocomplete.
- **Complete NameMap generation** — Save builds a proper NameMap by walking the row
  structure (field names, enum values, asset paths, gameplay tags, struct types).
- **Name Tag validation** — Auto-replaces spaces with underscores on all tabs.

### Improvements

- **174 automated tests** (up from 83) with 30% overall coverage:
  - config.py 99%, mod_utils 98%, json_split_combine 96%
  - json_handler 90%, colour_variants 81%, field_helpers 78%
- **Knowledge base rewritten** — 1,100+ lines covering weapon type rules, broken
  variants, New/Save workflow, per-tab field lists, NameMap generation.
- **Fixed tag indexes** — Gameplay tags were being split into individual characters;
  now properly collected as full tag strings from game data.
- **Fixed SkillsGranted/SkillsRequired** — Tag indexes rebuilt correctly (14 skills
  for armor, 12 for tools, etc.)

### Technical

- Dotted field name support (DamageType.TagName, Tags.Tags) for loading and saving
  nested struct values through the generic tab system.
- Master-selector pattern in TabConfig — reusable for any tab needing auto-fill rules.
- `_BROKEN_VARIANT_TABLES` frozenset for clean conditional logic.
- `_collect_namemap_strings` / `_collect_from_dict` extracted to module level for
  pylint compliance and testability.
- Pylint 10.00/10 maintained throughout.

---

## v3.1.1 (2026-03-28)

### Features

- **ST_Mod_Items imports** — Build Combined Files now appends string table imports
  to DT_Armor, DT_Weapons, DT_Tools, and DT_Items (previously only DT_Constructions).
- **Display names from game string tables** — 1,521 tag-to-display-name mappings
  extracted from 4 vanilla string tables + mod Game.po.
- **Material picker "Display Name (tag)" format** — Dropdowns show human-readable
  names with the game tag in parentheses.

---

## v3.1.0 (2026-03-28)

### Features

- **9 application tabs** — New Construction, New Armor, New Weapon, New Tool,
  New Item, New Loot, New Ore, Localization, Color Variants.
- **Generic ItemAdderTab** — One reusable tab class for all item types, driven
  by TabConfig dataclass.
- **Field-value indexes** — Autocomplete for all 9 DataTables from both mod and
  vanilla game data (de-duped, sorted).
- **Generated templates** — Row templates for 7 tables auto-generated from
  existing per-item files or vanilla data.
- **Build pipeline consolidation** — Build Combined Files runs combine + restore
  1.2 constructions + string table imports in one click.
- **Shared helpers** — MaterialPicker, UnlockPicker, field_helpers extracted as
  reusable modules.

### Code Quality

- **Pylint 10.00/10** (from 7.16)
- Dead code removed: 3 obsolete tabs, armor package, duplicate material picker.
- Net reduction: ~1,200 lines removed from codebase.

---

## v3.0.0 (2026-03-18)

### Features

- Per-item JSON files — each construction/armor saved as its own editable file.
- Game extraction — retoc + UAssetGUI extract vanilla DataTables on first run.
- Directory restructure — clean separation of templates, game_extract, Tobis_json.
- 621 custom items extracted across 9 DataTables.
- UI improvements — left pane item list, Build/Delete buttons, game path dialog.
- Installer size down from 68.6 MB to 51.5 MB.
