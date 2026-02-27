# bot/handlers/transfer_approve.py
"""
搬运任务审核与确认功能
"""

import json
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from functools import wraps

from database import User, UserRole, AccessLevel
from database.crud import (
    get_transfer_task,
    create_collection,
    create_media,
    update_collection,
    update_transfer_task,
    create_admin_log
)
from database.models import TaskStatus
from bot.states import ApproveTaskStates
from utils.deep_link import generate_unique_deep_link_code, create_deep_link
from utils.channel_sender import send_collection_to_channel
from config import settings

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


# ==================== 审核任务 ====================

@router.message(Command("approve_task"))
@require_admin
async def cmd_approve_task(message: Message, user: User, db: AsyncSession, redis_client):
    """
    审核搬运任务

    命令: /approve_task {task_id}
    """
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(
            "用法: /approve_task {任务ID}\n"
            "示例: /approve_task 1"
        )
        return

    try:
        task_id = int(args[1].strip())
    except ValueError:
        await message.answer("❌ 无效的任务 ID")
        return

    # 获取任务
    task = await get_transfer_task(db, task_id)
    if not task:
        await message.answer("❌ 任务不存在")
        return

    if task.status != TaskStatus.COMPLETED:
        await message.answer("❌ 只能审核已完成的任务")
        return

    # 从 Redis 获取文件列表
    redis_key = f"task:{task_id}:files"
    file_count = await redis_client.llen(redis_key)

    if file_count == 0:
        await message.answer("❌ 任务没有搬运到任何文件")
        return

    # 获取前 5 个文件作为预览
    preview_files = await redis_client.lrange(redis_key, 0, 4)
    preview_text = f"📋 任务预览\n\n"
    preview_text += f"📦 任务名称: {task.task_name}\n"
    preview_text += f"📊 文件数量: {file_count} 个\n\n"
    preview_text += f"前 5 个文件:\n"

    for idx, file_data_str in enumerate(preview_files, 1):
        file_data = json.loads(file_data_str)
        file_type_emoji = "📷" if file_data["file_type"] == "photo" else "🎬"
        preview_text += f"{idx}. {file_type_emoji} {file_data['file_type']}\n"

    await message.answer(preview_text)

    # 保存任务 ID 到状态
    await message.answer(
        "📝 请输入合集名称\n"
        "（建议简短明了，如：猫咪合集）"
    )

    state = FSMContext(storage=message.bot.fsm.storage, key=message.bot.fsm.resolve_context_key(message))
    await state.set_state(ApproveTaskStates.waiting_for_name)
    await state.update_data(task_id=task_id)


@router.message(ApproveTaskStates.waiting_for_name)
async def handle_approve_name(message: Message, state: FSMContext):
    """处理合集名称"""
    name = message.text.strip()

    # 验证
    if not name or len(name) > 100:
        await message.answer("❌ 名称长度必须在 1-100 字符之间")
        return

    if any(char in name for char in '<>/\\|:*?"'):
        await message.answer("❌ 名称不能包含特殊字符: < > / \\ | : * ? \"")
        return

    await state.update_data(name=name)

    await message.answer(
        "📝 请输入合集描述（可选）\n\n"
        "发送 /skip 跳过此步骤"
    )

    await state.set_state(ApproveTaskStates.waiting_for_description)


@router.message(ApproveTaskStates.waiting_for_description)
async def handle_approve_description(message: Message, state: FSMContext):
    """处理合集描述"""
    if message.text == "/skip":
        description = ""
    else:
        description = message.text.strip()
        if len(description) > 500:
            await message.answer("❌ 描述长度不能超过 500 字符")
            return

    await state.update_data(description=description)

    await message.answer(
        "🏷️ 请输入标签（用空格分隔，可选）\n\n"
        "示例: 猫咪 可爱 宠物\n"
        "发送 /skip 跳过此步骤"
    )

    await state.set_state(ApproveTaskStates.waiting_for_tags)


@router.message(ApproveTaskStates.waiting_for_tags)
async def handle_approve_tags(message: Message, state: FSMContext):
    """处理标签"""
    if message.text == "/skip":
        tags = []
    else:
        tags = message.text.strip().split()

        # 验证
        if len(tags) > 10:
            await message.answer("❌ 标签数量不能超过 10 个")
            return

        for tag in tags:
            if len(tag) > 20:
                await message.answer(f"❌ 标签 '{tag}' 长度超过 20 字符")
                return

    await state.update_data(tags=tags)

    # 显示权限选择按钮
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🌍 公开", callback_data="approve_access_public"),
            InlineKeyboardButton(text="💎 VIP", callback_data="approve_access_vip")
        ]
    ])

    await message.answer(
        "🔒 请选择访问权限:",
        reply_markup=keyboard
    )

    await state.set_state(ApproveTaskStates.waiting_for_permission)


@router.callback_query(ApproveTaskStates.waiting_for_permission, F.data.startswith("approve_access_"))
async def handle_approve_permission(callback: CallbackQuery, user: User, db: AsyncSession, redis_client, state: FSMContext):
    """处理权限选择并创建合集"""
    access_level = AccessLevel.PUBLIC if callback.data == "approve_access_public" else AccessLevel.VIP

    # 获取所有数据
    data = await state.get_data()
    task_id = data.get("task_id")

    try:
        # 从 Redis 获取文件列表
        redis_key = f"task:{task_id}:files"
        file_data_list = await redis_client.lrange(redis_key, 0, -1)

        if not file_data_list:
            await callback.message.answer("❌ 没有找到文件数据")
            await callback.answer("❌ 创建失败", show_alert=True)
            return

        media_list = [json.loads(data_str) for data_str in file_data_list]

        # 生成深链接码
        deep_link_code = await generate_unique_deep_link_code(db)

        # 创建合集
        collection = await create_collection(
            db,
            name=data["name"],
            deep_link_code=deep_link_code,
            description=data.get("description", ""),
            tags=data.get("tags", []),
            access_level=access_level,
            created_by=user.id
        )

        # 批量插入媒体
        for index, media_data in enumerate(media_list):
            await create_media(
                db,
                collection_id=collection.id,
                file_id=media_data["file_id"],
                file_unique_id=media_data["file_unique_id"],
                file_type=media_data["file_type"],
                order_index=index,
                file_size=media_data.get("file_size"),
                caption=media_data.get("caption")
            )

        # 更新合集媒体数量
        await update_collection(db, collection.id, media_count=len(media_list))

        # 清空 Redis
        await redis_client.delete(redis_key)

        # 更新任务状态
        await update_transfer_task(
            db,
            task_id,
            status=TaskStatus.COMPLETED
        )

        # 记录日志
        await create_admin_log(
            db,
            user_id=user.id,
            action="approve_transfer_task",
            details={
                "task_id": task_id,
                "collection_name": collection.name,
                "media_count": len(media_list),
                "access_level": access_level.value
            }
        )

        # 发送到私有频道
        await send_collection_to_channel(callback.bot, media_list, collection.name)

        # 清除状态
        await state.clear()

        # 发送成功消息
        access_emoji = "🌍" if access_level == AccessLevel.PUBLIC else "💎"
        deep_link = create_deep_link(settings.BOT_USERNAME, deep_link_code)

        await callback.message.answer(
            f"✅ 合集创建成功！\n\n"
            f"📦 合集名称: {collection.name}\n"
            f"🔗 深链接: {deep_link}\n"
            f"📊 媒体数量: {len(media_list)}\n"
            f"🔒 访问权限: {access_emoji} {access_level.value.upper()}\n\n"
            f"搬运任务已完成！"
        )

        await callback.answer("✅ 合集创建成功")

    except Exception as e:
        await callback.message.answer(f"❌ 创建失败: {str(e)}")
        await callback.answer("❌ 创建失败", show_alert=True)


# ==================== 拒绝任务 ====================

@router.message(Command("reject_task"))
@require_admin
async def cmd_reject_task(message: Message, user: User, db: AsyncSession, redis_client):
    """
    拒绝搬运任务

    命令: /reject_task {task_id}
    """
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(
            "用法: /reject_task {任务ID}\n"
            "示例: /reject_task 1"
        )
        return

    try:
        task_id = int(args[1].strip())
    except ValueError:
        await message.answer("❌ 无效的任务 ID")
        return

    # 获取任务
    task = await get_transfer_task(db, task_id)
    if not task:
        await message.answer("❌ 任务不存在")
        return

    if task.status != TaskStatus.COMPLETED:
        await message.answer("❌ 只能拒绝已完成的任务")
        return

    # 清空 Redis 中的文件
    redis_key = f"task:{task_id}:files"
    await redis_client.delete(redis_key)

    # 更新任务状态
    await update_transfer_task(
        db,
        task_id,
        status=TaskStatus.FAILED,
        error_message="任务被管理员拒绝"
    )

    # 记录日志
    await create_admin_log(
        db,
        user_id=user.id,
        action="reject_transfer_task",
        details={"task_id": task_id}
    )

    await message.answer(f"✅ 任务 {task_id} 已拒绝，文件已清理")
