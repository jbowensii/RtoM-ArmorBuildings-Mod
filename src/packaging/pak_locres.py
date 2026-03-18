"""
pak_locres — Generate a Paklist and invoke UnrealPak to build a
             localisation .pak archive.

This is the Python equivalent of ``PakLocres.bat``.  It can be called
from the command line or imported and used programmatically.

Workflow
--------
1. Read paths from ``config.ini``.
2. Generate ``Paklist.txt`` mapping source ``.locres`` files to their
   in-pak mount points.
3. Invoke ``UnrealPak.exe`` with ``-create`` and ``-compress``.
"""

from __future__ import annotations

import os
import subprocess
import sys

from src.config import cfg


def generate_paklist(mod_loc_dir: str, project_root: str) -> list[str]:
    """Build the Paklist entries for the localisation pak.

    Each entry is a line: ``"<absolute_source>" "<relative_mount>"``

    Returns:
        List of paklist lines (without trailing newlines).
    """
    entries = [
        (
            os.path.join(
                mod_loc_dir, "Moria", "Content", "Localization",
                "Game", lang, "Game.locres",
            ),
            f"../../../Moria/Content/Localization/Game/{lang}/Game.locres",
        )
        for lang in ("es", "fr")
    ]

    # DefaultGameplayTags.ini is also bundled in the localization pak
    entries.append((
        os.path.join(
            project_root, "modified-json", "Moria", "Config",
            "DefaultGameplayTags.ini",
        ),
        "../../../Moria/Config/DefaultGameplayTags.ini",
    ))

    return [f'"{src}" "{mount}"' for src, mount in entries]


def run() -> int:
    """Execute the pak build.

    Returns:
        UnrealPak exit code (0 = success).
    """
    unrealpak = cfg.ue4_path("Engine", "Binaries", "Win64", "UnrealPak.exe")
    loc_dir = cfg.path("Localization")
    mod_loc_dir = os.path.join(loc_dir, "ModLocalization")
    paklist_path = os.path.join(mod_loc_dir, "Paklist.txt")
    pak_filename = cfg.localization["pak_filename"]
    pak_output = os.path.join(loc_dir, pak_filename)

    # ── Validate ──
    if not os.path.isfile(unrealpak):
        print(
            f"[pak_locres] ERROR: UnrealPak.exe not found: {unrealpak}",
            file=sys.stderr,
        )
        sys.exit(1)

    # ── Generate Paklist.txt ──
    lines = generate_paklist(mod_loc_dir, cfg.project_root)
    with open(paklist_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"Generated Paklist.txt ({len(lines)} entries)")

    # ── Invoke UnrealPak ──
    cmd = [unrealpak, pak_output, f"-create={paklist_path}", "-compress"]
    print(f"Running: {' '.join(cmd)}")

    result = subprocess.run(cmd, capture_output=True, text=True, check=False)

    if result.returncode != 0:
        print(f"[pak_locres] ERROR: UnrealPak exited {result.returncode}")
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        return result.returncode

    print(f"SUCCESS: {pak_output}")
    return 0


def main() -> None:
    """CLI entry point."""
    sys.exit(run())


if __name__ == "__main__":
    main()
