"""Tests for src.localization.csv_to_po — CSV → PO merge."""

from __future__ import annotations

from src.localization.csv_to_po import load_csv_translations


class TestLoadCsvTranslations:
    """Tests for loading translations from CSV."""

    def test_loads_all_non_empty_rows(self, sample_csv_file):
        translations = load_csv_translations(sample_csv_file)
        # 3 rows in the sample CSV, all with translations
        assert len(translations) == 3

    def test_correct_key_value_pairs(self, sample_csv_file):
        translations = load_csv_translations(sample_csv_file)
        assert translations[("ST_Mod,Item_A.Name", "Iron Helmet")] == "Eisenhelm"
        assert translations[("ST_Mod,Item_B.Name", "Steel Boots")] == "Stahlstiefel"

    def test_skips_empty_translations(self, tmp_path):
        csv_path = tmp_path / "partial.csv"
        csv_path.write_text(
            "Context,Source,Translation\n"
            '"Ctx","Source",""\n'
            '"Ctx2","Source2","Has translation"\n',
            encoding="utf-8-sig",
        )
        translations = load_csv_translations(str(csv_path))
        assert len(translations) == 1
        assert ("Ctx2", "Source2") in translations

    def test_strips_whitespace(self, tmp_path):
        csv_path = tmp_path / "spaces.csv"
        csv_path.write_text(
            "Context,Source,Translation\n"
            '" Ctx "," Source "," Trans "\n',
            encoding="utf-8-sig",
        )
        translations = load_csv_translations(str(csv_path))
        assert ("Ctx", "Source") in translations
        assert translations[("Ctx", "Source")] == "Trans"
