# bot/handlers/admin.py
"""
管理员处理器
"""

import asyncio
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from functools import wraps

from database import User, UserRole, AccessLevel
from database.crud import (
    create_collection,
    create_media,
    update_collection,
    create_admin_log,
    get_collection,
)
from bot.states import UploadStates, AddMediaStates
from utils import generate_unique_deep_link_code, create_deep_link
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


# ==================== 上传新合集 ====================

@router.message(Command("upload"))
@require_admin
async def cmd_upload(message: Message, user: User, state: FSMContext):
    """
    开始上传新合集

    命令: /upload
    """
    await state.clear()  # 清除之前的状态

    await message.answer(
        "📤 开始创建新合集\n\n"
        "请发送媒体文件（图片或视频）\n"
        "• 可以一次发送多个文件\n"
        "• 支持媒体组（最多10个）\n"
        "• 完成后发送 /done\n\n"
        "💡 提示: 发送 /cancel 可随时取消"
    )

    await state.set_state(UploadStates.waiting_for_media)
    await state.update_data(media_list=[])


@router.message(UploadStates.waiting_for_media, F.photo | F.video)
async def handle_media_upload(message: Message, state: FSMContext):
    """接收媒体文件"""
    data = await state.get_data()
    media_list = data.get("media_list", [])

    # 提取文件信息
    if message.photo:
        file_id = message.photo[-1].file_id
        file_unique_id = message.photo[-1].file_unique_id
        file_type = "photo"
        file_size = message.photo[-1].file_size
    elif message.video:
        file_id = message.video.file_id
        file_unique_id = message.video.file_unique_id
        file_type = "video"
        file_size = message.video.file_size
    else:
        return

    # 检查是否重复
    if any(m["file_unique_id"] == file_unique_id for m in media_list):
        return

    # 添加到列表
    media_list.append({
        "file_id": file_id,
        "file_unique_id": file_unique_id,
        "file_type": file_type,
        "file_size": file_size,
        "caption": message.caption
    })

    await state.update_data(media_list=media_list)


@router.message(UploadStates.waiting_for_media, Command("done"))
async def cmd_done_media(message: Message, state: FSMContext):
    """完成媒体上传"""
    data = await state.get_data()
    media_list = data.get("media_list", [])

    # 验证
    if not media_list:
        await message.answer("❌ 还没有上传任何媒体文件")
        return

    if len(media_list) > settings.MAX_MEDIA_PER_COLLECTION:
        await message.answer(
            f"❌ 媒体数量超过限制（最多 {settings.MAX_MEDIA_PER_COLLECTION} 个）"
        )
        return

    await message.answer(
        f"✅ 已接收 {len(media_list)} 个媒体文件\n\n"
        f"📝 请输入合集名称\n"
        f"（建议简短明了，如：可爱猫咪合集）"
    )

    await state.set_state(UploadStates.waiting_for_name)


@router.message(UploadStates.waiting_for_name)
async def handle_collection_name(message: Message, state: FSMContext):
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

    await state.set_state(UploadStates.waiting_for_description)


@router.message(UploadStates.waiting_for_description)
async def handle_collection_description(message: Message, state: FSMContext):
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

    await state.set_state(UploadStates.waiting_for_tags)


@router.message(UploadStates.waiting_for_tags)
async def handle_collection_tags(message: Message, state: FSMContext):
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
            InlineKeyboardButton(text="🌍 公开", callback_data="access_public"),
            InlineKeyboardButton(text="💎 VIP", callback_data="access_vip")
        ]
    ])

    await message.answer(
        "🔒 请选择访问权限:",
        reply_markup=keyboard
    )

    await state.set_state(UploadStates.waiting_for_permission)


@router.callback_query(UploadStates.waiting_for_permission, F.data.in_(["access_public", "access_vip"]))
async def handle_access_permission(callback: CallbackQuery, user: User, db: AsyncSession, state: FSMContext):
    """处理权限选择并创建合集"""
    access_level = AccessLevel.PUBLIC if callback.data == "access_public" else AccessLevel.VIP

    # 获取所有数据
    data = await state.get_data()

    try:
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
        media_list = data["media_list"]
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

        # 记录日志
        await create_admin_log(
            db,
            user_id=user.id,
            action="create_collection",
            details={
                "collection_name": collection.name,
                "media_count": len(media_list),
                "access_level": access_level.value
            }
        )

        # 清除状态
        await state.clear()

        # 发送成功消息
        access_emoji = "🌍" if access_level == AccessLevel.PUBLIC else "💎"
        deep_link = create_deep_link(settings.BOT_USERNAME, deep_link_code)

        await callback.message.answer(
            f"✅ 创建成功！\n\n"
            f"📦 合集名称: {collection.name}\n"
            f"🔗 深链接: {deep_link}\n"
            f"📊 媒体数量: {len(media_list)}\n"
            f"🔒 访问权限: {access_emoji} {access_level.value.upper()}"
        )

        await callback.answer("✅ 合集创建成功")

    except Exception as e:
        # 转义 HTML 字符避免 Telegram 解析错误
        error_msg = str(e).replace('<', '&lt;').replace('>', '&gt;')
        await callback.message.answer(f"❌ 创建失败: {error_msg}")
        await callback.answer("❌ 创建失败", show_alert=True)


# ==================== 取消操作 ====================

@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    """取消当前操作"""
    current_state = await state.get_state()

    if current_state is None:
        await message.answer("❌ 没有正在进行的操作")
        return

    await state.clear()
    await message.answer("✅ 已取消操作")


# ==================== 向现有合集添加媒体 ====================

@router.message(Command("add_media"))
@require_admin
async def cmd_add_media(message: Message, user: User, state: FSMContext, db: AsyncSession):
    """
    向现有合集添加媒体

    命令: /add_media <collection_id>
    """
    # 解析参数
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("❌ 请提供合集 ID\n\n用法: /add_media <collection_id>")
        return

    try:
        collection_id = int(args[1])
    except ValueError:
        await message.answer("❌ 合集 ID 必须是数字")
        return

    # 检查合集是否存在
    collection = await get_collection(db, collection_id)
    if not collection:
        await message.answer("❌ 合集不存在")
        return

    # 检查权限（只有创建者或超级管理员可以添加）
    if collection.created_by != user.id and user.role != UserRole.SUPER_ADMIN:
        await message.answer("❌ 权限不足，只有合集创建者或超级管理员可以添加媒体")
        return

    await state.clear()
    await state.set_state(AddMediaStates.waiting_for_media)
    await state.update_data(
        collection_id=collection_id,
        collection_name=collection.name,
        media_list=[],
        current_media_count=collection.media_count
    )

    await message.answer(
        f"📤 向合集 「{collection.name}」 添加媒体\n\n"
        f"当前媒体数: {collection.media_count}\n\n"
        f"请发送媒体文件（图片或视频）\n"
        f"• 可以一次发送多个文件\n"
        f"• 支持媒体组（最多10个）\n"
        f"• 完成后发送 /done\n\n"
        f"💡 提示: 发送 /cancel 可随时取消"
    )


@router.message(AddMediaStates.waiting_for_media, F.photo | F.video)
async def handle_add_media_upload(message: Message, state: FSMContext):
    """接收要添加的媒体文件"""
    import logging
    logger = logging.getLogger(__name__)

    data = await state.get_data()
    media_list = data.get("media_list", [])

    logger.info(f"Receiving media in AddMediaStates, current list size: {len(media_list)}")

    # 提取文件信息
    if message.photo:
        file_id = message.photo[-1].file_id
        file_unique_id = message.photo[-1].file_unique_id
        file_type = "photo"
        file_size = message.photo[-1].file_size
    elif message.video:
        file_id = message.video.file_id
        file_unique_id = message.video.file_unique_id
        file_type = "video"
        file_size = message.video.file_size
    else:
        return

    # 检查是否重复
    if any(m["file_unique_id"] == file_unique_id for m in media_list):
        logger.info(f"Duplicate media detected: {file_unique_id}")
        return

    # 添加到列表
    media_list.append({
        "file_id": file_id,
        "file_unique_id": file_unique_id,
        "file_type": file_type,
        "file_size": file_size,
        "caption": message.caption
    })

    await state.update_data(media_list=media_list)
    logger.info(f"Media added, new list size: {len(media_list)}")


@router.message(AddMediaStates.waiting_for_media, Command("done"))
async def cmd_done_add_media(message: Message, user: User, state: FSMContext, db: AsyncSession):
    """完成添加媒体"""
    import logging
    logger = logging.getLogger(__name__)

    data = await state.get_data()
    media_list = data.get("media_list", [])
    collection_id = data.get("collection_id")
    collection_name = data.get("collection_name")
    current_media_count = data.get("current_media_count", 0)

    logger.info(f"Done command received. Media list size: {len(media_list)}, collection_id: {collection_id}")

    # 验证
    if not media_list:
        await message.answer("❌ 还没有上传任何媒体文件")
        logger.warning("No media in list when done command received")
        return

    # 检查总数是否超限
    total_count = current_media_count + len(media_list)
    if total_count > settings.MAX_MEDIA_PER_COLLECTION:
        await message.answer(
            f"❌ 添加后总媒体数将超过限制\n"
            f"当前: {current_media_count}\n"
            f"新增: {len(media_list)}\n"
            f"限制: {settings.MAX_MEDIA_PER_COLLECTION}"
        )
        return

    try:
        # 批量插入媒体
        for index, media_data in enumerate(media_list):
            await create_media(
                db,
                collection_id=collection_id,
                file_id=media_data["file_id"],
                file_unique_id=media_data["file_unique_id"],
                file_type=media_data["file_type"],
                order_index=current_media_count + index,
                file_size=media_data.get("file_size"),
                caption=media_data.get("caption")
            )

        # 更新合集媒体数量
        await update_collection(db, collection_id, media_count=total_count)

        # 记录日志
        await create_admin_log(
            db,
            user_id=user.id,
            action="add_media",
            details={
                "collection_id": collection_id,
                "collection_name": collection_name,
                "added_count": len(media_list),
                "total_count": total_count
            }
        )

        # 清除状态
        await state.clear()

        logger.info(f"Successfully added {len(media_list)} media to collection {collection_id}")

        await message.answer(
            f"✅ 添加成功！\n\n"
            f"📦 合集: {collection_name}\n"
            f"➕ 新增媒体: {len(media_list)}\n"
            f"📊 总媒体数: {total_count}"
        )

    except Exception as e:
        logger.error(f"Error adding media: {e}", exc_info=True)
        error_msg = str(e).replace('<', '&lt;').replace('>', '&gt;')
        await message.answer(f"❌ 添加失败: {error_msg}")



