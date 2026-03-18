"""
CSVTOPo.py — Merge translated CSV rows back into a PO file.

Workflow
--------
1. Read a CSV file that contains translated strings (columns: Context,
   Source, Translation).  The CSV is typically produced by sending
   PoToCSV.py output to a translator or spreadsheet.
2. Load the *source* PO file which provides the structural template
   (comments, ordering, metadata).
3. Walk through every entry in the PO template.  When the (msgctxt,
   msgid) pair matches a row in the CSV *and* the CSV has a non-empty
   translation, replace the msgstr with the translated text.
4. Write the merged result to a new PO file for the target language.

The target language and file paths are driven by config.ini so this
script works on any machine without editing source code.
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

    # Source PO used as the structural template
    source_po = os.path.join(loc_dir, cfg.localization["source_po"])

    # CSV with translations for the target language
    csv_file = os.path.join(loc_dir, lang, f"Game_{lang}.csv")

    # Output PO file for the target language
    po_output = os.path.join(loc_dir, lang, f"Game.po")

    # ── Validate inputs exist ──
    for label, path in [("Source PO", source_po), ("CSV", csv_file)]:
        if not os.path.isfile(path):
            print(f"[ERROR] {label} not found: {path}", file=sys.stderr)
            sys.exit(1)

    # ─────────────────────────────────────────────────────────────────
    # Step 1: Build a lookup dictionary from the CSV.
    #         Key   = (msgctxt, msgid)  — uniquely identifies a string
    #         Value = translated text
    # ─────────────────────────────────────────────────────────────────
    translations: dict[tuple[str, str], str] = {}

    with open(csv_file, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            context = row["Context"].strip()
            source = row["Source"].strip()
            translation = row["Translation"].strip()

            if translation:  # skip rows without a translation
                translations[(context, source)] = translation

    # ─────────────────────────────────────────────────────────────────
    # Step 2: Walk the source PO line-by-line, replacing msgstr when
    #         a matching translation exists in the CSV.
    # ─────────────────────────────────────────────────────────────────
    output_lines: list[str] = []
    current_ctxt = ""
    current_id = ""
    inside_entry = False

    with open(source_po, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()

            if stripped.startswith("msgctxt"):
                # Extract the context string between quotes
                current_ctxt = re.findall(r'"(.*)"', stripped)[0]
                inside_entry = True
                output_lines.append(line)

            elif stripped.startswith("msgid"):
                # Extract the source string between quotes
                current_id = re.findall(r'"(.*)"', stripped)[0]
                inside_entry = True
                output_lines.append(line)

            elif stripped.startswith("msgstr") and inside_entry:
                # Check if we have a CSV translation for this entry
                key = (current_ctxt, current_id)

                if key in translations:
                    # Escape internal double-quotes in the translated text
                    translated = translations[key].replace('"', '\\"')
                    output_lines.append(f'msgstr "{translated}"\n')
                else:
                    # No CSV match — keep the original msgstr unchanged
                    output_lines.append(line)

                # Reset state for the next entry
                inside_entry = False
                current_ctxt = ""
                current_id = ""

            else:
                output_lines.append(line)

    # ─────────────────────────────────────────────────────────────────
    # Step 3: Write the merged PO to disk.
    # ─────────────────────────────────────────────────────────────────
    with open(po_output, "w", encoding="utf-8") as f:
        f.writelines(output_lines)

    print(f"PO updated successfully → {po_output}")
    print(f"Translations applied: {len(translations)}")


if __name__ == "__main__":
    main()
