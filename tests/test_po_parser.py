"""Tests for src.localization.po_parser — PO file parsing and merging."""

from __future__ import annotations

import pytest

from src.localization.po_parser import POEntry, extract_quoted, merge_translations, parse_po


# ── extract_quoted ───────────────────────────────────────────────────


class TestExtractQuoted:
    """Tests for the extract_quoted helper."""

    def test_simple_string(self):
        assert extract_quoted('msgid "Hello World"') == "Hello World"

    def test_empty_string(self):
        assert extract_quoted('msgstr ""') == ""

    def test_string_with_escaped_quotes(self):
        assert extract_quoted(r'msgstr "He said \"hi\""') == r'He said \"hi\"'

    def test_no_quotes_raises(self):
        with pytest.raises(ValueError, match="No quoted string"):
            extract_quoted("no quotes here")

    def test_context_string(self):
        result = extract_quoted('msgctxt "ST_Mod,Item_A.Name"')
        assert result == "ST_Mod,Item_A.Name"


# ── parse_po ─────────────────────────────────────────────────────────


class TestParsePo:
    """Tests for parsing PO files into POEntry lists."""

    def test_parses_all_entries(self, sample_po_file):
        entries = parse_po(sample_po_file)
        # Should have 3 entries (header with empty msgid is skipped)
        assert len(entries) == 3

    def test_entry_fields(self, sample_po_file):
        entries = parse_po(sample_po_file)
        first = entries[0]
        assert first.msgctxt == "ST_Mod,Item_A.Name"
        assert first.msgid == "Iron Helmet"
        assert first.msgstr == "Iron Helmet"

    def test_empty_msgstr_preserved(self, sample_po_file):
        entries = parse_po(sample_po_file)
        # Item_B has an empty msgstr
        item_b = [e for e in entries if "Item_B" in e.msgctxt][0]
        assert item_b.msgstr == ""

    def test_skips_header(self, sample_po_file):
        entries = parse_po(sample_po_file)
        # No entry should have an empty msgid (header is skipped)
        assert all(e.msgid for e in entries)

    def test_missing_file_raises(self):
        with pytest.raises(FileNotFoundError):
            parse_po("/nonexistent/path/Game.po")


# ── merge_translations ───────────────────────────────────────────────


class TestMergeTranslations:
    """Tests for merging CSV translations into PO lines."""

    def test_replaces_matching_msgstr(self, sample_po_file):
        translations = {
            ("ST_Mod,Item_A.Name", "Iron Helmet"): "Eisenhelm",
        }
        lines = merge_translations(sample_po_file, translations)
        output = "".join(lines)
        assert 'msgstr "Eisenhelm"' in output

    def test_preserves_unmatched_entries(self, sample_po_file):
        translations = {
            ("ST_Mod,Item_A.Name", "Iron Helmet"): "Eisenhelm",
        }
        lines = merge_translations(sample_po_file, translations)
        output = "".join(lines)
        # Item_A.Description was NOT in translations — should be unchanged
        assert 'msgstr "A sturdy helmet."' in output

    def test_escapes_quotes_in_translation(self, sample_po_file):
        translations = {
            ("ST_Mod,Item_A.Name", "Iron Helmet"): 'Helm "Eisen"',
        }
        lines = merge_translations(sample_po_file, translations)
        output = "".join(lines)
        assert r'msgstr "Helm \"Eisen\""' in output

    def test_empty_translations_dict_passes_through(self, sample_po_file):
        lines = merge_translations(sample_po_file, {})
        output = "".join(lines)
        # All original msgstr lines should be preserved unchanged
        assert 'msgstr "Iron Helmet"' in output
        assert 'msgstr "A sturdy helmet."' in output

    def test_preserves_comments(self, sample_po_file):
        lines = merge_translations(sample_po_file, {})
        output = "".join(lines)
        assert "#. Key: Item_A.Name" in output
