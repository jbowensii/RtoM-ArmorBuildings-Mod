"""
build_release.py — Orchestrates the full build pipeline.

Steps:
    1. Read version from src/__init__.py
    2. Run sync export -> build/staging/
    3. Build exe with PyInstaller
    4. Copy exe to release/
    5. Compile Inno Setup installer (optional)

Usage:
    python build/build_release.py
    python build/build_release.py --no-installer
    python build/build_release.py --skip-sync
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys

# -- Resolve project root (one level up from this script) --
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

# Add project root to path so we can import src/
sys.path.insert(0, PROJECT_ROOT)


def get_version() -> str:
    """Read APP_VERSION from src/__init__.py."""
    init_path = os.path.join(PROJECT_ROOT, "src", "__init__.py")
    with open(init_path, encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("APP_VERSION"):
                # APP_VERSION = "1.1.0"
                return line.split('"')[1]
    raise RuntimeError("APP_VERSION not found in src/__init__.py")


def run_cmd(cmd: list[str], description: str) -> None:
    """Run a command, printing status and raising on failure."""
    print(f"\n{'-' * 60}")
    print(f"  {description}")
    print(f"  -> {' '.join(cmd)}")
    print(f"{'-' * 60}")

    result = subprocess.run(cmd, cwd=PROJECT_ROOT, check=False)
    if result.returncode != 0:
        print(f"\n  FAILED: {description} (exit code {result.returncode})")
        sys.exit(result.returncode)


def step_sync() -> None:
    """Step 1: Export localization files to build/staging/."""
    import shutil  # pylint: disable=import-outside-toplevel
    staging = os.path.join(PROJECT_ROOT, "build", "staging")
    # Copy localization files to staging
    loc_src = os.path.join(PROJECT_ROOT, "Localization")
    loc_dst = os.path.join(staging, "localization")
    if os.path.isdir(loc_src):
        if os.path.isdir(loc_dst):
            shutil.rmtree(loc_dst)
        shutil.copytree(loc_src, loc_dst, dirs_exist_ok=True)
    print(f"EXPORT: localization -> {loc_dst}")


def step_pyinstaller() -> None:
    """Step 2: Build the exe with PyInstaller."""
    spec = os.path.join(SCRIPT_DIR, "RtoMModTools.spec")
    run_cmd(
        [sys.executable, "-m", "PyInstaller", spec, "--noconfirm",
         "--distpath", os.path.join(PROJECT_ROOT, "dist"),
         "--workpath", os.path.join(PROJECT_ROOT, "build", "pyinstaller")],
        "Building executable with PyInstaller",
    )


def step_copy_to_release() -> None:
    """Step 3: Copy exe to release/."""
    release_dir = os.path.join(PROJECT_ROOT, "release")
    os.makedirs(release_dir, exist_ok=True)

    src_exe = os.path.join(PROJECT_ROOT, "dist", "RtoMModTools.exe")
    dst_exe = os.path.join(release_dir, "RtoMModTools.exe")

    if not os.path.isfile(src_exe):
        print(f"  ERROR: exe not found at {src_exe}")
        sys.exit(1)

    shutil.copy2(src_exe, dst_exe)
    size_mb = os.path.getsize(dst_exe) / (1024 * 1024)
    print(f"  Copied -> {dst_exe} ({size_mb:.1f} MB)")


def step_inno_setup(version: str) -> None:
    """Step 4: Compile the Inno Setup installer."""
    iss_path = os.path.join(SCRIPT_DIR, "installer", "RtoMModTools.iss")

    # Try common Inno Setup install locations
    iscc_candidates = [
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"),
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
    ]

    iscc = None
    for candidate in iscc_candidates:
        if os.path.isfile(candidate):
            iscc = candidate
            break

    if iscc is None:
        print("  WARNING: Inno Setup (ISCC.exe) not found.")
        print("  Install from: https://jrsoftware.org/isdl.php")
        print("  Skipping installer build.")
        return

    # Pass version as a define so the .iss picks it up
    run_cmd(
        [iscc, f"/DMyAppVersion={version}", iss_path],
        f"Building installer v{version} with Inno Setup",
    )

    installer = os.path.join(
        PROJECT_ROOT, "release", f"RtoMModTools_Setup_v{version}.exe",
    )
    if os.path.isfile(installer):
        size_mb = os.path.getsize(installer) / (1024 * 1024)
        print(f"\n  SUCCESS: {installer} ({size_mb:.1f} MB)")


def main() -> None:
    """Run the full build pipeline."""
    parser = argparse.ArgumentParser(description="Build RtoM Mod Tools release.")
    parser.add_argument("--no-installer", action="store_true",
                        help="Skip Inno Setup installer build")
    parser.add_argument("--skip-sync", action="store_true",
                        help="Skip sync export (use existing staging)")
    args = parser.parse_args()

    version = get_version()

    print(f"\n{'=' * 60}")
    print(f"  RtoM Mod Tools — Build Pipeline v{version}")
    print(f"{'=' * 60}")

    # Step 1: Sync
    if not args.skip_sync:
        print("\n[1/4] Syncing repo -> staging...")
        step_sync()
    else:
        print("\n[1/4] Skipping sync (--skip-sync)")

    # Step 2: PyInstaller
    print("\n[2/4] Building executable...")
    step_pyinstaller()

    # Step 3: Copy to release
    print("\n[3/4] Copying to release/...")
    step_copy_to_release()

    # Step 4: Inno Setup
    if not args.no_installer:
        print("\n[4/4] Building installer...")
        step_inno_setup(version)
    else:
        print("\n[4/4] Skipping installer (--no-installer)")

    divider = "=" * 60
    print(f"\n{divider}")
    print("  Build complete.")
    print(f"{divider}\n")


if __name__ == "__main__":
    main()
