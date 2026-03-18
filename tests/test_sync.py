"""Tests for src.sync — repo ↔ install layout synchronisation."""

from __future__ import annotations

import json
import os

from src.sync import SYNC_MAP, SyncEntry, sync_check, sync_export, sync_import


class TestSyncMap:
    """Validate the SYNC_MAP configuration itself."""

    def test_all_entries_have_descriptions(self):
        for entry in SYNC_MAP:
            assert entry.description, f"Missing description for {entry.repo}"

    def test_no_duplicate_install_paths(self):
        install_paths = [e.install for e in SYNC_MAP]
        assert len(install_paths) == len(set(install_paths)), (
            "Duplicate install paths in SYNC_MAP"
        )

    def test_no_duplicate_repo_paths(self):
        repo_paths = [e.repo for e in SYNC_MAP]
        assert len(repo_paths) == len(set(repo_paths)), (
            "Duplicate repo paths in SYNC_MAP"
        )


class TestSyncExport:
    """Tests for exporting repo → staging directory."""

    def test_exports_files_to_target(self, tmp_path):
        # Create a minimal repo structure
        repo = tmp_path / "repo"
        target = tmp_path / "staging"

        # Create a fake file that maps to a known SyncEntry
        config_example = repo / "config.ini.example"
        config_example.parent.mkdir(parents=True, exist_ok=True)
        config_example.write_text("test content")

        license_file = repo / "LICENSE"
        license_file.write_text("MIT License")

        # Monkey-patch cfg for this test
        from src import config as config_mod
        original_root = config_mod.cfg.project_root
        config_mod.cfg.project_root = str(repo)

        try:
            total = sync_export(target_root=str(target))
            # Should have exported at least the files we created
            assert total >= 2
            assert (target / "config.ini.example").exists()
            assert (target / "LICENSE").exists()
            assert (target / "config.ini.example").read_text() == "test content"
        finally:
            config_mod.cfg.project_root = original_root

    def test_skips_missing_sources(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        target = tmp_path / "staging"

        from src import config as config_mod
        original_root = config_mod.cfg.project_root
        config_mod.cfg.project_root = str(repo)

        try:
            # Empty repo — everything should be skipped gracefully
            total = sync_export(target_root=str(target))
            assert total == 0
        finally:
            config_mod.cfg.project_root = original_root


class TestSyncImport:
    """Tests for importing staging → repo directory."""

    def test_imports_files_to_repo(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        source = tmp_path / "staging"

        # Create a file in staging at the install layout path
        staged_license = source / "LICENSE"
        staged_license.parent.mkdir(parents=True, exist_ok=True)
        staged_license.write_text("Updated MIT License")

        from src import config as config_mod
        original_root = config_mod.cfg.project_root
        config_mod.cfg.project_root = str(repo)

        try:
            total = sync_import(source_root=str(source))
            assert total >= 1
            assert (repo / "LICENSE").read_text() == "Updated MIT License"
        finally:
            config_mod.cfg.project_root = original_root


class TestSyncCheck:
    """Tests for diffing repo vs staging."""

    def test_detects_added_files(self, tmp_path):
        repo = tmp_path / "repo"
        target = tmp_path / "staging"

        # File exists in repo but not staging
        license_file = repo / "LICENSE"
        license_file.parent.mkdir(parents=True, exist_ok=True)
        license_file.write_text("MIT")
        target.mkdir()

        from src import config as config_mod
        original_root = config_mod.cfg.project_root
        config_mod.cfg.project_root = str(repo)

        try:
            results = sync_check(target_root=str(target))
            assert "LICENSE" in results["added"]
        finally:
            config_mod.cfg.project_root = original_root

    def test_detects_unchanged(self, tmp_path):
        repo = tmp_path / "repo"
        target = tmp_path / "staging"

        # Same file in both locations
        (repo / "LICENSE").parent.mkdir(parents=True, exist_ok=True)
        (repo / "LICENSE").write_text("MIT")
        (target / "LICENSE").parent.mkdir(parents=True, exist_ok=True)
        (target / "LICENSE").write_text("MIT")

        from src import config as config_mod
        original_root = config_mod.cfg.project_root
        config_mod.cfg.project_root = str(repo)

        try:
            results = sync_check(target_root=str(target))
            assert "LICENSE" in results["unchanged"]
        finally:
            config_mod.cfg.project_root = original_root

    def test_nonexistent_staging_dir(self, tmp_path):
        from src import config as config_mod
        original_root = config_mod.cfg.project_root
        config_mod.cfg.project_root = str(tmp_path / "repo")

        try:
            results = sync_check(target_root=str(tmp_path / "nope"))
            # Should return empty results, not crash
            assert results["added"] == []
            assert results["modified"] == []
        finally:
            config_mod.cfg.project_root = original_root
