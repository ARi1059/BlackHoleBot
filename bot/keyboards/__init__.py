# bot/keyboards/__init__.py
"""
键盘模块
"""

from .inline import (
    create_pagination_keyboard,
    create_search_results_keyboard,
    create_collection_info_keyboard,
    create_confirm_keyboard,
    create_main_menu_keyboard,
    create_browse_keyboard,
    create_hot_collections_keyboard,
    create_admin_panel_keyboard,
)

__all__ = [
    "create_pagination_keyboard",
    "create_search_results_keyboard",
    "create_collection_info_keyboard",
    "create_confirm_keyboard",
    "create_main_menu_keyboard",
    "create_browse_keyboard",
    "create_hot_collections_keyboard",
    "create_admin_panel_keyboard",
]
