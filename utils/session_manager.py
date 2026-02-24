# utils/session_manager.py
"""
Telegram Session 账号管理器
"""

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict
from datetime import datetime, timedelta

from database.crud import (
    create_session_account,
    get_session_account,
    get_available_session,
    update_session_account
)
from database.models import SessionAccount
from utils.encryption import session_encryption
from config import settings


class SessionManager:
    """Session 账号管理器"""

    def __init__(self):
        self.active_clients: Dict[int, TelegramClient] = {}

    async def login_session(
        self,
        phone: str,
        api_id: int,
        api_hash: str,
        code: Optional[str] = None,
        password: Optional[str] = None
    ) -> Dict[str, str]:
        """
        登录 Telegram 账号

        Args:
            phone: 手机号
            api_id: API ID
            api_hash: API Hash
            code: 验证码（可选）
            password: 两步验证密码（可选）

        Returns:
            登录结果字典
        """
        client = TelegramClient(
            StringSession(),
            api_id,
            api_hash
        )

        await client.connect()

        try:
            if not code:
                # 发送验证码
                await client.send_code_request(phone)
                await client.disconnect()
                return {
                    "status": "code_sent",
                    "message": "验证码已发送到手机"
                }

            # 使用验证码登录
            try:
                await client.sign_in(phone, code)
            except SessionPasswordNeededError:
                if not password:
                    await client.disconnect()
                    return {
                        "status": "password_required",
                        "message": "需要两步验证密码"
                    }
                await client.sign_in(password=password)
            except PhoneCodeInvalidError:
                await client.disconnect()
                return {
                    "status": "error",
                    "message": "验证码无效"
                }

            # 获取 session_string
            session_string = client.session.save()

            await client.disconnect()

            return {
                "status": "success",
                "session_string": session_string,
                "message": "登录成功"
            }

        except Exception as e:
            await client.disconnect()
            return {
                "status": "error",
                "message": f"登录失败: {str(e)}"
            }

    async def add_session_account(
        self,
        db: AsyncSession,
        phone_number: str,
        api_id: int,
        api_hash: str,
        session_string: str,
        priority: int = 0
    ) -> SessionAccount:
        """
        添加 Session 账号到数据库

        Args:
            db: 数据库 session
            phone_number: 手机号
            api_id: API ID
            api_hash: API Hash
            session_string: Session 字符串
            priority: 优先级

        Returns:
            创建的 SessionAccount 对象
        """
        # 加密 session_string
        encrypted_session = session_encryption.encrypt(session_string)

        # 保存到数据库
        session_account = await create_session_account(
            db,
            phone_number=phone_number,
            api_id=api_id,
            api_hash=api_hash,
            session_string=encrypted_session,
            priority=priority
        )

        return session_account

    async def get_client(
        self,
        db: AsyncSession,
        session_id: int
    ) -> Optional[TelegramClient]:
        """
        获取 Telethon 客户端

        Args:
            db: 数据库 session
            session_id: Session 账号 ID

        Returns:
            TelegramClient 实例
        """
        # 检查是否已有活跃客户端
        if session_id in self.active_clients:
            return self.active_clients[session_id]

        # 从数据库获取 session 账号
        session_account = await get_session_account(db, session_id)
        if not session_account or not session_account.is_active:
            return None

        # 解密 session_string
        session_string = session_encryption.decrypt(session_account.session_string)

        # 创建客户端
        client = TelegramClient(
            StringSession(session_string),
            session_account.api_id,
            session_account.api_hash
        )

        await client.connect()

        # 缓存客户端
        self.active_clients[session_id] = client

        return client

    async def disconnect_client(self, session_id: int):
        """
        断开客户端连接

        Args:
            session_id: Session 账号 ID
        """
        if session_id in self.active_clients:
            client = self.active_clients[session_id]
            await client.disconnect()
            del self.active_clients[session_id]

    async def disconnect_all(self):
        """断开所有客户端连接"""
        for session_id in list(self.active_clients.keys()):
            await self.disconnect_client(session_id)

    async def get_next_available_session(
        self,
        db: AsyncSession
    ) -> Optional[SessionAccount]:
        """
        获取下一个可用的 Session 账号

        Args:
            db: 数据库 session

        Returns:
            可用的 SessionAccount，如果没有则返回 None
        """
        return await get_available_session(db)

    async def set_session_cooldown(
        self,
        db: AsyncSession,
        session_id: int,
        cooldown_minutes: int
    ):
        """
        设置 Session 冷却时间

        Args:
            db: 数据库 session
            session_id: Session 账号 ID
            cooldown_minutes: 冷却分钟数
        """
        cooldown_until = datetime.now() + timedelta(minutes=cooldown_minutes)
        await update_session_account(
            db,
            session_id,
            cooldown_until=cooldown_until,
            transfer_count=0  # 重置计数
        )

    async def increment_transfer_count(
        self,
        db: AsyncSession,
        session_id: int
    ) -> int:
        """
        增加转发计数

        Args:
            db: 数据库 session
            session_id: Session 账号 ID

        Returns:
            更新后的计数
        """
        session_account = await get_session_account(db, session_id)
        if not session_account:
            return 0

        new_count = session_account.transfer_count + 1
        await update_session_account(
            db,
            session_id,
            transfer_count=new_count,
            last_transfer_time=datetime.now(),
            last_used_at=datetime.now()
        )

        return new_count

    async def check_transfer_limit(
        self,
        db: AsyncSession,
        session_id: int
    ) -> bool:
        """
        检查是否达到转发限制

        Args:
            db: 数据库 session
            session_id: Session 账号 ID

        Returns:
            True 表示需要冷却，False 表示可以继续
        """
        session_account = await get_session_account(db, session_id)
        if not session_account:
            return True

        return session_account.transfer_count >= settings.TRANSFER_LIMIT_PER_SESSION


# 全局 Session 管理器实例
session_manager = SessionManager()
