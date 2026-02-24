#!/usr/bin/env python3
"""
添加 Session 账号脚本
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.connection import get_db
from utils.session_manager import session_manager


async def main():
    """主函数"""
    print("=" * 50)
    print("添加 Telegram Session 账号")
    print("=" * 50)
    print()

    # 获取账号信息
    phone = input("手机号（带国家码，如 +8613800138000）: ").strip()
    api_id = input("API ID: ").strip()
    api_hash = input("API Hash: ").strip()

    try:
        api_id = int(api_id)
    except ValueError:
        print("❌ API ID 必须是数字")
        return

    print()
    print("正在发送验证码...")

    # 发送验证码
    result = await session_manager.login_session(phone, api_id, api_hash)
    print(f"✅ {result['message']}")

    if result["status"] == "code_sent":
        print()
        code = input("请输入验证码: ").strip()

        print("正在验证...")
        result = await session_manager.login_session(
            phone, api_id, api_hash, code=code
        )

        if result["status"] == "password_required":
            print()
            password = input("请输入两步验证密码: ").strip()

            print("正在验证密码...")
            result = await session_manager.login_session(
                phone, api_id, api_hash, code=code, password=password
            )

    if result["status"] == "success":
        print()
        print("登录成功！正在保存到数据库...")

        # 获取优先级
        priority = input("优先级（数字越小越优先，默认 0）: ").strip()
        priority = int(priority) if priority else 0

        async for db in get_db():
            try:
                session_account = await session_manager.add_session_account(
                    db,
                    phone_number=phone,
                    api_id=api_id,
                    api_hash=api_hash,
                    session_string=result["session_string"],
                    priority=priority
                )

                print()
                print("=" * 50)
                print("✅ Session 账号添加成功！")
                print("=" * 50)
                print(f"ID: {session_account.id}")
                print(f"手机号: {session_account.phone_number}")
                print(f"优先级: {session_account.priority}")
                print(f"状态: {'激活' if session_account.is_active else '未激活'}")
                print()

            except Exception as e:
                print(f"❌ 保存失败: {str(e)}")
            finally:
                break
    else:
        print(f"❌ 登录失败: {result.get('message', '未知错误')}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n操作已取消")
    except Exception as e:
        print(f"\n❌ 发生错误: {str(e)}")
        sys.exit(1)
