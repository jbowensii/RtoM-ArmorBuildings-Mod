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

    from PySide6.QtWidgets import QApplication
    from src.gui.main_window import MainWindow

    log.debug("All modules imported successfully")

    app = QApplication(sys.argv)
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
