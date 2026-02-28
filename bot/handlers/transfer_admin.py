# bot/handlers/transfer_admin.py
"""
搬运任务管理命令处理器（管理员）
"""

import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from functools import wraps

from database import User, UserRole
from database.crud import (
    create_transfer_task,
    get_transfer_task,
    get_transfer_tasks,
    update_transfer_task
)
from database.models import TaskStatus
from bot.states import TransferTaskStates
from utils.task_queue import task_queue
from config import settings

logger = logging.getLogger(__name__)

router = Router()


# 权限检查装饰器
def require_admin(func):
    """要求管理员权限的装饰器"""
    @wraps(func)
    async def wrapper(message: Message, user: User, *args, **kwargs):
        if user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
            await message.answer("❌ 权限不足，仅管理员可使用此功能")
            return
        return await func(message, user, *args, **kwargs)
    return wrapper


# ==================== 创建搬运任务 ====================

@router.message(Command("create_transfer"))
@require_admin
async def cmd_create_transfer(message: Message, user: User, state: FSMContext):
    """
    创建搬运任务

    命令: /create_transfer
    """
    await state.clear()

    logger.info(f"管理员 {user.id} 开始创建搬运任务")

    await message.answer(
        "📥 创建搬运任务\n\n"
        "请输入来源频道 ID 或用户名\n\n"
        "示例:\n"
        "• -1001234567890\n"
        "• @channel_username\n\n"
        "💡 提示: 发送 /cancel 可随时取消"
    )

    await state.set_state(TransferTaskStates.waiting_for_chat_id)


@router.message(TransferTaskStates.waiting_for_chat_id)
async def handle_chat_id(message: Message, state: FSMContext):
    """处理频道 ID 输入"""
    chat_input = message.text.strip()

    # 解析频道 ID
    if chat_input.startswith("@"):
        # 用户名格式
        chat_username = chat_input[1:]
        await state.update_data(
            source_chat_username=chat_username,
            source_chat_id=0  # 将在执行时解析
        )
    else:
        # 数字 ID 格式
        try:
            chat_id = int(chat_input)
            await state.update_data(
                source_chat_id=chat_id,
                source_chat_username=None
            )
        except ValueError:
            await message.answer("❌ 无效的频道 ID 格式")
            return

    # 显示过滤类型选择
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📷 仅图片", callback_data="filter_photo"),
            InlineKeyboardButton(text="🎬 仅视频", callback_data="filter_video")
        ],
        [
            InlineKeyboardButton(text="📦 全部媒体", callback_data="filter_all")
        ]
    ])

    await message.answer(
        "🔍 请选择要搬运的媒体类型:",
        reply_markup=keyboard
    )

    await state.set_state(TransferTaskStates.waiting_for_filter_type)


@router.callback_query(TransferTaskStates.waiting_for_filter_type, F.data.startswith("filter_"))
async def handle_filter_type(callback: CallbackQuery, state: FSMContext):
    """处理过滤类型选择"""
    filter_type = callback.data.replace("filter_", "")
    await state.update_data(filter_type=filter_type)

    await callback.message.answer(
        "🏷️ 请输入过滤关键词（可选）\n\n"
        "多个关键词用空格分隔\n"
        "示例: 猫咪 可爱 宠物\n\n"
        "发送 /skip 跳过此步骤"
    )

    await state.set_state(TransferTaskStates.waiting_for_keywords)
    await callback.answer()


@router.message(TransferTaskStates.waiting_for_keywords)
async def handle_keywords(message: Message, state: FSMContext):
    """处理关键词输入"""
    if message.text == "/skip":
        keywords = []
    else:
        keywords = message.text.strip().split()

    await state.update_data(filter_keywords=keywords)

    await message.answer(
        "📝 请输入任务名称\n\n"
        "示例: 猫咪频道搬运任务"
    )

    await state.set_state(TransferTaskStates.waiting_for_task_name)


@router.message(TransferTaskStates.waiting_for_task_name)
async def handle_task_name(message: Message, user: User, db: AsyncSession, state: FSMContext):
    """处理任务名称并创建任务"""
    task_name = message.text.strip()

    if not task_name or len(task_name) > 100:
        await message.answer("❌ 任务名称长度必须在 1-100 字符之间")
        return

    # 获取所有数据
    data = await state.get_data()

    try:
        # 创建搬运任务
        task = await create_transfer_task(
            db,
            task_name=task_name,
            source_chat_id=data.get("source_chat_id", 0),
            source_chat_username=data.get("source_chat_username"),
            filter_keywords=data.get("filter_keywords", []),
            filter_type=data.get("filter_type", "all"),
            created_by=user.id
        )

        # 添加到任务队列
        await task_queue.add_task(task.id)

        await state.clear()

        logger.info(
            f"管理员 {user.id} 创建搬运任务成功: task_id={task.id}, "
            f"name={task_name}, source={data.get('source_chat_username') or data.get('source_chat_id')}, "
            f"filter_type={data.get('filter_type', 'all')}"
        )

        # 显示任务信息
        filter_type_text = {
            "photo": "📷 仅图片",
            "video": "🎬 仅视频",
            "all": "📦 全部媒体"
        }.get(data.get("filter_type", "all"), "📦 全部媒体")

        keywords_text = " ".join(data.get("filter_keywords", [])) or "无"
        source_text = data.get("source_chat_username") or str(data.get("source_chat_id"))

        await message.answer(
            f"✅ 搬运任务创建成功！\n\n"
            f"📦 任务名称: {task_name}\n"
            f"📍 来源频道: {source_text}\n"
            f"🔍 媒体类型: {filter_type_text}\n"
            f"🏷️ 关键词: {keywords_text}\n"
            f"🆔 任务 ID: {task.id}\n\n"
            f"任务已加入队列，等待执行..."
        )

    except Exception as e:
        logger.error(f"管理员 {user.id} 创建搬运任务失败: {str(e)}", exc_info=True)
        await message.answer(f"❌ 创建任务失败: {str(e)}")


# ==================== 查看任务列表 ====================

@router.message(Command("list_tasks"))
@require_admin
async def cmd_list_tasks(message: Message, user: User, db: AsyncSession):
    """
    查看搬运任务列表

    命令: /list_tasks
    """
    tasks, total = await get_transfer_tasks(db, skip=0, limit=10)

    if not tasks:
        await message.answer("❌ 暂无搬运任务")
        return

    text = f"📋 搬运任务列表（共 {total} 个）\n\n"

    for idx, task in enumerate(tasks, 1):
        status_emoji = {
            TaskStatus.PENDING: "⏳",
            TaskStatus.RUNNING: "▶️",
            TaskStatus.PAUSED: "⏸️",
            TaskStatus.WAITING_BOT: "⏰",
            TaskStatus.COMPLETED: "✅",
            TaskStatus.FAILED: "❌"
        }.get(task.status, "❓")

        progress_text = ""
        if task.progress_total > 0:
            progress_percent = int(task.progress_current / task.progress_total * 100)
            progress_text = f" ({task.progress_current}/{task.progress_total} - {progress_percent}%)"

        text += (
            f"{idx}. {status_emoji} {task.task_name}\n"
            f"   🆔 ID: {task.id}\n"
            f"   📊 状态: {task.status.value}{progress_text}\n"
            f"   📅 创建: {task.created_at.strftime('%Y-%m-%d %H:%M')}\n\n"
        )

    if total > 10:
        text += f"💡 仅显示前 10 个任务"

    await message.answer(text)


# ==================== 查看任务详情 ====================

@router.message(Command("task_info"))
@require_admin
async def cmd_task_info(message: Message, user: User, db: AsyncSession):
    """
    查看任务详情

    命令: /task_info {task_id}
    """
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(
            "用法: /task_info {任务ID}\n"
            "示例: /task_info 1"
        )
        return

    try:
        task_id = int(args[1].strip())
    except ValueError:
        await message.answer("❌ 无效的任务 ID")
        return

    task = await get_transfer_task(db, task_id)
    if not task:
        await message.answer("❌ 任务不存在")
        return

    # 构建详情信息
    status_emoji = {
        TaskStatus.PENDING: "⏳ 等待执行",
        TaskStatus.RUNNING: "▶️ 执行中",
        TaskStatus.PAUSED: "⏸️ 已暂停",
        TaskStatus.WAITING_BOT: "⏰ 等待 Bot 恢复",
        TaskStatus.COMPLETED: "✅ 已完成",
        TaskStatus.FAILED: "❌ 失败"
    }.get(task.status, "❓ 未知")

    filter_type_text = {
        "photo": "📷 仅图片",
        "video": "🎬 仅视频",
        "all": "📦 全部媒体"
    }.get(task.filter_type, "📦 全部媒体")

    keywords_text = " ".join(task.filter_keywords or []) or "无"
    source_text = task.source_chat_username or str(task.source_chat_id)

    progress_text = f"{task.progress_current}/{task.progress_total}"
    if task.progress_total > 0:
        progress_percent = int(task.progress_current / task.progress_total * 100)
        progress_text += f" ({progress_percent}%)"

    text = (
        f"📋 任务详情\n\n"
        f"🆔 任务 ID: {task.id}\n"
        f"📦 任务名称: {task.task_name}\n"
        f"📊 状态: {status_emoji}\n"
        f"📍 来源频道: {source_text}\n"
        f"🔍 媒体类型: {filter_type_text}\n"
        f"🏷️ 关键词: {keywords_text}\n"
        f"📈 进度: {progress_text}\n"
        f"📅 创建时间: {task.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
    )

    if task.started_at:
        text += f"▶️ 开始时间: {task.started_at.strftime('%Y-%m-%d %H:%M:%S')}\n"

    if task.completed_at:
        text += f"✅ 完成时间: {task.completed_at.strftime('%Y-%m-%d %H:%M:%S')}\n"

    if task.error_message:
        text += f"\n❌ 错误信息: {task.error_message}\n"

    # 显示最近的日志
    if task.logs:
        text += f"\n📝 最近日志:\n"
        for log in task.logs[-5:]:
            text += f"• [{log.log_type}] {log.message}\n"

    await message.answer(text)


# ==================== 暂停/恢复任务 ====================

@router.message(Command("pause_task"))
@require_admin
async def cmd_pause_task(message: Message, user: User, db: AsyncSession):
    """
    暂停任务

    命令: /pause_task {task_id}
    """
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(
            "用法: /pause_task {任务ID}\n"
            "示例: /pause_task 1"
        )
        return

    try:
        task_id = int(args[1].strip())
    except ValueError:
        await message.answer("❌ 无效的任务 ID")
        return

    task = await get_transfer_task(db, task_id)
    if not task:
        await message.answer("❌ 任务不存在")
        return

    if task.status != TaskStatus.RUNNING:
        await message.answer("❌ 只能暂停正在执行的任务")
        return

    await update_transfer_task(db, task_id, status=TaskStatus.PAUSED)
    logger.info(f"管理员 {user.id} 暂停任务 {task_id}")
    await message.answer(f"✅ 任务 {task_id} 已暂停")


@router.message(Command("resume_task"))
@require_admin
async def cmd_resume_task(message: Message, user: User, db: AsyncSession):
    """
    恢复任务

    命令: /resume_task {task_id}
    """
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(
            "用法: /resume_task {任务ID}\n"
            "示例: /resume_task 1"
        )
        return

    try:
        task_id = int(args[1].strip())
    except ValueError:
        await message.answer("❌ 无效的任务 ID")
        return

    task = await get_transfer_task(db, task_id)
    if not task:
        await message.answer("❌ 任务不存在")
        return

    if task.status != TaskStatus.PAUSED:
        await message.answer("❌ 只能恢复已暂停的任务")
        return

    # 重新加入队列
    await task_queue.add_task(task_id)
    logger.info(f"管理员 {user.id} 恢复任务 {task_id}")
    await message.answer(f"✅ 任务 {task_id} 已恢复，重新加入队列")
