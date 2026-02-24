# utils/task_queue.py
"""
搬运任务队列管理器
"""

import asyncio
from typing import Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from database.crud import (
    get_transfer_task,
    update_transfer_task,
    create_task_log
)
from database.models import TaskStatus


class TaskQueue:
    """任务队列管理器 - 确保同时只有一个任务执行"""

    def __init__(self):
        self.current_task_id: Optional[int] = None
        self.queue: asyncio.Queue = asyncio.Queue()
        self.is_processing: bool = False
        self._process_task = None

    async def add_task(self, task_id: int):
        """
        添加任务到队列

        Args:
            task_id: 任务 ID
        """
        await self.queue.put(task_id)

        # 如果没有任务在执行，立即开始处理
        if not self.is_processing:
            self._process_task = asyncio.create_task(self._process_queue())

    async def _process_queue(self):
        """处理队列中的任务"""
        from utils.transfer_executor import transfer_executor

        self.is_processing = True

        while not self.queue.empty():
            task_id = await self.queue.get()
            self.current_task_id = task_id

            try:
                # 执行搬运任务
                await transfer_executor.execute_task(task_id)
            except Exception as e:
                print(f"Task {task_id} failed: {str(e)}")
            finally:
                self.queue.task_done()

        self.current_task_id = None
        self.is_processing = False

    def get_current_task_id(self) -> Optional[int]:
        """获取当前正在执行的任务 ID"""
        return self.current_task_id

    def get_queue_size(self) -> int:
        """获取队列中等待的任务数量"""
        return self.queue.qsize()

    async def pause_current_task(self, db: AsyncSession):
        """暂停当前任务"""
        if self.current_task_id:
            await update_transfer_task(
                db,
                self.current_task_id,
                status=TaskStatus.PAUSED
            )
            await create_task_log(
                db,
                self.current_task_id,
                "info",
                "任务已暂停"
            )

    async def resume_task(self, task_id: int):
        """恢复任务"""
        await self.add_task(task_id)


# 全局任务队列实例
task_queue = TaskQueue()
