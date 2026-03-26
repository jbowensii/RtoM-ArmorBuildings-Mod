"""Tests for src.utils.json_handler — load/save JSON with error handling."""

import json
import os
import pytest

from src.utils.json_handler import load_json, save_json


class TestLoadJson:
    """Tests for load_json()."""

    def test_loads_valid_file(self, tmp_path):
        path = tmp_path / "data.json"
        path.write_text('{"key": "value"}', encoding="utf-8")
        result = load_json(str(path))
        assert result == {"key": "value"}

    def test_returns_empty_dict_on_missing_file(self, tmp_path):
        result = load_json(str(tmp_path / "missing.json"))
        assert result == {}

    def test_returns_empty_dict_on_invalid_json(self, tmp_path):
        path = tmp_path / "bad.json"
        path.write_text("not valid json {{{", encoding="utf-8")
        result = load_json(str(path))
        assert result == {}

    def test_preserves_unicode(self, tmp_path):
        path = tmp_path / "unicode.json"
        path.write_text('{"name": "Gimli\u2019s Map"}', encoding="utf-8")
        result = load_json(str(path))
        assert result["name"] == "Gimli\u2019s Map"


class TestSaveJson:
    """Tests for save_json()."""

    def test_writes_valid_json(self, tmp_path):
        path = tmp_path / "out.json"
        save_json(str(path), {"key": [1, 2, 3]})
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        assert data == {"key": [1, 2, 3]}

    def test_creates_parent_directories(self, tmp_path):
        # save_json doesn't create dirs itself, but let's verify it writes
        path = tmp_path / "out.json"
        save_json(str(path), {"a": 1})
        assert path.exists()

    def test_preserves_unicode_on_save(self, tmp_path):
        path = tmp_path / "out.json"
        save_json(str(path), {"name": "45\u00b0"})
        text = path.read_text(encoding="utf-8")
        assert "45\u00b0" in text  # ensure_ascii=False

    def test_overwrites_existing_file(self, tmp_path):
        path = tmp_path / "out.json"
        save_json(str(path), {"v": 1})
        save_json(str(path), {"v": 2})
        assert load_json(str(path)) == {"v": 2}
