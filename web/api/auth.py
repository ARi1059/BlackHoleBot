# web/api/auth.py
"""
认证相关 API
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
import hashlib
import hmac
from datetime import datetime, timedelta
from jose import jwt

from database.connection import get_db
from database.crud import get_user_by_telegram_id
from database.models import UserRole
from web.schemas import TelegramAuthData, TokenResponse, UserInfo
from web.dependencies import get_current_user
from config import settings

router = APIRouter()


def verify_telegram_auth(auth_data: dict, bot_token: str) -> bool:
    """
    验证 Telegram Login 数据

    Args:
        auth_data: Telegram 认证数据
        bot_token: Bot Token

    Returns:
        验证是否通过
    """
    check_hash = auth_data.pop("hash")

    # 构建数据检查字符串
    data_check_string = "\n".join(
        f"{k}={v}" for k, v in sorted(auth_data.items())
    )

    # 计算密钥
    secret_key = hashlib.sha256(bot_token.encode()).digest()

    # 计算哈希
    calculated_hash = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256
    ).hexdigest()

    return calculated_hash == check_hash


def create_access_token(data: dict) -> str:
    """
    创建 JWT token

    Args:
        data: 要编码的数据

    Returns:
        JWT token
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.JWT_EXPIRE_DAYS)
    to_encode.update({"exp": expire})

    return jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )


@router.post("/telegram", response_model=TokenResponse)
async def telegram_login(
    auth_data: TelegramAuthData,
    db: AsyncSession = Depends(get_db)
):
    """
    Telegram 登录

    验证 Telegram Login Widget 返回的数据，并生成 JWT token
    """
    # 验证数据
    auth_dict = auth_data.dict()
    if not verify_telegram_auth(auth_dict.copy(), settings.BOT_TOKEN):
        raise HTTPException(status_code=401, detail="认证失败")

    # 检查认证时间（防止重放攻击）
    auth_time = datetime.fromtimestamp(auth_data.auth_date)
    if datetime.utcnow() - auth_time > timedelta(hours=1):
        raise HTTPException(status_code=401, detail="认证已过期")

    # 获取用户
    async for session in get_db():
        user = await get_user_by_telegram_id(session, auth_data.id)
        if not user:
            raise HTTPException(status_code=403, detail="用户不存在")

        # 检查权限
        if user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
            raise HTTPException(status_code=403, detail="权限不足，仅管理员可访问")

        # 检查是否被封禁
        if user.is_banned:
            raise HTTPException(status_code=403, detail="账号已被封禁")

        # 生成 token
        token = create_access_token(
            data={"user_id": user.id, "role": user.role.value}
        )

        return TokenResponse(
            access_token=token,
            token_type="bearer",
            user={
                "id": user.telegram_id,
                "username": user.username,
                "first_name": user.first_name,
                "role": user.role.value
            }
        )


@router.get("/me", response_model=UserInfo)
async def get_current_user_info(
    current_user = Depends(get_current_user)
):
    """
    获取当前用户信息

    需要认证
    """
    return UserInfo(
        id=current_user.id,
        telegram_id=current_user.telegram_id,
        username=current_user.username,
        first_name=current_user.first_name,
        role=current_user.role.value,
        created_at=current_user.created_at
    )
