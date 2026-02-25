# web/api/collections.py
"""
合集管理 API
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from database.connection import get_db
from database.crud import (
    get_collections,
    get_collection,
    update_collection,
    delete_collection,
    create_admin_log
)
from database.models import AccessLevel
from web.schemas import (
    CollectionListResponse,
    CollectionResponse,
    CollectionUpdate,
    SuccessResponse,
    BatchDeleteRequest
)
from web.dependencies import require_admin

router = APIRouter()


@router.get("", response_model=CollectionListResponse)
async def list_collections(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    access_level: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    获取合集列表

    需要管理员权限
    """
    skip = (page - 1) * limit

    # 转换 access_level
    access_filter = None
    if access_level:
        try:
            access_filter = AccessLevel(access_level)
        except ValueError:
            pass

    collections, total = await get_collections(
        db,
        skip=skip,
        limit=limit,
        access_level=access_filter,
        search=search
    )

    return CollectionListResponse(
        collections=[CollectionResponse.from_orm(c) for c in collections],
        total=total,
        page=page,
        limit=limit
    )


@router.get("/{collection_id}", response_model=CollectionResponse)
async def get_collection_detail(
    collection_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    获取合集详情

    需要管理员权限
    """
    collection = await get_collection(db, collection_id)
    if not collection:
        raise HTTPException(status_code=404, detail="合集不存在")

    return CollectionResponse.from_orm(collection)


@router.put("/{collection_id}", response_model=SuccessResponse)
async def update_collection_info(
    collection_id: int,
    data: CollectionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    更新合集信息

    需要管理员权限
    """
    collection = await get_collection(db, collection_id)
    if not collection:
        raise HTTPException(status_code=404, detail="合集不存在")

    # 准备更新数据
    update_data = {}
    if data.name is not None:
        update_data["name"] = data.name
    if data.description is not None:
        update_data["description"] = data.description
    if data.tags is not None:
        update_data["tags"] = data.tags
    if data.access_level is not None:
        try:
            update_data["access_level"] = AccessLevel(data.access_level).value
        except ValueError:
            raise HTTPException(status_code=400, detail="无效的访问权限")

    # 更新
    success = await update_collection(db, collection_id, **update_data)
    if not success:
        raise HTTPException(status_code=500, detail="更新失败")

    # 记录日志
    await create_admin_log(
        db,
        user_id=current_user.id,
        action="update_collection",
        details={
            "collection_id": collection_id,
            "updates": update_data
        }
    )

    return SuccessResponse(message="更新成功")


@router.delete("/{collection_id}", response_model=SuccessResponse)
async def delete_collection_by_id(
    collection_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    删除合集

    需要管理员权限
    """
    collection = await get_collection(db, collection_id)
    if not collection:
        raise HTTPException(status_code=404, detail="合集不存在")

    success = await delete_collection(db, collection_id)
    if not success:
        raise HTTPException(status_code=500, detail="删除失败")

    # 记录日志
    await create_admin_log(
        db,
        user_id=current_user.id,
        action="delete_collection",
        details={"collection_id": collection_id}
    )

    return SuccessResponse(message="删除成功")


@router.post("/batch-delete", response_model=SuccessResponse)
async def batch_delete_collections(
    request: BatchDeleteRequest,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    批量删除合集

    需要管理员权限
    """
    deleted_count = 0
    for collection_id in request.collection_ids:
        success = await delete_collection(db, collection_id)
        if success:
            deleted_count += 1

    # 记录日志
    await create_admin_log(
        db,
        user_id=current_user.id,
        action="batch_delete_collections",
        details={
            "collection_ids": request.collection_ids,
            "deleted_count": deleted_count
        }
    )

    return SuccessResponse(message=f"已删除 {deleted_count} 个合集")


@router.post("/{collection_id}/trigger-add-media", response_model=SuccessResponse)
async def trigger_add_media(
    collection_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    触发 Bot 向指定合集添加媒体

    直接将用户状态设置为添加媒体状态，无需手动输入命令

    需要管理员权限
    """
    from aiogram import Bot
    from aiogram.fsm.context import FSMContext
    from aiogram.fsm.storage.redis import RedisStorage, DefaultKeyBuilder
    from config import settings
    import redis.asyncio as redis

    # 检查合集是否存在
    collection = await get_collection(db, collection_id)
    if not collection:
        raise HTTPException(status_code=404, detail="合集不存在")

    try:
        # 创建临时 Bot 实例
        bot = Bot(token=settings.BOT_TOKEN)

        # 创建 Redis 存储
        redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        storage = RedisStorage(redis_client, key_builder=DefaultKeyBuilder(with_destiny=True))

        # 获取 FSM 上下文
        from bot.states import AddMediaStates
        from aiogram.fsm.storage.base import StorageKey

        key = StorageKey(
            bot_id=bot.id,
            chat_id=current_user.telegram_id,
            user_id=current_user.telegram_id
        )

        state = FSMContext(storage=storage, key=key)

        # 设置状态和数据
        await state.set_state(AddMediaStates.waiting_for_media)
        await state.update_data(
            collection_id=collection_id,
            collection_name=collection.name,
            media_list=[],
            current_media_count=collection.media_count
        )

        # 向管理员发送通知
        await bot.send_message(
            current_user.telegram_id,
            f"📤 开始向合集添加媒体\n\n"
            f"📦 合集: {collection.name}\n"
            f"📊 当前媒体数: {collection.media_count}\n\n"
            f"请直接发送媒体文件（图片或视频）\n"
            f"• 可以一次发送多个文件\n"
            f"• 支持媒体组（最多10个）\n"
            f"• 完成后发送 /done\n\n"
            f"💡 提示: 发送 /cancel 可随时取消"
        )

        # 关闭连接
        await bot.session.close()
        await redis_client.aclose()

        # 记录日志
        await create_admin_log(
            db,
            user_id=current_user.id,
            action="trigger_add_media",
            details={
                "collection_id": collection_id,
                "collection_name": collection.name
            }
        )

        return SuccessResponse(message="已进入添加媒体模式，请在 Telegram 中发送媒体文件")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"操作失败: {str(e)}")

