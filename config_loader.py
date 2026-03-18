"""
Backward-compatible shim — imports from the new package location.

New code should use::

    from src.config import cfg

This file exists so that the old Localization/ and modified-json/
scripts (which are kept as thin CLI wrappers) can still
``from config_loader import cfg`` without breaking.
"""

from src.config import cfg  # noqa: F401 — re-export for legacy scripts

__all__ = ["cfg"]
