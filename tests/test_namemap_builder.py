"""Tests for item_adder_tab module-level NameMap builder functions.

Tests _collect_namemap_strings, _collect_from_dict, and
ItemAdderTab._build_namemap (static method, no Qt required).
"""

import pytest

from src.gui.item_adder_tab import (
    _collect_namemap_strings,
    _collect_from_dict,
    ItemAdderTab,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def simple_row():
    """A minimal row with string values and a Name field."""
    return {
        "$type": "UAssetAPI.PropertyTypes.Structs.StructPropertyData, UAssetAPI",
        "StructType": "MorArmorDefinition",
        "Name": "TestArmor",
        "Value": [
            {
                "$type": "UAssetAPI.PropertyTypes.Objects.TextPropertyData, UAssetAPI",
                "Name": "DisplayName",
                "Value": "TestArmor.Name",
            },
            {
                "$type": "UAssetAPI.PropertyTypes.Objects.TextPropertyData, UAssetAPI",
                "Name": "Description",
                "Value": "TestArmor.Description",
            },
        ],
    }


@pytest.fixture
def enum_row():
    """A row with an EnumProperty field."""
    return {
        "Name": "EnumTest",
        "Value": [
            {
                "$type": "UAssetAPI.PropertyTypes.Objects.EnumPropertyData, UAssetAPI",
                "EnumType": "EArmorType",
                "Name": "ArmorType",
                "Value": "EArmorType::Heavy",
            },
        ],
    }


@pytest.fixture
def asset_path_row():
    """A row with a SoftObjectProperty containing an AssetPath."""
    return {
        "Name": "AssetTest",
        "Value": [
            {
                "$type": "UAssetAPI.PropertyTypes.Objects.SoftObjectPropertyData, UAssetAPI",
                "Name": "Mesh",
                "Value": {
                    "AssetPath": {
                        "AssetName": "/Game/Items/Armor/SM_TestHelm.SM_TestHelm",
                    },
                    "SubPathString": None,
                },
            },
        ],
    }


@pytest.fixture
def gameplay_tag_row():
    """A row with a GameplayTagContainer."""
    return {
        "Name": "TagTest",
        "Value": [
            {
                "$type": "UAssetAPI.PropertyTypes.Structs.StructPropertyData, UAssetAPI",
                "StructType": "GameplayTagContainer",
                "Name": "Tags",
                "Value": [
                    {
                        "$type": "UAssetAPI.PropertyTypes.Structs."
                                 "GameplayTagContainerPropertyData, UAssetAPI",
                        "Name": "Tags",
                        "Value": [
                            "Equipment.Armor.Head",
                            "Equipment.Armor.Heavy",
                        ],
                    },
                ],
            },
        ],
    }


@pytest.fixture
def nested_struct_row():
    """A row with a nested struct inside its Value."""
    return {
        "Name": "NestedTest",
        "Value": [
            {
                "$type": "UAssetAPI.PropertyTypes.Structs.StructPropertyData, UAssetAPI",
                "StructType": "MorConstructionRowHandle",
                "Name": "ResultConstructionHandle",
                "Value": [
                    {
                        "$type": "UAssetAPI.PropertyTypes.Objects.NamePropertyData, UAssetAPI",
                        "Name": "RowName",
                        "Value": "TestConstruction_A",
                    },
                ],
            },
        ],
    }


@pytest.fixture
def object_name_row():
    """A row with an ObjectName field (used in Imports)."""
    return {
        "$type": "UAssetAPI.Import, UAssetAPI",
        "ObjectName": "T_UI_BuildIcon_TestWall",
        "ClassName": "Texture2D",
        "ClassPackage": "/Script/Engine",
        "OuterIndex": -5,
    }


# ---------------------------------------------------------------------------
# Tests: _collect_namemap_strings
# ---------------------------------------------------------------------------

class TestCollectNamemapStrings:
    """Tests for _collect_namemap_strings()."""

    def test_collects_from_list_of_strings(self):
        names = {}
        _collect_namemap_strings(["Alpha", "Beta", "Gamma"], names)
        assert "Alpha" in names
        assert "Beta" in names
        assert "Gamma" in names

    def test_skips_empty_strings_in_list(self):
        names = {}
        _collect_namemap_strings(["Hello", "", "World"], names)
        assert "" not in names
        assert "Hello" in names
        assert "World" in names

    def test_recurses_into_nested_list(self):
        names = {}
        obj = [{"Name": "InnerField", "Value": "InnerValue"}]
        _collect_namemap_strings(obj, names)
        assert "InnerField" in names
        assert "InnerValue" in names

    def test_handles_dict_input(self):
        names = {}
        _collect_namemap_strings({"Name": "MyField", "Value": "MyValue"}, names)
        assert "MyField" in names
        assert "MyValue" in names

    def test_handles_non_string_non_container(self):
        """Numbers and booleans should not crash or add entries."""
        names = {}
        _collect_namemap_strings([42, True, None, 3.14], names)
        assert len(names) == 0


# ---------------------------------------------------------------------------
# Tests: _collect_from_dict
# ---------------------------------------------------------------------------

class TestCollectFromDict:
    """Tests for _collect_from_dict()."""

    def test_collects_metadata_fields(self):
        names = {}
        obj = {
            "Name": "BuildProcess",
            "StructType": "MorRecipeDefinition",
            "EnumType": "EBuildProcess",
            "ArrayType": "StructProperty",
        }
        _collect_from_dict(obj, names)
        assert "BuildProcess" in names
        assert "MorRecipeDefinition" in names
        assert "EBuildProcess" in names
        assert "StructProperty" in names

    def test_collects_property_type_from_dtype(self):
        names = {}
        obj = {
            "$type": "UAssetAPI.PropertyTypes.Objects.EnumPropertyData, UAssetAPI",
            "Name": "TestField",
        }
        _collect_from_dict(obj, names)
        assert "EnumProperty" in names

    def test_strips_data_suffix_from_type(self):
        """TextPropertyData should become TextProperty."""
        names = {}
        obj = {
            "$type": "UAssetAPI.PropertyTypes.Objects.TextPropertyData, UAssetAPI",
            "Name": "DisplayName",
            "Value": "Hello",
        }
        _collect_from_dict(obj, names)
        assert "TextProperty" in names

    def test_ignores_non_property_types(self):
        """Type names like StructPropertyData → StructProperty are fine,
        but random types should not be added."""
        names = {}
        obj = {
            "$type": "UAssetAPI.Import, UAssetAPI",
            "Name": "SomeName",
        }
        _collect_from_dict(obj, names)
        # "Import" is not in _PROP_TYPE_NAMES, should not be added
        assert "Import" not in names

    def test_collects_string_value(self):
        names = {}
        obj = {"Name": "Field", "Value": "SomeEnumValue"}
        _collect_from_dict(obj, names)
        assert "SomeEnumValue" in names

    def test_collects_asset_path(self):
        names = {}
        obj = {
            "Name": "Mesh",
            "Value": {},
            "AssetPath": {"AssetName": "/Game/Items/SM_Helm.SM_Helm"},
        }
        _collect_from_dict(obj, names)
        assert "/Game/Items/SM_Helm.SM_Helm" in names

    def test_collects_object_name(self):
        names = {}
        obj = {
            "ObjectName": "T_UI_Icon_Sword",
            "ClassName": "Texture2D",
        }
        _collect_from_dict(obj, names)
        assert "T_UI_Icon_Sword" in names
        assert "Texture2D" in names

    def test_recurses_into_child_structures(self):
        names = {}
        obj = {
            "Name": "Parent",
            "SomeList": [
                {"Name": "Child", "Value": "ChildVal"},
            ],
        }
        _collect_from_dict(obj, names)
        assert "Child" in names
        assert "ChildVal" in names

    def test_skips_empty_strings(self):
        names = {}
        obj = {"Name": "", "Value": "", "ObjectName": ""}
        _collect_from_dict(obj, names)
        assert "" not in names


# ---------------------------------------------------------------------------
# Tests: ItemAdderTab._build_namemap (static method)
# ---------------------------------------------------------------------------

class TestBuildNamemap:
    """Tests for ItemAdderTab._build_namemap() — called as static method."""

    def test_simple_row(self, simple_row):
        result = ItemAdderTab._build_namemap(simple_row)
        assert "MorArmorDefinition" in result
        assert "TestArmor" in result
        assert "DisplayName" in result
        assert "Description" in result
        assert "TestArmor.Name" in result
        assert "TestArmor.Description" in result

    def test_enum_values_collected(self, enum_row):
        result = ItemAdderTab._build_namemap(enum_row)
        assert "EArmorType" in result
        assert "EArmorType::Heavy" in result
        assert "ArmorType" in result
        assert "EnumProperty" in result

    def test_asset_paths_collected(self, asset_path_row):
        result = ItemAdderTab._build_namemap(asset_path_row)
        assert "/Game/Items/Armor/SM_TestHelm.SM_TestHelm" in result
        assert "Mesh" in result

    def test_gameplay_tag_container(self, gameplay_tag_row):
        result = ItemAdderTab._build_namemap(gameplay_tag_row)
        assert "GameplayTagContainer" in result
        assert "Tags" in result
        assert "Equipment.Armor.Head" in result
        assert "Equipment.Armor.Heavy" in result

    def test_nested_structs(self, nested_struct_row):
        result = ItemAdderTab._build_namemap(nested_struct_row)
        assert "MorConstructionRowHandle" in result
        assert "ResultConstructionHandle" in result
        assert "RowName" in result
        assert "TestConstruction_A" in result

    def test_standard_entries_always_present(self, simple_row):
        result = ItemAdderTab._build_namemap(simple_row)
        for std in ("None", "Object", "Package", "StringTable",
                    "GameplayTag", "GameplayTagContainer"):
            assert std in result, f"Standard entry '{std}' missing"

    def test_filters_uasset_internals(self, simple_row):
        result = ItemAdderTab._build_namemap(simple_row)
        for name in result:
            assert not name.startswith("UAssetAPI."), \
                f"UAssetAPI internal '{name}' should be filtered"
            assert not name.startswith("{00000000"), \
                f"GUID '{name}' should be filtered"
            assert name != "NoExtension", \
                "'NoExtension' should be filtered"

    def test_empty_row(self):
        """An empty row should still have standard entries."""
        result = ItemAdderTab._build_namemap({})
        assert "None" in result
        assert "Package" in result

    def test_object_name_collected(self, object_name_row):
        """ObjectName from Import-style dicts should be collected."""
        names = {}
        _collect_from_dict(object_name_row, names)
        assert "T_UI_BuildIcon_TestWall" in names
        assert "Texture2D" in names

    def test_no_duplicates(self, simple_row):
        """NameMap should not contain duplicate entries."""
        result = ItemAdderTab._build_namemap(simple_row)
        assert len(result) == len(set(result))

    def test_complex_construction_template(self):
        """Test with a structure similar to ConstructionTemplate.json."""
        row = {
            "$type": "UAssetAPI.PropertyTypes.Structs.StructPropertyData, UAssetAPI",
            "StructType": "MorConstructionDefinition",
            "Name": "TestWall_A",
            "Value": [
                {
                    "$type": "UAssetAPI.PropertyTypes.Objects.TextPropertyData, UAssetAPI",
                    "Name": "DisplayName",
                    "TableId": "/Game/Mods/Tech/Data/StringTables/ST_Mod_Architecture.ST_Mod_Architecture",
                    "Value": "TestWall_A.Name",
                },
                {
                    "$type": "UAssetAPI.PropertyTypes.Objects.ObjectPropertyData, UAssetAPI",
                    "Name": "Icon",
                    "Value": -1,
                },
                {
                    "$type": "UAssetAPI.PropertyTypes.Objects.SoftObjectPropertyData, UAssetAPI",
                    "Name": "Actor",
                    "Value": {
                        "AssetPath": {
                            "AssetName": "/Game/Mods/BP_TestWall.BP_TestWall_C",
                        },
                    },
                },
                {
                    "$type": "UAssetAPI.PropertyTypes.Objects.EnumPropertyData, UAssetAPI",
                    "EnumType": "ERowEnabledState",
                    "Name": "EnabledState",
                    "Value": "ERowEnabledState::Live",
                },
            ],
        }
        result = ItemAdderTab._build_namemap(row)
        assert "MorConstructionDefinition" in result
        assert "TestWall_A" in result
        assert "DisplayName" in result
        assert "Icon" in result
        assert "Actor" in result
        assert "EnabledState" in result
        assert "ERowEnabledState" in result
        assert "ERowEnabledState::Live" in result
        assert "/Game/Mods/BP_TestWall.BP_TestWall_C" in result
        assert "/Game/Mods/Tech/Data/StringTables/ST_Mod_Architecture.ST_Mod_Architecture" in result
        assert "TextProperty" in result
        assert "ObjectProperty" in result
        assert "SoftObjectProperty" in result
        assert "EnumProperty" in result
