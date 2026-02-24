# web/api/sessions.py
"""
Session 账号管理 API
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from database.connection import get_db
from database.crud import (
    get_all_sessions,
    get_session_account,
    update_session_account,
    create_admin_log
)
from database.models import SessionAccount
from web.schemas import (
    SessionLoginRequest,
    SessionResponse,
    SessionUpdateRequest,
    SuccessResponse
)
from web.dependencies import require_admin
from utils.session_manager import session_manager

router = APIRouter()


@router.get("", response_model=List[SessionResponse])
async def list_sessions(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    获取 Session 账号列表

    需要管理员权限
    """
    sessions = await get_all_sessions(db)
    return [SessionResponse.from_orm(s) for s in sessions]


@router.post("/login", response_model=dict)
async def login_session(
    login_data: SessionLoginRequest,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    登录 Session 账号

    需要管理员权限

    分步骤登录：
    1. 发送验证码
    2. 输入验证码登录
    3. （如需要）输入两步验证密码
    """
    # 调用 session_manager 登录
    result = await session_manager.login_session(
        phone=login_data.phone_number,
        api_id=login_data.api_id,
        api_hash=login_data.api_hash,
        code=login_data.code,
        password=login_data.password
    )

    # 如果登录成功，保存到数据库
    if result["status"] == "success":
        session_account = await session_manager.add_session_account(
            db,
            phone_number=login_data.phone_number,
            api_id=login_data.api_id,
            api_hash=login_data.api_hash,
            session_string=result["session_string"],
            priority=0
        )

        # 记录日志
        await create_admin_log(
            db,
            user_id=current_user.id,
            action="add_session_account",
            details={
                "session_id": session_account.id,
                "phone_number": login_data.phone_number
            }
        )

        return {
            "success": True,
            "session_id": session_account.id,
            "message": "登录成功"
        }

    elif result["status"] == "code_sent":
        return {
            "success": True,
            "message": result["message"]
        }

    elif result["status"] == "password_required":
        return {
            "success": False,
            "password_required": True,
            "message": result["message"]
        }

    else:
        return {
            "success": False,
            "message": result.get("message", "登录失败")
        }


@router.put("/{session_id}", response_model=SuccessResponse)
async def update_session(
    session_id: int,
    update_data: SessionUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    更新 Session 账号

    需要管理员权限
    """
    session = await get_session_account(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session 账号不存在")

    # 准备更新数据
    update_dict = {}
    if update_data.priority is not None:
        update_dict["priority"] = update_data.priority
    if update_data.is_active is not None:
        update_dict["is_active"] = update_data.is_active

    # 更新
    success = await update_session_account(db, session_id, **update_dict)
    if not success:
        raise HTTPException(status_code=500, detail="更新失败")

    # 记录日志
    await create_admin_log(
        db,
        user_id=current_user.id,
        action="update_session_account",
        details={
            "session_id": session_id,
            "updates": update_dict
        }
    )

    return SuccessResponse(message="更新成功")


@router.delete("/{session_id}", response_model=SuccessResponse)
async def delete_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    删除 Session 账号

    需要管理员权限
    """
    from sqlalchemy import delete as sql_delete

    session = await get_session_account(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session 账号不存在")

    # 删除
    await db.execute(
        sql_delete(SessionAccount).where(SessionAccount.id == session_id)
    )
    await db.commit()

    # 记录日志
    await create_admin_log(
        db,
        user_id=current_user.id,
        action="delete_session_account",
        details={"session_id": session_id}
    )

    return SuccessResponse(message="账号已删除")
