#!/usr/bin/env python3
"""
创建超级管理员脚本
"""

import asyncio
import sys
import argparse
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import UserRole
from database.crud import get_user_by_telegram_id, create_user, update_user_role
from database.connection import async_session_maker


async def create_admin(telegram_id: int, username: str = None, first_name: str = None):
    """创建或升级为超级管理员"""
    async with async_session_maker() as db:
        # 检查用户是否存在
        user = await get_user_by_telegram_id(db, telegram_id)

        if user:
            # 用户已存在，升级为超级管理员
            if user.role == UserRole.SUPER_ADMIN:
                print(f"✅ 用户 {telegram_id} 已经是超级管理员")
                return

            await update_user_role(db, user.id, UserRole.SUPER_ADMIN)
            print(f"✅ 用户 {telegram_id} 已升级为超级管理员")
        else:
            # 创建新用户
            user = await create_user(
                db,
                telegram_id=telegram_id,
                username=username,
                first_name=first_name or "Admin",
                role=UserRole.SUPER_ADMIN
            )
            print(f"✅ 超级管理员创建成功")
            print(f"   Telegram ID: {user.telegram_id}")
            print(f"   用户名: {user.username or 'N/A'}")
            print(f"   姓名: {user.first_name}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="创建超级管理员")
    parser.add_argument(
        "--telegram-id",
        type=int,
        required=True,
        help="Telegram 用户 ID"
    )
    parser.add_argument(
        "--username",
        type=str,
        help="Telegram 用户名（可选）"
    )
    parser.add_argument(
        "--first-name",
        type=str,
        help="用户姓名（可选）"
    )

    args = parser.parse_args()

    print("🚀 创建超级管理员...")
    print(f"   Telegram ID: {args.telegram_id}")

    try:
        asyncio.run(create_admin(
            telegram_id=args.telegram_id,
            username=args.username,
            first_name=args.first_name
        ))
    except Exception as e:
        print(f"❌ 创建失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
