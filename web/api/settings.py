# web/api/settings.py
"""
系统设置 API
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db
from database.crud import (
    get_all_settings,
    set_setting,
    create_admin_log
)
from web.schemas import (
    SettingsResponse,
    SettingsUpdateRequest,
    SuccessResponse
)
from web.dependencies import require_admin, require_super_admin

router = APIRouter()


@router.get("", response_model=SettingsResponse)
async def get_settings(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    获取系统设置

    需要管理员权限
    """
    settings_dict = await get_all_settings(db)

    return SettingsResponse(
        welcome_message=settings_dict.get("welcome_message", "欢迎使用 BlackHoleBot！"),
        bot_name=settings_dict.get("bot_name", "BlackHoleBot"),
        max_media_per_collection=int(settings_dict.get("max_media_per_collection", "1000"))
    )


@router.put("", response_model=SuccessResponse)
async def update_settings(
    update_data: SettingsUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_super_admin)
):
    """
    更新系统设置

    需要超级管理员权限
    """
    updates = {}

    if update_data.welcome_message is not None:
        await set_setting(db, "welcome_message", update_data.welcome_message)
        updates["welcome_message"] = update_data.welcome_message

    if update_data.bot_name is not None:
        await set_setting(db, "bot_name", update_data.bot_name)
        updates["bot_name"] = update_data.bot_name

    if update_data.max_media_per_collection is not None:
        await set_setting(
            db,
            "max_media_per_collection",
            str(update_data.max_media_per_collection)
        )
        updates["max_media_per_collection"] = update_data.max_media_per_collection

    # 记录日志
    await create_admin_log(
        db,
        user_id=current_user.id,
        action="update_settings",
        details=updates
    )

    return SuccessResponse(message="设置已更新")
