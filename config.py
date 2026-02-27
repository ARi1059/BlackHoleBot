# config.py
"""
项目配置文件
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """应用配置"""

    # Bot 配置
    BOT_TOKEN: str
    BOT_USERNAME: str

    # 数据库配置
    DATABASE_URL: str

    # Redis 配置
    REDIS_URL: str = "redis://localhost:6379/0"

    # 安全配置
    SESSION_ENCRYPTION_KEY: str
    SECRET_KEY: str

    # Web 配置
    WEB_HOST: str = "0.0.0.0"
    WEB_PORT: int = 8000
    WEB_DOMAIN: Optional[str] = None  # 可选的 Web 域名，用于 CORS 配置

    # Telegram Login
    TELEGRAM_BOT_USERNAME: str

    # 限流配置
    TRANSFER_LIMIT_PER_SESSION: int = 500
    TRANSFER_COOLDOWN_MINUTES: int = 3

    # 合集配置
    MAX_MEDIA_PER_COLLECTION: int = 1000
    MEDIA_PER_PAGE: int = 10
    PRIVATE_CHANNEL: Optional[int] = None  # 私有频道ID，用于发送合集内容

    # JWT 配置
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_DAYS: int = 7

    # 日志配置
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = True


# 创建全局配置实例
settings = Settings()
