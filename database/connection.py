# database/connection.py
"""
数据库连接管理
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from typing import AsyncGenerator
import logging
import redis.asyncio as redis

from config import settings
from .models import Base

logger = logging.getLogger(__name__)

# 创建 Redis 客户端
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

# 创建异步引擎
engine = create_async_engine(
    settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
    echo=settings.LOG_LEVEL == "DEBUG",
    poolclass=NullPool,
    pool_pre_ping=True,
)

# 创建异步 session 工厂
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    获取数据库 session
    用于依赖注入
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """
    初始化数据库
    创建所有表
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Database initialized successfully")


async def drop_db():
    """
    删除所有表（仅用于开发/测试）
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    logger.warning("All database tables dropped")


async def close_db():
    """
    关闭数据库连接
    """
    await engine.dispose()
    logger.info("Database connection closed")
