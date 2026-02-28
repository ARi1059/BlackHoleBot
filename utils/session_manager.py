# utils/session_manager.py
"""
Telegram Session 账号管理器
"""

import logging
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

logger = logging.getLogger(__name__)


class SessionManager:
    """Session 账号管理器"""

    def __init__(self):
        self.active_clients: Dict[int, TelegramClient] = {}
        self.login_clients: Dict[str, TelegramClient] = {}  # 用于保存登录过程中的客户端

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
        # 使用手机号作为 key 来保存登录过程中的客户端
        client_key = phone

        try:
            if not code:
                # 第一步：发送验证码
                logger.info(f"Session 登录第一步: 向手机号发送验证码")
                client = TelegramClient(
                    StringSession(),
                    api_id,
                    api_hash
                )
                await client.connect()
                await client.send_code_request(phone)

                # 保存客户端供后续步骤使用
                self.login_clients[client_key] = client
                logger.info(f"验证码已发送，客户端已缓存")

                return {
                    "status": "code_sent",
                    "message": "验证码已发送到手机"
                }

            # 获取之前保存的客户端
            if client_key not in self.login_clients:
                # 如果没有保存的客户端，创建新的
                client = TelegramClient(
                    StringSession(),
                    api_id,
                    api_hash
                )
                await client.connect()
                self.login_clients[client_key] = client
            else:
                client = self.login_clients[client_key]

            # 使用验证码登录
            try:
                await client.sign_in(phone, code)
            except SessionPasswordNeededError:
                if not password:
                    # 需要两步验证密码，保持客户端连接
                    return {
                        "status": "password_required",
                        "message": "需要两步验证密码"
                    }
                # 使用两步验证密码登录
                await client.sign_in(password=password)
            except PhoneCodeInvalidError:
                # 验证码无效，清理客户端
                logger.warning(f"Session 登录失败: 验证码无效")
                await client.disconnect()
                del self.login_clients[client_key]
                return {
                    "status": "error",
                    "message": "验证码无效"
                }

            # 登录成功，获取 session_string
            logger.info(f"Session 登录成功，获取 session_string")
            session_string = client.session.save()

            # 清理客户端
            await client.disconnect()
            if client_key in self.login_clients:
                del self.login_clients[client_key]

            return {
                "status": "success",
                "session_string": session_string,
                "message": "登录成功"
            }

        except Exception as e:
            # 出错时清理客户端
            logger.error(f"Session 登录异常: {str(e)}", exc_info=True)
            if client_key in self.login_clients:
                try:
                    await self.login_clients[client_key].disconnect()
                except:
                    pass
                del self.login_clients[client_key]

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

        logger.info(f"Session 账号已添加到数据库, session_id={session_account.id}, priority={priority}")
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
            logger.debug(f"复用已有 Telethon 客户端, session_id={session_id}")
            return self.active_clients[session_id]

        # 从数据库获取 session 账号
        session_account = await get_session_account(db, session_id)
        if not session_account or not session_account.is_active:
            logger.warning(f"Session {session_id} 不存在或未激活")
            return None

        # 解密 session_string
        session_string = session_encryption.decrypt(session_account.session_string)

        # 创建客户端
        logger.info(f"创建新的 Telethon 客户端, session_id={session_id}")
        client = TelegramClient(
            StringSession(session_string),
            session_account.api_id,
            session_account.api_hash
        )

        await client.connect()
        logger.info(f"Telethon 客户端已连接, session_id={session_id}")

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
            logger.info(f"Telethon 客户端已断开, session_id={session_id}")
        else:
            logger.debug(f"尝试断开不存在的客户端, session_id={session_id}")

    async def disconnect_all(self):
        """断开所有客户端连接"""
        count = len(self.active_clients)
        logger.info(f"断开所有 Telethon 客户端, 共 {count} 个")
        for session_id in list(self.active_clients.keys()):
            await self.disconnect_client(session_id)
        logger.info("所有 Telethon 客户端已断开")

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
        logger.info(f"Session {session_id} 进入冷却, 冷却 {cooldown_minutes} 分钟, 恢复时间: {cooldown_until.strftime('%H:%M:%S')}")

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
