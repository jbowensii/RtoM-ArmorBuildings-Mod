"""Tests for src.gui.shared — build pipeline helpers."""

import json

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

    def test_multiple_pairs_appended(self, tmp_path):
        """Appending two Package+StringTable pairs should reindex both correctly."""
        path = self._make_dt(tmp_path, "DT_Multi", num_existing=2)
        entries = [
            {"ObjectName": "PKG_Arch", "OuterIndex": 0, "ClassName": "Package"},
            {"ObjectName": "ST_Arch", "OuterIndex": -1, "ClassName": "StringTable"},
            {"ObjectName": "PKG_Inter", "OuterIndex": 0, "ClassName": "Package"},
            {"ObjectName": "ST_Inter", "OuterIndex": -1, "ClassName": "StringTable"},
        ]
        _append_string_table_imports(path, entries)

        with open(path, "r", encoding="utf-8") as f:
            result = json.load(f)

        # 2 existing + 4 new = 6
        assert len(result["Imports"]) == 6

        # First StringTable (index 3, 0-based) → Package at index 2
        # OuterIndex = -(2 + 1) = -3
        assert result["Imports"][3]["OuterIndex"] == -3

        # Second StringTable (index 5, 0-based) → Package at index 4
        # OuterIndex = -(4 + 1) = -5
        assert result["Imports"][5]["OuterIndex"] == -5

    def test_serial_deps_for_multiple_pairs(self, tmp_path):
        """Multiple StringTable entries should each add a serial dep."""
        path = self._make_dt(tmp_path, "DT_Multi", num_existing=2)
        entries = [
            {"ObjectName": "PKG_A", "OuterIndex": 0, "ClassName": "Package"},
            {"ObjectName": "ST_A", "OuterIndex": -1, "ClassName": "StringTable"},
            {"ObjectName": "PKG_B", "OuterIndex": 0, "ClassName": "Package"},
            {"ObjectName": "ST_B", "OuterIndex": -1, "ClassName": "StringTable"},
        ]
        _append_string_table_imports(path, entries)

        with open(path, "r", encoding="utf-8") as f:
            result = json.load(f)
        deps = result["Exports"][0]["SerializationBeforeCreateDependencies"]
        # ST_A at position 4 (0-based index 3) → -(3+1) = -4
        # ST_B at position 6 (0-based index 5) → -(5+1) = -6
        assert -4 in deps
        assert -6 in deps

    def test_package_outer_index_stays_zero(self, tmp_path):
        """Package entries should keep OuterIndex=0."""
        path = self._make_dt(tmp_path, "DT_Pkg", num_existing=3)
        entries = [
            {"ObjectName": "PKG", "OuterIndex": 0, "ClassName": "Package"},
            {"ObjectName": "ST", "OuterIndex": -1, "ClassName": "StringTable"},
        ]
        _append_string_table_imports(path, entries)

        with open(path, "r", encoding="utf-8") as f:
            result = json.load(f)
        pkg = result["Imports"][3]
        assert pkg["ClassName"] == "Package"
        assert pkg["OuterIndex"] == 0


class TestUpdateAllModImports:
    """Tests for _update_all_mod_imports()."""

    def _setup_dt_files(self, tmp_path):
        """Create all 5 DataTable files and Imports.json, return data_dir."""
        building = tmp_path / "Moria" / "Content" / "Tech" / "Data" / "Building"
        building.mkdir(parents=True)
        items = tmp_path / "Moria" / "Content" / "Tech" / "Data" / "Items"
        items.mkdir(parents=True)

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

        return str(data_dir), building, items

    def test_applies_to_constructions_and_items(self, tmp_path):
        """All 5 DataTables should get their string table imports."""
        data_dir, building, items = self._setup_dt_files(tmp_path)

        _update_all_mod_imports(str(tmp_path), data_dir)

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

    def test_tools_and_items_get_imports(self, tmp_path):
        """DT_Tools and DT_Items should also get ST_Mod_Items imports."""
        data_dir, _building, items = self._setup_dt_files(tmp_path)

        _update_all_mod_imports(str(tmp_path), data_dir)

        with open(items / "DT_Tools.json", "r", encoding="utf-8") as f:
            tools = json.load(f)
        assert len(tools["Imports"]) == 3

        with open(items / "DT_Items.json", "r", encoding="utf-8") as f:
            dt_items = json.load(f)
        assert len(dt_items["Imports"]) == 3

    def test_constructions_gets_arch_and_interactables(self, tmp_path):
        """DT_Constructions should get Architecture + Interactables (4 entries)."""
        data_dir, building, _items = self._setup_dt_files(tmp_path)

        _update_all_mod_imports(str(tmp_path), data_dir)

        with open(building / "DT_Constructions.json", "r", encoding="utf-8") as f:
            constr = json.load(f)
        # Check that the appended names match the first 4 import entries
        appended_names = [imp["ObjectName"] for imp in constr["Imports"][1:]]
        assert "Arch_PKG" in appended_names
        assert "Arch_ST" in appended_names
        assert "Inter_PKG" in appended_names
        assert "Inter_ST" in appended_names

    def test_items_tables_get_items_st(self, tmp_path):
        """Armor/Weapons/Tools/Items should get Items_PKG + Items_ST."""
        data_dir, _building, items = self._setup_dt_files(tmp_path)

        _update_all_mod_imports(str(tmp_path), data_dir)

        for table in ("DT_Armor", "DT_Weapons", "DT_Tools", "DT_Items"):
            with open(items / f"{table}.json", "r", encoding="utf-8") as f:
                dt = json.load(f)
            appended_names = [imp["ObjectName"] for imp in dt["Imports"][1:]]
            assert "Items_PKG" in appended_names, f"{table} missing Items_PKG"
            assert "Items_ST" in appended_names, f"{table} missing Items_ST"

    def test_deep_copy_safety_across_tables(self, tmp_path):
        """Each item table should get its own reindexed OuterIndex values,
        not shared references from the same entries list."""
        data_dir, _building, items = self._setup_dt_files(tmp_path)

        _update_all_mod_imports(str(tmp_path), data_dir)

        # All item tables have 1 existing import, so each should get
        # the same reindexing (OuterIndex = -(1+1) = -2 for the ST entry)
        for table in ("DT_Armor", "DT_Weapons", "DT_Tools", "DT_Items"):
            with open(items / f"{table}.json", "r", encoding="utf-8") as f:
                dt = json.load(f)
            st = dt["Imports"][-1]
            assert st["ClassName"] == "StringTable"
            assert st["OuterIndex"] == -2

    def test_missing_imports_json_no_error(self, tmp_path):
        """If Imports.json is missing, _update_all_mod_imports should return safely."""
        data_dir = str(tmp_path / "nonexistent_data")
        # Should not raise
        _update_all_mod_imports(str(tmp_path), data_dir)

    def test_serial_deps_added_for_constructions(self, tmp_path):
        """Constructions should have serial deps for both StringTable entries."""
        data_dir, building, _items = self._setup_dt_files(tmp_path)

        _update_all_mod_imports(str(tmp_path), data_dir)

        with open(building / "DT_Constructions.json", "r", encoding="utf-8") as f:
            constr = json.load(f)
        deps = constr["Exports"][0]["SerializationBeforeCreateDependencies"]
        # Two StringTable entries → 2 serial deps
        assert len(deps) == 2
