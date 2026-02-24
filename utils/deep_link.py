# utils/deep_link.py
"""
深链接生成工具
"""

import secrets
import string
from sqlalchemy.ext.asyncio import AsyncSession
from database.crud import get_collection_by_code


def generate_deep_link_code(length: int = 8) -> str:
    """
    生成随机深链接码

    Args:
        length: 链接码长度，默认 8

    Returns:
        随机生成的深链接码
    """
    chars = string.ascii_letters + string.digits
    return ''.join(secrets.choice(chars) for _ in range(length))


async def generate_unique_deep_link_code(db: AsyncSession, length: int = 8) -> str:
    """
    生成唯一的深链接码（确保不重复）

    Args:
        db: 数据库 session
        length: 链接码长度，默认 8

    Returns:
        唯一的深链接码
    """
    max_attempts = 10
    for _ in range(max_attempts):
        code = generate_deep_link_code(length)
        # 检查是否已存在
        existing = await get_collection_by_code(db, code)
        if not existing:
            return code

    # 如果 10 次都重复，增加长度再试
    return generate_deep_link_code(length + 2)


def parse_start_parameter(text: str) -> str | None:
    """
    从 /start 命令中解析深链接参数

    Args:
        text: 命令文本，如 "/start abc123"

    Returns:
        深链接码，如果没有参数则返回 None
    """
    parts = text.split(maxsplit=1)
    if len(parts) > 1:
        return parts[1].strip()
    return None


def create_deep_link(bot_username: str, deep_link_code: str) -> str:
    """
    创建完整的深链接 URL

    Args:
        bot_username: Bot 用户名
        deep_link_code: 深链接码

    Returns:
        完整的深链接 URL
    """
    return f"https://t.me/{bot_username}?start={deep_link_code}"
