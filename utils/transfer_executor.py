# utils/transfer_executor.py
"""
搬运任务执行器
"""

import asyncio
import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
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


# 配置日志
logger = logging.getLogger(__name__)


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
                    logger.error(f"任务 {task_id} 不存在")
                    return

                logger.info(
                    f"[任务 {task_id}] 开始执行: name={task.task_name}, "
                    f"source={task.source_chat_username or task.source_chat_id}, "
                    f"filter_type={task.filter_type}"
                )

                # 更新任务状态为运行中
                await update_transfer_task(
                    db,
                    task_id,
                    status=TaskStatus.RUNNING,
                    started_at=datetime.now()
                )

                # 设置当前任务 ID 到 Redis，供 Bot 端使用
                if self.redis_client:
                    await self.redis_client.set("current_transfer_task_id", str(task_id))
                    logger.info(f"已设置当前任务 ID 到 Redis: {task_id}")

                await create_task_log(
                    db,
                    task_id,
                    "info",
                    f"开始执行搬运任务: {task.task_name}"
                )

                # 获取可用的 session 账号
                session_account = await session_manager.get_next_available_session(db)
                if not session_account:
                    logger.warning(f"[任务 {task_id}] 没有可用的 Session 账号，任务暂停")
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
                logger.info(f"[任务 {task_id}] 使用 Session {session_account.id} 执行搬运")
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

                # 延迟 10 分钟后清除 Redis 中的任务 ID，避免 Bot 接收延迟消息时找不到 task_id
                logger.info(f"任务完成，将在 10 分钟后清除 Redis 中的任务 ID")
                await asyncio.sleep(600)
                if self.redis_client:
                    await self.redis_client.delete("current_transfer_task_id")
                    logger.info(f"延迟删除 Redis 中的任务 ID")

            except Exception as e:
                logger.error(f"[任务 {task_id}] 执行失败: {str(e)}", exc_info=True)
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

                # 延迟 10 分钟后清除 Redis 中的任务 ID，避免 Bot 接收延迟消息时找不到 task_id
                logger.info(f"任务失败，将在 10 分钟后清除 Redis 中的任务 ID")
                await asyncio.sleep(600)
                if self.redis_client:
                    await self.redis_client.delete("current_transfer_task_id")
                    logger.info(f"延迟删除 Redis 中的任务 ID")
            finally:
                break

    class _SwitchSessionSignal(Exception):
        """切换 Session 时的内部信号，用于跳出 iter_messages 循环"""
        def __init__(self, last_message_id: int):
            self.last_message_id = last_message_id

    async def _transfer_media(
        self,
        db: AsyncSession,
        task,
        session_account
    ):
        """
        从频道转发媒体到 Bot

        通过外层循环管理 Session 切换：当需要切换账号时，跳出内层的
        iter_messages 循环，用新客户端从断点消息 ID 继续遍历。

        Args:
            db: 数据库 session
            task: 搬运任务对象
            session_account: Session 账号对象
        """
        # 创建 Redis key 用于存储文件
        redis_key = f"task:{task.id}:files"
        await update_transfer_task(db, task.id, temp_redis_key=redis_key)

        # 全局计数器，跨 Session 保持
        transferred_count = 0
        matched_count = 0
        message_count = 0
        offset_id = 0  # 断点消息 ID，0 表示从最新消息开始
        finished = False  # 是否遍历完成

        logger.info(f"[任务 {task.id}] 开始遍历频道消息, 频道: {task.source_chat_username or task.source_chat_id}")

        while not finished:
            # 获取当前 Session 的客户端
            client = await session_manager.get_client(db, session_account.id)
            if not client:
                raise Exception(f"无法创建 Telethon 客户端 (Session {session_account.id})")

            try:
                # 获取频道实体（每个客户端需要独立获取）
                try:
                    if task.source_chat_username:
                        channel = await client.get_entity(task.source_chat_username)
                    else:
                        channel = await client.get_entity(task.source_chat_id)
                except (ChannelPrivateError, ChatAdminRequiredError):
                    raise Exception("无法访问频道，请确保账号已加入该频道")

                # 使用当前客户端遍历消息
                iter_kwargs = {"limit": None, "reverse": False}
                if offset_id:
                    iter_kwargs["offset_id"] = offset_id
                    logger.info(f"[任务 {task.id}] 从消息 ID {offset_id} 继续遍历 (Session {session_account.id})")

                async for message in client.iter_messages(channel, **iter_kwargs):
                    message_count += 1

                    # 检查 Bot 是否限流
                    while bot_rate_limiter.is_bot_limited():
                        await asyncio.sleep(1)

                    # 应用过滤条件
                    try:
                        if not await self._apply_filters(message, task):
                            continue
                    except self.StopIterationSignal as e:
                        logger.info(f"[任务 {task.id}] 停止遍历: {str(e)}, 已遍历 {message_count} 条消息, 已转发 {transferred_count} 个文件")
                        await create_task_log(
                            db,
                            task.id,
                            "info",
                            f"已到达日期范围下限，提前终止遍历。已转发 {transferred_count} 个文件"
                        )
                        finished = True
                        break

                    # 匹配成功，计数并更新总数
                    matched_count += 1
                    await update_transfer_task(db, task.id, progress_total=matched_count)

                    # 检查 session 限流
                    if await session_rate_limiter.check_and_update(db, session_account.id, task.id):
                        await create_task_log(
                            db, task.id, "session_switch",
                            f"Session {session_account.id} 达到限流阈值，尝试切换账号"
                        )
                        # 抛出信号跳出 iter_messages 循环，记录当前消息 ID
                        raise self._SwitchSessionSignal(message.id)

                    # 转发消息到 Bot
                    try:
                        await client.forward_messages(
                            entity=settings.BOT_USERNAME,
                            messages=message.id,
                            from_peer=channel
                        )

                        transferred_count += 1
                        await update_transfer_task(
                            db, task.id, progress_current=transferred_count
                        )

                        if transferred_count % 10 == 0:
                            await create_task_log(
                                db, task.id, "info",
                                f"已转发 {transferred_count}/{matched_count} 个文件"
                            )

                    except FloodWaitError as e:
                        await create_task_log(
                            db, task.id, "rate_limit",
                            f"遇到 API 限流，需要等待 {e.seconds} 秒"
                        )
                        await session_manager.set_session_cooldown(
                            db, session_account.id,
                            cooldown_minutes=int(e.seconds / 60) + 1
                        )
                        # 抛出信号跳出循环，从当前消息重试
                        raise self._SwitchSessionSignal(message.id)

                    except Exception as e:
                        await create_task_log(
                            db, task.id, "error",
                            f"转发消息失败: {str(e)}"
                        )
                else:
                    # for 循环正常结束（没有 break），说明所有消息遍历完毕
                    finished = True

            except self._SwitchSessionSignal as sig:
                # 需要切换 Session，记录断点
                offset_id = sig.last_message_id

                # 断开当前客户端
                await session_manager.disconnect_client(session_account.id)

                # 获取下一个可用 Session
                next_session = await session_manager.get_next_available_session(db)
                if not next_session:
                    await update_transfer_task(db, task.id, status=TaskStatus.PAUSED)
                    await create_task_log(
                        db, task.id, "warning",
                        "所有 Session 都在冷却中，任务已暂停"
                    )
                    return

                session_account = next_session
                await update_transfer_task(db, task.id, session_account_id=session_account.id)
                await create_task_log(
                    db, task.id, "session_switch",
                    f"已切换到 Session {session_account.id}，从消息 ID {offset_id} 继续"
                )

            except self.StopIterationSignal:
                finished = True

            finally:
                # 每轮循环结束都断开当前客户端
                if finished:
                    await session_manager.disconnect_client(session_account.id)

    class StopIterationSignal(Exception):
        """用于提前终止遍历的信号"""
        pass

    async def _apply_filters(self, message, task) -> bool:
        """
        应用过滤条件

        Args:
            message: Telegram 消息对象
            task: 搬运任务对象

        Returns:
            True 表示通过过滤，False 表示不通过

        Raises:
            StopIterationSignal: 当确定后续消息都不符合条件时，抛出此异常提前终止遍历
        """
        try:
            # 获取消息基本信息
            message_id = message.id
            message_date = getattr(message, 'date', None)
            has_photo = bool(message.photo)
            has_video = bool(message.video)

            # 打印入参和消息信息
            logger.info(
                f"[任务 {task.id}] 检查消息 ID={message_id}, "
                f"日期={message_date}, photo={has_photo}, video={has_video}, "
                f"过滤条件: type={task.filter_type}, "
                f"date_from={task.filter_date_from}, date_to={task.filter_date_to}, "
                f"keywords={task.filter_keywords}"
            )

            # 媒体类型过滤
            filter_type = task.filter_type

            if filter_type == "photo" and not message.photo:
                logger.info(f"[任务 {task.id}] 消息 {message_id} 不通过: 需要图片但不是图片")
                return False
            if filter_type == "video" and not message.video:
                logger.info(f"[任务 {task.id}] 消息 {message_id} 不通过: 需要视频但不是视频")
                return False
            if filter_type == "all" and not (message.photo or message.video):
                logger.info(f"[任务 {task.id}] 消息 {message_id} 不通过: 需要媒体但没有图片或视频")
                return False

            logger.info(f"[任务 {task.id}] 消息 {message_id} 通过媒体类型过滤")

            logger.info(f"[任务 {task.id}] 消息 {message_id} 通过媒体类型过滤")

            # 日期范围过滤 - 优先执行，减少后续处理
            # 从最新消息开始遍历（reverse=False），先判断截止日期，再判断起始日期
            if task.filter_date_from or task.filter_date_to:
                message_datetime = getattr(message, 'date', None)
                if message_datetime is None:
                    # 没有日期信息，跳过
                    logger.info(f"[任务 {task.id}] 消息 {message_id} 不通过: 没有日期信息")
                    return False

                # Telegram 消息时间是 UTC（offset-aware），转换为 offset-naive 后再转北京时间
                message_datetime_naive = message_datetime.replace(tzinfo=None)
                beijing_time = message_datetime_naive + timedelta(hours=8)
                message_date = beijing_time.date()

                logger.info(
                    f"[任务 {task.id}] 消息 {message_id} 日期检查: "
                    f"UTC={message_datetime}, 北京时间={beijing_time}, 日期={message_date}"
                )

                # 从最新消息开始遍历，先判断截止日期
                if task.filter_date_to:
                    filter_to_date = task.filter_date_to.date() if hasattr(task.filter_date_to, 'date') else task.filter_date_to
                    if message_date > filter_to_date:
                        # 消息日期晚于截止日期，跳过当前消息，继续遍历
                        logger.info(
                            f"[任务 {task.id}] 消息 {message_id} 不通过: "
                            f"消息日期 {message_date} 晚于截止日期 {filter_to_date}"
                        )
                        return False

                # 再判断起始日期
                if task.filter_date_from:
                    filter_from_date = task.filter_date_from.date() if hasattr(task.filter_date_from, 'date') else task.filter_date_from
                    if message_date < filter_from_date:
                        # 消息日期早于起始日期，后续消息会更早，直接终止遍历
                        logger.info(
                            f"[任务 {task.id}] 消息 {message_id} 触发终止: "
                            f"消息日期 {message_date} 早于起始日期 {filter_from_date}"
                        )
                        raise self.StopIterationSignal("消息日期早于起始日期，终止遍历")

                # 消息在日期范围内
                logger.info(f"[任务 {task.id}] 消息 {message_id} 通过日期过滤")

            # 关键词过滤 - 在日期过滤之后执行
            if task.filter_keywords:
                # Telethon Message 对象的文本属性：
                # - text: 纯文本消息的文本
                # - message: 媒体消息的文本（相当于 Bot API 的 caption）
                text = getattr(message, 'text', None) or getattr(message, 'message', None) or ""

                # 如果消息没有文本，直接跳过
                if not text:
                    logger.info(f"[任务 {task.id}] 消息 {message_id} 不通过: 需要关键词但消息没有提取到文本")
                    return False

                # 检查关键词是否在文本中（模糊匹配）
                if not any(keyword in text for keyword in task.filter_keywords):
                    logger.info(
                        f"[任务 {task.id}] 消息 {message_id} 不通过: "
                        f"文本中不包含关键词 {task.filter_keywords}"
                    )
                    return False

                logger.info(f"[任务 {task.id}] 消息 {message_id} 通过关键词过滤")

            logger.info(f"[任务 {task.id}] ✅ 消息 {message_id} 通过所有过滤条件")
            return True

        except self.StopIterationSignal:
            # 重新抛出停止信号
            raise
        except Exception as e:
            logger.error(f"_apply_filters 异常: {str(e)}", exc_info=True)
            raise


# 全局执行器实例
transfer_executor = TransferExecutor()
