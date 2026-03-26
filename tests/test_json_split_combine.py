"""Tests for src.utils.json_split_combine — per-item combine pipeline."""

import json
import os
import pytest

from src.utils.json_split_combine import combine_dt_file, combine_architecture_file


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
        output = str(tmp_path / "combined.json")
        count = combine_dt_file(per_item_dir, vanilla_shell, output)
        assert count == 2

    def test_output_contains_rows(self, per_item_dir, vanilla_shell, tmp_path):
        output = str(tmp_path / "combined.json")
        combine_dt_file(per_item_dir, vanilla_shell, output)
        with open(output, "r", encoding="utf-8") as f:
            data = json.load(f)
        rows = data["Exports"][0]["Table"]["Data"]
        assert len(rows) == 2
        names = {r["Name"] for r in rows}
        assert names == {"ItemA", "ItemB"}

    def test_merges_namemap(self, per_item_dir, vanilla_shell, tmp_path):
        output = str(tmp_path / "combined.json")
        combine_dt_file(per_item_dir, vanilla_shell, output)
        with open(output, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Should have Existing + ItemA_Name + ItemB_Name
        assert "Existing" in data["NameMap"]
        assert "ItemA_Name" in data["NameMap"]
        assert "ItemB_Name" in data["NameMap"]

    def test_empty_source_produces_zero(self, vanilla_shell, tmp_path):
        empty = tmp_path / "empty_source"
        empty.mkdir()
        output = str(tmp_path / "combined.json")
        count = combine_dt_file(str(empty), vanilla_shell, output)
        assert count == 0

    def test_deduplicates_namemap(self, per_item_dir, vanilla_shell, tmp_path):
        output = str(tmp_path / "combined.json")
        combine_dt_file(per_item_dir, vanilla_shell, output)
        with open(output, "r", encoding="utf-8") as f:
            data = json.load(f)
        # No duplicates in NameMap
        assert len(data["NameMap"]) == len(set(data["NameMap"]))


class TestCombineArchitectureFile:
    """Tests for combine_architecture_file()."""

    def test_combines_entries(self, tmp_path):
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
