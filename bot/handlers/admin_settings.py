# bot/handlers/admin_settings.py
"""
管理员设置处理器
"""

import asyncio
import logging
from datetime import datetime
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter, TelegramBadRequest
from sqlalchemy.ext.asyncio import AsyncSession

from database import User, UserRole
from database.crud import (
    get_setting,
    set_setting,
    get_users,
    create_broadcast_log,
    update_broadcast_log
)
from bot.states import AdminSettingsStates
from bot.keyboards import create_confirm_keyboard

router = Router()
logger = logging.getLogger(__name__)

# 广播限流配置
BROADCAST_RATE = 0.05  # 每条消息间隔 50ms，即每秒 20 条


def check_admin_permission(user: User) -> bool:
    """检查是否有管理员权限"""
    return user.role in [UserRole.ADMIN, UserRole.SUPER_ADMIN]


# ==================== 设置欢迎消息 ====================

@router.message(Command("set_welcome"))
async def cmd_set_welcome(message: Message, user: User, state: FSMContext, db: AsyncSession):
    """设置欢迎消息"""
    # 检查权限
    if not check_admin_permission(user):
        await message.answer("❌ 此命令仅限管理员使用")
        return

    # 获取当前欢迎消息
    current_message = await get_setting(db, "welcome_message")
    if not current_message:
        current_message = "（未设置）"

    await message.answer(
        f"📝 <b>当前欢迎消息：</b>\n\n"
        f"{current_message}\n\n"
        f"━━━━━━━━━━━━━━━━\n\n"
        f"请发送新的欢迎消息：\n"
        f"• 支持文本（HTML 格式）\n"
        f"• 支持图片/视频（可附带文字说明）\n"
        f"• 支持按钮（使用 inline keyboard）\n\n"
        f"发送 /cancel 取消设置",
        parse_mode="HTML"
    )

    # 设置状态
    await state.set_state(AdminSettingsStates.waiting_welcome_message)


@router.message(AdminSettingsStates.waiting_welcome_message, Command("cancel"))
async def cancel_set_welcome(message: Message, state: FSMContext):
    """取消设置欢迎消息"""
    await state.clear()
    await message.answer("❌ 已取消设置欢迎消息")


@router.message(AdminSettingsStates.waiting_welcome_message)
async def process_welcome_message(message: Message, state: FSMContext, db: AsyncSession):
    """处理欢迎消息"""
    import json

    # 提取消息数据
    message_data = {}

    if message.photo:
        # 图片消息
        message_data['type'] = 'photo'
        message_data['file_id'] = message.photo[-1].file_id
        message_data['caption'] = message.caption or ""
    elif message.video:
        # 视频消息
        message_data['type'] = 'video'
        message_data['file_id'] = message.video.file_id
        message_data['caption'] = message.caption or ""
    elif message.text:
        # 纯文本消息
        message_data['type'] = 'text'
        message_data['text'] = message.text
    else:
        await message.answer("❌ 不支持的消息类型，请发送文本、图片或视频")
        return

    # 保存消息数据到状态
    await state.update_data(message_data=message_data)

    # 询问是否添加按钮
    await message.answer(
        "✅ 消息内容已接收！\n\n"
        "是否需要添加内联按钮？\n\n"
        "• 发送 /skip 跳过按钮设置\n"
        "• 发送按钮配置（每行一个按钮）\n\n"
        "格式：<code>按钮文字|链接</code>\n"
        "示例：\n"
        "<code>访问网站|https://example.com\n"
        "联系客服|https://t.me/support</code>",
        parse_mode="HTML"
    )

    await state.set_state(AdminSettingsStates.waiting_welcome_buttons)


@router.message(AdminSettingsStates.waiting_welcome_buttons, Command("skip"))
async def skip_welcome_buttons(message: Message, state: FSMContext, db: AsyncSession):
    """跳过按钮设置"""
    import json

    # 获取消息数据
    data = await state.get_data()
    message_data = data.get('message_data', {})

    # 保存到数据库（JSON 格式）
    await set_setting(db, "welcome_message", json.dumps(message_data, ensure_ascii=False))

    await message.answer(
        f"✅ <b>欢迎消息已更新！</b>\n\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"<b>消息类型：</b>{message_data['type']}\n"
        f"<b>按钮：</b>无",
        parse_mode="HTML"
    )

    await state.clear()


@router.message(AdminSettingsStates.waiting_welcome_buttons)
async def process_welcome_buttons(message: Message, state: FSMContext, db: AsyncSession):
    """处理欢迎消息按钮"""
    import json
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    # 获取消息数据
    data = await state.get_data()
    message_data = data.get('message_data', {})

    # 解析按钮配置
    try:
        lines = message.text.strip().split('\n')
        buttons = []

        for line in lines:
            if '|' not in line:
                await message.answer("❌ 格式错误！每行格式应为：<code>按钮文字|链接</code>", parse_mode="HTML")
                return

            text, url = line.split('|', 1)
            text = text.strip()
            url = url.strip()

            if not text or not url:
                await message.answer("❌ 按钮文字和链接不能为空", parse_mode="HTML")
                return

            buttons.append([InlineKeyboardButton(text=text, url=url)])

        # 创建键盘
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        message_data['reply_markup'] = keyboard.model_dump()

        # 保存到数据库
        await set_setting(db, "welcome_message", json.dumps(message_data, ensure_ascii=False))

        await message.answer(
            f"✅ <b>欢迎消息已更新！</b>\n\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"<b>消息类型：</b>{message_data['type']}\n"
            f"<b>按钮数量：</b>{len(buttons)}",
            parse_mode="HTML"
        )

        await state.clear()

    except Exception as e:
        logger.error(f"解析按钮配置失败: {e}")
        await message.answer("❌ 解析按钮配置失败，请检查格式")


# ==================== 广播消息 ====================

@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message, user: User, state: FSMContext):
    """开始广播消息"""
    # 检查权限
    if not check_admin_permission(user):
        await message.answer("❌ 此命令仅限管理员使用")
        return

    await message.answer(
        "📢 <b>广播消息设置</b>\n\n"
        "请发送要广播的内容：\n"
        "• 支持文本（HTML 格式）\n"
        "• 支持图片/视频（可附带文字说明）\n"
        "• 支持按钮（使用 inline keyboard）\n\n"
        "发送 /cancel 取消",
        parse_mode="HTML"
    )

    # 设置状态
    await state.set_state(AdminSettingsStates.waiting_broadcast_message)


@router.message(AdminSettingsStates.waiting_broadcast_message, Command("cancel"))
async def cancel_broadcast(message: Message, state: FSMContext):
    """取消广播"""
    await state.clear()
    await message.answer("❌ 已取消广播")


@router.message(AdminSettingsStates.waiting_broadcast_message)
async def process_broadcast_message(message: Message, user: User, state: FSMContext, db: AsyncSession):
    """处理广播消息"""
    # 提取消息数据
    message_data = {}

    if message.photo:
        # 图片消息
        message_data['type'] = 'photo'
        message_data['file_id'] = message.photo[-1].file_id
        message_data['caption'] = message.caption or ""
    elif message.video:
        # 视频消息
        message_data['type'] = 'video'
        message_data['file_id'] = message.video.file_id
        message_data['caption'] = message.caption or ""
    elif message.text:
        # 纯文本消息
        message_data['type'] = 'text'
        message_data['text'] = message.text
    else:
        await message.answer("❌ 不支持的消息类型，请发送文本、图片或视频")
        return

    # 保存消息数据到状态
    await state.update_data(message_data=message_data)

    # 询问是否添加按钮
    await message.answer(
        "✅ 消息内容已接收！\n\n"
        "是否需要添加内联按钮？\n\n"
        "• 发送 /skip 跳过按钮设置\n"
        "• 发送按钮配置（每行一个按钮）\n\n"
        "格式：<code>按钮文字|链接</code>\n"
        "示例：\n"
        "<code>访问网站|https://example.com\n"
        "联系客服|https://t.me/support</code>",
        parse_mode="HTML"
    )

    await state.set_state(AdminSettingsStates.waiting_broadcast_buttons)


@router.message(AdminSettingsStates.waiting_broadcast_buttons, Command("skip"))
async def skip_broadcast_buttons(message: Message, state: FSMContext, db: AsyncSession):
    """跳过广播按钮设置"""
    # 获取消息数据
    data = await state.get_data()
    message_data = data.get('message_data', {})

    # 获取用户总数
    users, total_users = await get_users(db, skip=0, limit=999999)

    if total_users == 0:
        await message.answer("❌ 没有用户可以广播")
        await state.clear()
        return

    # 更新状态数据
    await state.update_data(total_users=total_users)

    # 显示预览和确认按钮
    preview_text = f"📋 <b>广播预览：</b>\n\n"

    if message_data['type'] == 'text':
        preview_text += f"{message_data['text']}\n\n"
    else:
        preview_text += f"[{message_data['type'].upper()}]\n"
        if message_data.get('caption'):
            preview_text += f"{message_data['caption']}\n\n"

    preview_text += f"━━━━━━━━━━━━━━━━\n"
    preview_text += f"目标用户：<b>{total_users}</b> 人\n"
    preview_text += f"按钮：无"

    # 创建确认键盘
    keyboard = create_confirm_keyboard()

    await message.answer(
        preview_text,
        parse_mode="HTML",
        reply_markup=keyboard
    )

    # 设置状态
    await state.set_state(AdminSettingsStates.confirming_broadcast)


@router.message(AdminSettingsStates.waiting_broadcast_buttons)
async def process_broadcast_buttons(message: Message, state: FSMContext, db: AsyncSession):
    """处理广播消息按钮"""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    # 获取消息数据
    data = await state.get_data()
    message_data = data.get('message_data', {})

    # 解析按钮配置
    try:
        lines = message.text.strip().split('\n')
        buttons = []

        for line in lines:
            if '|' not in line:
                await message.answer("❌ 格式错误！每行格式应为：<code>按钮文字|链接</code>", parse_mode="HTML")
                return

            text, url = line.split('|', 1)
            text = text.strip()
            url = url.strip()

            if not text or not url:
                await message.answer("❌ 按钮文字和链接不能为空", parse_mode="HTML")
                return

            buttons.append([InlineKeyboardButton(text=text, url=url)])

        # 创建键盘
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        message_data['reply_markup'] = keyboard

        # 获取用户总数
        users, total_users = await get_users(db, skip=0, limit=999999)

        if total_users == 0:
            await message.answer("❌ 没有用户可以广播")
            await state.clear()
            return

        # 更新状态数据
        await state.update_data(message_data=message_data, total_users=total_users)

        # 显示预览和确认按钮
        preview_text = f"📋 <b>广播预览：</b>\n\n"

        if message_data['type'] == 'text':
            preview_text += f"{message_data['text']}\n\n"
        else:
            preview_text += f"[{message_data['type'].upper()}]\n"
            if message_data.get('caption'):
                preview_text += f"{message_data['caption']}\n\n"

        preview_text += f"━━━━━━━━━━━━━━━━\n"
        preview_text += f"目标用户：<b>{total_users}</b> 人\n"
        preview_text += f"按钮数量：<b>{len(buttons)}</b>"

        # 创建确认键盘
        confirm_keyboard = create_confirm_keyboard()

        await message.answer(
            preview_text,
            parse_mode="HTML",
            reply_markup=confirm_keyboard
        )

        # 设置状态
        await state.set_state(AdminSettingsStates.confirming_broadcast)

    except Exception as e:
        logger.error(f"解析按钮配置失败: {e}")
        await message.answer("❌ 解析按钮配置失败，请检查格式")


@router.callback_query(AdminSettingsStates.confirming_broadcast, F.data == "confirm")
async def confirm_broadcast(callback: CallbackQuery, user: User, state: FSMContext, db: AsyncSession):
    """确认并开始广播"""
    await callback.answer()

    # 获取消息数据
    data = await state.get_data()
    message_data = data['message_data']
    total_users = data['total_users']

    # 创建广播日志
    log_id = await create_broadcast_log(
        db=db,
        admin_id=user.id,
        message_type=message_data['type'],
        message_text=message_data.get('text') or message_data.get('caption'),
        file_id=message_data.get('file_id'),
        has_buttons=message_data.get('reply_markup') is not None,
        total_users=total_users
    )

    # 更新消息
    await callback.message.edit_text(
        "🚀 开始广播，结束后将发送广播任务统计详情...",
        parse_mode="HTML"
    )

    # 清除状态
    await state.clear()

    # 开始广播
    start_time = datetime.now()
    success_count, failed_count = await broadcast_to_users(
        bot=callback.bot,
        message_data=message_data,
        db=db
    )
    end_time = datetime.now()
    duration = int((end_time - start_time).total_seconds())

    # 更新广播日志
    await update_broadcast_log(
        db=db,
        log_id=log_id,
        success_count=success_count,
        failed_count=failed_count,
        completed_at=end_time,
        duration_seconds=duration
    )

    # 发送完成消息
    await callback.message.answer(
        f"✅ <b>广播完成！</b>\n\n"
        f"成功：<b>{success_count}</b> 人\n"
        f"失败：<b>{failed_count}</b> 人（用户已屏蔽 Bot）\n"
        f"总耗时：<b>{duration}</b> 秒",
        parse_mode="HTML"
    )


@router.callback_query(AdminSettingsStates.confirming_broadcast, F.data == "cancel")
async def cancel_broadcast_confirm(callback: CallbackQuery, state: FSMContext):
    """取消广播"""
    await callback.answer()
    await state.clear()
    await callback.message.edit_text("❌ 已取消广播")


async def broadcast_to_users(bot, message_data: dict, db: AsyncSession) -> tuple[int, int]:
    """
    向所有用户广播消息

    Returns:
        (success_count, failed_count)
    """
    success = 0
    failed = 0

    # 获取所有用户
    users, total = await get_users(db, skip=0, limit=999999)

    for user in users:
        try:
            # 发送消息
            if message_data['type'] == 'text':
                await bot.send_message(
                    chat_id=user.telegram_id,
                    text=message_data['text'],
                    parse_mode="HTML",
                    reply_markup=message_data.get('reply_markup')
                )
            elif message_data['type'] == 'photo':
                await bot.send_photo(
                    chat_id=user.telegram_id,
                    photo=message_data['file_id'],
                    caption=message_data.get('caption'),
                    parse_mode="HTML",
                    reply_markup=message_data.get('reply_markup')
                )
            elif message_data['type'] == 'video':
                await bot.send_video(
                    chat_id=user.telegram_id,
                    video=message_data['file_id'],
                    caption=message_data.get('caption'),
                    parse_mode="HTML",
                    reply_markup=message_data.get('reply_markup')
                )

            success += 1

        except TelegramForbiddenError:
            # 用户屏蔽了 Bot，跳过
            failed += 1
            logger.info(f"User {user.telegram_id} has blocked the bot")

        except TelegramRetryAfter as e:
            # API 限流，等待后重试
            logger.warning(f"Rate limit hit, waiting {e.retry_after}s")
            await asyncio.sleep(e.retry_after)

            # 重试当前用户
            try:
                if message_data['type'] == 'text':
                    await bot.send_message(
                        chat_id=user.telegram_id,
                        text=message_data['text'],
                        parse_mode="HTML",
                        reply_markup=message_data.get('reply_markup')
                    )
                elif message_data['type'] == 'photo':
                    await bot.send_photo(
                        chat_id=user.telegram_id,
                        photo=message_data['file_id'],
                        caption=message_data.get('caption'),
                        parse_mode="HTML",
                        reply_markup=message_data.get('reply_markup')
                    )
                elif message_data['type'] == 'video':
                    await bot.send_video(
                        chat_id=user.telegram_id,
                        video=message_data['file_id'],
                        caption=message_data.get('caption'),
                        parse_mode="HTML",
                        reply_markup=message_data.get('reply_markup')
                    )
                success += 1
            except Exception as retry_error:
                failed += 1
                logger.error(f"Retry failed for user {user.telegram_id}: {retry_error}")

        except TelegramBadRequest as e:
            # 无效请求，跳过
            failed += 1
            logger.error(f"Bad request for user {user.telegram_id}: {e}")

        except Exception as e:
            # 其他错误，记录并跳过
            failed += 1
            logger.error(f"Broadcast failed for user {user.telegram_id}: {e}")

        # 限流：每秒 20 条
        await asyncio.sleep(BROADCAST_RATE)

    return success, failed
