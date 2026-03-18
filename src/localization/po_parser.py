"""
Shared PO-file parsing utilities.

The PO (Portable Object) format is a GNU gettext standard used by UE4's
localisation system.  A simplified entry looks like::

    #. Key: SomeKey
    #: /Game/Path/To/StringTable.StringTable
    msgctxt "StringTable,SomeKey"
    msgid   "English source text"
    msgstr  "Translated text"

Entries are separated by blank lines.  This module provides helpers to
parse and reassemble PO files without pulling in a full gettext library.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Pre-compiled regex: extract the first double-quoted string on a line.
_QUOTED_RE = re.compile(r'"(.*)"')


@dataclass
class POEntry:
    """One translation unit from a PO file."""

    msgctxt: str = ""
    msgid: str = ""
    msgstr: str = ""


def extract_quoted(line: str) -> str:
    """Return the text between the first pair of double-quotes on *line*.

    Raises ``ValueError`` if no quoted string is found.
    """
    match = _QUOTED_RE.search(line)
    if match is None:
        raise ValueError(f"No quoted string found in: {line!r}")
    return match.group(1)


def parse_po(filepath: str, encoding: str = "utf-8-sig") -> list[POEntry]:
    """Parse a PO file into a list of :class:`POEntry` objects.

    Only entries with a non-empty ``msgid`` are returned (the header
    entry, which has an empty msgid, is skipped).

    Args:
        filepath: Absolute path to the ``.po`` file.
        encoding: File encoding (default ``utf-8-sig`` to handle BOM).

    Returns:
        List of parsed entries.
    """
    entries: list[POEntry] = []
    current = POEntry()

    def _flush() -> None:
        """Append current entry if it has content, then reset."""
        if current.msgid:
            entries.append(POEntry(
                msgctxt=current.msgctxt,
                msgid=current.msgid,
                msgstr=current.msgstr,
            ))

    with open(filepath, "r", encoding=encoding) as fh:
        for line in fh:
            stripped = line.strip()

            if stripped.startswith("msgctxt"):
                current.msgctxt = extract_quoted(stripped)
            elif stripped.startswith("msgid"):
                current.msgid = extract_quoted(stripped)
            elif stripped.startswith("msgstr"):
                current.msgstr = extract_quoted(stripped)
            elif stripped == "":
                _flush()
                current = POEntry()

        # Flush last entry (file may not end with a blank line)
        _flush()

    return entries


def merge_translations(
    po_path: str,
    translations: dict[tuple[str, str], str],
    encoding: str = "utf-8",
) -> list[str]:
    """Walk a PO file line-by-line, replacing msgstr where translations exist.

    This preserves all comments, ordering, and metadata from the original
    file — only ``msgstr`` lines are touched.

    Args:
        po_path:      Path to the source/template PO file.
        translations: Mapping of ``(msgctxt, msgid) → translated text``.
        encoding:     File encoding for the source PO.

    Returns:
        List of output lines (including newlines) ready to be written.
    """
    output_lines: list[str] = []
    current_ctxt = ""
    current_id = ""
    inside_entry = False

    with open(po_path, "r", encoding=encoding) as fh:
        for line in fh:
            stripped = line.strip()

            if stripped.startswith("msgctxt"):
                current_ctxt = extract_quoted(stripped)
                inside_entry = True
                output_lines.append(line)

            elif stripped.startswith("msgid"):
                current_id = extract_quoted(stripped)
                inside_entry = True
                output_lines.append(line)

            elif stripped.startswith("msgstr") and inside_entry:
                key = (current_ctxt, current_id)

                if key in translations:
                    escaped = translations[key].replace('"', '\\"')
                    output_lines.append(f'msgstr "{escaped}"\n')
                else:
                    output_lines.append(line)

                inside_entry = False
                current_ctxt = ""
                current_id = ""

            else:
                output_lines.append(line)

    return output_lines
