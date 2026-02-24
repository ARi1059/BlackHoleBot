# bot/middlewares/__init__.py
"""
中间件模块
"""

from .auth import AuthMiddleware

__all__ = ["AuthMiddleware"]
