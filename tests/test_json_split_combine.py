"""Tests for src.utils.json_split_combine — per-item combine pipeline."""

import json
import os

import pytest

from src.utils.json_split_combine import (
    combine_dt_file, combine_architecture_file, combine_all,
)


@pytest.fixture
def vanilla_shell(tmp_path):
    """Create a minimal vanilla DataTable JSON shell."""
    shell = {
        "$type": "UAssetAPI.UAsset, UAssetAPI",
        "NameMap": ["Existing"],
        "Imports": [],
        "Exports": [{"Table": {"Data": []}}],
    }
    path = tmp_path / "shell.json"
    path.write_text(json.dumps(shell), encoding="utf-8")
    return str(path)


@pytest.fixture
def per_item_dir(tmp_path):
    """Create a directory with two sample per-item files."""
    source = tmp_path / "source"
    source.mkdir()

    item_a = {
        "NameMap": ["ItemA_Name"],
        "Imports": [],
        "Row": {
            "Name": "ItemA",
            "Value": [{"Name": "Foo", "Value": 1}],
        },
    }
    item_b = {
        "NameMap": ["ItemB_Name"],
        "Imports": [],
        "Row": {
            "Name": "ItemB",
            "Value": [{"Name": "Foo", "Value": 2}],
        },
    }
    (source / "ItemA.json").write_text(json.dumps(item_a), encoding="utf-8")
    (source / "ItemB.json").write_text(json.dumps(item_b), encoding="utf-8")
    return str(source)


class TestCombineDtFile:
    """Tests for combine_dt_file()."""

    def test_combines_two_items(self, per_item_dir, vanilla_shell, tmp_path):
        """Two per-item files should produce count=2."""
        output = str(tmp_path / "combined.json")
        count = combine_dt_file(per_item_dir, vanilla_shell, output)
        assert count == 2

    def test_output_contains_rows(self, per_item_dir, vanilla_shell, tmp_path):
        """Combined file should contain both rows."""
        output = str(tmp_path / "combined.json")
        combine_dt_file(per_item_dir, vanilla_shell, output)
        with open(output, "r", encoding="utf-8") as f:
            data = json.load(f)
        rows = data["Exports"][0]["Table"]["Data"]
        assert len(rows) == 2
        names = {r["Name"] for r in rows}
        assert names == {"ItemA", "ItemB"}

    def test_merges_namemap(self, per_item_dir, vanilla_shell, tmp_path):
        """NameMap should include base + per-item entries."""
        output = str(tmp_path / "combined.json")
        combine_dt_file(per_item_dir, vanilla_shell, output)
        with open(output, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Should have Existing + ItemA_Name + ItemB_Name
        assert "Existing" in data["NameMap"]
        assert "ItemA_Name" in data["NameMap"]
        assert "ItemB_Name" in data["NameMap"]

    def test_empty_source_produces_zero(self, vanilla_shell, tmp_path):
        """An empty source dir should produce count=0."""
        empty = tmp_path / "empty_source"
        empty.mkdir()
        output = str(tmp_path / "combined.json")
        count = combine_dt_file(str(empty), vanilla_shell, output)
        assert count == 0

    def test_deduplicates_namemap(self, per_item_dir, vanilla_shell, tmp_path):
        """NameMap should have no duplicate entries."""
        output = str(tmp_path / "combined.json")
        combine_dt_file(per_item_dir, vanilla_shell, output)
        with open(output, "r", encoding="utf-8") as f:
            data = json.load(f)
        # No duplicates in NameMap
        assert len(data["NameMap"]) == len(set(data["NameMap"]))


class TestCombineDtFileWithImports:
    """Tests for combine_dt_file() with has_imports=True (icon reindexing)."""

    @pytest.fixture
    def shell_with_imports(self, tmp_path):
        """A vanilla shell that already has some imports."""
        shell = {
            "$type": "UAssetAPI.UAsset, UAssetAPI",
            "NameMap": ["BaseEntry"],
            "Imports": [
                {"ObjectName": "ExistingPkg", "OuterIndex": 0,
                 "ClassName": "Package"},
                {"ObjectName": "ExistingTex", "OuterIndex": -1,
                 "ClassName": "Texture2D"},
            ],
            "Exports": [{"Table": {"Data": []}}],
        }
        path = tmp_path / "shell_imports.json"
        path.write_text(json.dumps(shell), encoding="utf-8")
        return str(path)

    @pytest.fixture
    def import_items_dir(self, tmp_path):
        """Per-item files with Imports (Package + Texture2D) and Icon field."""
        source = tmp_path / "import_source"
        source.mkdir()

        item_a = {
            "NameMap": ["WallA"],
            "Imports": [
                {"ObjectName": "/Game/Mods/Icons/WallA_PKG", "OuterIndex": 0,
                 "ClassName": "Package"},
                {"ObjectName": "T_UI_WallA", "OuterIndex": -1,
                 "ClassName": "Texture2D"},
            ],
            "Row": {
                "Name": "WallA",
                "Value": [
                    {"Name": "Icon", "Value": -1},
                    {"Name": "DisplayName", "Value": "Wall A"},
                ],
            },
        }
        item_b = {
            "NameMap": ["WallB"],
            "Imports": [
                {"ObjectName": "/Game/Mods/Icons/WallB_PKG", "OuterIndex": 0,
                 "ClassName": "Package"},
                {"ObjectName": "T_UI_WallB", "OuterIndex": -1,
                 "ClassName": "Texture2D"},
            ],
            "Row": {
                "Name": "WallB",
                "Value": [
                    {"Name": "Icon", "Value": -1},
                    {"Name": "OtherField", "Value": "hello"},
                ],
            },
        }
        (source / "WallA.json").write_text(json.dumps(item_a), encoding="utf-8")
        (source / "WallB.json").write_text(json.dumps(item_b), encoding="utf-8")
        return str(source)

    def test_imports_appended(self, import_items_dir, shell_with_imports, tmp_path):
        """Imports from per-item files should be appended to the base."""
        output = str(tmp_path / "combined.json")
        combine_dt_file(import_items_dir, shell_with_imports, output,
                        has_imports=True)
        with open(output, "r", encoding="utf-8") as f:
            data = json.load(f)
        # 2 base + 2 from WallA + 2 from WallB = 6
        assert len(data["Imports"]) == 6

    def test_package_outer_index_zero(self, import_items_dir, shell_with_imports,
                                      tmp_path):
        """Package imports should always have OuterIndex=0."""
        output = str(tmp_path / "combined.json")
        combine_dt_file(import_items_dir, shell_with_imports, output,
                        has_imports=True)
        with open(output, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Check new Package entries (indices 2, 4)
        assert data["Imports"][2]["OuterIndex"] == 0
        assert data["Imports"][4]["OuterIndex"] == 0

    def test_texture_outer_index_reindexed(self, import_items_dir,
                                           shell_with_imports, tmp_path):
        """Texture2D OuterIndex should point to its Package (1-based negative)."""
        output = str(tmp_path / "combined.json")
        combine_dt_file(import_items_dir, shell_with_imports, output,
                        has_imports=True)
        with open(output, "r", encoding="utf-8") as f:
            data = json.load(f)
        # WallA Texture at index 3, its Package at index 2 → OuterIndex = -(2+1) = -3
        assert data["Imports"][3]["OuterIndex"] == -3
        # WallB Texture at index 5, its Package at index 4 → OuterIndex = -(4+1) = -5
        assert data["Imports"][5]["OuterIndex"] == -5

    def test_icon_value_reindexed(self, import_items_dir, shell_with_imports,
                                  tmp_path):
        """Icon field in each row should be reindexed to Texture2D position."""
        output = str(tmp_path / "combined.json")
        combine_dt_file(import_items_dir, shell_with_imports, output,
                        has_imports=True)
        with open(output, "r", encoding="utf-8") as f:
            data = json.load(f)
        rows = data["Exports"][0]["Table"]["Data"]
        # WallA Icon → Texture at index 3 → -(3+1) = -4
        icon_a = next(p for p in rows[0]["Value"] if p["Name"] == "Icon")
        assert icon_a["Value"] == -4
        # WallB Icon → Texture at index 5 → -(5+1) = -6
        icon_b = next(p for p in rows[1]["Value"] if p["Name"] == "Icon")
        assert icon_b["Value"] == -6

    def test_no_imports_no_reindex(self, per_item_dir, vanilla_shell, tmp_path):
        """Items without Imports should work with has_imports=True (no-op)."""
        output = str(tmp_path / "combined.json")
        count = combine_dt_file(per_item_dir, vanilla_shell, output,
                                has_imports=True)
        assert count == 2
        with open(output, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Base had 0 imports, items had no imports → still 0
        assert len(data["Imports"]) == 0

    def test_namemap_merged_with_imports(self, import_items_dir,
                                        shell_with_imports, tmp_path):
        """NameMap should include entries from items that have imports."""
        output = str(tmp_path / "combined.json")
        combine_dt_file(import_items_dir, shell_with_imports, output,
                        has_imports=True)
        with open(output, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert "BaseEntry" in data["NameMap"]
        assert "WallA" in data["NameMap"]
        assert "WallB" in data["NameMap"]


class TestCombineArchitectureFile:
    """Tests for combine_architecture_file()."""

    def test_combines_entries(self, tmp_path):
        """Architecture entries should be appended to the shell."""
        source = tmp_path / "arch_source"
        source.mkdir()
        (source / "Wall_A.json").write_text(json.dumps({
            "Entries": [
                ["Wall_A.Name", "My Wall"],
                ["Wall_A.Description", "A wall"],
            ],
        }), encoding="utf-8")

        shell = {
            "$type": "UAssetAPI.UAsset, UAssetAPI",
            "NameMap": [],
            "Exports": [{"Table": {"Value": []}}],
        }
        shell_path = tmp_path / "arch_shell.json"
        shell_path.write_text(json.dumps(shell), encoding="utf-8")

        output = str(tmp_path / "arch_out.json")
        count = combine_architecture_file(str(source), str(shell_path), output)
        assert count == 1

    def test_empty_source_returns_zero(self, tmp_path):
        """An empty source dir should return count=0."""
        source = tmp_path / "empty"
        source.mkdir()
        shell = {
            "$type": "UAssetAPI.UAsset, UAssetAPI",
            "NameMap": [],
            "Exports": [{"Table": {"Value": []}}],
        }
        shell_path = tmp_path / "shell.json"
        shell_path.write_text(json.dumps(shell), encoding="utf-8")
        output = str(tmp_path / "out.json")
        count = combine_architecture_file(str(source), str(shell_path), output)
        assert count == 0


class TestCombineAll:
    """Tests for combine_all() orchestrator."""

    @pytest.fixture
    def full_setup(self, tmp_path):
        """Create a minimal setup for combine_all with a few tables."""
        tobis_json = tmp_path / "Tobis_json"
        tobis_json.mkdir()
        game_extract = tmp_path / "game_extract"
        uassetgui = game_extract / "uassetgui"
        output = tmp_path / "output"

        # Create vanilla shell for DT_Constructions
        constr_dir = uassetgui / "Moria" / "Content" / "Tech" / "Data" / "Building"
        constr_dir.mkdir(parents=True)
        shell = {
            "$type": "UAssetAPI.UAsset, UAssetAPI",
            "NameMap": ["VanillaConstr"],
            "Imports": [],
            "Exports": [{"Table": {"Data": []}}],
        }
        (constr_dir / "DT_Constructions.json").write_text(
            json.dumps(shell), encoding="utf-8")

        # Create per-item file for DT_Constructions
        constr_source = tobis_json / "DT_Constructions"
        constr_source.mkdir()
        item = {
            "NameMap": ["Wall_A"],
            "Imports": [
                {"ObjectName": "PKG", "OuterIndex": 0, "ClassName": "Package"},
                {"ObjectName": "TEX", "OuterIndex": -1, "ClassName": "Texture2D"},
            ],
            "Row": {
                "Name": "Wall_A",
                "Value": [{"Name": "Icon", "Value": -1}],
            },
        }
        (constr_source / "Wall_A.json").write_text(
            json.dumps(item), encoding="utf-8")

        # Create Architecture source + shell
        arch_source = tobis_json / "Architecture"
        arch_source.mkdir()
        (arch_source / "Wall_A.json").write_text(json.dumps({
            "Entries": [["Wall_A.Name", "Test Wall"]],
        }), encoding="utf-8")

        return {
            "tobis_json_dir": str(tobis_json),
            "game_extract_dir": str(game_extract),
            "output_dir": str(output),
        }

    def test_returns_results_dict(self, full_setup):
        """combine_all should return a dict mapping table names to counts."""
        results = combine_all(**full_setup)
        assert isinstance(results, dict)
        assert "DT_Constructions" in results
        assert "Architecture" in results

    def test_constructions_combined(self, full_setup):
        """DT_Constructions should have 1 item combined."""
        results = combine_all(**full_setup)
        assert results["DT_Constructions"] == 1

    def test_architecture_combined(self, full_setup):
        """Architecture should have 1 item combined."""
        results = combine_all(**full_setup)
        assert results["Architecture"] == 1

    def test_missing_vanilla_base_returns_zero(self, full_setup):
        """Tables without a vanilla base file should return 0."""
        results = combine_all(**full_setup)
        # DT_Armor has no vanilla base in this minimal setup
        assert results.get("DT_Armor", 0) == 0

    def test_output_files_created(self, full_setup):
        """Combined output files should be written to disk."""
        combine_all(**full_setup)
        output = full_setup["output_dir"]
        constr_path = os.path.join(
            output, "Moria", "Content", "Tech", "Data", "Building",
            "DT_Constructions.json",
        )
        assert os.path.isfile(constr_path)

    def test_architecture_output_created(self, full_setup):
        """Architecture output should be created under Building/."""
        combine_all(**full_setup)
        output = full_setup["output_dir"]
        arch_path = os.path.join(
            output, "Moria", "Content", "Tech", "Data", "Building",
            "Architecture.json",
        )
        assert os.path.isfile(arch_path)

    def test_architecture_shell_auto_generated(self, full_setup):
        """If _architecture_shell.json is missing, it should be auto-created."""
        tobis_json = full_setup["tobis_json_dir"]
        shell_path = os.path.join(tobis_json, "_architecture_shell.json")
        # Ensure it does not exist before combine
        assert not os.path.isfile(shell_path)
        combine_all(**full_setup)
        assert os.path.isfile(shell_path)

    def test_import_reindexing_in_combined_constructions(self, full_setup):
        """DT_Constructions should have reindexed imports after combine_all."""
        combine_all(**full_setup)
        output = full_setup["output_dir"]
        constr_path = os.path.join(
            output, "Moria", "Content", "Tech", "Data", "Building",
            "DT_Constructions.json",
        )
        with open(constr_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Should have 2 imports (Package + Texture2D)
        assert len(data["Imports"]) == 2
        # Package OuterIndex stays 0
        assert data["Imports"][0]["OuterIndex"] == 0
        # Texture points to Package at index 0 → -(0+1) = -1
        assert data["Imports"][1]["OuterIndex"] == -1
