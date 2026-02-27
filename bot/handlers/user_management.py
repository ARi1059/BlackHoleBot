# bot/handlers/user_management.py
"""
用户管理处理器
"""

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from functools import wraps

from database import User, UserRole
from database.crud import (
    get_user_by_telegram_id,
    get_user_with_statistics,
    ban_user,
    create_admin_log
)

router = Router()


# 权限检查装饰器
def require_super_admin(func):
    """要求超级管理员权限的装饰器"""
    @wraps(func)
    async def wrapper(message: Message, user: User, *args, **kwargs):
        if user.role != UserRole.SUPER_ADMIN:
            await message.answer("❌ 权限不足，仅超级管理员可使用此功能")
            return
        return await func(message, user, *args, **kwargs)
    return wrapper


def require_admin(func):
    """要求管理员权限的装饰器"""
    @wraps(func)
    async def wrapper(message: Message, user: User, *args, **kwargs):
        if user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
            await message.answer("❌ 权限不足，仅管理员可使用此功能")
            return
        return await func(message, user, *args, **kwargs)
    return wrapper


# ==================== /ban 命令 ====================

@router.message(Command("ban"))
@require_super_admin
async def cmd_ban(message: Message, user: User, db: AsyncSession):
    """
    封禁用户

    命令: /ban {telegram_id} [原因]
    示例: /ban 123456789 违规发送垃圾信息
    """
    args = message.text.split(maxsplit=2)

    if len(args) < 2:
        await message.answer(
            "📝 使用方法:\n"
            "/ban {telegram_id} [原因]\n\n"
            "示例:\n"
            "/ban 123456789\n"
            "/ban 123456789 违规发送垃圾信息"
        )
        return

    try:
        target_telegram_id = int(args[1])
    except ValueError:
        await message.answer("❌ 无效的 Telegram ID")
        return

    ban_reason = args[2] if len(args) > 2 else "未提供原因"

    # 不能封禁自己
    if target_telegram_id == user.telegram_id:
        await message.answer("❌ 不能封禁自己")
        return

    # 查询目标用户
    target_user = await get_user_by_telegram_id(db, target_telegram_id)
    if not target_user:
        await message.answer("❌ 用户不存在，请确认该用户已使用过 Bot")
        return

    # 不能封禁其他超级管理员
    if target_user.role == UserRole.SUPER_ADMIN:
        await message.answer("❌ 不能封禁超级管理员")
        return

    # 检查是否已被封禁
    if target_user.is_banned:
        await message.answer("⚠️ 该用户已被封禁")
        return

    # 显示确认按钮
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ 确认封禁", callback_data=f"ban_confirm:{target_user.id}:{ban_reason}"),
            InlineKeyboardButton(text="❌ 取消", callback_data="ban_cancel")
        ]
    ])

    user_info = (
        f"👤 用户信息\n\n"
        f"ID: {target_user.telegram_id}\n"
        f"用户名: @{target_user.username or 'N/A'}\n"
        f"姓名: {target_user.first_name or ''} {target_user.last_name or ''}\n"
        f"角色: {target_user.role.value}\n\n"
        f"封禁原因: {ban_reason}\n\n"
        f"确认封禁此用户？"
    )

    await message.answer(user_info, reply_markup=keyboard)


@router.callback_query(F.data.startswith("ban_confirm:"))
async def handle_ban_confirm(callback: CallbackQuery, user: User, db: AsyncSession):
    """确认封禁用户"""
    try:
        _, target_user_id, ban_reason = callback.data.split(":", 2)
        target_user_id = int(target_user_id)
    except ValueError:
        await callback.answer("❌ 数据格式错误", show_alert=True)
        return

    # 执行封禁
    success = await ban_user(db, target_user_id, is_banned=True)
    if not success:
        await callback.answer("❌ 封禁失败", show_alert=True)
        return

    # 记录日志
    await create_admin_log(
        db,
        user_id=user.id,
        action="ban_user",
        details={
            "target_user_id": target_user_id,
            "reason": ban_reason
        }
    )

    # 获取被封禁用户信息
    from database.crud import get_user
    target_user = await get_user(db, target_user_id)

    # 发送通知给被封禁用户
    try:
        from bot.main import bot
        await bot.send_message(
            target_user.telegram_id,
            f"🚫 您已被管理员封禁\n\n"
            f"原因: {ban_reason}\n\n"
            f"如有疑问，请联系管理员"
        )
    except Exception:
        pass  # 发送失败不影响主流程

    await callback.message.edit_text(
        f"✅ 已封禁用户 {target_user.telegram_id}\n"
        f"原因: {ban_reason}"
    )
    await callback.answer()


@router.callback_query(F.data == "ban_cancel")
async def handle_ban_cancel(callback: CallbackQuery):
    """取消封禁"""
    await callback.message.edit_text("❌ 已取消封禁操作")
    await callback.answer()


# ==================== /unban 命令 ====================

@router.message(Command("unban"))
@require_super_admin
async def cmd_unban(message: Message, user: User, db: AsyncSession):
    """
    解封用户

    命令: /unban {telegram_id}
    示例: /unban 123456789
    """
    args = message.text.split()

    if len(args) < 2:
        await message.answer(
            "📝 使用方法:\n"
            "/unban {telegram_id}\n\n"
            "示例:\n"
            "/unban 123456789"
        )
        return

    try:
        target_telegram_id = int(args[1])
    except ValueError:
        await message.answer("❌ 无效的 Telegram ID")
        return

    # 查询目标用户
    target_user = await get_user_by_telegram_id(db, target_telegram_id)
    if not target_user:
        await message.answer("❌ 用户不存在")
        return

    # 检查是否已被封禁
    if not target_user.is_banned:
        await message.answer("⚠️ 该用户未被封禁")
        return

    # 执行解封
    success = await ban_user(db, target_user.id, is_banned=False)
    if not success:
        await message.answer("❌ 解封失败")
        return

    # 记录日志
    await create_admin_log(
        db,
        user_id=user.id,
        action="unban_user",
        details={"target_user_id": target_user.id}
    )

    # 发送通知给被解封用户
    try:
        from bot.main import bot
        await bot.send_message(
            target_user.telegram_id,
            "✅ 您已被解封，现在可以正常使用 Bot 了"
        )
    except Exception:
        pass  # 发送失败不影响主流程

    await message.answer(
        f"✅ 已解封用户 {target_user.telegram_id}\n"
        f"用户名: @{target_user.username or 'N/A'}"
    )


# ==================== /userinfo 命令 ====================

@router.message(Command("userinfo"))
@require_admin
async def cmd_userinfo(message: Message, user: User, db: AsyncSession):
    """
    查看用户信息

    命令: /userinfo {telegram_id}
    示例: /userinfo 123456789
    """
    args = message.text.split()

    if len(args) < 2:
        await message.answer(
            "📝 使用方法:\n"
            "/userinfo {telegram_id}\n\n"
            "示例:\n"
            "/userinfo 123456789"
        )
        return

    try:
        target_telegram_id = int(args[1])
    except ValueError:
        await message.answer("❌ 无效的 Telegram ID")
        return

    # 查询目标用户
    target_user = await get_user_by_telegram_id(db, target_telegram_id)
    if not target_user:
        await message.answer("❌ 用户不存在")
        return

    # 获取统计信息
    user_data = await get_user_with_statistics(db, target_user.id)
    statistics = user_data["statistics"]

    # 角色 emoji
    role_emoji = {
        UserRole.USER: "👤",
        UserRole.VIP: "💎",
        UserRole.ADMIN: "👨‍💼",
        UserRole.SUPER_ADMIN: "👑"
    }

    # 状态 emoji
    status_emoji = "🚫" if target_user.is_banned else "✅"
    status_text = "已封禁" if target_user.is_banned else "正常"

    info_text = (
        f"👤 用户信息\n\n"
        f"ID: {target_user.telegram_id}\n"
        f"用户名: @{target_user.username or 'N/A'}\n"
        f"姓名: {target_user.first_name or ''} {target_user.last_name or ''}\n"
        f"角色: {role_emoji.get(target_user.role, '❓')} {target_user.role.value}\n"
        f"状态: {status_emoji} {status_text}\n"
        f"注册时间: {target_user.created_at.strftime('%Y-%m-%d %H:%M')}\n"
        f"最后活跃: {target_user.last_active_at.strftime('%Y-%m-%d %H:%M')}\n\n"
        f"📊 统计信息\n"
        f"创建合集: {statistics['collections_created']} 个\n"
        f"上传媒体: {statistics['total_media_uploaded']} 个\n"
        f"搬运任务: {statistics['transfer_tasks_created']} 个"
    )

    # 添加快捷操作按钮（仅超级管理员）
    if user.role == UserRole.SUPER_ADMIN and target_user.id != user.id:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🚫 封禁" if not target_user.is_banned else "✅ 解封",
                    callback_data=f"quick_ban:{target_user.telegram_id}:{not target_user.is_banned}"
                )
            ]
        ])
        await message.answer(info_text, reply_markup=keyboard)
    else:
        await message.answer(info_text)


@router.callback_query(F.data.startswith("quick_ban:"))
async def handle_quick_ban(callback: CallbackQuery, user: User, db: AsyncSession):
    """快捷封禁/解封"""
    try:
        _, target_telegram_id, should_ban = callback.data.split(":")
        target_telegram_id = int(target_telegram_id)
        should_ban = should_ban == "True"
    except ValueError:
        await callback.answer("❌ 数据格式错误", show_alert=True)
        return

    # 查询目标用户
    target_user = await get_user_by_telegram_id(db, target_telegram_id)
    if not target_user:
        await callback.answer("❌ 用户不存在", show_alert=True)
        return

    # 执行操作
    success = await ban_user(db, target_user.id, is_banned=should_ban)
    if not success:
        await callback.answer("❌ 操作失败", show_alert=True)
        return

    # 记录日志
    await create_admin_log(
        db,
        user_id=user.id,
        action="ban_user" if should_ban else "unban_user",
        details={"target_user_id": target_user.id}
    )

    # 发送通知
    try:
        from bot.main import bot
        if should_ban:
            await bot.send_message(
                target_user.telegram_id,
                "🚫 您已被管理员封禁\n\n如有疑问，请联系管理员"
            )
        else:
            await bot.send_message(
                target_user.telegram_id,
                "✅ 您已被解封，现在可以正常使用 Bot 了"
            )
    except Exception:
        pass

    action_text = "封禁" if should_ban else "解封"
    await callback.answer(f"✅ 已{action_text}用户", show_alert=True)

    # 刷新用户信息显示
    await cmd_userinfo(callback.message, user, db)
