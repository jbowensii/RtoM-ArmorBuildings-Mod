"""Main application window — QMainWindow with tabbed interface."""

from __future__ import annotations

import logging
import os

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QMainWindow, QTabWidget

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
        items = load_json(os.path.join(
            templates_dir, "MoreBuildings", "Items.json",
        ))
        cat_tags = load_json(os.path.join(
            templates_dir, "MoreBuildings", "CategoryTags.json",
        ))
        unlock_buildings = load_json(os.path.join(
            templates_dir, "MoreBuildings",
            "UnlockRequirementsItemsConstructions.json",
        ))
        unlock_armor = load_json(os.path.join(
            templates_dir, "MoreArmor",
            "UnlockRequirementsItemsConstructions.json",
        ))

        # Common kwargs for generic item tabs
        common = dict(
            tobis_json_dir=tobis_json_dir,
            templates_dir=templates_dir,
            game_extract_dir=game_extract_dir,
            tobis_mod_dir=tobis_mod_dir,
            data_dir=data_dir,
            items_index=items,
            unlock_requirements=unlock_armor,
        )

        # --- Construction tab (custom) ---
        from src.gui.construction_adder_tab import ConstructionAdderTab

        self.tabs.addTab(
            ConstructionAdderTab(
                tobis_json_dir, templates_dir, game_extract_dir, tobis_mod_dir,
                items, cat_tags, unlock_buildings, data_dir,
            ),
            "New Construction",
        )

        # --- Generic item tabs ---
        from src.gui.item_adder_tab import ItemAdderTab
        from src.gui.tab_configs import (
            ARMOR_CONFIG, WEAPON_CONFIG, TOOL_CONFIG,
            ITEM_CONFIG, LOOT_CONFIG, ORE_CONFIG,
        )

        for config in (ARMOR_CONFIG, WEAPON_CONFIG, TOOL_CONFIG,
                        ITEM_CONFIG, LOOT_CONFIG, ORE_CONFIG):
            self.tabs.addTab(
                ItemAdderTab(config, **common),
                config.tab_label,
            )

        # --- Pipeline tabs ---
        from src.gui.localization_tab import LocalizationTab
        from src.gui.recipes_tab import RecipesTab

        self.tabs.addTab(LocalizationTab(), "Localization")
        self.tabs.addTab(RecipesTab(), "Color Variants")
