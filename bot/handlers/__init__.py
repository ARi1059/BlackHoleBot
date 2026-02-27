# bot/handlers/__init__.py
"""
处理器模块
"""

from .user import router as user_router
from .admin import router as admin_router
from .transfer import router as transfer_router
from .transfer_admin import router as transfer_admin_router
from .transfer_approve import router as transfer_approve_router
from .user_management import router as user_management_router

__all__ = [
    "user_router",
    "admin_router",
    "transfer_router",
    "transfer_admin_router",
    "transfer_approve_router",
    "user_management_router"
]
