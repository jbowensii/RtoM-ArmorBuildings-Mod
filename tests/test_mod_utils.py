"""Tests for src.construction.mod_utils — template population and file generation."""

import json
import os
import pytest

from src.construction.mod_utils import (
    gen_unique_tag, architecture_handle, advanced_bannister_post_stone_unlock,
)


@pytest.fixture
def tobis_dir(tmp_path):
    """Create a minimal Tobis_json directory structure."""
    arch_dir = tmp_path / "Architecture"
    arch_dir.mkdir()
    constr_dir = tmp_path / "DT_Constructions"
    constr_dir.mkdir()
    recipe_dir = tmp_path / "DT_ConstructionRecipes"
    recipe_dir.mkdir()
    return str(tmp_path)


class TestGenUniqueTag:
    """Tests for gen_unique_tag()."""

    def test_first_tag_returns_A(self, tobis_dir):
        letter = gen_unique_tag("TestPack_Wall", tobis_dir)
        assert letter == "A"

    def test_skips_existing(self, tobis_dir):
        # Create A suffix file
        arch = os.path.join(tobis_dir, "Architecture")
        with open(os.path.join(arch, "TestPack_Wall_A.json"), "w") as f:
            f.write("{}")
        letter = gen_unique_tag("TestPack_Wall", tobis_dir)
        assert letter == "B"

    def test_skips_multiple_existing(self, tobis_dir):
        arch = os.path.join(tobis_dir, "Architecture")
        for ch in "ABCDE":
            with open(os.path.join(arch, f"TestPack_Wall_{ch}.json"), "w") as f:
                f.write("{}")
        letter = gen_unique_tag("TestPack_Wall", tobis_dir)
        assert letter == "F"


class TestArchitectureHandle:
    """Tests for architecture_handle()."""

    def test_creates_file(self, tobis_dir):
        tag = architecture_handle("TestPack_Wall", "My Wall", "A nice wall", tobis_dir)
        assert tag.startswith("TestPack_Wall_")
        path = os.path.join(tobis_dir, "Architecture", f"{tag}.json")
        assert os.path.isfile(path)

    def test_file_has_entries(self, tobis_dir):
        tag = architecture_handle("TestPack_Item", "Cool Item", "Very cool", tobis_dir)
        path = os.path.join(tobis_dir, "Architecture", f"{tag}.json")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        entries = data["Entries"]
        assert len(entries) == 2
        assert entries[0][0].endswith(".Name")
        assert entries[0][1] == "Cool Item"
        assert entries[1][0].endswith(".Description")
        assert entries[1][1] == "Very cool"

    def test_unique_tags_increment(self, tobis_dir):
        tag1 = architecture_handle("TestPack_X", "X1", "Desc1", tobis_dir)
        tag2 = architecture_handle("TestPack_X", "X2", "Desc2", tobis_dir)
        assert tag1 != tag2
        assert tag1.endswith("_A")
        assert tag2.endswith("_B")


class TestBannisterUnlock:
    """Tests for advanced_bannister_post_stone_unlock()."""

    def test_returns_valid_struct(self):
        result = advanced_bannister_post_stone_unlock()
        assert result["Name"] == "UnlockRequiredItems"
        assert result["ArrayType"] == "StructProperty"
        # Should reference Ore.Granite
        row_name = result["Value"][0]["Value"][0]["Value"]
        assert row_name == "Ore.Granite"
