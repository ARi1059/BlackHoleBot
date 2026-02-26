# web/schemas.py
"""
Pydantic 数据模型
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Union
from datetime import datetime, date


# ==================== 认证相关 ====================

class TelegramAuthData(BaseModel):
    """Telegram 登录数据"""
    id: int
    first_name: str
    username: Optional[str] = None
    photo_url: Optional[str] = None
    auth_date: int
    hash: str


class TokenResponse(BaseModel):
    """Token 响应"""
    access_token: str
    token_type: str = "bearer"
    user: dict


class UserInfo(BaseModel):
    """用户信息"""
    id: int
    telegram_id: int
    username: Optional[str]
    first_name: Optional[str]
    role: str
    created_at: datetime


# ==================== 仪表盘相关 ====================

class DashboardStats(BaseModel):
    """仪表盘统计数据"""
    total_users: int
    total_vip_users: int
    total_collections: int
    total_media: int
    public_collections: int
    vip_collections: int
    active_tasks: int
    completed_tasks: int


class ActivityItem(BaseModel):
    """活动项"""
    id: int
    type: str
    user: str
    description: str
    created_at: datetime


class RecentActivity(BaseModel):
    """最近活动"""
    activities: List[ActivityItem]


# ==================== 合集相关 ====================

class CollectionBase(BaseModel):
    """合集基础信息"""
    name: str
    description: Optional[str] = None
    tags: List[str] = []
    access_level: str


class CollectionCreate(CollectionBase):
    """创建合集"""
    pass


class CollectionUpdate(BaseModel):
    """更新合集"""
    name: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    access_level: Optional[str] = None


class CollectionResponse(CollectionBase):
    """合集响应"""
    id: int
    deep_link_code: str
    media_count: int
    created_by: Optional[int]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CollectionListResponse(BaseModel):
    """合集列表响应"""
    collections: List[CollectionResponse]
    total: int
    page: int
    limit: int


class BatchDeleteRequest(BaseModel):
    """批量删除请求"""
    collection_ids: List[int]


# ==================== 用户相关 ====================

class UserResponse(BaseModel):
    """用户响应"""
    id: int
    telegram_id: int
    username: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    role: str
    is_banned: bool
    created_at: datetime
    last_active_at: datetime

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    """用户列表响应"""
    users: List[UserResponse]
    total: int
    page: int
    limit: int


class UpdateRoleRequest(BaseModel):
    """更新角色请求"""
    role: str


class BanUserRequest(BaseModel):
    """封禁用户请求"""
    is_banned: bool


# ==================== 搬运任务相关 ====================

class TaskCreate(BaseModel):
    """创建任务"""
    task_name: str
    source_chat_id: Optional[int] = 0
    source_chat_username: Optional[str] = None
    filter_keywords: List[str] = []
    filter_type: str = "all"
    filter_date_from: Optional[Union[date, str]] = None
    filter_date_to: Optional[Union[date, str]] = None


class TaskResponse(BaseModel):
    """任务响应"""
    id: int
    task_name: str
    source_chat_id: int
    source_chat_username: Optional[str]
    filter_type: str
    status: str
    progress_current: int
    progress_total: int
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


class TaskListResponse(BaseModel):
    """任务列表响应"""
    tasks: List[TaskResponse]
    total: int
    page: int
    limit: int


class TaskApproveRequest(BaseModel):
    """任务审核请求"""
    name: str
    description: Optional[str] = None
    tags: List[str] = []
    access_level: str


# ==================== Session 相关 ====================

class SessionLoginRequest(BaseModel):
    """Session 登录请求"""
    phone_number: str
    api_id: int
    api_hash: str
    code: Optional[str] = None
    password: Optional[str] = None


class SessionResponse(BaseModel):
    """Session 响应"""
    id: int
    phone_number: str
    priority: int
    is_active: bool
    transfer_count: int
    cooldown_until: Optional[datetime]
    created_at: datetime
    last_used_at: Optional[datetime]

    class Config:
        from_attributes = True


class SessionUpdateRequest(BaseModel):
    """Session 更新请求"""
    priority: Optional[int] = None
    is_active: Optional[bool] = None


# ==================== 系统设置相关 ====================

class SettingsResponse(BaseModel):
    """系统设置响应"""
    welcome_message: str
    bot_name: str
    max_media_per_collection: int


class SettingsUpdateRequest(BaseModel):
    """系统设置更新请求"""
    welcome_message: Optional[str] = None
    bot_name: Optional[str] = None
    max_media_per_collection: Optional[int] = None


# ==================== 通用响应 ====================

class SuccessResponse(BaseModel):
    """成功响应"""
    success: bool = True
    message: str


class ErrorResponse(BaseModel):
    """错误响应"""
    success: bool = False
    message: str
    detail: Optional[str] = None
