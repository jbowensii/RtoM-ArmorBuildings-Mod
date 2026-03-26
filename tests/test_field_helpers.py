"""Tests for src.gui.field_helpers — field-value loading and combo helpers."""

from src.gui.field_helpers import (
    load_field_values, load_string_table, enum_short_values,
)


class TestLoadFieldValues:
    """Tests for load_field_values()."""

    def test_loads_existing_table(self):
        # DT_Constructions_fields.json should exist from extraction
        result = load_field_values("DT_Constructions")
        assert isinstance(result, dict)
        assert len(result) > 0

    def test_returns_empty_on_missing(self):
        result = load_field_values("NonExistentTable_99")
        assert result == {}

    def test_has_type_and_values(self):
        result = load_field_values("DT_ConstructionRecipes")
        for field_name, field_data in result.items():
            assert "type" in field_data, f"{field_name} missing 'type'"
            assert "values" in field_data, f"{field_name} missing 'values'"
            assert isinstance(field_data["values"], list)


class TestLoadStringTable:
    """Tests for load_string_table()."""

    def test_loads_entries(self):
        result = load_string_table()
        assert isinstance(result, dict)
        # Should have entries parsed from Game.po
        assert len(result) > 0

    def test_entries_have_name_and_description(self):
        result = load_string_table()
        for tag, entry in result.items():
            assert "name" in entry
            assert "description" in entry


class TestEnumShortValues:
    """Tests for enum_short_values()."""

    def test_strips_prefix(self):
        fv = {"values": [
            "EBuildProcess::DualMode",
            "EBuildProcess::Instant",
        ]}
        result = enum_short_values(fv)
        assert "DualMode" in result
        assert "Instant" in result
        assert not any("::" in v for v in result)

    def test_deduplicates(self):
        fv = {"values": [
            "EFoo::Bar", "EFoo::Bar", "EFoo::Baz",
        ]}
        result = enum_short_values(fv)
        assert result == ["Bar", "Baz"]

    def test_returns_sorted(self):
        fv = {"values": [
            "EFoo::Zebra", "EFoo::Apple", "EFoo::Mango",
        ]}
        result = enum_short_values(fv)
        assert result == ["Apple", "Mango", "Zebra"]

    def test_empty_input(self):
        assert enum_short_values({}) == []
        assert enum_short_values({"values": []}) == []

    def test_no_prefix(self):
        fv = {"values": ["NoPrefixValue"]}
        result = enum_short_values(fv)
        assert result == ["NoPrefixValue"]
