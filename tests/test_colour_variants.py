"""Tests for src.recipes.colour_variants — recipe auto-linking."""

from __future__ import annotations

import copy
import json

from src.recipes.colour_variants import (
    clean_name,
    is_colour_variant,
    patch_recipe,
    run,
)
from tests.conftest import UNLOCK_TEMPLATE


# ── clean_name ───────────────────────────────────────────────────────


class TestCleanName:
    """Tests for stripping colour tags from item names."""

    def test_white_variant(self):
        assert clean_name("Khazad_White_Chest") == "Khazad_Chest"

    def test_black_variant(self):
        assert clean_name("Erebor_Black_Boots") == "Erebor_Boots"

    def test_gold_variant(self):
        assert clean_name("Durin_Gold_Helm") == "Durin_Helm"

    def test_no_colour_tag_unchanged(self):
        assert clean_name("Khazad_Chest") == "Khazad_Chest"

    def test_multiple_colour_tags(self):
        # Regex replaces one tag at a time, left to right.
        # In practice items only have one colour tag, but verify
        # that at least the first match is stripped.
        result = clean_name("Khazad_White_Black_Chest")
        assert "_White_" not in result
        # After _White_ is removed, result is "Khazad_Black_Chest"
        # which still contains _Black_ — this is expected since the
        # regex matched "_White_" and the remaining "_Black_" is a
        # separate valid colour tag (would be caught on a second pass).
        assert result == "Khazad_Black_Chest"

    def test_colour_at_boundaries(self):
        # Colour must be surrounded by underscores to match
        assert clean_name("Whiteboard_Item") == "Whiteboard_Item"
        assert clean_name("Item_Blacksmith") == "Item_Blacksmith"


# ── is_colour_variant ────────────────────────────────────────────────


class TestIsColourVariant:
    """Tests for colour variant detection."""

    def test_detects_white(self):
        assert is_colour_variant("Khazad_White_Chest") is True

    def test_detects_black(self):
        assert is_colour_variant("Erebor_Black_Boots") is True

    def test_detects_gold(self):
        assert is_colour_variant("Durin_Gold_Helm") is True

    def test_rejects_base_item(self):
        assert is_colour_variant("Khazad_Chest") is False

    def test_rejects_substring_match(self):
        # "White" without surrounding underscores
        assert is_colour_variant("Whitestone_Wall") is False


# ── patch_recipe ─────────────────────────────────────────────────────


class TestPatchRecipe:
    """Tests for patching a single recipe row."""

    def _make_row(self, name, unlock_type="EMorRecipeUnlockType::Manual"):
        """Helper to build a minimal recipe row."""
        return {
            "Value": [
                {"Value": [{"Value": name}]},
                *[{"Value": "pad"} for _ in range(11)],
                {
                    "Value": [
                        {"Value": unlock_type},
                        {"Value": "x"},
                        {"Value": "x"},
                        {"Value": "x"},
                    ]
                },
            ]
        }

    def test_patches_white_variant(self):
        row = self._make_row("Khazad_White_Chest")
        template = copy.deepcopy(UNLOCK_TEMPLATE)

        result = patch_recipe(row, template)

        assert result == "Khazad_White_Chest"
        assert row["Value"][12]["Value"][0]["Value"] == (
            "EMorRecipeUnlockType::DiscoverDependencies"
        )
        # Template should have the base name filled in
        dep = row["Value"][12]["Value"][3]
        assert dep["Value"][0]["Value"][0]["Value"] == "Khazad_Chest"

    def test_skips_base_item(self):
        row = self._make_row("Khazad_Chest")
        template = copy.deepcopy(UNLOCK_TEMPLATE)

        result = patch_recipe(row, template)
        assert result is None

    def test_preserves_non_manual_unlock_type(self):
        row = self._make_row(
            "Khazad_White_Chest",
            unlock_type="EMorRecipeUnlockType::DiscoverDependencies",
        )
        template = copy.deepcopy(UNLOCK_TEMPLATE)

        patch_recipe(row, template)
        # Should NOT change — already DiscoverDependencies
        assert row["Value"][12]["Value"][0]["Value"] == (
            "EMorRecipeUnlockType::DiscoverDependencies"
        )

    def test_handles_malformed_row_gracefully(self):
        row = {"Value": []}  # Missing expected structure
        template = copy.deepcopy(UNLOCK_TEMPLATE)

        result = patch_recipe(row, template)
        assert result is None


# ── run (integration) ────────────────────────────────────────────────


class TestRunIntegration:
    """Integration tests for the full colour-variant patching pass."""

    def test_patches_correct_count(self, sample_recipes_json, unlock_template_json):
        patched = run(
            recipes_path=sample_recipes_json,
            template_path=unlock_template_json,
        )
        # 3 colour variants: White, Black, Gold
        assert patched == 3

    def test_base_items_untouched(self, sample_recipes_json, unlock_template_json):
        run(
            recipes_path=sample_recipes_json,
            template_path=unlock_template_json,
        )

        with open(sample_recipes_json, encoding="utf-8") as fh:
            data = json.load(fh)

        rows = data["Exports"][0]["Table"]["Data"]
        base_row = [r for r in rows if r["Name"] == "Khazad_Chest"][0]

        # Base item should still have Manual unlock type
        assert base_row["Value"][12]["Value"][0]["Value"] == (
            "EMorRecipeUnlockType::Manual"
        )

    def test_output_is_valid_json(self, sample_recipes_json, unlock_template_json):
        run(
            recipes_path=sample_recipes_json,
            template_path=unlock_template_json,
        )

        # Should not raise
        with open(sample_recipes_json, encoding="utf-8") as fh:
            data = json.load(fh)

        assert "Exports" in data
