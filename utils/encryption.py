# utils/encryption.py
"""
Session 加密工具
"""

from cryptography.fernet import Fernet
from config import settings


class SessionEncryption:
    """Session 字符串加密/解密"""

    def __init__(self):
        # 从配置读取加密密钥
        self.cipher = Fernet(settings.SESSION_ENCRYPTION_KEY.encode())

    def encrypt(self, session_string: str) -> str:
        """
        加密 session 字符串

        Args:
            session_string: 原始 session 字符串

        Returns:
            加密后的字符串
        """
        return self.cipher.encrypt(session_string.encode()).decode()

    def decrypt(self, encrypted_session: str) -> str:
        """
        解密 session 字符串

        Args:
            encrypted_session: 加密的 session 字符串

        Returns:
            解密后的原始字符串
        """
        return self.cipher.decrypt(encrypted_session.encode()).decode()


# 全局加密实例
session_encryption = SessionEncryption()
