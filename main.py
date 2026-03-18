"""
main.py — Application entry point for RtoM Mod Tools.

Launches the PySide6 GUI with tabbed interface combining the
Moding-Tool (construction/armor editors) and the ArmorBuildings-Mod
pipelines (localization, recipes, sync).
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


def main() -> None:
    """Launch the GUI application."""
    from src.config import cfg

    setup_logging(cfg.debug, cfg.app_root)
    log.debug("Application starting")
    log.debug("sys.executable: %s", sys.executable)
    log.debug("sys.argv      : %s", sys.argv)
    log.debug("cwd           : %s", os.getcwd())

    from PySide6.QtWidgets import QApplication, QDialog
    from src.gui.main_window import MainWindow

    log.debug("All modules imported successfully")

    app = QApplication(sys.argv)

    # ── First-run: game path selection ──
    if not cfg.game_install_path:
        from src.gui.game_path_dialog import GamePathDialog
        dlg = GamePathDialog(cfg)
        if dlg.exec() != QDialog.Accepted:
            sys.exit(0)

    # ── Check if game files need extraction ──
    from src.utils.game_extractor import load_manifest, validate_extraction
    manifest_path = os.path.join(cfg.data_dir, "extraction_manifest.ini")
    if os.path.isfile(manifest_path):
        manifest = load_manifest(manifest_path)
        missing = validate_extraction(cfg.game_extract_dir, manifest)
        if missing:
            from src.gui.extraction_dialog import ExtractionProgressDialog
            dlg = ExtractionProgressDialog(cfg, missing)
            if dlg.exec() != QDialog.Accepted:
                sys.exit(0)

    window = MainWindow(cfg)
    window.showMaximized()
    sys.exit(app.exec())


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        print("\n[ERROR] An unexpected error occurred. See above for details.")
        input("Press Enter to exit...")
        sys.exit(1)
