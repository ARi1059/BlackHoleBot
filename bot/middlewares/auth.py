# bot/middlewares/auth.py
"""
用户认证中间件
"""

from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession

from database import UserRole
from database.crud import get_user_by_telegram_id, create_user, update_user_last_active
from database.connection import async_session_maker


class AuthMiddleware(BaseMiddleware):
    """
    用户认证中间件

    功能：
    1. 自动注册新用户
    2. 检查用户封禁状态
    3. 更新用户最后活跃时间
    4. 将用户信息注入到 handler
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # 获取用户信息
        user_obj = None
        if isinstance(event, Message):
            user_obj = event.from_user
        elif isinstance(event, CallbackQuery):
            user_obj = event.from_user

        if not user_obj:
            return await handler(event, data)

        # 获取数据库 session
        async with async_session_maker() as db:
            # 查询或创建用户
            user = await get_user_by_telegram_id(db, user_obj.id)

            if not user:
                # 自动注册新用户
                user = await create_user(
                    db,
                    telegram_id=user_obj.id,
                    username=user_obj.username,
                    first_name=user_obj.first_name,
                    last_name=user_obj.last_name,
                    role=UserRole.USER
                )
            else:
                # 更新最后活跃时间
                await update_user_last_active(db, user.id)
                # 刷新用户对象以获取最新数据
                await db.refresh(user)

            # 检查封禁状态
            if user.is_banned:
                if isinstance(event, Message):
                    await event.answer(
                        "🚫 您已被管理员封禁\n\n"
                        "如有疑问，请联系管理员"
                    )
                elif isinstance(event, CallbackQuery):
                    await event.answer("🚫 您已被封禁", show_alert=True)
                return

            # 将用户信息注入到 handler
            data["user"] = user
            data["db"] = db

        return await handler(event, data)
