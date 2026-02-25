# bot/main.py
"""
Bot 主程序
"""

import asyncio
import logging
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage, DefaultKeyBuilder

from config import settings
from bot.middlewares import AuthMiddleware
from bot.handlers import (
    user_router,
    admin_router,
    transfer_router,
    transfer_admin_router,
    transfer_approve_router
)
from database.connection import init_db
from utils.transfer_executor import transfer_executor
import redis.asyncio as redis

# 配置日志
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot.log')
    ]
)

logger = logging.getLogger(__name__)


async def main():
    """主函数"""
    logger.info("Starting BlackHoleBot...")

    # 初始化数据库
    await init_db()
    logger.info("Database initialized")

    # 创建 Redis 客户端
    redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    logger.info("Redis client created")

    # 设置 Redis 客户端到 transfer_executor
    transfer_executor.set_redis_client(redis_client)

    # 创建 Bot 实例
    bot = Bot(token=settings.BOT_TOKEN, parse_mode=ParseMode.HTML)

    # 创建 Redis 存储用于 FSM，使用与 Web 端相同的 key_builder
    storage = RedisStorage(redis_client, key_builder=DefaultKeyBuilder(with_destiny=True))

    # 创建 Dispatcher，使用 Redis 存储
    dp = Dispatcher(storage=storage)

    # 注册中间件
    dp.message.middleware(AuthMiddleware())
    dp.callback_query.middleware(AuthMiddleware())

    # 注册路由
    dp.include_router(user_router)
    dp.include_router(admin_router)
    dp.include_router(transfer_router)
    dp.include_router(transfer_admin_router)
    dp.include_router(transfer_approve_router)

    # 将 redis_client 添加到 bot 数据中，供 handlers 使用
    dp["redis_client"] = redis_client

    logger.info("Bot configuration completed")

    # 启动 Bot
    try:
        logger.info("Bot is starting polling...")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except Exception as e:
        logger.error(f"Error during polling: {e}")
    finally:
        await bot.session.close()
        await redis_client.aclose()
        logger.info("Bot stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
