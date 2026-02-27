# web/api/auth.py
"""
认证相关 API
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
import hashlib
import hmac
from datetime import datetime, timedelta
from jose import jwt

from database.connection import get_db, redis_client
from database.crud import get_user_by_telegram_id
from database.models import UserRole
from web.schemas import TelegramAuthData, TokenResponse, UserInfo
from web.dependencies import get_current_user
from config import settings

router = APIRouter()


class LoginRequest(BaseModel):
    """登录请求"""
    telegram_id: int
    password: str


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


async def _validate_and_login(db: AsyncSession, telegram_id: int) -> TokenResponse:
    """
    验证用户权限并生成登录凭证（公共逻辑）

    Args:
        db: 数据库 session
        telegram_id: 用户 Telegram ID

    Returns:
        TokenResponse

    Raises:
        HTTPException: 用户不存在、权限不足或已封禁
    """
    user = await get_user_by_telegram_id(db, telegram_id)
    if not user:
        raise HTTPException(status_code=403, detail="用户不存在")

    if user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
        raise HTTPException(status_code=403, detail="权限不足，仅管理员可访问")

    if user.is_banned:
        raise HTTPException(status_code=403, detail="账号已被封禁")

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


@router.post("/login", response_model=TokenResponse)
async def login_with_code(
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    使用验证码登录

    用户在 Bot 中使用 /login 命令获取验证码，然后在此接口验证
    """
    # 从 Redis 获取验证码
    redis_key = f"web_login:{login_data.telegram_id}"
    fail_key = f"web_login_fail:{login_data.telegram_id}"
    stored_code = await redis_client.get(redis_key)

    if not stored_code:
        raise HTTPException(status_code=401, detail="验证码不存在或已过期，请在 Bot 中发送 /login 获取新验证码")

    # 检查失败次数（最多允许 5 次尝试）
    fail_count = await redis_client.get(fail_key)
    if fail_count and int(fail_count) >= 5:
        # 超过限制，直接删除验证码使其失效
        await redis_client.delete(redis_key)
        await redis_client.delete(fail_key)
        raise HTTPException(status_code=429, detail="验证码尝试次数过多，请重新获取验证码")

    # 验证验证码（Redis 已配置 decode_responses=True，返回的是字符串）
    if stored_code != login_data.password:
        # 记录失败次数，过期时间与验证码一致（5分钟）
        await redis_client.incr(fail_key)
        await redis_client.expire(fail_key, 300)
        raise HTTPException(status_code=401, detail="验证码错误")

    # 验证通过，删除验证码和失败计数
    await redis_client.delete(redis_key)
    await redis_client.delete(fail_key)

    return await _validate_and_login(db, login_data.telegram_id)


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

    # 检查认证时间（防止重放攻击，统一使用 UTC 时间）
    auth_time = datetime.utcfromtimestamp(auth_data.auth_date)
    if datetime.utcnow() - auth_time > timedelta(hours=1):
        raise HTTPException(status_code=401, detail="认证已过期")

    return await _validate_and_login(db, auth_data.id)


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
