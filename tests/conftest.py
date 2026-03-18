"""
Shared pytest fixtures for RtoM-ArmorBuildings-Mod tests.

These fixtures create temporary PO files, CSV files, and JSON structures
so tests run in isolation without touching real project data.
"""

from __future__ import annotations

import json
import os
import textwrap

import pytest


# ── PO content fixtures ─────────────────────────────────────────────


SAMPLE_PO = textwrap.dedent("""\
    # Sample PO for testing.
    msgid ""
    msgstr ""
    "Content-Type: text/plain; charset=UTF-8\\n"

    #. Key: Item_A.Name
    msgctxt "ST_Mod,Item_A.Name"
    msgid "Iron Helmet"
    msgstr "Iron Helmet"

    #. Key: Item_A.Description
    msgctxt "ST_Mod,Item_A.Description"
    msgid "A sturdy helmet."
    msgstr "A sturdy helmet."

    #. Key: Item_B.Name
    msgctxt "ST_Mod,Item_B.Name"
    msgid "Steel Boots"
    msgstr ""

""")

SAMPLE_CSV_HEADER = "Context,Source,Translation\n"

SAMPLE_CSV_ROWS = (
    '"ST_Mod,Item_A.Name","Iron Helmet","Eisenhelm"\n'
    '"ST_Mod,Item_A.Description","A sturdy helmet.","Ein robuster Helm."\n'
    '"ST_Mod,Item_B.Name","Steel Boots","Stahlstiefel"\n'
)


@pytest.fixture()
def sample_po_file(tmp_path):
    """Write the sample PO to a temp file and return its path."""
    po = tmp_path / "Game.po"
    po.write_text(SAMPLE_PO, encoding="utf-8")
    return str(po)


@pytest.fixture()
def sample_csv_file(tmp_path):
    """Write a sample translations CSV and return its path."""
    csv_path = tmp_path / "Game_de.csv"
    csv_path.write_text(
        SAMPLE_CSV_HEADER + SAMPLE_CSV_ROWS,
        encoding="utf-8-sig",
    )
    return str(csv_path)


# ── Recipe JSON fixtures ────────────────────────────────────────────


def _make_recipe_row(name: str, unlock_type: str = "EMorRecipeUnlockType::Manual"):
    """Build a minimal UAssetAPI-style recipe row for testing."""
    return {
        "Name": name,
        "Value": [
            # Index 0: item reference
            {"Value": [{"Value": name}]},
            # Indices 1-11: placeholder padding
            *[{"Value": "padding"} for _ in range(11)],
            # Index 12: unlock info
            {
                "Value": [
                    {"Value": unlock_type},   # [0] unlock type
                    {"Value": "placeholder"}, # [1]
                    {"Value": "placeholder"}, # [2]
                    {"Value": "placeholder"}, # [3] will be replaced by template
                ]
            },
        ],
    }


UNLOCK_TEMPLATE = {
    "$type": "UAssetAPI.PropertyTypes.Objects.ArrayPropertyData, UAssetAPI",
    "Name": "UnlockRequiredItems",
    "Value": [
        {
            "$type": "UAssetAPI.PropertyTypes.Structs.StructPropertyData, UAssetAPI",
            "Name": "UnlockRequiredItems",
            "Value": [
                {
                    "$type": "UAssetAPI.PropertyTypes.Objects.NamePropertyData, UAssetAPI",
                    "Name": "RowName",
                    "Value": "",
                }
            ],
        }
    ],
}


@pytest.fixture()
def sample_recipes_json(tmp_path):
    """Write a minimal DT_ItemRecipes.json and return its path."""
    data = {
        "Exports": [
            {
                "Table": {
                    "Data": [
                        _make_recipe_row("Khazad_Chest"),
                        _make_recipe_row("Khazad_White_Chest"),
                        _make_recipe_row("Khazad_Black_Chest"),
                        _make_recipe_row("Khazad_Gold_Chest"),
                        _make_recipe_row("Erebor_Boots"),
                    ]
                }
            }
        ]
    }
    path = tmp_path / "DT_ItemRecipes.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return str(path)


@pytest.fixture()
def unlock_template_json(tmp_path):
    """Write the UnlockRequiredItems template and return its path."""
    path = tmp_path / "UnlockRequiredItems.json"
    path.write_text(json.dumps(UNLOCK_TEMPLATE, indent=2), encoding="utf-8")
    return str(path)
