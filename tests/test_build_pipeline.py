"""Tests for src.gui.shared — build pipeline helpers."""

import json
import os
import pytest

from src.gui.shared import (
    _find_prop, _restore_constructions, _update_mod_imports,
    refresh_item_list, delete_per_item,
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
        # Elder_Archway_A should be changed
        elder = result["Exports"][0]["Table"]["Data"][0]
        unlock_val = elder["Value"][0]["Value"][0]["Value"]
        assert unlock_val == "EMorRecipeUnlockType::DiscoverDependencies"
        # SomeOtherItem should be unchanged
        other = result["Exports"][0]["Table"]["Data"][1]
        other_val = other["Value"][0]["Value"][0]["Value"]
        assert other_val == "EMorRecipeUnlockType::Manual"

    def test_returns_zero_on_missing_file(self, tmp_path):
        assert _restore_constructions(str(tmp_path)) == 0


class TestUpdateModImports:
    """Tests for _update_mod_imports()."""

    def test_appends_imports(self, tmp_path):
        constr = {
            "Imports": [{"ObjectName": "Existing", "OuterIndex": 0}],
            "Exports": [{
                "SerializationBeforeCreateDependencies": [],
            }],
        }
        imports = {
            "Imports": [
                {"ObjectName": "ST_A", "OuterIndex": 0},
                {"ObjectName": "ST_B", "OuterIndex": -1},
                {"ObjectName": "ST_C", "OuterIndex": 0},
                {"ObjectName": "ST_D", "OuterIndex": -1},
            ],
        }
        (tmp_path / "DT_Constructions.json").write_text(
            json.dumps(constr), encoding="utf-8")
        (tmp_path / "Imports.json").write_text(
            json.dumps(imports), encoding="utf-8")

        _update_mod_imports(str(tmp_path), str(tmp_path))

        with open(tmp_path / "DT_Constructions.json", "r", encoding="utf-8") as f:
            result = json.load(f)
        # Original 1 + 4 new = 5 imports
        assert len(result["Imports"]) == 5

    def test_skips_on_missing_files(self, tmp_path):
        # Should not raise
        _update_mod_imports(str(tmp_path), str(tmp_path))
