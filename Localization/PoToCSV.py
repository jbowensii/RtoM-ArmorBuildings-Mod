"""
PoToCSV.py — Export a PO file to a CSV spreadsheet for translators.

Workflow
--------
1. Read the PO file for the target language (set in config.ini).
   Each PO entry has three fields: msgctxt (context key), msgid
   (English source), and msgstr (current translation — may be empty).
2. Collect every entry into a list.
3. Write the list to a CSV with columns: Context, Source, Translation.
   Translators fill in or correct the Translation column, and the
   result is fed back through CSVTOPo.py to produce an updated PO.

The CSV uses UTF-8 with BOM so Excel opens it correctly.
"""

import csv
import os
import re
import sys

# ── Add project root to path so we can import the shared config loader ──
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config_loader import cfg


def main():
    # ── Resolve paths from config ──
    lang = cfg.localization["target_lang"]
    loc_dir = cfg.path("Localization")

    po_file = os.path.join(loc_dir, lang, "Game.po")
    csv_file = os.path.join(loc_dir, lang, f"Game_{lang}.csv")

    if not os.path.isfile(po_file):
        print(f"[ERROR] PO file not found: {po_file}", file=sys.stderr)
        sys.exit(1)

    # ─────────────────────────────────────────────────────────────────
    # Step 1: Parse every entry from the PO file.
    #
    #   PO format (simplified):
    #     msgctxt "SomeContext"
    #     msgid   "English text"
    #     msgstr  "Translated text"
    #     <blank line separates entries>
    #
    #   We collect each triple into a dict and flush it on blank lines.
    # ─────────────────────────────────────────────────────────────────
    entries: list[dict[str, str]] = []
    current: dict[str, str] = {"msgctxt": "", "msgid": "", "msgstr": ""}

    def flush_entry():
        """Append the current entry to the list if it has a source string."""
        if current["msgid"]:
            entries.append(current.copy())

    with open(po_file, "r", encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()

            if line.startswith("msgctxt"):
                current["msgctxt"] = re.findall(r'"(.*)"', line)[0]

            elif line.startswith("msgid"):
                current["msgid"] = re.findall(r'"(.*)"', line)[0]

            elif line.startswith("msgstr"):
                current["msgstr"] = re.findall(r'"(.*)"', line)[0]

            elif line == "":
                # Blank line = end of entry
                flush_entry()
                current = {"msgctxt": "", "msgid": "", "msgstr": ""}

        # Flush the last entry (file may not end with a blank line)
        flush_entry()

    # ─────────────────────────────────────────────────────────────────
    # Step 2: Write entries to CSV.
    # ─────────────────────────────────────────────────────────────────
    with open(csv_file, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["Context", "Source", "Translation"])
        for entry in entries:
            writer.writerow([entry["msgctxt"], entry["msgid"], entry["msgstr"]])

    print(f"Converted: {len(entries)} entries → {csv_file}")


if __name__ == "__main__":
    main()
