# web/api/users.py
"""
用户管理 API
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from database.connection import get_db
from database.crud import (
    get_users,
    get_user,
    update_user_role,
    ban_user,
    create_admin_log
)
from database.models import UserRole
from web.schemas import (
    UserListResponse,
    UserResponse,
    UpdateRoleRequest,
    BanUserRequest,
    SuccessResponse
)
from web.dependencies import require_admin, require_super_admin

router = APIRouter()


@router.get("", response_model=UserListResponse)
async def list_users(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    role: Optional[str] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    获取用户列表

    需要管理员权限
    """
    skip = (page - 1) * limit

    # 转换 role
    role_filter = None
    if role:
        try:
            role_filter = UserRole(role)
        except ValueError:
            pass

    users, total = await get_users(
        db,
        skip=skip,
        limit=limit,
        role=role_filter,
        search=search
    )

    return UserListResponse(
        users=[UserResponse.from_orm(u) for u in users],
        total=total,
        page=page,
        limit=limit
    )


@router.put("/{user_id}/role", response_model=SuccessResponse)
async def update_user_role_endpoint(
    user_id: int,
    request: UpdateRoleRequest,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_super_admin)
):
    """
    修改用户角色

    需要超级管理员权限
    """
    user = await get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 验证角色
    try:
        new_role = UserRole(request.role)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的角色")

    # 不能修改自己的角色
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="不能修改自己的角色")

    # 更新角色
    success = await update_user_role(db, user_id, new_role)
    if not success:
        raise HTTPException(status_code=500, detail="更新失败")

    # 记录日志
    await create_admin_log(
        db,
        user_id=current_user.id,
        action="update_user_role",
        details={
            "target_user_id": user_id,
            "old_role": user.role.value,
            "new_role": new_role.value
        }
    )

    return SuccessResponse(message="角色更新成功")


@router.put("/{user_id}/ban", response_model=SuccessResponse)
async def ban_user_endpoint(
    user_id: int,
    request: BanUserRequest,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    封禁/解封用户

    需要管理员权限
    """
    user = await get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 不能封禁自己
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="不能封禁自己")

    # 不能封禁管理员（除非是超级管理员）
    if user.role in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
        if current_user.role != UserRole.SUPER_ADMIN:
            raise HTTPException(status_code=403, detail="权限不足")

    # 更新封禁状态
    success = await ban_user(db, user_id, request.is_banned)
    if not success:
        raise HTTPException(status_code=500, detail="操作失败")

    # 记录日志
    await create_admin_log(
        db,
        user_id=current_user.id,
        action="ban_user" if request.is_banned else "unban_user",
        details={"target_user_id": user_id}
    )

    message = "用户已封禁" if request.is_banned else "用户已解封"
    return SuccessResponse(message=message)
