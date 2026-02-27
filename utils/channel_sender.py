# utils/channel_sender.py
"""
发送合集内容到私有频道
"""

import logging
from typing import List, Dict, Any, Optional
from aiogram import Bot
from aiogram.types import InputMediaPhoto, InputMediaVideo
from config import settings

logger = logging.getLogger(__name__)


async def send_collection_to_channel(bot: Optional[Bot], media_list: List[Dict[str, Any]], collection_name: str):
    """
    将合集内容发送到私有频道

    Args:
        bot: Bot 实例（可选，为 None 时自动创建临时实例）
        media_list: 媒体文件列表
        collection_name: 合集名称
    """
    if not settings.PRIVATE_CHANNEL:
        logger.warning("PRIVATE_CHANNEL 未配置，跳过发送到频道")
        return

    bot_instance = bot
    should_close = False
    if bot_instance is None:
        bot_instance = Bot(token=settings.BOT_TOKEN)
        should_close = True

    try:
        # 发送合集标题
        await bot_instance.send_message(
            chat_id=settings.PRIVATE_CHANNEL,
            text=f"📦 合集: {collection_name}\n📊 共 {len(media_list)} 个文件"
        )

        # 按每10个文件分组发送媒体组
        for i in range(0, len(media_list), 10):
            batch = media_list[i:i+10]
            media_group = []

            for media_data in batch:
                file_id = media_data["file_id"]
                file_type = media_data["file_type"]

                if file_type == "photo":
                    media_group.append(InputMediaPhoto(media=file_id))
                elif file_type == "video":
                    media_group.append(InputMediaVideo(media=file_id))

            if media_group:
                await bot_instance.send_media_group(
                    chat_id=settings.PRIVATE_CHANNEL,
                    media=media_group
                )

        logger.info(f"成功发送合集 '{collection_name}' 到私有频道，共 {len(media_list)} 个文件")

    except Exception as e:
        logger.error(f"发送合集到私有频道失败: {e}", exc_info=True)
    finally:
        if should_close:
            await bot_instance.session.close()
