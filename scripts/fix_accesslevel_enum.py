#!/usr/bin/env python3
"""
修复 accesslevel 枚举值大小写问题
将数据库中的大写值改为小写
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from database.connection import async_session_maker


async def fix_accesslevel_enum():
    """修复 accesslevel 枚举值"""
    async with async_session_maker() as db:
        try:
            # 更新 collections 表中的 access_level 值
            print("正在更新 collections 表中的 access_level 值...")

            # 先检查是否有数据
            result = await db.execute(text("SELECT COUNT(*) FROM collections"))
            count = result.scalar()
            print(f"找到 {count} 条合集记录")

            if count > 0:
                # 更新现有数据
                await db.execute(text("UPDATE collections SET access_level = 'public' WHERE access_level = 'PUBLIC'"))
                await db.execute(text("UPDATE collections SET access_level = 'vip' WHERE access_level = 'VIP'"))

            # 修改枚举类型定义
            print("正在修改枚举类型定义...")

            # 1. 先将列改为 varchar 类型
            await db.execute(text("ALTER TABLE collections ALTER COLUMN access_level TYPE varchar(20)"))

            # 2. 删除旧的枚举类型
            await db.execute(text("DROP TYPE IF EXISTS accesslevel CASCADE"))

            # 3. 创建新的枚举类型（小写值）
            await db.execute(text("CREATE TYPE accesslevel AS ENUM ('public', 'vip')"))

            # 4. 将列改回枚举类型
            await db.execute(text("ALTER TABLE collections ALTER COLUMN access_level TYPE accesslevel USING access_level::accesslevel"))

            # 5. 设置默认值
            await db.execute(text("ALTER TABLE collections ALTER COLUMN access_level SET DEFAULT 'public'::accesslevel"))

            await db.commit()
            print("✅ accesslevel 枚举值修复完成")

        except Exception as e:
            await db.rollback()
            print(f"❌ 修复失败: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(fix_accesslevel_enum())
