"""Main application window — QMainWindow with tabbed interface."""

from __future__ import annotations

import logging
import os

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QMainWindow, QMessageBox, QTabWidget

from src import APP_NAME, APP_VERSION
from src.config import Config
from src.utils.json_handler import load_json

log = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    def __init__(self, cfg: Config) -> None:
        super().__init__()
        self.cfg = cfg
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")

        # Icon
        icon_path = os.path.join(cfg.app_root, "assets", "icons", "app_icon.ico")
        if os.path.isfile(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        # Central tabs
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self._add_tabs()

    def _add_tabs(self) -> None:
        data_dir = self.cfg.modtool_data_dir
        saves_dir = self.cfg.modtool_saves_dir

        log.debug("ModTool data_dir : %s", data_dir)
        log.debug("ModTool saves_dir: %s", saves_dir)

        # Load shared reference data
        items = load_json(os.path.join(data_dir, "MoreBuildings", "Items.json"))
        cat_tags = load_json(os.path.join(data_dir, "MoreBuildings", "CategoryTags.json"))
        unlock_buildings = load_json(os.path.join(data_dir, "MoreBuildings", "UnlockRequirementsItemsConstructions.json"))
        unlock_armor = load_json(os.path.join(data_dir, "MoreArmor", "UnlockRequirementsItemsConstructions.json"))

        # --- Moding-Tool tabs ---
        from src.gui.construction_adder_tab import ConstructionAdderTab
        from src.gui.construction_updater_tab import ConstructionUpdaterTab
        from src.gui.armor_adder_tab import ArmorAdderTab
        from src.gui.armor_updater_tab import ArmorUpdaterTab

        self.tabs.addTab(
            ConstructionAdderTab(saves_dir, data_dir, items, cat_tags, unlock_buildings),
            "New Construction",
        )
        self.tabs.addTab(
            ConstructionUpdaterTab(saves_dir, data_dir),
            "Buildings Maintainer",
        )
        self.tabs.addTab(
            ArmorAdderTab(saves_dir, data_dir, items, unlock_armor),
            "New Armor",
        )
        self.tabs.addTab(
            ArmorUpdaterTab(saves_dir, data_dir),
            "Armor Maintainer",
        )

        # --- Pipeline tabs ---
        from src.gui.localization_tab import LocalizationTab
        from src.gui.recipes_tab import RecipesTab
        from src.gui.sync_tab import SyncTab

        self.tabs.addTab(LocalizationTab(), "Localization")
        self.tabs.addTab(RecipesTab(), "Recipes")
        self.tabs.addTab(SyncTab(), "Sync")
