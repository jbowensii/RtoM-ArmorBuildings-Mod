"""
main.py — Application entry point for RtoM Mod Tools.

Currently provides a CLI menu for the three pipelines.  This will be
replaced with a GUI (customtkinter) in a future release.
"""

from __future__ import annotations

from src import APP_NAME, APP_VERSION
from src.localization.csv_to_po import run as csv_to_po_run
from src.localization.po_to_csv import run as po_to_csv_run
from src.packaging.pak_locres import run as pak_locres_run
from src.recipes.colour_variants import run as colour_variants_run
from src.sync import sync_check, sync_export, sync_import


def print_banner() -> None:
    """Print the application header."""
    divider = "=" * 50
    print(f"\n{divider}")
    print(f"  {APP_NAME} v{APP_VERSION}")
    print("  Return to Moria — Armor & Buildings Mod Tools")
    print(f"{divider}\n")


def print_menu() -> None:
    """Print the main menu."""
    print("  Localization")
    print("    1. Export PO → CSV (for translators)")
    print("    2. Import CSV → PO (merge translations)")
    print("    3. Build localization pak")
    print()
    print("  Recipes")
    print("    4. Patch colour-variant recipes")
    print()
    print("  Sync")
    print("    5. Export repo → staging")
    print("    6. Import staging → repo")
    print("    7. Check repo vs staging")
    print()
    print("    0. Exit")
    print()


def main() -> None:
    """Run the CLI menu loop."""
    print_banner()

    while True:
        print_menu()
        choice = input("  Select option: ").strip()

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
    main()
