# bot/handlers/transfer.py
"""
搬运任务处理器 - Bot 接收转发的文件
"""

import json
from aiogram import Router, F
from aiogram.types import Message
from aiogram.exceptions import TelegramRetryAfter
from sqlalchemy.ext.asyncio import AsyncSession

from utils.rate_limiter import bot_rate_limiter
from utils.task_queue import task_queue


router = Router()


@router.message(F.forward_from_chat)
async def receive_transferred_media(message: Message, redis_client):
    """
    接收转发的媒体文件

    当 Telethon 客户端转发文件到 Bot 时，Bot 接收并提取 file_id
    """
    # 获取当前正在执行的任务 ID
    task_id = task_queue.get_current_task_id()
    if not task_id:
        # 没有正在执行的任务，忽略
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
                "caption": message.caption
            }
        elif message.video:
            file_data = {
                "file_id": message.video.file_id,
                "file_unique_id": message.video.file_unique_id,
                "file_type": "video",
                "file_size": message.video.file_size,
                "caption": message.caption
            }

        if not file_data:
            return

        # 存入 Redis
        redis_key = f"task:{task_id}:files"
        await redis_client.rpush(redis_key, json.dumps(file_data))

        # 设置过期时间（24 小时）
        await redis_client.expire(redis_key, 86400)

    except TelegramRetryAfter as e:
        # Bot API 限流
        from database.connection import get_db
        async for db in get_db():
            await bot_rate_limiter.handle_rate_limit(db, task_id, e.retry_after)
            break

    except Exception as e:
        print(f"Error receiving transferred media: {str(e)}")

    finally:
        # 移除 pending 标记
        bot_rate_limiter.remove_pending_file(message.message_id)
