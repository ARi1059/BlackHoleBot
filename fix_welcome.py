import asyncio
from database.connection import get_db
from database.crud import get_setting, set_setting

async def main():
    async for db in get_db():
        welcome = await get_setting(db, "welcome_message")
        print(f"当前欢迎消息: {welcome}")
        
        # 清除欢迎消息，让它使用默认的主菜单
        if welcome:
            choice = input("\n是否清除自定义欢迎消息，使用默认主菜单？(y/n): ")
            if choice.lower() == 'y':
                await set_setting(db, "welcome_message", "")
                print("✅ 已清除自定义欢迎消息")
        break

if __name__ == "__main__":
    asyncio.run(main())
