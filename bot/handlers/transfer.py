# bot/handlers/transfer.py
"""
搬运任务处理器 - Bot 接收转发的文件
"""

import json
import logging
from aiogram import Router, F
from aiogram.types import Message
from aiogram.exceptions import TelegramRetryAfter
from sqlalchemy.ext.asyncio import AsyncSession

from utils.rate_limiter import bot_rate_limiter
from utils.task_queue import task_queue

logger = logging.getLogger(__name__)

router = Router()


@router.message(F.forward_from_chat)
async def receive_transferred_media(message: Message, redis_client):
    """
    接收转发的媒体文件

    当 Telethon 客户端转发文件到 Bot 时，Bot 接收并提取 file_id
    """
    # 从 Redis 获取当前正在执行的任务 ID
    task_id_str = await redis_client.get("current_transfer_task_id")
    task_id = int(task_id_str) if task_id_str else None

    if not task_id:
        # 没有正在执行的任务，忽略
        logger.debug(f"收到转发消息 message_id={message.message_id}，但无活跃任务，忽略")
        return

    # 标记为 pending
    bot_rate_limiter.add_pending_file(message.message_id)

    try:
        # 提取 file_id
        file_data = None

        if message.photo:
            file_data = {
                "file_id": message.photo[-1].file_id,
                "file_unique_id": message.photo[-1].file_unique_id,
                "file_type": "photo",
                "file_size": message.photo[-1].file_size,
                "caption": getattr(message, 'caption', None)
            }
            logger.debug(f"[任务 {task_id}] 提取照片 file_id: {file_data['file_unique_id']}")
        elif message.video:
            file_data = {
                "file_id": message.video.file_id,
                "file_unique_id": message.video.file_unique_id,
                "file_type": "video",
                "file_size": message.video.file_size,
                "caption": getattr(message, 'caption', None)
            }
            logger.debug(f"[任务 {task_id}] 提取视频 file_id: {file_data['file_unique_id']}")

        if not file_data:
            logger.debug(f"[任务 {task_id}] 转发消息 message_id={message.message_id} 不含媒体，跳过")
            return

        # 存入 Redis
        redis_key = f"task:{task_id}:files"
        await redis_client.rpush(redis_key, json.dumps(file_data))

        # 设置过期时间（24 小时）
        await redis_client.expire(redis_key, 86400)

        logger.debug(f"[任务 {task_id}] 文件已存入 Redis: {file_data['file_type']}, key={redis_key}")

    except TelegramRetryAfter as e:
        # Bot API 限流
        logger.warning(f"[任务 {task_id}] Bot 接收文件时触发限流, retry_after={e.retry_after}s")
        from database.connection import get_db
        async for db in get_db():
            await bot_rate_limiter.handle_rate_limit(db, task_id, e.retry_after)
            break

    except Exception as e:
        logger.error(f"[任务 {task_id}] 接收转发媒体异常: {str(e)}", exc_info=True)

    finally:
        # 移除 pending 标记
        bot_rate_limiter.remove_pending_file(message.message_id)
