# utils/transfer_executor.py
"""
搬运任务执行器
"""

import asyncio
import json
from typing import Optional, Dict, Any
from datetime import datetime
from telethon.errors import FloodWaitError, ChannelPrivateError, ChatAdminRequiredError
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db
from database.crud import (
    get_transfer_task,
    update_transfer_task,
    create_task_log,
    get_session_account
)
from database.models import TaskStatus
from utils.session_manager import session_manager
from utils.rate_limiter import session_rate_limiter, bot_rate_limiter
from config import settings


class TransferExecutor:
    """搬运任务执行器"""

    def __init__(self):
        self.redis_client = None  # 将在初始化时设置

    def set_redis_client(self, redis_client):
        """设置 Redis 客户端"""
        self.redis_client = redis_client

    async def execute_task(self, task_id: int):
        """
        执行搬运任务

        Args:
            task_id: 任务 ID
        """
        async for db in get_db():
            try:
                # 获取任务信息
                task = await get_transfer_task(db, task_id)
                if not task:
                    print(f"Task {task_id} not found")
                    return

                # 更新任务状态为运行中
                await update_transfer_task(
                    db,
                    task_id,
                    status=TaskStatus.RUNNING,
                    started_at=datetime.now()
                )

                await create_task_log(
                    db,
                    task_id,
                    "info",
                    f"开始执行搬运任务: {task.task_name}"
                )

                # 获取可用的 session 账号
                session_account = await session_manager.get_next_available_session(db)
                if not session_account:
                    await update_transfer_task(
                        db,
                        task_id,
                        status=TaskStatus.PAUSED,
                        error_message="没有可用的 Session 账号"
                    )
                    await create_task_log(
                        db,
                        task_id,
                        "error",
                        "没有可用的 Session 账号，任务已暂停"
                    )
                    return

                # 更新任务使用的 session
                await update_transfer_task(
                    db,
                    task_id,
                    session_account_id=session_account.id
                )

                # 执行转发
                await self._transfer_media(db, task, session_account)

                # 任务完成
                await update_transfer_task(
                    db,
                    task_id,
                    status=TaskStatus.COMPLETED,
                    completed_at=datetime.now()
                )

                await create_task_log(
                    db,
                    task_id,
                    "info",
                    f"✅ 任务完成，共转发 {task.progress_current} 个文件"
                )

            except Exception as e:
                await update_transfer_task(
                    db,
                    task_id,
                    status=TaskStatus.FAILED,
                    error_message=str(e)
                )
                await create_task_log(
                    db,
                    task_id,
                    "error",
                    f"任务执行失败: {str(e)}"
                )
            finally:
                break

    async def _transfer_media(
        self,
        db: AsyncSession,
        task,
        session_account
    ):
        """
        从频道转发媒体到 Bot

        Args:
            db: 数据库 session
            task: 搬运任务对象
            session_account: Session 账号对象
        """
        # 获取 Telethon 客户端
        client = await session_manager.get_client(db, session_account.id)
        if not client:
            raise Exception("无法创建 Telethon 客户端")

        try:
            # 获取频道实体
            try:
                # 优先使用 username，如果没有则使用 chat_id
                if task.source_chat_username:
                    channel = await client.get_entity(task.source_chat_username)
                else:
                    channel = await client.get_entity(task.source_chat_id)
            except (ChannelPrivateError, ChatAdminRequiredError):
                raise Exception("无法访问频道，请确保账号已加入该频道")

            # 创建 Redis key 用于存储文件
            redis_key = f"task:{task.id}:files"
            await update_transfer_task(db, task.id, temp_redis_key=redis_key)

            # 统计总消息数（用于进度显示）
            total_messages = 0
            async for _ in client.iter_messages(channel, limit=None):
                total_messages += 1

            await update_transfer_task(db, task.id, progress_total=total_messages)

            # 遍历消息并转发
            transferred_count = 0
            async for message in client.iter_messages(
                channel,
                limit=None,
                reverse=False
            ):
                # 检查 Bot 是否限流
                while bot_rate_limiter.is_bot_limited():
                    await asyncio.sleep(1)

                # 应用过滤条件
                if not await self._apply_filters(message, task):
                    continue

                # 检查 session 限流
                if await session_rate_limiter.check_and_update(db, session_account.id, task.id):
                    # 需要冷却，切换 session
                    await create_task_log(
                        db,
                        task.id,
                        "session_switch",
                        f"Session {session_account.id} 需要冷却，尝试切换账号"
                    )

                    # 获取下一个可用 session
                    next_session = await session_manager.get_next_available_session(db)
                    if not next_session:
                        # 没有可用 session，暂停任务
                        await update_transfer_task(db, task.id, status=TaskStatus.PAUSED)
                        await create_task_log(
                            db,
                            task.id,
                            "warning",
                            "所有 Session 都在冷却中，任务已暂停"
                        )
                        return

                    # 断开当前客户端
                    await session_manager.disconnect_client(session_account.id)

                    # 切换到新 session
                    session_account = next_session
                    client = await session_manager.get_client(db, session_account.id)
                    await update_transfer_task(db, task.id, session_account_id=session_account.id)

                    await create_task_log(
                        db,
                        task.id,
                        "session_switch",
                        f"已切换到 Session {session_account.id}"
                    )

                # 转发消息到 Bot
                try:
                    await client.forward_messages(
                        entity=settings.BOT_USERNAME,
                        messages=message.id,
                        from_peer=channel
                    )

                    transferred_count += 1

                    # 更新进度
                    await update_transfer_task(
                        db,
                        task.id,
                        progress_current=transferred_count
                    )

                    # 每转发 10 个文件记录一次日志
                    if transferred_count % 10 == 0:
                        await create_task_log(
                            db,
                            task.id,
                            "info",
                            f"已转发 {transferred_count}/{total_messages} 个文件"
                        )

                except FloodWaitError as e:
                    # API 限流
                    await create_task_log(
                        db,
                        task.id,
                        "rate_limit",
                        f"遇到 API 限流，需要等待 {e.seconds} 秒"
                    )

                    # 设置当前 session 冷却
                    await session_manager.set_session_cooldown(
                        db,
                        session_account.id,
                        cooldown_minutes=int(e.seconds / 60) + 1
                    )

                    # 切换 session
                    next_session = await session_manager.get_next_available_session(db)
                    if not next_session:
                        await update_transfer_task(db, task.id, status=TaskStatus.PAUSED)
                        return

                    await session_manager.disconnect_client(session_account.id)
                    session_account = next_session
                    client = await session_manager.get_client(db, session_account.id)
                    await update_transfer_task(db, task.id, session_account_id=session_account.id)

                except Exception as e:
                    await create_task_log(
                        db,
                        task.id,
                        "error",
                        f"转发消息失败: {str(e)}"
                    )

        finally:
            # 断开客户端
            await session_manager.disconnect_client(session_account.id)

    async def _apply_filters(self, message, task) -> bool:
        """
        应用过滤条件

        Args:
            message: Telegram 消息对象
            task: 搬运任务对象

        Returns:
            True 表示通过过滤，False 表示不通过
        """
        # 媒体类型过滤
        filter_type = task.filter_type
        if filter_type == "photo" and not message.photo:
            return False
        if filter_type == "video" and not message.video:
            return False
        if filter_type == "all" and not (message.photo or message.video):
            return False

        # 关键词过滤
        if task.filter_keywords:
            # 安全获取文本内容，使用 getattr 避免 AttributeError
            text = getattr(message, 'text', None) or getattr(message, 'caption', None) or ""
            if not any(keyword in text for keyword in task.filter_keywords):
                return False

        # 日期范围过滤
        if task.filter_date_from and message.date < task.filter_date_from:
            return False
        if task.filter_date_to and message.date > task.filter_date_to:
            return False

        return True


# 全局执行器实例
transfer_executor = TransferExecutor()
