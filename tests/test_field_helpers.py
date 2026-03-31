"""Tests for src.gui.field_helpers — field-value loading and combo helpers."""

import json
import os

from src.gui.field_helpers import (
    load_field_values, load_string_table, enum_short_values,
    load_item_display_names,
)


class TestLoadFieldValues:
    """Tests for load_field_values()."""

    def test_loads_existing_table(self):
        """Known field-value index should load as a non-empty dict."""
        result = load_field_values("DT_Constructions")
        assert isinstance(result, dict)
        assert len(result) > 0

    def test_returns_empty_on_missing(self):
        """A nonexistent table name should return an empty dict."""
        result = load_field_values("NonExistentTable_99")
        assert result == {}

    def test_has_type_and_values(self):
        """Each field entry should have 'type' and 'values' keys."""
        result = load_field_values("DT_ConstructionRecipes")
        for field_name, field_data in result.items():
            assert "type" in field_data, f"{field_name} missing 'type'"
            assert "values" in field_data, f"{field_name} missing 'values'"
            assert isinstance(field_data["values"], list)


class TestLoadStringTable:
    """Tests for load_string_table()."""

    def test_loads_entries(self):
        """String table lookup should load as a non-empty dict."""
        result = load_string_table()
        assert isinstance(result, dict)
        # Should have entries parsed from Game.po
        assert len(result) > 0

    def test_entries_have_name_and_description(self):
        """Each entry should have 'name' and 'description' keys."""
        result = load_string_table()
        for _tag, entry in result.items():
            assert "name" in entry
            assert "description" in entry


class TestEnumShortValues:
    """Tests for enum_short_values()."""

    def test_strips_prefix(self):
        """Qualified enum values should have prefix stripped."""
        fv = {"values": [
            "EBuildProcess::DualMode",
            "EBuildProcess::Instant",
        ]}
        result = enum_short_values(fv)
        assert "DualMode" in result
        assert "Instant" in result
        assert not any("::" in v for v in result)

    def test_deduplicates(self):
        """Duplicate enum values should be collapsed."""
        fv = {"values": [
            "EFoo::Bar", "EFoo::Bar", "EFoo::Baz",
        ]}
        result = enum_short_values(fv)
        assert result == ["Bar", "Baz"]

    def test_returns_sorted(self):
        """Result should be sorted alphabetically."""
        fv = {"values": [
            "EFoo::Zebra", "EFoo::Apple", "EFoo::Mango",
        ]}
        result = enum_short_values(fv)
        assert result == ["Apple", "Mango", "Zebra"]

    def test_empty_input(self):
        """Empty or missing values should return empty list."""
        assert enum_short_values({}) == []
        assert enum_short_values({"values": []}) == []

    def test_no_prefix(self):
        """Values without '::' should be returned as-is."""
        fv = {"values": ["NoPrefixValue"]}
        result = enum_short_values(fv)
        assert result == ["NoPrefixValue"]


class TestLoadItemDisplayNames:
    """Tests for load_item_display_names()."""

    def test_loads_as_dict(self):
        """Should return a dict (possibly empty if file is missing)."""
        result = load_item_display_names()
        assert isinstance(result, dict)

    def test_returns_empty_on_missing_file(self, tmp_path, monkeypatch):
        """If the JSON file is missing, should return an empty dict."""
        import src.gui.field_helpers as fh_mod
        monkeypatch.setattr(fh_mod, "_FIELD_VALUES_DIR", str(tmp_path))
        result = fh_mod.load_item_display_names()
        assert result == {}

    def test_loads_from_custom_file(self, tmp_path, monkeypatch):
        """Should load tag-to-name mapping from item_display_names.json."""
        import src.gui.field_helpers as fh_mod
        monkeypatch.setattr(fh_mod, "_FIELD_VALUES_DIR", str(tmp_path))

        data = {
            "Item.Leather": "Leather",
            "Item.Iron_Ingot": "Iron Ingot",
            "Ore.Granite": "Granite",
        }
        path = tmp_path / "item_display_names.json"
        path.write_text(json.dumps(data), encoding="utf-8")

        result = fh_mod.load_item_display_names()
        assert result == data
        assert result["Item.Leather"] == "Leather"
        assert result["Item.Iron_Ingot"] == "Iron Ingot"

    def test_values_are_strings(self, tmp_path, monkeypatch):
        """All values in the mapping should be strings."""
        import src.gui.field_helpers as fh_mod
        monkeypatch.setattr(fh_mod, "_FIELD_VALUES_DIR", str(tmp_path))

        data = {"Tag.A": "Name A", "Tag.B": "Name B"}
        path = tmp_path / "item_display_names.json"
        path.write_text(json.dumps(data), encoding="utf-8")

        result = fh_mod.load_item_display_names()
        for tag, name in result.items():
            assert isinstance(tag, str)
            assert isinstance(name, str)

    def test_real_data_has_string_values(self):
        """If real data exists, all values should be strings."""
        result = load_item_display_names()
        if result:
            for tag, name in result.items():
                assert isinstance(name, str), f"Value for '{tag}' is not a string"
