"""
csv_to_po — Merge translated CSV rows back into a PO file.

Workflow
--------
1. Read a CSV with columns ``Context``, ``Source``, ``Translation``.
2. Load the source PO file as a structural template.
3. Replace ``msgstr`` for every entry that has a CSV translation.
4. Write the merged PO for the target language.

The target language and file paths come from ``config.ini``.
"""

from __future__ import annotations

import csv
import os
import sys

from src.config import cfg
from src.localization.po_parser import merge_translations


def load_csv_translations(csv_path: str) -> dict[tuple[str, str], str]:
    """Read a translations CSV into a lookup dict.

    Args:
        csv_path: Path to the CSV file (UTF-8 with optional BOM).

    Returns:
        Dict mapping ``(context, source) → translation``.
        Rows with an empty Translation column are skipped.
    """
    translations: dict[tuple[str, str], str] = {}

    with open(csv_path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            context = row["Context"].strip()
            source = row["Source"].strip()
            translation = row["Translation"].strip()

            if translation:
                translations[(context, source)] = translation

    return translations


def run(
    source_po: str | None = None,
    csv_file: str | None = None,
    output_po: str | None = None,
) -> int:
    """Execute the CSV → PO merge.

    All arguments are optional — defaults are derived from ``config.ini``.

    Returns:
        Number of translations applied.
    """
    lang = cfg.localization["target_lang"]
    loc_dir = cfg.path("Localization")

    if source_po is None:
        source_po = os.path.join(loc_dir, cfg.localization["source_po"])
    if csv_file is None:
        csv_file = os.path.join(loc_dir, lang, f"Game_{lang}.csv")
    if output_po is None:
        output_po = os.path.join(loc_dir, lang, "Game.po")

    # ── Validate inputs ──
    for label, path in [("Source PO", source_po), ("CSV", csv_file)]:
        if not os.path.isfile(path):
            print(f"[csv_to_po] ERROR: {label} not found: {path}", file=sys.stderr)
            sys.exit(1)

    # ── Step 1: Build translation lookup from CSV ──
    translations = load_csv_translations(csv_file)

    # ── Step 2: Merge into the PO template ──
    output_lines = merge_translations(source_po, translations)

    # ── Step 3: Write result ──
    with open(output_po, "w", encoding="utf-8") as fh:
        fh.writelines(output_lines)

    print(f"PO updated successfully -> {output_po}")
    print(f"Translations applied: {len(translations)}")
    return len(translations)


def main() -> None:
    """CLI entry point."""
    run()


if __name__ == "__main__":
    main()
