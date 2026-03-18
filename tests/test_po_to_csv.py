"""Tests for src.localization.po_to_csv — PO → CSV export."""

from __future__ import annotations

import csv

from src.localization.po_parser import POEntry
from src.localization.po_to_csv import write_entries_csv


class TestWriteEntriesCsv:
    """Tests for CSV output generation."""

    def test_creates_csv_with_header(self, tmp_path):
        csv_path = str(tmp_path / "output.csv")
        entries = [POEntry(msgctxt="Ctx", msgid="Hello", msgstr="Hallo")]

        write_entries_csv(entries, csv_path)

        with open(csv_path, newline="", encoding="utf-8-sig") as fh:
            reader = csv.reader(fh)
            header = next(reader)

        assert header == ["Context", "Source", "Translation"]

    def test_writes_all_entries(self, tmp_path):
        csv_path = str(tmp_path / "output.csv")
        entries = [
            POEntry(msgctxt="A", msgid="One", msgstr="Eins"),
            POEntry(msgctxt="B", msgid="Two", msgstr="Zwei"),
            POEntry(msgctxt="C", msgid="Three", msgstr=""),
        ]

        write_entries_csv(entries, csv_path)

        with open(csv_path, newline="", encoding="utf-8-sig") as fh:
            reader = csv.reader(fh)
            next(reader)  # skip header
            rows = list(reader)

        assert len(rows) == 3
        assert rows[0] == ["A", "One", "Eins"]
        assert rows[2] == ["C", "Three", ""]

    def test_empty_entries_produces_header_only(self, tmp_path):
        csv_path = str(tmp_path / "output.csv")
        write_entries_csv([], csv_path)

        with open(csv_path, newline="", encoding="utf-8-sig") as fh:
            reader = csv.reader(fh)
            header = next(reader)
            rows = list(reader)

        assert header == ["Context", "Source", "Translation"]
        assert rows == []
