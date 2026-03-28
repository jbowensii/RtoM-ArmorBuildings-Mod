"""Tests for src.gui.shared — build pipeline helpers."""

import json
import os
import pytest

from src.gui.shared import (
    _find_prop, _restore_constructions,
    _append_string_table_imports, _update_all_mod_imports,
)


class TestFindProp:
    """Tests for _find_prop()."""

    def test_finds_matching_prop(self):
        values = [
            {"Name": "Alpha", "Value": 1},
            {"Name": "Beta", "Value": 2},
        ]
        result = _find_prop(values, "Beta")
        assert result["Value"] == 2

    def test_returns_none_on_miss(self):
        values = [{"Name": "Alpha", "Value": 1}]
        assert _find_prop(values, "Missing") is None

    def test_empty_list(self):
        assert _find_prop([], "Any") is None


class TestRestoreConstructions:
    """Tests for _restore_constructions()."""

    def test_restores_matching_recipes(self, tmp_path):
        data = {
            "Exports": [{"Table": {"Data": [
                {
                    "Name": "Elder_Archway_A",
                    "Value": [{
                        "Name": "DefaultUnlocks",
                        "Value": [
                            {"Value": "EMorRecipeUnlockType::Manual"},
                            {}, {}, {},
                        ],
                    }],
                },
                {
                    "Name": "SomeOtherItem",
                    "Value": [{
                        "Name": "DefaultUnlocks",
                        "Value": [
                            {"Value": "EMorRecipeUnlockType::Manual"},
                        ],
                    }],
                },
            ]}}],
        }
        path = tmp_path / "DT_ConstructionRecipes.json"
        path.write_text(json.dumps(data), encoding="utf-8")

        count = _restore_constructions(str(tmp_path))
        assert count == 1

        with open(path, "r", encoding="utf-8") as f:
            result = json.load(f)
        elder = result["Exports"][0]["Table"]["Data"][0]
        unlock_val = elder["Value"][0]["Value"][0]["Value"]
        assert unlock_val == "EMorRecipeUnlockType::DiscoverDependencies"
        other = result["Exports"][0]["Table"]["Data"][1]
        other_val = other["Value"][0]["Value"][0]["Value"]
        assert other_val == "EMorRecipeUnlockType::Manual"

    def test_returns_zero_on_missing_file(self, tmp_path):
        assert _restore_constructions(str(tmp_path)) == 0


class TestAppendStringTableImports:
    """Tests for _append_string_table_imports()."""

    def _make_dt(self, tmp_path, name, num_existing=1):
        """Create a minimal DataTable JSON with existing imports."""
        dt = {
            "Imports": [
                {"ObjectName": f"Existing_{i}", "OuterIndex": 0,
                 "ClassName": "Package"}
                for i in range(num_existing)
            ],
            "Exports": [{
                "SerializationBeforeCreateDependencies": [],
            }],
        }
        path = tmp_path / f"{name}.json"
        path.write_text(json.dumps(dt), encoding="utf-8")
        return str(path)

    def test_appends_package_and_stringtable(self, tmp_path):
        path = self._make_dt(tmp_path, "DT_Test", num_existing=3)
        entries = [
            {"$type": "UAssetAPI.Import, UAssetAPI",
             "ObjectName": "/Game/Mods/ST_Mod_Items",
             "OuterIndex": 0, "ClassName": "Package"},
            {"$type": "UAssetAPI.Import, UAssetAPI",
             "ObjectName": "ST_Mod_Items",
             "OuterIndex": -1, "ClassName": "StringTable"},
        ]
        _append_string_table_imports(path, entries)

        with open(path, "r", encoding="utf-8") as f:
            result = json.load(f)
        # 3 existing + 2 new = 5
        assert len(result["Imports"]) == 5

    def test_reindexes_outer_index(self, tmp_path):
        """StringTable OuterIndex should point to its Package's position."""
        path = self._make_dt(tmp_path, "DT_Test", num_existing=5)
        entries = [
            {"ObjectName": "PKG", "OuterIndex": 0, "ClassName": "Package"},
            {"ObjectName": "ST", "OuterIndex": -1, "ClassName": "StringTable"},
        ]
        _append_string_table_imports(path, entries)

        with open(path, "r", encoding="utf-8") as f:
            result = json.load(f)
        # Package goes at position -6 (5 existing + 1st new, 1-based negative)
        # StringTable should point to Package = -(5 + 1) = -6
        st_entry = result["Imports"][-1]
        assert st_entry["OuterIndex"] == -6

    def test_adds_serial_dep(self, tmp_path):
        """StringTable position should be added to SerializationBeforeCreateDependencies."""
        path = self._make_dt(tmp_path, "DT_Test", num_existing=5)
        entries = [
            {"ObjectName": "PKG", "OuterIndex": 0, "ClassName": "Package"},
            {"ObjectName": "ST", "OuterIndex": -1, "ClassName": "StringTable"},
        ]
        _append_string_table_imports(path, entries)

        with open(path, "r", encoding="utf-8") as f:
            result = json.load(f)
        deps = result["Exports"][0]["SerializationBeforeCreateDependencies"]
        # StringTable is at position 7 (5 existing + 2 new), 1-based neg = -7
        assert -7 in deps

    def test_skips_missing_file(self, tmp_path):
        # Should not raise
        _append_string_table_imports(
            str(tmp_path / "nonexistent.json"),
            [{"ObjectName": "X", "OuterIndex": 0, "ClassName": "Package"}],
        )

    def test_does_not_mutate_source_entries(self, tmp_path):
        """Entries should be deep-copied so reuse across tables is safe."""
        path1 = self._make_dt(tmp_path, "DT_A", num_existing=3)
        path2 = self._make_dt(tmp_path, "DT_B", num_existing=10)
        entries = [
            {"ObjectName": "PKG", "OuterIndex": 0, "ClassName": "Package"},
            {"ObjectName": "ST", "OuterIndex": -1, "ClassName": "StringTable"},
        ]
        _append_string_table_imports(path1, entries)
        _append_string_table_imports(path2, entries)

        # Verify each got different OuterIndex values
        with open(path1, "r", encoding="utf-8") as f:
            r1 = json.load(f)
        with open(path2, "r", encoding="utf-8") as f:
            r2 = json.load(f)
        # DT_A: 3 existing, ST OuterIndex = -(3+1) = -4
        assert r1["Imports"][-1]["OuterIndex"] == -4
        # DT_B: 10 existing, ST OuterIndex = -(10+1) = -11
        assert r2["Imports"][-1]["OuterIndex"] == -11


class TestUpdateAllModImports:
    """Tests for _update_all_mod_imports()."""

    def test_applies_to_constructions_and_items(self, tmp_path):
        """All 5 DataTables should get their string table imports."""
        # Create directory structure
        building = tmp_path / "Moria" / "Content" / "Tech" / "Data" / "Building"
        building.mkdir(parents=True)
        items = tmp_path / "Moria" / "Content" / "Tech" / "Data" / "Items"
        items.mkdir(parents=True)

        # Create minimal DataTable JSONs
        for name, parent in [
            ("DT_Constructions", building),
            ("DT_Armor", items),
            ("DT_Weapons", items),
            ("DT_Tools", items),
            ("DT_Items", items),
        ]:
            dt = {
                "Imports": [{"ObjectName": "Base", "OuterIndex": 0,
                             "ClassName": "Package"}],
                "Exports": [{"SerializationBeforeCreateDependencies": []}],
            }
            (parent / f"{name}.json").write_text(
                json.dumps(dt), encoding="utf-8")

        # Create Imports.json with all 8 entries
        imports = {"Imports": [
            {"ObjectName": "Arch_PKG", "OuterIndex": 0, "ClassName": "Package"},
            {"ObjectName": "Arch_ST", "OuterIndex": -1, "ClassName": "StringTable"},
            {"ObjectName": "Inter_PKG", "OuterIndex": 0, "ClassName": "Package"},
            {"ObjectName": "Inter_ST", "OuterIndex": -1, "ClassName": "StringTable"},
            {"ObjectName": "Eff_PKG", "OuterIndex": 0, "ClassName": "Package"},
            {"ObjectName": "Eff_ST", "OuterIndex": -1, "ClassName": "StringTable"},
            {"ObjectName": "Items_PKG", "OuterIndex": 0, "ClassName": "Package"},
            {"ObjectName": "Items_ST", "OuterIndex": -1, "ClassName": "StringTable"},
        ]}
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        (data_dir / "Imports.json").write_text(
            json.dumps(imports), encoding="utf-8")

        _update_all_mod_imports(str(tmp_path), str(data_dir))

        # DT_Constructions: 1 base + 4 (Arch + Inter) = 5
        with open(building / "DT_Constructions.json", "r", encoding="utf-8") as f:
            constr = json.load(f)
        assert len(constr["Imports"]) == 5

        # DT_Armor: 1 base + 2 (Items) = 3
        with open(items / "DT_Armor.json", "r", encoding="utf-8") as f:
            armor = json.load(f)
        assert len(armor["Imports"]) == 3

        # DT_Weapons: 1 base + 2 (Items) = 3
        with open(items / "DT_Weapons.json", "r", encoding="utf-8") as f:
            weapons = json.load(f)
        assert len(weapons["Imports"]) == 3
