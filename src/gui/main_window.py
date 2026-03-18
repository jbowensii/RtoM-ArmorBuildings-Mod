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
        templates_dir = self.cfg.templates_dir
        tobis_json_dir = self.cfg.tobis_json_dir
        tobis_mod_dir = self.cfg.tobis_mod_dir
        game_extract_dir = self.cfg.game_extract_dir
        data_dir = self.cfg.data_dir

        log.debug("TemplatesDir   : %s", templates_dir)
        log.debug("TobisJsonDir   : %s", tobis_json_dir)
        log.debug("TobisModDir    : %s", tobis_mod_dir)
        log.debug("GameExtractDir : %s", game_extract_dir)

        # Load shared reference data
        items = load_json(os.path.join(templates_dir, "MoreBuildings", "Items.json"))
        cat_tags = load_json(os.path.join(templates_dir, "MoreBuildings", "CategoryTags.json"))
        unlock_buildings = load_json(os.path.join(
            templates_dir, "MoreBuildings", "UnlockRequirementsItemsConstructions.json"
        ))
        unlock_armor = load_json(os.path.join(
            templates_dir, "MoreArmor", "UnlockRequirementsItemsConstructions.json"
        ))

        # --- Moding-Tool tabs ---
        from src.gui.construction_adder_tab import ConstructionAdderTab
        from src.gui.construction_updater_tab import ConstructionUpdaterTab
        from src.gui.armor_adder_tab import ArmorAdderTab
        from src.gui.armor_updater_tab import ArmorUpdaterTab

        self.tabs.addTab(
            ConstructionAdderTab(
                tobis_json_dir, templates_dir, game_extract_dir, tobis_mod_dir,
                items, cat_tags, unlock_buildings,
            ),
            "New Construction",
        )
        self.tabs.addTab(
            ConstructionUpdaterTab(
                tobis_mod_dir, templates_dir, data_dir,
                tobis_json_dir, game_extract_dir,
            ),
            "Buildings Maintainer",
        )
        self.tabs.addTab(
            ArmorAdderTab(
                tobis_json_dir, templates_dir, game_extract_dir, tobis_mod_dir,
                items, unlock_armor,
            ),
            "New Armor",
        )
        self.tabs.addTab(
            ArmorUpdaterTab(
                tobis_mod_dir, templates_dir, data_dir,
                tobis_json_dir, game_extract_dir,
            ),
            "Armor Maintainer",
        )

        # --- Pipeline tabs ---
        from src.gui.localization_tab import LocalizationTab
        from src.gui.recipes_tab import RecipesTab

        self.tabs.addTab(LocalizationTab(), "Localization")
        self.tabs.addTab(RecipesTab(), "Recipes")
