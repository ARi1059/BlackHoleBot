#!/usr/bin/env python3
"""
初始化数据库脚本
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import init_db
from database.crud import set_setting
from database.connection import async_session_maker


async def init_default_settings():
    """初始化默认设置"""
    async with async_session_maker() as db:
        # 欢迎消息
        await set_setting(
            db,
            "welcome_message",
            "👋 欢迎使用 BlackHoleBot！\n\n"
            "🎯 功能介绍:\n"
            "• 📦 浏览海量媒体合集\n"
            "• 🔍 快速搜索感兴趣的内容\n"
            "• 💎 VIP 用户专享高质量资源\n\n"
            "📖 使用指南:\n"
            "/search - 搜索合集\n"
            "/help - 查看帮助\n\n"
            "💡 提示: 点击频道分享的链接即可直接访问合集\n\n"
            "祝你使用愉快！✨",
            "用户首次启动时的欢迎消息"
        )

        # Bot 名称
        await set_setting(
            db,
            "bot_name",
            "BlackHoleBot",
            "Bot 名称"
        )

        # 每个合集最大媒体数量
        await set_setting(
            db,
            "max_media_per_collection",
            "1000",
            "每个合集最大媒体数量"
        )

        print("✅ 默认设置已初始化")


async def main():
    """主函数"""
    print("🚀 开始初始化数据库...")

    try:
        # 创建所有表
        await init_db()
        print("✅ 数据库表创建成功")

        # 初始化默认设置
        await init_default_settings()

        print("\n✨ 数据库初始化完成！")
        print("\n下一步:")
        print("1. 创建超级管理员: python scripts/create_admin.py --telegram-id YOUR_ID")
        print("2. 启动 Bot: python bot/main.py")
        print("3. 启动 Web API: uvicorn web.main:app --reload")

    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
