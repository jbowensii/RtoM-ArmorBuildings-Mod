"""Simple JSON load/save utilities with logging."""

from __future__ import annotations

import json
import logging

log = logging.getLogger(__name__)


def load_json(path: str) -> dict:
    """Load and return a JSON file."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        log.debug("Loaded: %s", path)
        return data
    except Exception as e:
        log.error("Error loading %s: %s", path, e)
        return {}


def save_json(path: str, data: dict) -> None:
    """Write *data* to a JSON file."""
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        log.debug("Saved: %s", path)
    except Exception as e:
        log.error("Error saving %s: %s", path, e)
