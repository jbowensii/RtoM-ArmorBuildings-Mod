"""Simple JSON load/save utilities with logging."""

from __future__ import annotations

import json
import logging

log = logging.getLogger(__name__)


def load_json(path: str) -> dict:
    """Load and return a JSON file.  Returns ``{}`` on any I/O or parse error."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        log.debug("Loaded: %s", path)
        return data
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        log.error("Error loading %s: %s", path, exc)
        return {}


def save_json(path: str, data: dict) -> None:
    """Write *data* to a JSON file with pretty-print formatting."""
    try:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=4, ensure_ascii=False)
        log.debug("Saved: %s", path)
    except (OSError, TypeError, ValueError) as exc:
        log.error("Error saving %s: %s", path, exc)
