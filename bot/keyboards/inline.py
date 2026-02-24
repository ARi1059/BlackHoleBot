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
