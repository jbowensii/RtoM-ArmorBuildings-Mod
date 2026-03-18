"""
main.py — Application entry point for RtoM Mod Tools.

Currently provides a CLI menu for the three pipelines.  This will be
replaced with a GUI (customtkinter) in a future release.
"""

from __future__ import annotations

import logging
import os
import sys
import traceback

log = logging.getLogger(__name__)


def setup_logging(debug: bool, app_root: str) -> None:
    """Configure logging.  When *debug* is True, log DEBUG to both
    the console and a ``debug.log`` file next to the executable."""
    level = logging.DEBUG if debug else logging.WARNING
    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]

    if debug:
        log_path = os.path.join(app_root, "debug.log")
        handlers.append(logging.FileHandler(log_path, encoding="utf-8"))

    logging.basicConfig(level=level, format=fmt, handlers=handlers)


def print_banner() -> None:
    """Print the application header."""
    from src import APP_NAME, APP_VERSION

    divider = "=" * 50
    print(f"\n{divider}")
    print(f"  {APP_NAME} v{APP_VERSION}")
    print("  Return to Moria — Armor & Buildings Mod Tools")
    print(f"{divider}\n")


def print_menu() -> None:
    """Print the main menu."""
    print("  Localization")
    print("    1. Export PO -> CSV (for translators)")
    print("    2. Import CSV -> PO (merge translations)")
    print("    3. Build localization pak")
    print()
    print("  Recipes")
    print("    4. Patch colour-variant recipes")
    print()
    print("  Sync")
    print("    5. Export repo -> staging")
    print("    6. Import staging -> repo")
    print("    7. Check repo vs staging")
    print()
    print("    0. Exit")
    print()


def main() -> None:
    """Run the CLI menu loop."""
    # ── Bootstrap: load config first so we know debug state ──
    from src.config import cfg

    setup_logging(cfg.debug, cfg.app_root)
    log.debug("Application starting")
    log.debug("sys.executable: %s", sys.executable)
    log.debug("sys.argv      : %s", sys.argv)
    log.debug("cwd           : %s", os.getcwd())

    # Lazy-import pipeline modules after logging is configured
    from src.localization.csv_to_po import run as csv_to_po_run
    from src.localization.po_to_csv import run as po_to_csv_run
    from src.packaging.pak_locres import run as pak_locres_run
    from src.recipes.colour_variants import run as colour_variants_run
    from src.sync import sync_check, sync_export, sync_import

    log.debug("All modules imported successfully")

    print_banner()

    while True:
        print_menu()
        choice = input("  Select option: ").strip()
        log.debug("User selected: %r", choice)

        if choice == "0":
            print("  Goodbye.")
            break

        if choice == "1":
            po_to_csv_run()
        elif choice == "2":
            csv_to_po_run()
        elif choice == "3":
            pak_locres_run()
        elif choice == "4":
            colour_variants_run()
        elif choice == "5":
            sync_export()
        elif choice == "6":
            sync_import()
        elif choice == "7":
            sync_check()
        else:
            print("  Invalid option. Try again.\n")
            continue

        print()  # breathing room after operation output


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        print("\n[ERROR] An unexpected error occurred. See above for details.")
        input("Press Enter to exit...")
        sys.exit(1)
