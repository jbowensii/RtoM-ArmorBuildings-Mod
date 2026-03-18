"""
config_loader.py — Shared configuration loader for RtoM-ArmorBuildings-Mod.

Reads config.ini from the project root and exposes resolved paths to all
scripts.  Every path returned is absolute so scripts work regardless of
the current working directory.

Usage:
    from config_loader import cfg

    cfg.project_root   # absolute path to the repository root
    cfg.ue4_root       # absolute path to the UE4.27 install
    cfg.localization   # dict with source_po, target_lang, pak_filename
    cfg.path(...)      # resolve a project-relative path
"""

import configparser
import os
import sys


class Config:
    """Thin wrapper around config.ini that resolves paths."""

    def __init__(self, ini_path: str | None = None):
        # ── Locate config.ini next to this file (project root) ──
        if ini_path is None:
            ini_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "config.ini"
            )

        if not os.path.isfile(ini_path):
            print(
                f"[config_loader] ERROR: config.ini not found at {ini_path}\n"
                "  Copy config.ini.example or create config.ini with your paths.",
                file=sys.stderr,
            )
            sys.exit(1)

        parser = configparser.ConfigParser()
        parser.read(ini_path, encoding="utf-8")

        # ── [Paths] ──
        self.project_root = os.path.normpath(parser.get("Paths", "ProjectRoot"))
        self.ue4_root = os.path.normpath(parser.get("Paths", "UE4Root"))

        # ── [Localization] ──
        self.localization = {
            "source_po": parser.get("Localization", "SourcePO"),
            "target_lang": parser.get("Localization", "TargetLang"),
            "pak_filename": parser.get("Localization", "PakFileName"),
        }

    # ── Convenience helpers ──

    def path(self, *parts: str) -> str:
        """Join parts relative to ProjectRoot and return an absolute path."""
        return os.path.normpath(os.path.join(self.project_root, *parts))

    def ue4_path(self, *parts: str) -> str:
        """Join parts relative to UE4Root and return an absolute path."""
        return os.path.normpath(os.path.join(self.ue4_root, *parts))


# Module-level singleton — import this from other scripts.
cfg = Config()
