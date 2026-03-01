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


async def send_collection_to_channel(
    bot: Optional[Bot],
    media_list: List[Dict[str, Any]],
    collection_name: str,
    collection_description: str = "",
    collection_tags: List[str] = None,
    media_count: int = None
):
    """
    将合集内容发送到私有频道

    Args:
        bot: Bot 实例（可选，为 None 时自动创建临时实例）
        media_list: 媒体文件列表
        collection_name: 合集名称
        collection_description: 合集描述
        collection_tags: 合集标签列表
        media_count: 媒体总数
    """
    if not settings.PRIVATE_CHANNEL:
        logger.warning("未配置私有频道，跳过发送")
        return

    # 准备合集信息文本
    tags_text = " ".join([f"#{tag}" for tag in (collection_tags or [])])
    total_count = media_count or len(media_list)
    info_text = (
        f"📦 合集名称: {collection_name}\n"
        f"{collection_description or ''}\n"
        f"{tags_text or ''}\n"
        f"📊 文件总数 {total_count} "
    )

    # 创建或使用 Bot 实例
    should_close = False
    if bot is None:
        from aiogram import Bot as AiogramBot
        bot_instance = AiogramBot(token=settings.BOT_TOKEN)
        should_close = True
    else:
        bot_instance = bot

    try:
        # 分批发送媒体（每 10 个一组）
        for i in range(0, len(media_list), 10):
            batch = media_list[i:i+10]
            media_group = []

            for idx, media_data in enumerate(batch):
                file_id = media_data["file_id"]
                file_type = media_data["file_type"]

                # 每个媒体组的第一个文件带上合集信息
                caption = info_text if idx == 0 else None

                if file_type == "photo":
                    media_group.append(InputMediaPhoto(media=file_id, caption=caption))
                elif file_type == "video":
                    media_group.append(InputMediaVideo(media=file_id, caption=caption))

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
