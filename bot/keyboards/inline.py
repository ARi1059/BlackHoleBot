# bot/keyboards/inline.py
"""
内联键盘布局
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def create_pagination_keyboard(
    deep_link_code: str,
    current_page: int,
    total_pages: int
) -> InlineKeyboardMarkup:
    """
    创建分页键盘

    Args:
        deep_link_code: 合集深链接码
        current_page: 当前页码
        total_pages: 总页数

    Returns:
        InlineKeyboardMarkup
    """
    builder = InlineKeyboardBuilder()

    # 第一行：上一页、页码、下一页
    buttons = []

    if current_page > 1:
        buttons.append(InlineKeyboardButton(
            text="◀️ 上一页",
            callback_data=f"collection_{deep_link_code}_page_{current_page - 1}"
        ))

    buttons.append(InlineKeyboardButton(
        text=f"{current_page}/{total_pages}",
        callback_data="page_info"
    ))

    if current_page < total_pages:
        buttons.append(InlineKeyboardButton(
            text="下一页 ▶️",
            callback_data=f"collection_{deep_link_code}_page_{current_page + 1}"
        ))

    builder.row(*buttons)

    # 第二行：首页、合集信息、搜索
    builder.row(
        InlineKeyboardButton(
            text="🏠 首页",
            callback_data=f"collection_{deep_link_code}_page_1"
        ),
        InlineKeyboardButton(
            text="📋 合集信息",
            callback_data=f"collection_{deep_link_code}_info"
        ),
        InlineKeyboardButton(
            text="🔍 搜索",
            callback_data="search"
        )
    )

    return builder.as_markup()


def create_search_results_keyboard(collections: list) -> InlineKeyboardMarkup:
    """
    创建搜索结果键盘

    Args:
        collections: 合集列表

    Returns:
        InlineKeyboardMarkup
    """
    builder = InlineKeyboardBuilder()

    for collection in collections:
        # VIP 标记
        vip_mark = " 💎" if collection.access_level == "vip" else ""

        builder.row(InlineKeyboardButton(
            text=f"{collection.name}{vip_mark}",
            callback_data=f"view_collection_{collection.deep_link_code}"
        ))

    return builder.as_markup()


def create_collection_info_keyboard(deep_link_code: str) -> InlineKeyboardMarkup:
    """
    创建合集信息键盘

    Args:
        deep_link_code: 合集深链接码

    Returns:
        InlineKeyboardMarkup
    """
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="📦 查看内容",
            callback_data=f"collection_{deep_link_code}_page_1"
        )
    )

    return builder.as_markup()


def create_confirm_keyboard() -> InlineKeyboardMarkup:
    """
    创建确认键盘

    Returns:
        InlineKeyboardMarkup
    """
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="✅ 确认发送",
            callback_data="confirm"
        ),
        InlineKeyboardButton(
            text="❌ 取消",
            callback_data="cancel"
        )
    )

    return builder.as_markup()


def create_main_menu_keyboard(is_admin: bool = False) -> InlineKeyboardMarkup:
    """
    创建主菜单键盘

    Args:
        is_admin: 是否为管理员

    Returns:
        InlineKeyboardMarkup
    """
    builder = InlineKeyboardBuilder()

    # 第一行：浏览合集、热门合集
    builder.row(
        InlineKeyboardButton(text="📦 浏览合集", callback_data="browse_collections"),
        InlineKeyboardButton(text="🔥 热门合集", callback_data="hot_collections")
    )

    # 第二行：搜索
    builder.row(
        InlineKeyboardButton(text="🔍 搜索合集", callback_data="search")
    )

    # 管理员功能
    if is_admin:
        builder.row(
            InlineKeyboardButton(text="⚙️ 管理面板", callback_data="admin_panel")
        )

    return builder.as_markup()


def create_browse_keyboard(collections: list, page: int, total_pages: int) -> InlineKeyboardMarkup:
    """
    创建浏览合集键盘

    Args:
        collections: 合集列表
        page: 当前页码
        total_pages: 总页数

    Returns:
        InlineKeyboardMarkup
    """
    builder = InlineKeyboardBuilder()

    # 合集列表
    for collection in collections:
        vip_mark = " 💎" if collection.access_level.value == "vip" else ""
        builder.row(InlineKeyboardButton(
            text=f"{collection.name}{vip_mark}",
            callback_data=f"view_collection_{collection.deep_link_code}"
        ))

    # 分页按钮
    buttons = []
    if page > 1:
        buttons.append(InlineKeyboardButton(text="◀️ 上一页", callback_data=f"browse_page_{page - 1}"))

    buttons.append(InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data="page_info"))

    if page < total_pages:
        buttons.append(InlineKeyboardButton(text="下一页 ▶️", callback_data=f"browse_page_{page + 1}"))

    if buttons:
        builder.row(*buttons)

    # 返回主菜单
    builder.row(InlineKeyboardButton(text="🏠 返回主菜单", callback_data="main_menu"))

    return builder.as_markup()

