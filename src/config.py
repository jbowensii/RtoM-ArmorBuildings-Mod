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
import os
import sys

# Project root is one level up from this file (src/ lives inside root)
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DEFAULT_INI = os.path.join(_PROJECT_ROOT, "config.ini")


class Config:
    """Thin wrapper around config.ini that resolves paths."""

    def __init__(self, ini_path: str | None = None):
        """Load and parse config.ini.

        Args:
            ini_path: Override path to config.ini.  Defaults to
                      ``<project_root>/config.ini``.
        """
        if ini_path is None:
            ini_path = _DEFAULT_INI

        if not os.path.isfile(ini_path):
            print(
                f"[config] ERROR: config.ini not found at {ini_path}\n"
                "  Copy config.ini.example -> config.ini and set your paths.",
                file=sys.stderr,
            )
            sys.exit(1)

        parser = configparser.ConfigParser()
        parser.read(ini_path, encoding="utf-8")

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

    def path(self, *parts: str) -> str:
        """Join *parts* relative to ProjectRoot → absolute path."""
        return os.path.normpath(os.path.join(self.project_root, *parts))

    def ue4_path(self, *parts: str) -> str:
        """Join *parts* relative to UE4Root → absolute path."""
        return os.path.normpath(os.path.join(self.ue4_root, *parts))


# Module-level singleton — import ``cfg`` from here.
cfg = Config()
