"""Extract game DataTable files using retoc + UAssetGUI.

Reads the extraction manifest (``data/extraction_manifest.ini``) to know
which files to pull from the game's IoStore paks and converts them to JSON.
Extracted files land in ``data/game_extract/`` with both the retoc .uasset
intermediates and the final UAssetGUI JSON output preserved.
"""

from __future__ import annotations

import configparser
import logging
import os
import subprocess
from typing import Any, Callable

log = logging.getLogger(__name__)

# ── Known game install locations ────────────────────────────────────

STEAM_DEFAULT = (
    r"C:\Program Files (x86)\Steam\steamapps\common"
    r"\The Lord of the Rings Return to Moria™"
)
EPIC_DEFAULT = r"C:\Program Files\Epic Games\ReturnToMoria"

_CREATE_NO_WINDOW = 0x08000000


# ── Detection ───────────────────────────────────────────────────────

def _has_paks(path: str) -> bool:
    """Return True if *path* looks like a valid game installation."""
    paks = os.path.join(path, "Moria", "Content", "Paks")
    return os.path.isdir(paks)


def detect_game_paths() -> list[tuple[str, str]]:
    """Return a list of ``(path, type)`` for detected game installations."""
    found: list[tuple[str, str]] = []
    if _has_paks(STEAM_DEFAULT):
        found.append((STEAM_DEFAULT, "Steam"))
    if _has_paks(EPIC_DEFAULT):
        found.append((EPIC_DEFAULT, "Epic Games"))
    return found


# ── Manifest ────────────────────────────────────────────────────────

def load_manifest(manifest_path: str) -> list[dict[str, Any]]:
    """Parse ``extraction_manifest.ini`` into a list of extraction targets.

    Each dict has keys: name, stem, game_path, ue_version, retoc_version,
    shell_group (optional), has_imports (bool), update_mods_group (optional).
    """
    parser = configparser.ConfigParser()
    parser.read(manifest_path, encoding="utf-8")

    targets: list[dict[str, Any]] = []
    for section in parser.sections():
        entry: dict[str, Any] = {
            "name": section,
            "stem": parser.get(section, "stem"),
            "game_path": parser.get(section, "game_path"),
            "ue_version": parser.get(section, "ue_version", fallback="VER_UE4_27"),
            "retoc_version": parser.get(section, "retoc_version", fallback="UE4_27"),
            "shell_group": parser.get(section, "shell_group", fallback=""),
            "has_imports": parser.getboolean(section, "has_imports", fallback=False),
            "update_mods_group": parser.get(section, "update_mods_group", fallback=""),
        }
        targets.append(entry)
    return targets


# ── Single-file extraction ──────────────────────────────────────────

def _run(cmd: list[str], timeout: int = 120) -> subprocess.CompletedProcess:
    """Run a subprocess with hidden window and UTF-8 output."""
    log.debug("Running: %s", " ".join(cmd))
    return subprocess.run(
        cmd,
        check=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        creationflags=_CREATE_NO_WINDOW,
    )


def extract_uasset(
    stem: str,
    paks_dir: str,
    retoc_exe: str,
    output_dir: str,
    ue_version: str = "UE4_27",
) -> None:
    """Run retoc to extract a .uasset by stem name."""
    cmd = [
        retoc_exe, "to-legacy",
        "--version", ue_version,
        "--filter", stem,
        paks_dir, output_dir,
    ]
    result = _run(cmd, timeout=120)
    log.debug("retoc stdout: %s", result.stdout)


def convert_to_json(
    uasset_path: str,
    json_path: str,
    uassetgui_exe: str,
    ue_version: str = "UE4_27",
) -> None:
    """Run UAssetGUI to convert a .uasset to JSON."""
    os.makedirs(os.path.dirname(json_path), exist_ok=True)
    cmd = [uassetgui_exe, "tojson", uasset_path, json_path, ue_version]
    result = _run(cmd, timeout=60)
    log.debug("UAssetGUI stdout: %s", result.stdout)


# ── Orchestrator ────────────────────────────────────────────────────

ProgressCallback = Callable[[str, int, int], None]
"""Signature: (status_message, current_item, total_items)"""


def extract_all(
    paks_dir: str,
    retoc_exe: str,
    uassetgui_exe: str,
    game_extract_dir: str,
    manifest: list[dict[str, Any]],
    progress: ProgressCallback | None = None,
) -> dict[str, str]:
    """Extract all manifest entries, convert to JSON.

    Outputs:
        - retoc .uasset/.uexp → ``game_extract_dir/retoc/{game_path}.*``
        - UAssetGUI .json     → ``game_extract_dir/uassetgui/{game_path}.json``

    Args:
        paks_dir: Path to game's Moria/Content/Paks/ directory.
        retoc_exe: Path to retoc.exe.
        uassetgui_exe: Path to UAssetGUI.exe.
        game_extract_dir: data/game_extract/ directory.
        manifest: Parsed extraction targets from load_manifest().
        progress: Optional callback for progress updates.

    Returns:
        Dict mapping entry name to output JSON path.
    """
    results: dict[str, str] = {}
    total = len(manifest)

    retoc_dir = os.path.join(game_extract_dir, "retoc")
    uassetgui_dir = os.path.join(game_extract_dir, "uassetgui")

    for i, entry in enumerate(manifest):
        name = entry["name"]
        stem = entry["stem"]
        game_path = entry["game_path"]
        ue_version = entry["ue_version"]          # for UAssetGUI
        retoc_version = entry["retoc_version"]    # for retoc

        if progress:
            progress(f"Extracting {stem}...", i, total)

        # 1. retoc extraction → game_extract/retoc/
        os.makedirs(retoc_dir, exist_ok=True)
        try:
            extract_uasset(stem, paks_dir, retoc_exe, retoc_dir, retoc_version)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            log.error("retoc failed for %s: %s", stem, exc)
            continue

        # 2. Find the extracted .uasset
        uasset_path = os.path.join(retoc_dir, f"{game_path}.uasset")
        if not os.path.isfile(uasset_path):
            found = None
            for root, _dirs, files in os.walk(retoc_dir):
                for f in files:
                    if f == f"{stem}.uasset":
                        found = os.path.join(root, f)
                        break
                if found:
                    break
            if not found:
                log.error("Could not find %s.uasset in retoc output", stem)
                continue
            uasset_path = found

        # 3. Convert to JSON → game_extract/uassetgui/
        json_output = os.path.join(uassetgui_dir, f"{game_path}.json")
        if progress:
            progress(f"Converting {stem} to JSON...", i, total)

        try:
            convert_to_json(uasset_path, json_output, uassetgui_exe, ue_version)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            log.error("UAssetGUI failed for %s: %s", stem, exc)
            continue

        if not os.path.isfile(json_output):
            log.error("JSON output not created for %s", stem)
            continue

        results[name] = json_output
        log.info("Extracted: %s -> %s", stem, json_output)

    if progress:
        progress("Extraction complete.", total, total)

    return results


# ── Validation ──────────────────────────────────────────────────────

def validate_extraction(
    game_extract_dir: str,
    manifest: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return manifest entries whose JSON output is missing."""
    uassetgui_dir = os.path.join(game_extract_dir, "uassetgui")
    missing: list[dict[str, Any]] = []
    for entry in manifest:
        json_path = os.path.join(uassetgui_dir, f"{entry['game_path']}.json")
        if not os.path.isfile(json_path):
            missing.append(entry)
    return missing
