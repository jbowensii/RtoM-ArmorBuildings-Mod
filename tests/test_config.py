"""Tests for src.config — Config path resolution and INI loading."""

import configparser
import json
import os

import pytest


class TestConfigPathResolution:
    """Tests for Config path resolution with a tmp config.ini."""

    @staticmethod
    def _write_ini(tmp_path, extra_sections=None):
        """Write a minimal config.ini and return the path."""
        ini_path = tmp_path / "config.ini"
        parser = configparser.ConfigParser()
        parser["Paths"] = {
            "ProjectRoot": str(tmp_path / "project"),
            "UE4Root": str(tmp_path / "ue4"),
        }
        parser["Localization"] = {
            "SourcePO": "Game.po",
            "TargetLang": "de",
            "PakFileName": "ModLocalization",
        }
        if extra_sections:
            for section, values in extra_sections.items():
                parser[section] = values
        with open(ini_path, "w", encoding="utf-8") as fh:
            parser.write(fh)
        return str(ini_path)

    def test_loads_paths_from_ini(self, tmp_path, monkeypatch):
        """Config should read ProjectRoot and UE4Root from the INI file."""
        # Patch _APP_ROOT so that relative data_dir resolves under tmp_path
        import src.config as cfg_mod
        monkeypatch.setattr(cfg_mod, "_APP_ROOT", str(tmp_path))

        ini_path = self._write_ini(tmp_path)
        config = cfg_mod.Config(ini_path)

        assert config.project_root == os.path.normpath(str(tmp_path / "project"))
        assert config.ue4_root == os.path.normpath(str(tmp_path / "ue4"))

    def test_path_joins_relative_to_project_root(self, tmp_path, monkeypatch):
        """Config.path() should join parts relative to ProjectRoot."""
        import src.config as cfg_mod
        monkeypatch.setattr(cfg_mod, "_APP_ROOT", str(tmp_path))

        ini_path = self._write_ini(tmp_path)
        config = cfg_mod.Config(ini_path)

        result = config.path("Localization", "en")
        expected = os.path.normpath(
            os.path.join(str(tmp_path / "project"), "Localization", "en")
        )
        assert result == expected

    def test_ue4_path_joins_relative_to_ue4_root(self, tmp_path, monkeypatch):
        """Config.ue4_path() should join parts relative to UE4Root."""
        import src.config as cfg_mod
        monkeypatch.setattr(cfg_mod, "_APP_ROOT", str(tmp_path))

        ini_path = self._write_ini(tmp_path)
        config = cfg_mod.Config(ini_path)

        result = config.ue4_path("Engine", "Binaries")
        expected = os.path.normpath(
            os.path.join(str(tmp_path / "ue4"), "Engine", "Binaries")
        )
        assert result == expected

    def test_data_dir_defaults_relative_to_app_root(self, tmp_path, monkeypatch):
        """Without explicit DataDir, data_dir should be app_root/data."""
        import src.config as cfg_mod
        monkeypatch.setattr(cfg_mod, "_APP_ROOT", str(tmp_path))

        ini_path = self._write_ini(tmp_path)
        config = cfg_mod.Config(ini_path)

        expected = os.path.normpath(os.path.join(str(tmp_path), "data"))
        assert config.data_dir == expected

    def test_data_dir_absolute_override(self, tmp_path, monkeypatch):
        """An absolute DataDir should be used as-is."""
        import src.config as cfg_mod
        monkeypatch.setattr(cfg_mod, "_APP_ROOT", str(tmp_path))

        abs_data = str(tmp_path / "custom_data")
        ini_path = self._write_ini(tmp_path, extra_sections={
            "ModTool": {"DataDir": abs_data},
        })
        config = cfg_mod.Config(ini_path)

        assert config.data_dir == os.path.normpath(abs_data)

    def test_data_dir_relative_override(self, tmp_path, monkeypatch):
        """A relative DataDir should resolve against app_root."""
        import src.config as cfg_mod
        monkeypatch.setattr(cfg_mod, "_APP_ROOT", str(tmp_path))

        ini_path = self._write_ini(tmp_path, extra_sections={
            "ModTool": {"DataDir": "my_data"},
        })
        config = cfg_mod.Config(ini_path)

        expected = os.path.normpath(os.path.join(str(tmp_path), "my_data"))
        assert config.data_dir == expected

    def test_derived_dirs_under_data_dir(self, tmp_path, monkeypatch):
        """templates_dir, game_extract_dir, tobis_json_dir should be under data_dir."""
        import src.config as cfg_mod
        monkeypatch.setattr(cfg_mod, "_APP_ROOT", str(tmp_path))

        ini_path = self._write_ini(tmp_path)
        config = cfg_mod.Config(ini_path)

        assert config.templates_dir == os.path.join(config.data_dir, "templates")
        assert config.game_extract_dir == os.path.join(config.data_dir, "game_extract")
        assert config.tobis_json_dir == os.path.join(config.data_dir, "Tobis_json")

    def test_tobis_mod_dir_under_app_root(self, tmp_path, monkeypatch):
        """tobis_mod_dir should be under app_root."""
        import src.config as cfg_mod
        monkeypatch.setattr(cfg_mod, "_APP_ROOT", str(tmp_path))

        ini_path = self._write_ini(tmp_path)
        config = cfg_mod.Config(ini_path)

        assert config.tobis_mod_dir == os.path.join(str(tmp_path), "TobisMod")

    def test_localization_section(self, tmp_path, monkeypatch):
        """Localization config values should be accessible."""
        import src.config as cfg_mod
        monkeypatch.setattr(cfg_mod, "_APP_ROOT", str(tmp_path))

        ini_path = self._write_ini(tmp_path)
        config = cfg_mod.Config(ini_path)

        assert config.localization["source_po"] == "Game.po"
        assert config.localization["target_lang"] == "de"
        assert config.localization["pak_filename"] == "ModLocalization"

    def test_missing_ini_exits(self, tmp_path, monkeypatch):
        """Config should exit when config.ini is missing."""
        import src.config as cfg_mod
        monkeypatch.setattr(cfg_mod, "_APP_ROOT", str(tmp_path))
        # Prevent actual sys.exit from killing the test runner
        monkeypatch.setattr("builtins.input", lambda _: None)

        with pytest.raises(SystemExit):
            cfg_mod.Config(str(tmp_path / "nonexistent.ini"))

    def test_set_game_path(self, tmp_path, monkeypatch):
        """set_game_path should write back to the INI and update attributes."""
        import src.config as cfg_mod
        monkeypatch.setattr(cfg_mod, "_APP_ROOT", str(tmp_path))

        ini_path = self._write_ini(tmp_path)
        config = cfg_mod.Config(ini_path)

        game_path = str(tmp_path / "GameInstall")
        config.set_game_path(game_path, "Steam")

        assert config.game_install_path == game_path
        assert config.game_install_type == "Steam"
        assert config.game_paks_dir == os.path.join(
            game_path, "Moria", "Content", "Paks"
        )

        # Verify it was written to the INI file
        parser = configparser.ConfigParser()
        parser.read(ini_path, encoding="utf-8")
        assert parser.get("Game", "InstallPath") == game_path
        assert parser.get("Game", "InstallType") == "Steam"

    def test_debug_defaults_to_false(self, tmp_path, monkeypatch):
        """Debug should default to False when not specified."""
        import src.config as cfg_mod
        monkeypatch.setattr(cfg_mod, "_APP_ROOT", str(tmp_path))

        ini_path = self._write_ini(tmp_path)
        config = cfg_mod.Config(ini_path)

        assert config.debug is False

    def test_debug_flag(self, tmp_path, monkeypatch):
        """Debug=true in [General] should be read correctly."""
        import src.config as cfg_mod
        monkeypatch.setattr(cfg_mod, "_APP_ROOT", str(tmp_path))

        ini_path = self._write_ini(tmp_path, extra_sections={
            "General": {"Debug": "true"},
        })
        config = cfg_mod.Config(ini_path)

        assert config.debug is True
