"""
Shared configuration loader for RtoM-ArmorBuildings-Mod.

Reads config.ini from the project root and exposes resolved paths to all
modules.  Every path returned is absolute so scripts work regardless of
the current working directory.

Usage::

    from src.config import cfg

    cfg.project_root                    # absolute path to the repo root
    cfg.ue4_root                        # absolute path to the UE4.27 install
    cfg.localization["target_lang"]     # e.g. "de"
    cfg.path("Localization", "en")      # resolved absolute path
    cfg.ue4_path("Engine", "Binaries")  # resolved absolute path
"""

import configparser
import logging
import os
import sys

log = logging.getLogger(__name__)


def _resolve_app_root() -> str:
    """Return the application root directory.

    When running as a PyInstaller frozen exe the root is the directory
    containing the .exe, NOT the temp extraction folder.  When running
    from source the root is one level up from this file (src/ -> root).
    """
    if getattr(sys, "frozen", False):
        # PyInstaller: sys.executable is the .exe path
        return os.path.dirname(sys.executable)
    # Running from source
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


_APP_ROOT = _resolve_app_root()
_DEFAULT_INI = os.path.join(_APP_ROOT, "config.ini")


class Config:
    """Thin wrapper around config.ini that resolves paths."""

    def __init__(self, ini_path: str | None = None):
        """Load and parse config.ini.

        Args:
            ini_path: Override path to config.ini.  Defaults to
                      ``<app_root>/config.ini``.
        """
        if ini_path is None:
            ini_path = _DEFAULT_INI

        self.app_root: str = _APP_ROOT
        self.ini_path: str = ini_path

        log.debug("App root   : %s", self.app_root)
        log.debug("Frozen exe : %s", getattr(sys, "frozen", False))
        log.debug("INI path   : %s", ini_path)

        if not os.path.isfile(ini_path):
            print(
                f"[config] ERROR: config.ini not found at {ini_path}\n"
                "  Copy config.ini.example -> config.ini and set your paths.",
                file=sys.stderr,
            )
            input("Press Enter to exit...")
            sys.exit(1)

        parser = configparser.ConfigParser()
        parser.read(ini_path, encoding="utf-8")

        # ── [General] section (optional) ──
        self.debug: bool = parser.getboolean("General", "Debug", fallback=False)

        # ── [Paths] section ──
        self.project_root: str = os.path.normpath(
            parser.get("Paths", "ProjectRoot")
        )
        self.ue4_root: str = os.path.normpath(
            parser.get("Paths", "UE4Root")
        )

        # ── [Localization] section ──
        self.localization: dict[str, str] = {
            "source_po": parser.get("Localization", "SourcePO"),
            "target_lang": parser.get("Localization", "TargetLang"),
            "pak_filename": parser.get("Localization", "PakFileName"),
        }

        # ── [ModTool] section (optional) ──
        _data_raw = parser.get("ModTool", "DataDir", fallback="data")
        _saves_raw = parser.get("ModTool", "SavesDir", fallback="Saves")
        self.modtool_data_dir: str = os.path.normpath(
            _data_raw if os.path.isabs(_data_raw)
            else os.path.join(self.app_root, _data_raw)
        )
        self.modtool_saves_dir: str = os.path.normpath(
            _saves_raw if os.path.isabs(_saves_raw)
            else os.path.join(self.app_root, _saves_raw)
        )

        log.debug("Debug      : %s", self.debug)
        log.debug("ProjectRoot: %s", self.project_root)
        log.debug("UE4Root    : %s", self.ue4_root)
        log.debug("DataDir    : %s", self.modtool_data_dir)
        log.debug("SavesDir   : %s", self.modtool_saves_dir)

    def path(self, *parts: str) -> str:
        """Join *parts* relative to ProjectRoot → absolute path."""
        return os.path.normpath(os.path.join(self.project_root, *parts))

    def ue4_path(self, *parts: str) -> str:
        """Join *parts* relative to UE4Root → absolute path."""
        return os.path.normpath(os.path.join(self.ue4_root, *parts))


# Module-level singleton — import ``cfg`` from here.
cfg = Config()
