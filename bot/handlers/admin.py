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
    get_collection_by_code,
    delete_collection,
    update_collection,
    get_collections,
    create_admin_log,
)
from bot.states import UploadStates, AddMediaStates, EditCollectionStates, BatchDeleteStates
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
    processed_groups = data.get("processed_groups", set())  # 已处理的媒体组ID

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
        await message.answer("❌ 不支持的文件类型")
        return

    # 检查是否重复
    if any(m["file_unique_id"] == file_unique_id for m in media_list):
        await message.answer("⚠️ 文件已存在，已跳过")
        return

    # 添加到列表
    media_list.append({
        "file_id": file_id,
        "file_unique_id": file_unique_id,
        "file_type": file_type,
        "file_size": file_size,
        "caption": message.caption
    })

    # 处理通知：每个媒体组只通知一次
    media_group_id = message.media_group_id
    if media_group_id:
        # 如果这个媒体组还没处理过，通知一次
        if media_group_id not in processed_groups:
            processed_groups.add(media_group_id)
            await message.answer(f"✅ 已接收 {len(media_list)} 个文件")
    else:
        # 单个文件，直接通知
        await message.answer(f"✅ 已接收 {len(media_list)} 个文件")

    await state.update_data(media_list=media_list, processed_groups=processed_groups)


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


# ==================== 查看所有合集 ====================

@router.message(Command("list_collections"))
@require_admin
async def cmd_list_collections(message: Message, user: User, db: AsyncSession):
    """
    查看所有合集

    命令: /list_collections
    """
    collections, total = await get_collections(db, skip=0, limit=20)

    if not collections:
        await message.answer("❌ 暂无合集")
        return

    text = f"📦 合集列表（共 {total} 个）\n\n"

    for idx, collection in enumerate(collections, 1):
        access_emoji = "💎" if collection.access_level == AccessLevel.VIP else "🌍"
        text += (
            f"{idx}. {collection.name} {access_emoji}\n"
            f"   🔗 代码: {collection.deep_link_code}\n"
            f"   📊 媒体: {collection.media_count} 个\n"
            f"   📅 创建: {collection.created_at.strftime('%Y-%m-%d')}\n\n"
        )

    if total > 20:
        text += f"💡 仅显示前 20 个合集"

    await message.answer(text)


# ==================== 删除合集 ====================

@router.message(Command("delete_collection"))
@require_admin
async def cmd_delete_collection(message: Message, user: User, db: AsyncSession):
    """
    删除合集

    命令: /delete_collection {deep_link_code}
    """
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(
            "用法: /delete_collection {深链接码}\n"
            "示例: /delete_collection abc123"
        )
        return

    deep_link_code = args[1].strip()

    # 查询合集
    collection = await get_collection_by_code(db, deep_link_code)

    if not collection:
        await message.answer("❌ 合集不存在")
        return

    # 确认删除
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✅ 确认删除",
                callback_data=f"confirm_delete_{collection.id}"
            ),
            InlineKeyboardButton(
                text="❌ 取消",
                callback_data="cancel_delete"
            )
        ]
    ])

    await message.answer(
        f"⚠️ 确认删除合集？\n\n"
        f"📦 名称: {collection.name}\n"
        f"📊 媒体数量: {collection.media_count}\n\n"
        f"此操作不可撤销！",
        reply_markup=keyboard
    )


@router.callback_query(F.data.startswith("confirm_delete_"))
async def callback_confirm_delete(callback: CallbackQuery, user: User, db: AsyncSession):
    """确认删除合集"""
    collection_id = int(callback.data.replace("confirm_delete_", ""))

    try:
        # 删除合集
        success = await delete_collection(db, collection_id)

        if success:
            # 记录日志
            await create_admin_log(
                db,
                user_id=user.id,
                action="delete_collection",
                details={"collection_id": collection_id}
            )

            await callback.message.edit_text("✅ 已删除合集")
            await callback.answer("✅ 删除成功")
        else:
            await callback.message.edit_text("❌ 删除失败")
            await callback.answer("❌ 删除失败", show_alert=True)

    except Exception as e:
        await callback.message.edit_text(f"❌ 删除失败: {str(e)}")
        await callback.answer("❌ 删除失败", show_alert=True)


@router.callback_query(F.data == "cancel_delete")
async def callback_cancel_delete(callback: CallbackQuery):
    """取消删除"""
    await callback.message.edit_text("✅ 已取消删除")
    await callback.answer()


# ==================== 添加媒体到现有合集 ====================

@router.message(Command("add_media"))
@require_admin
async def cmd_add_media(message: Message, user: User, db: AsyncSession, state: FSMContext):
    """
    添加媒体到现有合集

    命令: /add_media {deep_link_code}
    """
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(
            "用法: /add_media {深链接码}\n"
            "示例: /add_media abc123"
        )
        return

    deep_link_code = args[1].strip()

    # 查询合集
    collection = await get_collection_by_code(db, deep_link_code)

    if not collection:
        await message.answer("❌ 合集不存在")
        return

    await state.clear()
    await state.set_state(AddMediaStates.waiting_for_media)
    await state.update_data(
        collection_id=collection.id,
        collection_name=collection.name,
        media_list=[]
    )

    await message.answer(
        f"📤 添加媒体到合集: {collection.name}\n\n"
        f"请发送媒体文件（图片或视频）\n"
        f"完成后发送 /done\n\n"
        f"💡 提示: 发送 /cancel 可随时取消"
    )


@router.message(AddMediaStates.waiting_for_media, F.photo | F.video)
async def handle_add_media_upload(message: Message, state: FSMContext):
    """接收要添加的媒体文件"""
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
        await message.answer("⚠️ 文件已存在，已跳过")
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
    await message.answer(f"✅ 已接收 {len(media_list)} 个文件")


@router.message(AddMediaStates.waiting_for_media, Command("done"))
async def cmd_done_add_media(message: Message, user: User, db: AsyncSession, state: FSMContext):
    """完成添加媒体"""
    data = await state.get_data()
    media_list = data.get("media_list", [])
    collection_id = data.get("collection_id")

    if not media_list:
        await message.answer("❌ 还没有上传任何媒体文件")
        return

    try:
        # 获取当前最大 order_index
        from sqlalchemy import select, func
        from database.models import Media

        result = await db.execute(
            select(func.max(Media.order_index))
            .where(Media.collection_id == collection_id)
        )
        max_order = result.scalar() or -1
        start_index = max_order + 1

        # 批量插入媒体
        for index, media_data in enumerate(media_list):
            await create_media(
                db,
                collection_id=collection_id,
                file_id=media_data["file_id"],
                file_unique_id=media_data["file_unique_id"],
                file_type=media_data["file_type"],
                order_index=start_index + index,
                file_size=media_data.get("file_size"),
                caption=media_data.get("caption")
            )

        # 更新合集媒体数量
        collection = await get_collection_by_code(db, None)  # 需要通过 ID 获取
        from database.models import Collection
        result = await db.execute(
            select(Collection).where(Collection.id == collection_id)
        )
        collection = result.scalar_one()

        await update_collection(
            db,
            collection_id,
            media_count=collection.media_count + len(media_list)
        )

        # 记录日志
        await create_admin_log(
            db,
            user_id=user.id,
            action="add_media",
            details={
                "collection_id": collection_id,
                "media_count": len(media_list)
            }
        )

        await state.clear()

        await message.answer(
            f"✅ 已添加 {len(media_list)} 个媒体到合集\n"
            f"📦 合集: {data.get('collection_name')}"
        )

    except Exception as e:
        await message.answer(f"❌ 添加失败: {str(e)}")


# ==================== 编辑合集 ====================

@router.message(Command("edit_collection"))
@require_admin
async def cmd_edit_collection(message: Message, user: User, db: AsyncSession):
    """
    编辑合集信息

    命令: /edit_collection {deep_link_code}
    """
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(
            "用法: /edit_collection {深链接码}\n"
            "示例: /edit_collection abc123"
        )
        return

    deep_link_code = args[1].strip()

    # 查询合集
    collection = await get_collection_by_code(db, deep_link_code)

    if not collection:
        await message.answer("❌ 合集不存在")
        return

    # 显示当前信息和编辑选项
    tags_text = " ".join(collection.tags or [])
    access_text = "💎 VIP" if collection.access_level == AccessLevel.VIP else "🌍 公开"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="📝 编辑名称",
                callback_data=f"edit_{collection.id}_name"
            ),
            InlineKeyboardButton(
                text="📄 编辑描述",
                callback_data=f"edit_{collection.id}_description"
            )
        ],
        [
            InlineKeyboardButton(
                text="🏷️ 编辑标签",
                callback_data=f"edit_{collection.id}_tags"
            ),
            InlineKeyboardButton(
                text="🔒 编辑权限",
                callback_data=f"edit_{collection.id}_access"
            )
        ]
    ])

    await message.answer(
        f"📦 合集信息\n\n"
        f"名称: {collection.name}\n"
        f"描述: {collection.description or '无'}\n"
        f"标签: {tags_text or '无'}\n"
        f"权限: {access_text}\n\n"
        f"请选择要编辑的项:",
        reply_markup=keyboard
    )


@router.callback_query(F.data.startswith("edit_"))
async def callback_edit_field(callback: CallbackQuery, state: FSMContext):
    """处理编辑字段选择"""
    parts = callback.data.split("_")
    collection_id = int(parts[1])
    field = parts[2]

    if field == "access":
        # 直接显示权限选择
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🌍 公开", callback_data=f"update_access_{collection_id}_public"),
                InlineKeyboardButton(text="💎 VIP", callback_data=f"update_access_{collection_id}_vip")
            ]
        ])
        await callback.message.edit_text(
            "🔒 请选择新的访问权限:",
            reply_markup=keyboard
        )
    else:
        # 其他字段需要输入
        field_names = {
            "name": "名称",
            "description": "描述",
            "tags": "标签（用空格分隔）"
        }

        await state.set_state(EditCollectionStates.waiting_for_value)
        await state.update_data(
            collection_id=collection_id,
            field=field
        )

        await callback.message.answer(
            f"📝 请输入新的{field_names.get(field, field)}:"
        )

    await callback.answer()


@router.message(EditCollectionStates.waiting_for_value)
async def handle_edit_value(message: Message, user: User, db: AsyncSession, state: FSMContext):
    """处理编辑值输入"""
    data = await state.get_data()
    collection_id = data.get("collection_id")
    field = data.get("field")
    value = message.text.strip()

    try:
        # 验证和处理值
        if field == "name":
            if not value or len(value) > 100:
                await message.answer("❌ 名称长度必须在 1-100 字符之间")
                return
            if any(char in value for char in '<>/\\|:*?"'):
                await message.answer("❌ 名称不能包含特殊字符")
                return
            await update_collection(db, collection_id, name=value)

        elif field == "description":
            if len(value) > 500:
                await message.answer("❌ 描述长度不能超过 500 字符")
                return
            await update_collection(db, collection_id, description=value)

        elif field == "tags":
            tags = value.split()
            if len(tags) > 10:
                await message.answer("❌ 标签数量不能超过 10 个")
                return
            for tag in tags:
                if len(tag) > 20:
                    await message.answer(f"❌ 标签 '{tag}' 长度超过 20 字符")
                    return
            await update_collection(db, collection_id, tags=tags)

        # 记录日志
        await create_admin_log(
            db,
            user_id=user.id,
            action="edit_collection",
            details={
                "collection_id": collection_id,
                "field": field,
                "new_value": value
            }
        )

        await state.clear()
        await message.answer("✅ 更新成功")

    except Exception as e:
        await message.answer(f"❌ 更新失败: {str(e)}")


@router.callback_query(F.data.startswith("update_access_"))
async def callback_update_access(callback: CallbackQuery, user: User, db: AsyncSession):
    """更新访问权限"""
    parts = callback.data.split("_")
    collection_id = int(parts[2])
    access_level = AccessLevel.PUBLIC if parts[3] == "public" else AccessLevel.VIP

    try:
        await update_collection(db, collection_id, access_level=access_level)

        # 记录日志
        await create_admin_log(
            db,
            user_id=user.id,
            action="edit_collection",
            details={
                "collection_id": collection_id,
                "field": "access_level",
                "new_value": access_level.value
            }
        )

        access_text = "💎 VIP" if access_level == AccessLevel.VIP else "🌍 公开"
        await callback.message.edit_text(f"✅ 访问权限已更新为: {access_text}")
        await callback.answer("✅ 更新成功")

    except Exception as e:
        await callback.message.edit_text(f"❌ 更新失败: {str(e)}")
        await callback.answer("❌ 更新失败", show_alert=True)


# ==================== 批量删除合集 ====================

@router.message(Command("batch_delete"))
@require_admin
async def cmd_batch_delete(message: Message, state: FSMContext):
    """
    批量删除合集

    命令: /batch_delete
    """
    await state.clear()
    await state.set_state(BatchDeleteStates.waiting_for_codes)

    await message.answer(
        "🗑️ 批量删除合集\n\n"
        "请发送要删除的深链接码（每行一个）\n\n"
        "示例:\n"
        "abc123\n"
        "def456\n"
        "ghi789\n\n"
        "💡 提示: 发送 /cancel 可随时取消"
    )


@router.message(BatchDeleteStates.waiting_for_codes)
async def handle_batch_delete_codes(message: Message, user: User, db: AsyncSession, state: FSMContext):
    """处理批量删除的深链接码"""
    codes = [line.strip() for line in message.text.strip().split('\n') if line.strip()]

    if not codes:
        await message.answer("❌ 请输入至少一个深链接码")
        return

    # 查询合集
    collections = []
    for code in codes:
        collection = await get_collection_by_code(db, code)
        if collection:
            collections.append(collection)

    if not collections:
        await message.answer("❌ 没有找到任何合集")
        return

    # 显示确认信息
    text = f"⚠️ 确认删除以下 {len(collections)} 个合集？\n\n"
    for collection in collections:
        text += f"• {collection.name} ({collection.deep_link_code})\n"

    text += "\n此操作不可撤销！"

    # 保存合集 ID 列表
    collection_ids = [c.id for c in collections]
    await state.update_data(collection_ids=collection_ids)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✅ 确认删除",
                callback_data="confirm_batch_delete"
            ),
            InlineKeyboardButton(
                text="❌ 取消",
                callback_data="cancel_batch_delete"
            )
        ]
    ])

    await message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data == "confirm_batch_delete")
async def callback_confirm_batch_delete(callback: CallbackQuery, user: User, db: AsyncSession, state: FSMContext):
    """确认批量删除"""
    data = await state.get_data()
    collection_ids = data.get("collection_ids", [])

    try:
        deleted_count = 0
        for collection_id in collection_ids:
            success = await delete_collection(db, collection_id)
            if success:
                deleted_count += 1

        # 记录日志
        await create_admin_log(
            db,
            user_id=user.id,
            action="batch_delete_collections",
            details={
                "collection_ids": collection_ids,
                "deleted_count": deleted_count
            }
        )

        await state.clear()
        await callback.message.edit_text(f"✅ 已删除 {deleted_count} 个合集")
        await callback.answer("✅ 删除成功")

    except Exception as e:
        await callback.message.edit_text(f"❌ 删除失败: {str(e)}")
        await callback.answer("❌ 删除失败", show_alert=True)


@router.callback_query(F.data == "cancel_batch_delete")
async def callback_cancel_batch_delete(callback: CallbackQuery, state: FSMContext):
    """取消批量删除"""
    await state.clear()
    await callback.message.edit_text("✅ 已取消批量删除")
    await callback.answer()
