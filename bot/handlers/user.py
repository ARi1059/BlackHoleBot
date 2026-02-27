# bot/handlers/user.py
"""
用户端处理器
"""

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InputMediaPhoto, InputMediaVideo
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
import random
import string

from database import User, UserRole, AccessLevel
from database.crud import (
    get_collection_by_code,
    get_media_by_collection,
    get_media_count,
    get_setting,
    search_collections,
    get_collections_by_role,
    get_hot_collections,
    increment_collection_view_count,
)
from bot.keyboards import (
    create_pagination_keyboard,
    create_search_results_keyboard,
    create_collection_info_keyboard,
    create_main_menu_keyboard,
    create_browse_keyboard,
    create_admin_panel_keyboard,
)
from bot.states import SearchStates, UploadStates, AdminSettingsStates
from utils import parse_start_parameter, calculate_total_pages
from config import settings

router = Router()


def check_collection_access(user: User, collection) -> bool:
    """
    检查用户是否有权限访问合集

    Args:
        user: 用户对象
        collection: 合集对象

    Returns:
        是否有权限
    """
    if collection.access_level == AccessLevel.PUBLIC:
        return True

    if collection.access_level == AccessLevel.VIP:
        return user.role in [UserRole.VIP, UserRole.ADMIN, UserRole.SUPER_ADMIN]

    return False


@router.message(Command("start"))
async def cmd_start(message: Message, user: User, db: AsyncSession):
    """
    处理 /start 命令

    功能：
    1. 无参数：显示主菜单
    2. 有参数：访问深链接合集
    """
    # 解析深链接参数
    deep_link_code = parse_start_parameter(message.text)

    if not deep_link_code:
        # 判断是否为管理员
        is_admin = user.role in [UserRole.ADMIN, UserRole.SUPER_ADMIN]

        # 管理员显示专门的管理员界面
        if is_admin:
            admin_message = (
                "⚙️ 管理员控制台\n\n"
                f"👤 管理员：{user.username or user.telegram_id}\n"
                f"🔐 权限等级：{user.role.value}\n\n"
                "请选择功能："
            )
            keyboard = create_main_menu_keyboard(is_admin=True)
            await message.answer(admin_message, reply_markup=keyboard)
            return

        # 普通用户显示欢迎消息
        import json
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        from aiogram.utils.keyboard import InlineKeyboardBuilder

        welcome_message = await get_setting(db, "welcome_message")

        if not welcome_message:
            # 默认欢迎消息
            default_message = (
                "👋 欢迎使用 BlackHoleBot！\n\n"
                "🎯 功能介绍:\n"
                "• 📦 浏览海量媒体合集\n"
                "• 🔍 快速搜索感兴趣的内容\n"
                "• 💎 VIP 用户专享高质量资源\n\n"
                "请选择功能："
            )
            keyboard = create_main_menu_keyboard(is_admin=False)
            await message.answer(default_message, reply_markup=keyboard)
            return

        # 尝试解析 JSON 格式的欢迎消息
        try:
            message_data = json.loads(welcome_message)

            # 构建键盘：自定义按钮 + 默认主菜单按钮
            builder = InlineKeyboardBuilder()

            # 添加自定义按钮（如果有）
            if message_data.get('reply_markup'):
                custom_markup = InlineKeyboardMarkup.model_validate(message_data['reply_markup'])
                for row in custom_markup.inline_keyboard:
                    builder.row(*row)

            # 添加默认主菜单按钮（始终显示）
            builder.row(
                InlineKeyboardButton(text="📦 浏览合集", callback_data="browse_collections"),
                InlineKeyboardButton(text="🔥 热门合集", callback_data="hot_collections")
            )
            builder.row(
                InlineKeyboardButton(text="🔍 搜索合集", callback_data="search")
            )

            reply_markup = builder.as_markup()

            # 根据消息类型发送
            if message_data['type'] == 'text':
                await message.answer(
                    text=message_data['text'],
                    parse_mode="HTML",
                    reply_markup=reply_markup
                )
            elif message_data['type'] == 'photo':
                await message.answer_photo(
                    photo=message_data['file_id'],
                    caption=message_data.get('caption'),
                    parse_mode="HTML",
                    reply_markup=reply_markup
                )
            elif message_data['type'] == 'video':
                await message.answer_video(
                    video=message_data['file_id'],
                    caption=message_data.get('caption'),
                    parse_mode="HTML",
                    reply_markup=reply_markup
                )
        except (json.JSONDecodeError, KeyError):
            # 如果不是 JSON 格式，按纯文本处理（兼容旧格式）
            keyboard = create_main_menu_keyboard(is_admin=False)
            await message.answer(welcome_message, reply_markup=keyboard)

        return

    # 访问深链接合集
    await view_collection(message, user, db, deep_link_code, page=1)


async def view_collection(
    message: Message,
    user: User,
    db: AsyncSession,
    deep_link_code: str,
    page: int = 1
):
    """
    查看合集内容

    Args:
        message: 消息对象
        user: 用户对象
        db: 数据库 session
        deep_link_code: 深链接码
        page: 页码
    """
    # 查询合集
    collection = await get_collection_by_code(db, deep_link_code)

    if not collection:
        await message.answer(
            "❌ 合集不存在或已被删除\n"
            "🔍 使用 /search 搜索其他合集"
        )
        return

    # 检查权限
    if not check_collection_access(user, collection):
        await message.answer(
            "❌ 抱歉，这是 VIP 专属合集\n"
            "💎 升级为 VIP 用户即可访问\n\n"
            "联系管理员获取 VIP 权限"
        )
        return

    # 增加浏览次数
    await increment_collection_view_count(db, collection.id)

    # 获取媒体数量和总页数
    media_count = await get_media_count(db, collection.id)
    total_pages = calculate_total_pages(media_count, settings.MEDIA_PER_PAGE)

    # 确保页码有效
    page = max(1, min(page, total_pages))

    # 获取当前页的媒体
    offset = (page - 1) * settings.MEDIA_PER_PAGE
    media_list = await get_media_by_collection(
        db,
        collection.id,
        skip=offset,
        limit=settings.MEDIA_PER_PAGE
    )

    if not media_list:
        await message.answer("❌ 该合集暂无内容")
        return

    # 发送合集信息
    tags_text = " ".join([f"#{tag}" for tag in (collection.tags or [])])
    info_text = (
        f"📦 合集名称: {collection.name}\n"
        f"📝 描述: {collection.description or '无'}\n"
        f"🏷️ 标签: {tags_text or '无'}\n"
        f"📊 共 {media_count} 个媒体"
    )

    # 准备媒体组
    media_group = []
    for idx, media in enumerate(media_list):
        caption = info_text if idx == 0 else None

        if media.file_type == "photo":
            media_group.append(InputMediaPhoto(
                media=media.file_id,
                caption=caption
            ))
        elif media.file_type == "video":
            media_group.append(InputMediaVideo(
                media=media.file_id,
                caption=caption
            ))

    # 发送媒体组
    try:
        await message.answer_media_group(media_group)

        # 发送分页按钮
        keyboard = create_pagination_keyboard(
            deep_link_code,
            page,
            total_pages
        )
        await message.answer(
            f"📄 第 {page}/{total_pages} 页",
            reply_markup=keyboard
        )
    except Exception as e:
        await message.answer(f"❌ 发送媒体失败: {str(e)}")


@router.callback_query(F.data.startswith("collection_"))
async def callback_collection_page(callback: CallbackQuery, user: User, db: AsyncSession):
    """
    处理合集分页回调

    Callback data 格式:
    - collection_{code}_page_{page}
    - collection_{code}_info
    """
    data = callback.data

    if data.startswith("collection_") and "_page_" in data:
        # 解析参数
        parts = data.split("_")
        deep_link_code = parts[1]
        page = int(parts[3])

        # 删除旧消息
        try:
            await callback.message.delete()
        except:
            pass

        # 显示新页面
        await view_collection(callback.message, user, db, deep_link_code, page)
        await callback.answer()

    elif data.startswith("collection_") and "_info" in data:
        # 显示合集信息
        deep_link_code = data.split("_")[1]
        collection = await get_collection_by_code(db, deep_link_code)

        if not collection:
            await callback.answer("❌ 合集不存在", show_alert=True)
            return

        tags_text = " ".join([f"#{tag}" for tag in (collection.tags or [])])
        media_count = await get_media_count(db, collection.id)

        info_text = (
            f"📦 合集名称: {collection.name}\n"
            f"📝 描述: {collection.description or '无'}\n"
            f"🏷️ 标签: {tags_text or '无'}\n"
            f"📊 媒体数量: {media_count}\n"
            f"🔒 访问权限: {'💎 VIP' if collection.access_level == AccessLevel.VIP else '🌍 公开'}\n"
            f"📅 创建时间: {collection.created_at.strftime('%Y-%m-%d')}"
        )

        keyboard = create_collection_info_keyboard(deep_link_code)
        await callback.message.answer(info_text, reply_markup=keyboard)
        await callback.answer()


@router.callback_query(F.data == "page_info")
async def callback_page_info(callback: CallbackQuery):
    """处理页码信息按钮点击"""
    await callback.answer("当前页码", show_alert=False)


@router.callback_query(F.data == "search")
async def callback_search(callback: CallbackQuery, state: FSMContext):
    """处理搜索按钮点击"""
    await state.set_state(SearchStates.waiting_for_keyword)
    await callback.message.answer(
        "🔍 请输入搜索关键词:\n\n"
        "直接发送关键词即可搜索\n"
        "示例: 猫咪"
    )
    await callback.answer()


@router.message(Command("search"))
async def cmd_search(message: Message, user: User, db: AsyncSession):
    """
    处理 /search 命令

    格式: /search 关键词
    """
    # 解析关键词
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer(
            "🔍 请输入搜索关键词\n\n"
            "格式: /search 关键词\n"
            "示例: /search 猫咪"
        )
        return

    keyword = parts[1].strip()

    # 搜索合集
    collections = await search_collections(
        db,
        keyword=keyword,
        user_role=user.role,
        skip=0,
        limit=10
    )

    if not collections:
        await message.answer(
            f"🔍 搜索结果: \"{keyword}\"\n\n"
            "❌ 未找到相关合集\n\n"
            "💡 提示:\n"
            "- 尝试使用其他关键词\n"
            "- 检查拼写是否正确\n"
            "- 联系管理员添加新内容"
        )
        return

    # 构建结果文本
    result_text = f"🔍 搜索结果: \"{keyword}\"\n\n找到 {len(collections)} 个合集:\n\n"

    for idx, collection in enumerate(collections, 1):
        vip_mark = " 💎VIP" if collection.access_level == AccessLevel.VIP else ""
        tags_text = " ".join([f"#{tag}" for tag in (collection.tags or [])])

        result_text += (
            f"{idx}️⃣ {collection.name}{vip_mark}\n"
            f"   📝 {collection.description or '无描述'}\n"
            f"   🏷️ {tags_text or '无标签'}\n"
            f"   📊 {collection.media_count} 个媒体\n\n"
        )

    result_text += "💡 点击按钮查看合集内容"

    # 创建按钮
    keyboard = create_search_results_keyboard(collections)

    await message.answer(result_text, reply_markup=keyboard)


@router.message(SearchStates.waiting_for_keyword)
async def process_search_keyword(message: Message, user: User, db: AsyncSession, state: FSMContext):
    """
    处理用户输入的搜索关键词
    """
    keyword = message.text.strip()

    # 清除状态
    await state.clear()

    # 搜索合集
    collections = await search_collections(
        db,
        keyword=keyword,
        user_role=user.role,
        skip=0,
        limit=10
    )

    if not collections:
        await message.answer(
            f"🔍 搜索结果: \"{keyword}\"\n\n"
            "❌ 未找到相关合集\n\n"
            "💡 提示:\n"
            "- 尝试使用其他关键词\n"
            "- 检查拼写是否正确\n"
            "- 联系管理员添加新内容"
        )
        return

    # 构建结果文本
    result_text = f"🔍 搜索结果: \"{keyword}\"\n\n找到 {len(collections)} 个合集:\n\n"

    for idx, collection in enumerate(collections, 1):
        vip_mark = " 💎VIP" if collection.access_level == AccessLevel.VIP else ""
        tags_text = " ".join([f"#{tag}" for tag in (collection.tags or [])])

        result_text += (
            f"{idx}️⃣ {collection.name}{vip_mark}\n"
            f"   📝 {collection.description or '无描述'}\n"
            f"   🏷️ {tags_text or '无标签'}\n"
            f"   📊 {collection.media_count} 个媒体\n\n"
        )

    result_text += "💡 点击按钮查看合集内容"

    # 创建按钮
    keyboard = create_search_results_keyboard(collections)

    await message.answer(result_text, reply_markup=keyboard)


@router.callback_query(F.data.startswith("view_collection_"))
async def callback_view_collection(callback: CallbackQuery, user: User, db: AsyncSession):
    """
    处理查看合集回调

    Callback data 格式: view_collection_{deep_link_code}
    """
    deep_link_code = callback.data.replace("view_collection_", "")

    # 先检查合集是否存在
    collection = await get_collection_by_code(db, deep_link_code)

    if not collection:
        await callback.answer("❌ 合集不存在或已被删除", show_alert=True)
        return

    # 检查权限
    if not check_collection_access(user, collection):
        await callback.answer(
            "❌ 这是 VIP 专属合集\n💎 升级为 VIP 用户即可访问",
            show_alert=True
        )
        return

    # 删除搜索结果消息
    try:
        await callback.message.delete()
    except:
        pass

    # 显示合集
    await view_collection(callback.message, user, db, deep_link_code, page=1)
    await callback.answer()


@router.callback_query(F.data == "main_menu")
async def callback_main_menu(callback: CallbackQuery, user: User, db: AsyncSession):
    """返回主菜单"""
    is_admin = user.role in [UserRole.ADMIN, UserRole.SUPER_ADMIN]
    keyboard = create_main_menu_keyboard(is_admin=is_admin)

    # 判断消息类型，如果是媒体消息则发送新消息，否则编辑
    if callback.message.photo or callback.message.video:
        await callback.message.answer(
            "👋 欢迎使用 BlackHoleBot！\n\n"
            "请选择功能：",
            reply_markup=keyboard
        )
    else:
        await callback.message.edit_text(
            "👋 欢迎使用 BlackHoleBot！\n\n"
            "请选择功能：",
            reply_markup=keyboard
        )
    await callback.answer()


@router.callback_query(F.data == "browse_collections")
async def callback_browse_collections(callback: CallbackQuery, user: User, db: AsyncSession):
    """浏览合集"""
    await show_browse_collections(callback.message, user, db, page=1, edit=True)
    await callback.answer()


@router.callback_query(F.data.startswith("browse_page_"))
async def callback_browse_page(callback: CallbackQuery, user: User, db: AsyncSession):
    """浏览合集分页"""
    page = int(callback.data.replace("browse_page_", ""))
    await show_browse_collections(callback.message, user, db, page=page, edit=True)
    await callback.answer()


@router.callback_query(F.data == "hot_collections")
async def callback_hot_collections(callback: CallbackQuery, user: User, db: AsyncSession):
    """热门合集"""
    collections = await get_hot_collections(db, user_role=user.role, limit=5)

    if not collections:
        await callback.answer("暂无热门合集", show_alert=True)
        return

    result_text = "🔥 热门合集 TOP 5\n\n"

    for idx, collection in enumerate(collections, 1):
        vip_mark = " 💎" if collection.access_level == AccessLevel.VIP else ""
        result_text += (
            f"{idx}. {collection.name}{vip_mark}\n"
            f"   📊 {collection.media_count} 个媒体\n\n"
        )

    keyboard = create_search_results_keyboard(collections, show_back=True)

    # 判断消息类型，如果是媒体消息则发送新消息，否则编辑
    if callback.message.photo or callback.message.video:
        await callback.message.answer(result_text, reply_markup=keyboard)
    else:
        await callback.message.edit_text(result_text, reply_markup=keyboard)
    await callback.answer()


async def show_browse_collections(message: Message, user: User, db: AsyncSession, page: int = 1, edit: bool = False):
    """显示浏览合集列表"""
    collections, total = await get_collections_by_role(
        db,
        user_role=user.role,
        skip=(page - 1) * 5,
        limit=5
    )

    if not collections:
        text = "📦 暂无合集"
        if edit:
            # 判断消息类型
            if message.photo or message.video:
                await message.answer(text)
            else:
                await message.edit_text(text)
        else:
            await message.answer(text)
        return

    total_pages = (total + 4) // 5

    text = f"📦 浏览合集 (第 {page}/{total_pages} 页)\n\n共 {total} 个合集"

    keyboard = create_browse_keyboard(collections, page, total_pages)

    if edit:
        # 判断消息类型，如果是媒体消息则发送新消息，否则编辑
        if message.photo or message.video:
            await message.answer(text, reply_markup=keyboard)
        else:
            await message.edit_text(text, reply_markup=keyboard)
    else:
        await message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data == "admin_panel")
async def callback_admin_panel(callback: CallbackQuery, user: User):
    """显示管理员面板"""
    if user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
        await callback.answer("❌ 权限不足", show_alert=True)
        return

    keyboard = create_admin_panel_keyboard()

    await callback.message.edit_text(
        "⚙️ 管理员面板\n\n"
        "请选择管理功能：",
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data == "admin_upload")
async def callback_admin_upload(callback: CallbackQuery, user: User, state: FSMContext):
    """开始上传合集流程"""
    if user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
        await callback.answer("❌ 权限不足", show_alert=True)
        return

    await state.clear()

    await callback.message.answer(
        "📤 开始创建新合集\n\n"
        "请发送媒体文件（图片或视频）\n"
        "• 可以一次发送多个文件\n"
        "• 支持媒体组（最多10个）\n"
        "• 完成后发送 /done\n\n"
        "💡 提示: 发送 /cancel 可随时取消"
    )

    await state.set_state(UploadStates.waiting_for_media)
    await state.update_data(media_list=[])
    await callback.answer()


@router.callback_query(F.data == "admin_welcome")
async def callback_admin_welcome(callback: CallbackQuery, user: User, state: FSMContext, db: AsyncSession):
    """开始设置欢迎消息流程"""
    if user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
        await callback.answer("❌ 权限不足", show_alert=True)
        return

    # 获取当前欢迎消息
    current_message = await get_setting(db, "welcome_message")
    if not current_message:
        current_message = "（未设置）"

    await callback.message.answer(
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

    await state.set_state(AdminSettingsStates.waiting_welcome_message)
    await callback.answer()


@router.callback_query(F.data == "admin_broadcast")
async def callback_admin_broadcast(callback: CallbackQuery, user: User, state: FSMContext):
    """开始广播消息流程"""
    if user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
        await callback.answer("❌ 权限不足", show_alert=True)
        return

    await state.clear()

    await callback.message.answer(
        "📢 <b>广播消息</b>\n\n"
        "请发送要广播的消息：\n"
        "• 支持文本（HTML 格式）\n"
        "• 支持图片/视频（可附带文字说明）\n"
        "• 支持按钮（使用 inline keyboard）\n\n"
        "发送 /cancel 取消广播",
        parse_mode="HTML"
    )

    await state.set_state(AdminSettingsStates.waiting_broadcast_message)
    await callback.answer()


@router.message(Command("help"))
async def cmd_help(message: Message):
    """处理 /help 命令"""
    help_text = (
        "📖 BlackHoleBot 使用帮助\n\n"
        "🔹 基础命令:\n"
        "/start - 启动 Bot\n"
        "/search [关键词] - 搜索合集\n"
        "/help - 查看帮助\n"
        "/myinfo - 查看个人信息\n\n"
        "🔹 使用方法:\n"
        "1. 点击频道分享的链接直接访问合集\n"
        "2. 使用 /search 命令搜索感兴趣的内容\n"
        "3. 在合集中使用翻页按钮浏览所有媒体\n\n"
        "🔹 权限说明:\n"
        "• 普通用户: 可访问公开合集\n"
        "• VIP 用户: 可访问所有合集\n\n"
        "💡 如需升级 VIP，请联系管理员"
    )

    await message.answer(help_text)


@router.message(Command("myinfo"))
async def cmd_myinfo(message: Message, user: User):
    """处理 /myinfo 命令"""
    import logging
    logger = logging.getLogger(__name__)

    logger.info(f"用户角色调试: {user.role}, 类型: {type(user.role)}, 值: {user.role.value if hasattr(user.role, 'value') else 'N/A'}")
    logger.info(f"是否等于 SUPER_ADMIN: {user.role == UserRole.SUPER_ADMIN}")

    role_names = {
        UserRole.USER: "👤 普通用户",
        UserRole.VIP: "💎 VIP 用户",
        UserRole.ADMIN: "👨‍💼 管理员",
        UserRole.SUPER_ADMIN: "👑 超级管理员"
    }

    logger.info(f"字典查找结果: {role_names.get(user.role, '未找到')}")

    info_text = (
        "👤 个人信息\n\n"
        f"ID: {user.telegram_id}\n"
        f"用户名: @{user.username or 'N/A'}\n"
        f"姓名: {user.first_name}\n"
        f"角色: {role_names.get(user.role, user.role)}\n"
        f"注册时间: {user.created_at.strftime('%Y-%m-%d %H:%M')}\n"
        f"最后活跃: {user.last_active_at.strftime('%Y-%m-%d %H:%M')}"
    )

    await message.answer(info_text)


@router.message(Command("login"))
async def cmd_login(message: Message, user: User):
    """处理 /login 命令 - 生成 Web 登录验证码"""
    # 检查用户是否是管理员
    if user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
        await message.answer("❌ 只有管理员才能登录 Web 后台")
        return

    # 生成 6 位数字验证码
    code = ''.join(random.choices(string.digits, k=6))

    # 保存到 Redis，有效期 5 分钟
    try:
        from database.connection import redis_client
        await redis_client.setex(
            f"web_login:{user.telegram_id}",
            300,  # 5 分钟
            code
        )

        await message.answer(
            f"🔐 Web 后台登录验证码\n\n"
            f"验证码: <code>{code}</code>\n"
            f"有效期: 5 分钟\n\n"
            f"请在 Web 登录页面输入您的 Telegram ID 和此验证码",
            parse_mode="HTML"
        )
    except Exception as e:
        await message.answer(f"❌ 生成验证码失败: {str(e)}")

