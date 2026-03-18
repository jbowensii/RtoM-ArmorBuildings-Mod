"""
sync.py — Synchronise files between the repo layout and the install layout.

The mod repository organises assets for developer convenience (UAssetGUI
editing, git history).  The installed application needs them in a
different tree under ``%LOCALAPPDATA%\\RtoMModTools\\``.  This module
defines the canonical mapping between the two and provides three
operations:

  **export**  repo → install/staging dir  (for builds and local testing)
  **import**  install dir → repo          (after UAssetGUI edits)
  **check**   diff the two trees, report what changed

The mapping table lives in :data:`SYNC_MAP` — every other part of the
build system (installer, tests, docs) should reference it rather than
hardcoding paths.

Usage::

    # CLI
    python -m src.sync export                 # repo → default staging
    python -m src.sync export --target D:/out # repo → custom dir
    python -m src.sync import --source D:/out # custom dir → repo
    python -m src.sync check                  # diff report

    # As a library (called by build_release.py)
    from src.sync import sync_export
    sync_export(target_root="build/staging")
"""

from __future__ import annotations

import argparse
import filecmp
import os
import shutil
from dataclasses import dataclass

from src.config import cfg


# ─────────────────────────────────────────────────────────────────────
# Mapping table — single source of truth for repo ↔ install layout
# ─────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class SyncEntry:
    """One mapping between a repo path and an install path.

    Both paths are relative:
      - ``repo`` is relative to ``cfg.project_root``
      - ``install`` is relative to the install/staging root

    If ``is_dir`` is True the entire directory tree is synced.
    """
    repo: str
    install: str
    is_dir: bool = True
    description: str = ""


SYNC_MAP: list[SyncEntry] = [
    # ── Core mod data (modified-json/Moria → data/Moria) ──
    SyncEntry(
        repo="modified-json/Moria/Config",
        install="data/Moria/Config",
        description="Gameplay tag definitions",
    ),
    SyncEntry(
        repo="modified-json/Moria/Content/Character",
        install="data/Moria/Content/Character",
        description="Loot tables",
    ),
    SyncEntry(
        repo="modified-json/Moria/Content/Items",
        install="data/Moria/Content/Items",
        description="Item effects",
    ),
    SyncEntry(
        repo="modified-json/Moria/Content/LevelDesign",
        install="data/Moria/Content/LevelDesign",
        description="Crafting station blueprints",
    ),
    SyncEntry(
        repo="modified-json/Moria/Content/Mods",
        install="data/Moria/Content/Mods",
        description="28 building/construction packs (147 MB)",
    ),
    SyncEntry(
        repo="modified-json/Moria/Content/Tech",
        install="data/Moria/Content/Tech",
        description="Master DataTables — recipes, constructions, economy (106 MB)",
    ),

    # ── Construction DataTables ──
    SyncEntry(
        repo="ConstructiondDT",
        install="data/ConstructiondDT",
        description="Construction definitions (DT_Const, DT_ConstRecipe)",
    ),

    # ── More Buildings plugin ──
    SyncEntry(
        repo="RtoMMoreBuildings_P/Moria/Content/Tech/Data/Items",
        install="data/RtoMMoreBuildings_P",
        description="More Buildings recipe table (DT_ItemRecipes)",
    ),

    # ── Templates ──
    SyncEntry(
        repo="modified-json/UnlockRequiredItems.json",
        install="data/templates/UnlockRequiredItems.json",
        is_dir=False,
        description="Recipe dependency template for colour variants",
    ),

    # ── Localization ──
    SyncEntry(
        repo="Localization/en",
        install="localization/en",
        description="English PO source strings",
    ),
    SyncEntry(
        repo="Localization/de",
        install="localization/de",
        description="German translations",
    ),
    SyncEntry(
        repo="Localization/es",
        install="localization/es",
        description="Spanish translations",
    ),
    SyncEntry(
        repo="Localization/fr",
        install="localization/fr",
        description="French translations",
    ),
    SyncEntry(
        repo="Localization/ModLocalization",
        install="localization/ModLocalization",
        description="Packaged .locres output",
    ),

    # ── Docs ──
    SyncEntry(
        repo="docs/knowledge-base.html",
        install="docs/knowledge-base.html",
        is_dir=False,
        description="Knowledge base documentation",
    ),
    SyncEntry(
        repo="docs/style.css",
        install="docs/style.css",
        is_dir=False,
        description="Documentation stylesheet",
    ),

    # ── Config template ──
    SyncEntry(
        repo="config.ini.example",
        install="config.ini.example",
        is_dir=False,
        description="Configuration template for new installs",
    ),

    # ── License ──
    SyncEntry(
        repo="LICENSE",
        install="LICENSE",
        is_dir=False,
        description="MIT license",
    ),
]


# ─────────────────────────────────────────────────────────────────────
# Core operations
# ─────────────────────────────────────────────────────────────────────

def _resolve(base: str, rel: str) -> str:
    """Join and normalise a base + relative path."""
    return os.path.normpath(os.path.join(base, rel))


def _copy_entry(src_root: str, dst_root: str, entry: SyncEntry) -> int:
    """Copy one SyncEntry from src to dst.  Returns file count copied."""
    src = _resolve(src_root, entry.repo if src_root == cfg.project_root else entry.install)
    dst = _resolve(dst_root, entry.install if dst_root != cfg.project_root else entry.repo)

    if not os.path.exists(src):
        print(f"  SKIP  {entry.description} — source not found: {src}")
        return 0

    if entry.is_dir:
        if os.path.exists(dst):
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
        count = sum(len(files) for _, _, files in os.walk(dst))
    else:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        count = 1

    print(f"  OK    {entry.description} ({count} files)")
    return count


def sync_export(target_root: str | None = None) -> int:
    """Copy repo → install/staging directory.

    Args:
        target_root: Destination root.  Defaults to ``build/staging/``
                     inside the project.

    Returns:
        Total number of files copied.
    """
    if target_root is None:
        target_root = cfg.path("build", "staging")

    print(f"EXPORT: repo → {target_root}")
    os.makedirs(target_root, exist_ok=True)

    total = 0
    for entry in SYNC_MAP:
        src = _resolve(cfg.project_root, entry.repo)
        dst = _resolve(target_root, entry.install)

        if not os.path.exists(src):
            print(f"  SKIP  {entry.description} — not found: {src}")
            continue

        if entry.is_dir:
            if os.path.exists(dst):
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
            count = sum(len(files) for _, _, files in os.walk(dst))
        else:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
            count = 1

        print(f"  OK    {entry.description} ({count} files)")
        total += count

    print(f"\nExported {total} files.")
    return total


def sync_import(source_root: str | None = None) -> int:
    """Copy install/staging directory → repo.

    Args:
        source_root: Source root.  Defaults to ``build/staging/``.

    Returns:
        Total number of files copied.
    """
    if source_root is None:
        source_root = cfg.path("build", "staging")

    print(f"IMPORT: {source_root} → repo")

    total = 0
    for entry in SYNC_MAP:
        src = _resolve(source_root, entry.install)
        dst = _resolve(cfg.project_root, entry.repo)

        if not os.path.exists(src):
            print(f"  SKIP  {entry.description} — not found: {src}")
            continue

        if entry.is_dir:
            if os.path.exists(dst):
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
            count = sum(len(files) for _, _, files in os.walk(dst))
        else:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
            count = 1

        print(f"  OK    {entry.description} ({count} files)")
        total += count

    print(f"\nImported {total} files.")
    return total


def _compare_dirs(path_a: str, path_b: str) -> tuple[str, str]:
    """Compare two directories and return (category, detail_string).

    ``category`` is ``"modified"`` or ``"unchanged"``.
    ``detail_string`` is empty for unchanged, or a human-readable summary.
    """
    diff = filecmp.dircmp(path_a, path_b)
    if not (diff.diff_files or diff.left_only or diff.right_only):
        return "unchanged", ""

    parts = []
    if diff.diff_files:
        parts.append(f"{len(diff.diff_files)} modified")
    if diff.left_only:
        parts.append(f"{len(diff.left_only)} repo-only")
    if diff.right_only:
        parts.append(f"{len(diff.right_only)} staging-only")
    return "modified", ", ".join(parts)


def sync_check(target_root: str | None = None) -> dict[str, list[str]]:
    """Compare repo vs install/staging and report differences.

    Returns:
        Dict with keys ``added``, ``removed``, ``modified``, ``unchanged``.
    """
    if target_root is None:
        target_root = cfg.path("build", "staging")

    results: dict[str, list[str]] = {
        "added": [],
        "removed": [],
        "modified": [],
        "unchanged": [],
    }

    if not os.path.isdir(target_root):
        print(f"CHECK: staging dir does not exist: {target_root}")
        print("  Run 'sync export' first.")
        return results

    print(f"CHECK: repo vs {target_root}\n")

    for entry in SYNC_MAP:
        repo_path = _resolve(cfg.project_root, entry.repo)
        install_path = _resolve(target_root, entry.install)

        repo_exists = os.path.exists(repo_path)
        install_exists = os.path.exists(install_path)

        label = entry.repo

        if not repo_exists and not install_exists:
            continue  # neither side has this entry — skip silently

        if repo_exists and not install_exists:
            results["added"].append(label)
            print(f"  + ADDED     {label} (in repo, not in staging)")

        elif install_exists and not repo_exists:
            results["removed"].append(label)
            print(f"  - REMOVED   {label} (in staging, not in repo)")

        elif entry.is_dir:
            category, detail = _compare_dirs(repo_path, install_path)
            results[category].append(label)
            if detail:
                print(f"  ~ MODIFIED  {label} ({detail})")

        elif not filecmp.cmp(repo_path, install_path, shallow=False):
            results["modified"].append(label)
            print(f"  ~ MODIFIED  {label}")
        else:
            results["unchanged"].append(label)

    # Summary
    print(f"\n  Added: {len(results['added'])}  |  "
          f"Removed: {len(results['removed'])}  |  "
          f"Modified: {len(results['modified'])}  |  "
          f"Unchanged: {len(results['unchanged'])}")

    return results


# ─────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────

def main() -> None:
    """Command-line interface for sync operations."""
    parser = argparse.ArgumentParser(
        description="Sync files between repo and install layout.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # export
    p_export = sub.add_parser("export", help="Copy repo → staging/install dir")
    p_export.add_argument("--target", default=None, help="Target directory")

    # import
    p_import = sub.add_parser("import", help="Copy staging/install dir → repo")
    p_import.add_argument("--source", default=None, help="Source directory")

    # check
    p_check = sub.add_parser("check", help="Diff repo vs staging")
    p_check.add_argument("--target", default=None, help="Staging directory")

    args = parser.parse_args()

    if args.command == "export":
        sync_export(target_root=args.target)
    elif args.command == "import":
        sync_import(source_root=args.source)
    elif args.command == "check":
        sync_check(target_root=args.target)


if __name__ == "__main__":
    main()
