"""
po_to_csv — Export a PO file to CSV for translators.

Workflow
--------
1. Parse the PO file for the target language.
2. Collect every ``(msgctxt, msgid, msgstr)`` entry.
3. Write to CSV with columns: ``Context``, ``Source``, ``Translation``.
   Uses UTF-8 with BOM so Excel opens it correctly.

Translators fill in the *Translation* column, then the result is fed
back through :mod:`src.localization.csv_to_po`.
"""

from __future__ import annotations

import csv
import os
import sys

from src.config import cfg
from src.localization.po_parser import POEntry, parse_po


def write_entries_csv(entries: list[POEntry], csv_path: str) -> None:
    """Write parsed PO entries to a CSV file.

    Args:
        entries:  List of :class:`POEntry` objects.
        csv_path: Output path (written with UTF-8 BOM for Excel).
    """
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.writer(fh)
        writer.writerow(["Context", "Source", "Translation"])
        for entry in entries:
            writer.writerow([entry.msgctxt, entry.msgid, entry.msgstr])


def run(
    po_file: str | None = None,
    csv_file: str | None = None,
) -> int:
    """Execute the PO → CSV export.

    All arguments are optional — defaults come from ``config.ini``.

    Returns:
        Number of entries exported.
    """
    lang = cfg.localization["target_lang"]
    loc_dir = cfg.path("Localization")

    if po_file is None:
        po_file = os.path.join(loc_dir, lang, "Game.po")
    if csv_file is None:
        csv_file = os.path.join(loc_dir, lang, f"Game_{lang}.csv")

    if not os.path.isfile(po_file):
        print(f"[po_to_csv] ERROR: PO file not found: {po_file}", file=sys.stderr)
        sys.exit(1)

    # ── Parse and export ──
    entries = parse_po(po_file)
    write_entries_csv(entries, csv_file)

    print(f"Converted: {len(entries)} entries → {csv_file}")
    return len(entries)


def main() -> None:
    """CLI entry point."""
    run()


if __name__ == "__main__":
    main()
