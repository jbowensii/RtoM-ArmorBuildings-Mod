"""Tests for src.construction.mod_utils — template population and file generation."""

import json
import os
import pytest

from src.construction.mod_utils import (
    gen_unique_tag, architecture_handle, advanced_bannister_post_stone_unlock,
    dt_constructions_handle, dt_construction_recipes_handle,
    _apply_recipe_overrides,
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


@pytest.fixture
def templates_dir(tmp_path):
    """Create a templates directory with all MoreBuildings templates."""
    mb = tmp_path / "templates" / "MoreBuildings"
    mb.mkdir(parents=True)

    # ConstructionTemplate.json — minimal version of the real template
    construction_tpl = {
        "Name": "",
        "Value": [
            {"Name": "DisplayName", "Value": ""},           # [0]
            {"Name": "Description", "Value": ""},            # [1]
            {"Name": "Icon", "Value": -1004},                # [2]
            {"Name": "Actor", "Value": {                     # [3]
                "AssetPath": {"AssetName": "PLACEHOLDER"}}},
            {"Name": "BackwardCompatibilityActors", "Value": [  # [4]
                {"Value": [{"Value": {
                    "AssetPath": {"AssetName": "PLACEHOLDER"}
                }}]}
            ]},
            {"Name": "Tags", "Value": [                      # [5]
                {"Value": []}
            ]},
            {"Name": "EnabledState", "Value": "ERowEnabledState::Live"},  # [6]
        ],
    }
    (mb / "ConstructionTemplate.json").write_text(
        json.dumps(construction_tpl), encoding="utf-8")

    # constructionsImportTemplates.json
    import_tpl = {
        "Package": {
            "$type": "UAssetAPI.Import, UAssetAPI",
            "ObjectName": "PLACEHOLDER_PKG",
            "OuterIndex": 0,
            "ClassPackage": "/Script/CoreUObject",
            "ClassName": "Package",
        },
        "Texture2D": {
            "$type": "UAssetAPI.Import, UAssetAPI",
            "ObjectName": "PLACEHOLDER_TEX",
            "OuterIndex": -56,
            "ClassPackage": "/Script/Engine",
            "ClassName": "Texture2D",
        },
    }
    (mb / "constructionsImportTemplates.json").write_text(
        json.dumps(import_tpl), encoding="utf-8")

    # ConstructionRecipeTemplate.json — minimal version
    recipe_tpl = {
        "Name": "",
        "Value": [
            {"Name": "ResultConstructionHandle",            # [0]
             "Value": [{"Value": ""}]},
            {"Name": "BuildProcess",                        # [1]
             "Value": "EBuildProcess::DualMode"},
            {"Name": "LocationRequirement",                 # [2]
             "Value": "EConstructionLocation::Base"},
            {"Name": "PlacementType",                       # [3]
             "Value": "EPlacementType::FreePlacement"},
            {"Name": "bOnWall", "Value": False},            # [4]
            {"Name": "bOnFloor", "Value": True},            # [5]
            {"Name": "bPlaceOnWater", "Value": False},      # [6]
            {"Name": "bOverrideRotation", "Value": False},  # [7]
            {"Name": "FoundationRule",                      # [8]
             "Value": "EFoundationRule::Never"},
            {"Name": "bAutoFoundation", "Value": False},    # [9]
            {"Name": "bInheritAutoFoundationStability",     # [10]
             "Value": False},
            {"Name": "bAllowRefunds", "Value": True},      # [11]
            {"Name": "Padding1", "Value": 0},               # [12]
            {"Name": "Padding2", "Value": 0},               # [13]
            {"Name": "Padding3", "Value": 0},               # [14]
            {"Name": "Padding4", "Value": 0},               # [15]
            {"Name": "DefaultRequiredMaterials",            # [16]
             "Value": []},
            {"Name": "Padding5", "Value": 0},               # [17]
            {"Name": "Padding6", "Value": 0},               # [18]
            {"Name": "Padding7", "Value": 0},               # [19]
            {"Name": "DefaultUnlocks", "Value": [           # [20]
                {"Value": "EMorRecipeUnlockType::DiscoverDependencies"},
                {"Value": 1},
                {"Value": []},
                {"Name": "UnlockRequiredItems", "Value": []},
                {"Name": "UnlockRequiredConstructions", "Value": []},
            ]},
            {"Name": "EnabledState",                        # [21]
             "Value": "ERowEnabledState::Live"},
        ],
    }
    (mb / "ConstructionRecipeTemplate.json").write_text(
        json.dumps(recipe_tpl), encoding="utf-8")

    # ItemTemplate.json — for required items in recipes
    item_tpl = {
        "Value": [
            {"Value": [{"Value": ""}]},   # [0] MaterialHandle.RowName
            {"Value": "None"},             # [1] WildcardHandle
            {"Value": 0},                  # [2] Count
        ],
    }
    (mb / "ItemTemplate.json").write_text(
        json.dumps(item_tpl), encoding="utf-8")

    # DumyStructs.json
    dummy = {
        "UnlockRequiredItems": {
            "Name": "UnlockRequiredItems", "Value": [],
        },
        "UnlockRequiredConstructions": {
            "Name": "UnlockRequiredConstructions", "Value": [],
        },
    }
    (mb / "DumyStructs.json").write_text(
        json.dumps(dummy), encoding="utf-8")

    # CategoryFlags.json
    flags = {
        "Walls": [
            "EConstructionLocation::Base",
            "EPlacementType::SnapGrid",
            False, True, False, False, True,
        ],
        "Ceilings": [
            "EConstructionLocation::Base",
            "EPlacementType::SnapGrid",
            False, True, False, False, True,
        ],
    }
    (mb / "CategoryFlags.json").write_text(
        json.dumps(flags), encoding="utf-8")

    # UnlockRequirementsStructs.json
    unlock_structs = {
        "UnlockRequiredItems": {
            "Name": "UnlockRequiredItems",
            "Value": [{"Value": [{"Value": ""}]}],
        },
        "UnlockRequiredConstructions": {
            "Name": "UnlockRequiredConstructions",
            "Value": [{"Value": [{"Value": ""}]}],
        },
    }
    (mb / "UnlockRequirementsStructs.json").write_text(
        json.dumps(unlock_structs), encoding="utf-8")

    return str(tmp_path / "templates")


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


class TestDtConstructionsHandle:
    """Tests for dt_constructions_handle()."""

    def test_creates_file(self, tobis_dir, templates_dir):
        dt_constructions_handle(
            unique_tag="TestPack_Wall_A",
            asset_path="/Game/Mods/TestPack/BP_TestWall",
            category_tag="Walls",
            tobis_json_dir=tobis_dir,
            templates_dir=templates_dir,
            user_name="TestUser",
        )
        path = os.path.join(tobis_dir, "DT_Constructions", "TestPack_Wall_A.json")
        assert os.path.isfile(path)

    def test_file_structure(self, tobis_dir, templates_dir):
        dt_constructions_handle(
            unique_tag="TestPack_Wall_A",
            asset_path="/Game/Mods/TestPack/BP_TestWall",
            category_tag="Walls",
            tobis_json_dir=tobis_dir,
            templates_dir=templates_dir,
            user_name="TestUser",
        )
        path = os.path.join(tobis_dir, "DT_Constructions", "TestPack_Wall_A.json")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert "NameMap" in data
        assert "Imports" in data
        assert "Row" in data

    def test_row_name_set(self, tobis_dir, templates_dir):
        dt_constructions_handle(
            unique_tag="TestPack_Wall_A",
            asset_path="/Game/Mods/TestPack/BP_TestWall",
            category_tag="Walls",
            tobis_json_dir=tobis_dir,
            templates_dir=templates_dir,
            user_name="TestUser",
        )
        path = os.path.join(tobis_dir, "DT_Constructions", "TestPack_Wall_A.json")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["Row"]["Name"] == "TestPack_Wall_A"

    def test_display_name_and_description_populated(self, tobis_dir, templates_dir):
        dt_constructions_handle(
            unique_tag="TestPack_Wall_A",
            asset_path="/Game/Mods/TestPack/BP_TestWall",
            category_tag="Walls",
            tobis_json_dir=tobis_dir,
            templates_dir=templates_dir,
            user_name="TestUser",
        )
        path = os.path.join(tobis_dir, "DT_Constructions", "TestPack_Wall_A.json")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        row = data["Row"]
        assert row["Value"][0]["Value"] == "TestPack_Wall_A.Name"
        assert row["Value"][1]["Value"] == "TestPack_Wall_A.Description"

    def test_actor_asset_path(self, tobis_dir, templates_dir):
        dt_constructions_handle(
            unique_tag="TestPack_Wall_A",
            asset_path="/Game/Mods/TestPack/BP_TestWall",
            category_tag="Walls",
            tobis_json_dir=tobis_dir,
            templates_dir=templates_dir,
            user_name="TestUser",
        )
        path = os.path.join(tobis_dir, "DT_Constructions", "TestPack_Wall_A.json")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        actor_asset = data["Row"]["Value"][3]["Value"]["AssetPath"]["AssetName"]
        assert actor_asset == "/Game/Mods/TestPack/BP_TestWall.BP_TestWall_C"

    def test_category_tag_appended(self, tobis_dir, templates_dir):
        dt_constructions_handle(
            unique_tag="TestPack_Wall_A",
            asset_path="/Game/Mods/TestPack/BP_TestWall",
            category_tag="Walls",
            tobis_json_dir=tobis_dir,
            templates_dir=templates_dir,
            user_name="TestUser",
        )
        path = os.path.join(tobis_dir, "DT_Constructions", "TestPack_Wall_A.json")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        tags_list = data["Row"]["Value"][5]["Value"][0]["Value"]
        assert "Walls" in tags_list

    def test_icon_placeholder(self, tobis_dir, templates_dir):
        dt_constructions_handle(
            unique_tag="TestPack_Wall_A",
            asset_path="/Game/Mods/TestPack/BP_TestWall",
            category_tag="Walls",
            tobis_json_dir=tobis_dir,
            templates_dir=templates_dir,
            user_name="TestUser",
        )
        path = os.path.join(tobis_dir, "DT_Constructions", "TestPack_Wall_A.json")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["Row"]["Value"][2]["Value"] == -1

    def test_imports_have_package_and_texture(self, tobis_dir, templates_dir):
        dt_constructions_handle(
            unique_tag="TestPack_Wall_A",
            asset_path="/Game/Mods/TestPack/BP_TestWall",
            category_tag="Walls",
            tobis_json_dir=tobis_dir,
            templates_dir=templates_dir,
            user_name="TestUser",
        )
        path = os.path.join(tobis_dir, "DT_Constructions", "TestPack_Wall_A.json")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        imports = data["Imports"]
        assert len(imports) == 2
        assert imports[0]["ClassName"] == "Package"
        assert imports[1]["ClassName"] == "Texture2D"
        assert "TestPack_Wall_A" in imports[0]["ObjectName"]
        assert imports[0]["OuterIndex"] == 0
        assert imports[1]["OuterIndex"] == -1  # placeholder

    def test_namemap_contains_key_entries(self, tobis_dir, templates_dir):
        dt_constructions_handle(
            unique_tag="TestPack_Wall_A",
            asset_path="/Game/Mods/TestPack/BP_TestWall",
            category_tag="Walls",
            tobis_json_dir=tobis_dir,
            templates_dir=templates_dir,
            user_name="TestUser",
        )
        path = os.path.join(tobis_dir, "DT_Constructions", "TestPack_Wall_A.json")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        nm = data["NameMap"]
        assert "TestPack_Wall_A" in nm
        assert "T_UI_BuildIcon_TestPack_Wall_A" in nm


class TestDtConstructionRecipesHandle:
    """Tests for dt_construction_recipes_handle()."""

    def test_creates_file(self, tobis_dir, templates_dir):
        dt_construction_recipes_handle(
            unique_tag="TestPack_Wall_A",
            tobis_json_dir=tobis_dir,
            templates_dir=templates_dir,
            category_tag="Walls",
            required_items=[("Item.Stone", 5)],
            unlock_option="UnlockRequiredItems",
            unlock_requirement="Ore.Iron",
        )
        path = os.path.join(tobis_dir, "DT_ConstructionRecipes", "TestPack_Wall_A.json")
        assert os.path.isfile(path)

    def test_recipe_name_set(self, tobis_dir, templates_dir):
        dt_construction_recipes_handle(
            unique_tag="TestPack_Wall_A",
            tobis_json_dir=tobis_dir,
            templates_dir=templates_dir,
            category_tag="Walls",
            required_items=[("Item.Stone", 5)],
            unlock_option="UnlockRequiredItems",
            unlock_requirement="Ore.Iron",
        )
        path = os.path.join(tobis_dir, "DT_ConstructionRecipes", "TestPack_Wall_A.json")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["Row"]["Name"] == "TestPack_Wall_A"

    def test_category_flags_applied(self, tobis_dir, templates_dir):
        dt_construction_recipes_handle(
            unique_tag="TestPack_Wall_A",
            tobis_json_dir=tobis_dir,
            templates_dir=templates_dir,
            category_tag="Walls",
            required_items=[("Item.Stone", 5)],
            unlock_option="UnlockRequiredItems",
            unlock_requirement="Ore.Iron",
        )
        path = os.path.join(tobis_dir, "DT_ConstructionRecipes", "TestPack_Wall_A.json")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        row = data["Row"]
        # Walls flags: Location=Base, Placement=SnapGrid, etc.
        assert row["Value"][2]["Value"] == "EConstructionLocation::Base"
        assert row["Value"][3]["Value"] == "EPlacementType::SnapGrid"

    def test_required_items_populated(self, tobis_dir, templates_dir):
        dt_construction_recipes_handle(
            unique_tag="TestPack_Wall_A",
            tobis_json_dir=tobis_dir,
            templates_dir=templates_dir,
            category_tag="Walls",
            required_items=[("Item.Stone", 5), ("Item.Wood", 3)],
            unlock_option="UnlockRequiredItems",
            unlock_requirement="Ore.Iron",
        )
        path = os.path.join(tobis_dir, "DT_ConstructionRecipes", "TestPack_Wall_A.json")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        materials = data["Row"]["Value"][16]["Value"]
        assert len(materials) == 2
        assert materials[0]["Value"][0]["Value"][0]["Value"] == "Item.Stone"
        assert materials[0]["Value"][2]["Value"] == 5
        assert materials[1]["Value"][0]["Value"][0]["Value"] == "Item.Wood"
        assert materials[1]["Value"][2]["Value"] == 3

    def test_namemap_contains_items(self, tobis_dir, templates_dir):
        dt_construction_recipes_handle(
            unique_tag="TestPack_Wall_A",
            tobis_json_dir=tobis_dir,
            templates_dir=templates_dir,
            category_tag="Walls",
            required_items=[("Item.Stone", 5), ("Item.Wood", 3)],
            unlock_option="UnlockRequiredItems",
            unlock_requirement="Ore.Iron",
        )
        path = os.path.join(tobis_dir, "DT_ConstructionRecipes", "TestPack_Wall_A.json")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        nm = data["NameMap"]
        assert "TestPack_Wall_A" in nm
        assert "Item.Stone" in nm
        assert "Item.Wood" in nm

    def test_unlock_required_items_path(self, tobis_dir, templates_dir):
        dt_construction_recipes_handle(
            unique_tag="TestPack_Wall_A",
            tobis_json_dir=tobis_dir,
            templates_dir=templates_dir,
            category_tag="Walls",
            required_items=[("Item.Stone", 5)],
            unlock_option="UnlockRequiredItems",
            unlock_requirement="Ore.Iron",
        )
        path = os.path.join(tobis_dir, "DT_ConstructionRecipes", "TestPack_Wall_A.json")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        unlocks = data["Row"]["Value"][20]["Value"]
        # [3] should be UnlockRequiredItems with Ore.Iron
        assert unlocks[3]["Value"][0]["Value"][0]["Value"] == "Ore.Iron"
        # [4] should be dummy UnlockRequiredConstructions
        assert unlocks[4]["Name"] == "UnlockRequiredConstructions"

    def test_unlock_required_constructions_path(self, tobis_dir, templates_dir):
        dt_construction_recipes_handle(
            unique_tag="TestPack_Wall_A",
            tobis_json_dir=tobis_dir,
            templates_dir=templates_dir,
            category_tag="Walls",
            required_items=[("Item.Stone", 5)],
            unlock_option="UnlockRequiredConstructions",
            unlock_requirement="Advanced_Column_A",
        )
        path = os.path.join(tobis_dir, "DT_ConstructionRecipes", "TestPack_Wall_A.json")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        unlocks = data["Row"]["Value"][20]["Value"]
        # [3] should be dummy UnlockRequiredItems
        assert unlocks[3]["Name"] == "UnlockRequiredItems"
        # [4] should be UnlockRequiredConstructions with Advanced_Column_A
        assert unlocks[4]["Value"][0]["Value"][0]["Value"] == "Advanced_Column_A"

    def test_dotted_category_tag_lookup(self, tobis_dir, templates_dir):
        """Category tag 'Granite.Floors' should fallback to 'Floors' lookup."""
        dt_construction_recipes_handle(
            unique_tag="TestPack_Floor_A",
            tobis_json_dir=tobis_dir,
            templates_dir=templates_dir,
            category_tag="Unknown.Walls",  # "Walls" exists as sub-key
            required_items=[("Item.Stone", 2)],
            unlock_option="UnlockRequiredItems",
            unlock_requirement="Ore.Iron",
        )
        path = os.path.join(tobis_dir, "DT_ConstructionRecipes", "TestPack_Floor_A.json")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Should have found Walls flags via dotted fallback
        row = data["Row"]
        assert row["Value"][2]["Value"] == "EConstructionLocation::Base"

    def test_empty_imports(self, tobis_dir, templates_dir):
        """Recipe files should have empty Imports."""
        dt_construction_recipes_handle(
            unique_tag="TestPack_Wall_A",
            tobis_json_dir=tobis_dir,
            templates_dir=templates_dir,
            category_tag="Walls",
            required_items=[("Item.Stone", 5)],
            unlock_option="UnlockRequiredItems",
            unlock_requirement="Ore.Iron",
        )
        path = os.path.join(tobis_dir, "DT_ConstructionRecipes", "TestPack_Wall_A.json")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["Imports"] == []


class TestApplyRecipeOverrides:
    """Tests for _apply_recipe_overrides()."""

    @staticmethod
    def _make_recipe_tpl():
        """Build a minimal recipe template with known fields."""
        return {
            "Value": [
                {"Name": "BuildProcess", "Value": "EBuildProcess::DualMode"},
                {"Name": "LocationRequirement",
                 "Value": "EConstructionLocation::Base"},
                {"Name": "PlacementType",
                 "Value": "EPlacementType::FreePlacement"},
                {"Name": "FoundationRule",
                 "Value": "EFoundationRule::Never"},
                {"Name": "bOnWall", "Value": False},
                {"Name": "bOnFloor", "Value": True},
                {"Name": "EnabledState",
                 "Value": "ERowEnabledState::Live"},
            ],
        }

    def test_override_enum_with_short_name(self):
        tpl = self._make_recipe_tpl()
        _apply_recipe_overrides(tpl, {"BuildProcess": "Instant"})
        bp = next(e for e in tpl["Value"] if e["Name"] == "BuildProcess")
        assert bp["Value"] == "EBuildProcess::Instant"

    def test_override_enum_with_full_name(self):
        tpl = self._make_recipe_tpl()
        _apply_recipe_overrides(tpl, {
            "LocationRequirement": "EConstructionLocation::Anywhere",
        })
        lr = next(e for e in tpl["Value"] if e["Name"] == "LocationRequirement")
        assert lr["Value"] == "EConstructionLocation::Anywhere"

    def test_override_bool(self):
        tpl = self._make_recipe_tpl()
        _apply_recipe_overrides(tpl, {"bOnWall": True})
        bw = next(e for e in tpl["Value"] if e["Name"] == "bOnWall")
        assert bw["Value"] is True

    def test_no_override_for_missing_field(self):
        tpl = self._make_recipe_tpl()
        _apply_recipe_overrides(tpl, {"NonExistentField": "whatever"})
        # Original values unchanged
        bp = next(e for e in tpl["Value"] if e["Name"] == "BuildProcess")
        assert bp["Value"] == "EBuildProcess::DualMode"

    def test_multiple_overrides(self):
        tpl = self._make_recipe_tpl()
        _apply_recipe_overrides(tpl, {
            "BuildProcess": "Instant",
            "bOnFloor": False,
            "FoundationRule": "Always",
        })
        bp = next(e for e in tpl["Value"] if e["Name"] == "BuildProcess")
        assert bp["Value"] == "EBuildProcess::Instant"
        bf = next(e for e in tpl["Value"] if e["Name"] == "bOnFloor")
        assert bf["Value"] is False
        fr = next(e for e in tpl["Value"] if e["Name"] == "FoundationRule")
        assert fr["Value"] == "EFoundationRule::Always"

    def test_override_non_enum_field(self):
        """Fields not in _enum_prefixes should be set directly."""
        tpl = self._make_recipe_tpl()
        # Add a non-enum field
        tpl["Value"].append({"Name": "CustomField", "Value": "old_value"})
        _apply_recipe_overrides(tpl, {"CustomField": "new_value"})
        cf = next(e for e in tpl["Value"] if e["Name"] == "CustomField")
        assert cf["Value"] == "new_value"

    def test_recipe_overrides_with_none(self):
        """Passing None for recipe_overrides in the caller should be safe."""
        tpl = self._make_recipe_tpl()
        # This should not raise (caller checks for None before calling)
        original_val = tpl["Value"][0]["Value"]
        _apply_recipe_overrides(tpl, {})
        assert tpl["Value"][0]["Value"] == original_val
