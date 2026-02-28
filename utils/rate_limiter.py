# utils/rate_limiter.py
"""
限流控制器
"""

import asyncio
import logging
from typing import Optional, Set
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from database.crud import (
    update_session_account,
    update_transfer_task,
    create_task_log,
    get_session_account
)
from database.models import TaskStatus
from config import settings

logger = logging.getLogger(__name__)


class SessionRateLimiter:
    """Session 账号限流控制器（500 文件/周期）"""

    def __init__(self):
        self.transfer_limit = settings.TRANSFER_LIMIT_PER_SESSION
        self.cooldown_minutes = settings.TRANSFER_COOLDOWN_MINUTES

    async def check_and_update(
        self,
        db: AsyncSession,
        session_id: int,
        task_id: int
    ) -> bool:
        """
        检查是否需要冷却并更新计数

        Args:
            db: 数据库 session
            session_id: Session 账号 ID
            task_id: 任务 ID

        Returns:
            True 表示需要冷却，False 表示可以继续
        """
        session = await get_session_account(db, session_id)
        if not session:
            logger.warning(f"[任务 {task_id}] Session {session_id} 不存在，触发冷却")
            return True

        # 检查是否达到限制
        if session.transfer_count >= self.transfer_limit:
            # 设置冷却时间
            cooldown_until = datetime.now() + timedelta(
                minutes=self.cooldown_minutes
            )
            await update_session_account(
                db,
                session_id,
                cooldown_until=cooldown_until,
                transfer_count=0
            )

            logger.info(
                f"[任务 {task_id}] Session {session_id} 达到转发限制 "
                f"({self.transfer_limit} 文件)，进入冷却 {self.cooldown_minutes} 分钟"
            )

            # 记录日志
            await create_task_log(
                db,
                task_id,
                "rate_limit",
                f"Session {session_id} 达到 {self.transfer_limit} 文件限制，冷却 {self.cooldown_minutes} 分钟"
            )

            return True

        # 增加计数
        new_count = session.transfer_count + 1
        await update_session_account(
            db,
            session_id,
            transfer_count=new_count,
            last_transfer_time=datetime.now(),
            last_used_at=datetime.now()
        )

        if new_count % 100 == 0:
            logger.info(f"[任务 {task_id}] Session {session_id} 已转发 {new_count}/{self.transfer_limit} 文件")

        return False


class BotRateLimiter:
    """Bot API 限流控制器"""

    def __init__(self):
        self.is_limited: bool = False
        self.pending_file_ids: Set[int] = set()
        self.current_task_id: Optional[int] = None

    async def handle_rate_limit(
        self,
        db: AsyncSession,
        task_id: int,
        retry_after: int
    ):
        """
        处理 Bot API 限流

        Args:
            db: 数据库 session
            task_id: 任务 ID
            retry_after: 需要等待的秒数
        """
        self.is_limited = True
        self.current_task_id = task_id
        logger.warning(f"[任务 {task_id}] Bot API 限流触发，需等待 {retry_after} 秒")

        # 更新任务状态
        await update_transfer_task(
            db,
            task_id,
            status=TaskStatus.WAITING_BOT
        )

        # 记录日志
        await create_task_log(
            db,
            task_id,
            "rate_limit",
            f"Bot API 限流，等待 {retry_after} 秒"
        )

        # 等待所有 pending 的 file_id 获取完成
        max_wait = 60  # 最多等待 60 秒
        waited = 0
        pending_count = len(self.pending_file_ids)
        if pending_count > 0:
            logger.info(f"[任务 {task_id}] 等待 {pending_count} 个 pending 文件处理完成")
        while self.pending_file_ids and waited < max_wait:
            await asyncio.sleep(0.5)
            waited += 0.5

        if waited >= max_wait and self.pending_file_ids:
            logger.warning(f"[任务 {task_id}] 等待 pending 文件超时，仍有 {len(self.pending_file_ids)} 个未完成")

        # 记录日志
        await create_task_log(
            db,
            task_id,
            "info",
            f"✅ 限流前文件已全部存储，等待 Bot API 恢复（{retry_after} 秒）"
        )

        logger.info(f"[任务 {task_id}] 开始等待 Bot API 限流恢复，{retry_after} 秒")
        # 等待限流时间
        await asyncio.sleep(retry_after)

        # 恢复
        await self.resume_after_limit(db, task_id)

    async def resume_after_limit(self, db: AsyncSession, task_id: int):
        """
        限流恢复后继续

        Args:
            db: 数据库 session
            task_id: 任务 ID
        """
        self.is_limited = False
        self.current_task_id = None
        logger.info(f"[任务 {task_id}] Bot API 限流已恢复，继续执行")

        # 更新任务状态
        await update_transfer_task(
            db,
            task_id,
            status=TaskStatus.RUNNING
        )

        # 记录日志
        await create_task_log(
            db,
            task_id,
            "info",
            "✅ Bot API 已恢复，继续搬运"
        )

    def add_pending_file(self, message_id: int):
        """添加待处理的文件 ID"""
        self.pending_file_ids.add(message_id)

    def remove_pending_file(self, message_id: int):
        """移除已处理的文件 ID"""
        self.pending_file_ids.discard(message_id)

    def is_bot_limited(self) -> bool:
        """检查 Bot 是否处于限流状态"""
        return self.is_limited


# 全局限流控制器实例
session_rate_limiter = SessionRateLimiter()
bot_rate_limiter = BotRateLimiter()
