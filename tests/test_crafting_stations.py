"""Tests for the Crafting Stations checkbox-group helpers in item_adder_tab.

Covers humanize_station_label, make_station_struct, and
extract_station_row_names — the pure helpers that back the new UI.
Also verifies the on-disk recipe template now loads (Part A regression check).
"""

from __future__ import annotations

import json
import os

import pytest

from src.gui.item_adder_tab import (
    extract_station_row_names,
    humanize_station_label,
    make_station_struct,
)


# ── humanize_station_label ────────────────────────────────────────────

class TestHumanizeStationLabel:
    """Label generation for a CraftingStations row name."""

    def test_uses_explicit_display_name_when_present(self):
        """display_names lookup wins over auto-humanisation."""
        display_names = {"CraftingStation_FabricStation": "Loom"}
        assert humanize_station_label(
            "CraftingStation_FabricStation", display_names) == "Loom"

    def test_strips_prefix_and_splits_camel_case(self):
        """CraftingStation_DurinForge → 'Durin Forge'."""
        assert humanize_station_label(
            "CraftingStation_DurinForge", {}) == "Durin Forge"

    def test_handles_furnace_rows(self):
        """Furnace rows split CamelCase the same as forges."""
        assert humanize_station_label(
            "CraftingStation_AdvancedFurnace", {}) == "Advanced Furnace"

    def test_normalises_legenday_typo_to_legendary(self):
        """The game data has 'Legenday' rows — surface them as Legendary."""
        assert humanize_station_label(
            "CraftingStation_LegendayElvishForge", {},
        ) == "Legendary Elvish Forge"

    def test_passes_through_non_prefixed_names(self):
        """Rows without the CraftingStation_ prefix still get CamelCase split.

        In practice "100BuildingsPack_TelcharForge_A" has an explicit
        display_name ("Telchar Forge") so this fallback never fires for it.
        """
        assert humanize_station_label(
            "100BuildingsPack_TelcharForge_A", {},
        ) == "100 Buildings Pack_ Telchar Forge_ A"


# ── make_station_struct ───────────────────────────────────────────────

class TestMakeStationStruct:
    """Single MorConstructionRowHandle entry for the CraftingStations array."""

    def test_struct_shape_matches_uassetapi_spec(self):
        """Top-level fields must satisfy UAssetAPI for round-trip serialization."""
        struct = make_station_struct("CraftingStation_DurinForge")
        assert struct["StructType"] == "MorConstructionRowHandle"
        assert struct["Name"] == "CraftingStations"
        assert struct["SerializeNone"] is True
        assert struct["StructGUID"] == "{00000000-0000-0000-0000-000000000000}"

    def test_inner_value_is_single_rowname_property(self):
        """Inner Value must be a one-element list of NameProperty 'RowName'."""
        struct = make_station_struct("CraftingStation_BasicFurnace")
        assert len(struct["Value"]) == 1
        inner = struct["Value"][0]
        assert inner["Name"] == "RowName"
        assert inner["Value"] == "CraftingStation_BasicFurnace"
        assert "NamePropertyData" in inner["$type"]

    def test_distinct_row_names_produce_independent_dicts(self):
        """Each call returns a fresh dict — mutating one must not bleed."""
        first = make_station_struct("CraftingStation_DurinForge")
        second = make_station_struct("CraftingStation_NogrodForge")
        first["Value"][0]["Value"] = "MUTATED"
        assert second["Value"][0]["Value"] == "CraftingStation_NogrodForge"


# ── extract_station_row_names ─────────────────────────────────────────

class TestExtractStationRowNames:
    """Reverse direction: pull RowNames out of a saved recipe row."""

    def test_returns_empty_when_field_absent(self):
        """No CraftingStations entry in the row → empty list."""
        assert not extract_station_row_names(
            [{"Name": "Other", "Value": []}])

    def test_returns_empty_when_array_empty(self):
        """CraftingStations exists but is empty → empty list."""
        values = [{"Name": "CraftingStations", "Value": []}]
        assert not extract_station_row_names(values)

    def test_returns_all_row_names_in_order(self):
        """Returned list preserves the on-disk array order."""
        values = [{
            "Name": "CraftingStations",
            "Value": [
                make_station_struct("CraftingStation_DurinForge"),
                make_station_struct("CraftingStation_MithrilForge"),
                make_station_struct("CraftingStation_BasicFurnace"),
            ],
        }]
        assert extract_station_row_names(values) == [
            "CraftingStation_DurinForge",
            "CraftingStation_MithrilForge",
            "CraftingStation_BasicFurnace",
        ]

    def test_skips_entries_without_a_rowname(self):
        """Malformed entries lacking a RowName field are ignored, not fatal."""
        values = [{
            "Name": "CraftingStations",
            "Value": [
                {"Value": [{"Name": "OtherField", "Value": "x"}]},
                make_station_struct("CraftingStation_Workbench"),
            ],
        }]
        assert extract_station_row_names(values) == ["CraftingStation_Workbench"]


# ── Build → extract round-trip ────────────────────────────────────────

class TestStationRoundTrip:
    """Verify make → extract recovers the original selection set."""

    def test_build_then_extract_recovers_original_set(self):
        """A list of chosen stations survives serialization untouched."""
        chosen = [
            "CraftingStation_DurinForge",
            "CraftingStation_LegendaryFloodedFurnace",
            "CraftingStation_Workbench",
        ]
        row_value = [{
            "Name": "CraftingStations",
            "Value": [make_station_struct(rn) for rn in chosen],
        }]
        assert extract_station_row_names(row_value) == chosen

    def test_empty_selection_round_trips_to_empty(self):
        """A recipe with no stations selected stays empty."""
        row_value = [{"Name": "CraftingStations", "Value": []}]
        assert not extract_station_row_names(row_value)


# ── Part A regression: template now loads with all 16 fields ─────────

def _template_path() -> str:
    """Absolute path to the renamed DT_ItemRecipes_template.json."""
    repo_root = os.path.dirname(os.path.dirname(__file__))
    return os.path.join(
        repo_root, "data", "templates", "MoreArmor",
        "DT_ItemRecipes_template.json",
    )


class TestRecipeTemplateOnDisk:
    """Confirms the renamed DT_ItemRecipes_template.json is reachable."""

    def test_template_file_exists_under_expected_name(self):
        """ItemAdderTab._load_template('DT_ItemRecipes') must find this file."""
        assert os.path.isfile(_template_path()), (
            "Template must be named DT_ItemRecipes_template.json so that "
            "ItemAdderTab._load_template('DT_ItemRecipes') finds it via the "
            "MoreArmor fallback."
        )

    def test_template_has_all_expected_recipe_fields(self):
        """All 16 fields the GUI relies on must be present in the template."""
        with open(_template_path(), "r", encoding="utf-8") as fh:
            tpl = json.load(fh)
        names = {entry.get("Name") for entry in tpl.get("Value", [])}
        for required in (
            "ResultItemHandle", "ResultItemCount", "CraftTimeSeconds",
            "bCanBePinned", "CraftingStations", "DestinationContainerClass",
            "bNpcOnlyRecipe", "bHasSandboxRequirementsOverride",
            "SandboxRequiredMaterials", "SandboxRequiredConstructions",
            "DefaultRequiredMaterials", "DefaultRequiredConstructions",
            "bHasSandboxUnlockOverride", "SandboxUnlocks", "DefaultUnlocks",
            "EnabledState",
        ):
            assert required in names, f"Template is missing {required!r}"

    def test_crafting_stations_starts_empty(self):
        """Template's CraftingStations begins with no selected stations."""
        with open(_template_path(), "r", encoding="utf-8") as fh:
            tpl = json.load(fh)
        for entry in tpl.get("Value", []):
            if entry.get("Name") == "CraftingStations":
                assert entry.get("Value") == []
                return
        pytest.fail("CraftingStations entry not found in template")
