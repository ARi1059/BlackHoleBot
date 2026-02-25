# database/models.py
"""
SQLAlchemy 数据库模型
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, BigInteger, Boolean, Text, DateTime,
    ForeignKey, JSON, Index, Enum as SQLEnum
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import enum

Base = declarative_base()


class UserRole(str, enum.Enum):
    """用户角色枚举"""
    USER = "user"
    VIP = "vip"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


class AccessLevel(str, enum.Enum):
    """访问权限枚举"""
    PUBLIC = "public"
    VIP = "vip"


class TaskStatus(str, enum.Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    WAITING_BOT = "waiting_bot"
    COMPLETED = "completed"
    FAILED = "failed"


class User(Base):
    """用户表"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String(255))
    first_name = Column(String(255))
    last_name = Column(String(255))
    role = Column(SQLEnum(UserRole), default=UserRole.USER, nullable=False, index=True)
    is_banned = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    last_active_at = Column(DateTime, default=datetime.now, nullable=False)

    # 关系
    collections = relationship("Collection", back_populates="creator", foreign_keys="Collection.created_by")
    transfer_tasks = relationship("TransferTask", back_populates="creator", foreign_keys="TransferTask.created_by")


class Collection(Base):
    """合集表"""
    __tablename__ = "collections"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    tags = Column(JSON)  # 存储标签数组
    deep_link_code = Column(String(32), unique=True, nullable=False, index=True)
    access_level = Column(SQLEnum(AccessLevel), default=AccessLevel.PUBLIC, nullable=False, index=True)
    media_count = Column(Integer, default=0, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

    # 关系
    creator = relationship("User", back_populates="collections", foreign_keys=[created_by])
    media = relationship("Media", back_populates="collection", cascade="all, delete-orphan")

    # 索引
    __table_args__ = (
        Index('idx_collections_name', 'name'),
        Index('idx_collections_tags', 'tags', postgresql_using='gin'),
    )


class Media(Base):
    """媒体文件表"""
    __tablename__ = "media"

    id = Column(Integer, primary_key=True, index=True)
    collection_id = Column(Integer, ForeignKey("collections.id", ondelete="CASCADE"), nullable=False)
    file_id = Column(String(255), nullable=False)
    file_unique_id = Column(String(255), unique=True, nullable=False, index=True)
    file_type = Column(String(20), nullable=False)  # photo, video, document
    file_size = Column(BigInteger)
    caption = Column(Text)
    order_index = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)

    # 关系
    collection = relationship("Collection", back_populates="media")

    # 索引
    __table_args__ = (
        Index('idx_media_collection_id', 'collection_id'),
        Index('idx_media_order', 'collection_id', 'order_index'),
    )


class SessionAccount(Base):
    """Session 账号表"""
    __tablename__ = "session_accounts"

    id = Column(Integer, primary_key=True, index=True)
    phone_number = Column(String(20), unique=True, nullable=False)
    api_id = Column(Integer, nullable=False)
    api_hash = Column(String(255), nullable=False)
    session_string = Column(Text, nullable=False)  # 加密存储
    priority = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    transfer_count = Column(Integer, default=0, nullable=False)
    last_transfer_time = Column(DateTime)
    cooldown_until = Column(DateTime)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    last_used_at = Column(DateTime)

    # 关系
    transfer_tasks = relationship("TransferTask", back_populates="session_account")

    # 索引
    __table_args__ = (
        Index('idx_session_priority', 'priority', 'is_active'),
        Index('idx_session_cooldown', 'cooldown_until'),
    )


class TransferTask(Base):
    """搬运任务表"""
    __tablename__ = "transfer_tasks"

    id = Column(Integer, primary_key=True, index=True)
    task_name = Column(String(255), nullable=False)
    source_chat_id = Column(BigInteger, nullable=False)
    source_chat_username = Column(String(255))
    filter_keywords = Column(JSON)  # 过滤关键词数组
    filter_type = Column(String(20), default="all")  # photo, video, all
    filter_date_from = Column(DateTime)
    filter_date_to = Column(DateTime)
    session_account_id = Column(Integer, ForeignKey("session_accounts.id", ondelete="SET NULL"))
    status = Column(SQLEnum(TaskStatus), default=TaskStatus.PENDING, nullable=False, index=True)
    progress_current = Column(Integer, default=0, nullable=False)
    progress_total = Column(Integer, default=0, nullable=False)
    temp_redis_key = Column(String(255))  # Redis 临时存储 key
    error_message = Column(Text)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)

    # 关系
    session_account = relationship("SessionAccount", back_populates="transfer_tasks")
    creator = relationship("User", back_populates="transfer_tasks", foreign_keys=[created_by])
    logs = relationship("TaskLog", back_populates="task", cascade="all, delete-orphan")

    # 索引
    __table_args__ = (
        Index('idx_tasks_status', 'status'),
        Index('idx_tasks_session', 'session_account_id'),
    )


class TaskLog(Base):
    """任务日志表"""
    __tablename__ = "task_logs"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("transfer_tasks.id", ondelete="CASCADE"), nullable=False)
    log_type = Column(String(20), nullable=False)  # info, warning, error, rate_limit, session_switch
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)

    # 关系
    task = relationship("TransferTask", back_populates="logs")

    # 索引
    __table_args__ = (
        Index('idx_logs_task_id', 'task_id', 'created_at'),
    )


class Setting(Base):
    """系统设置表"""
    __tablename__ = "settings"

    key = Column(String(255), primary_key=True)
    value = Column(Text, nullable=False)
    description = Column(Text)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)


class AdminLog(Base):
    """管理员操作日志表"""
    __tablename__ = "admin_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    action = Column(String(50), nullable=False)
    details = Column(JSON)
    ip_address = Column(String(45))
    user_agent = Column(String(255))
    created_at = Column(DateTime, default=datetime.now, nullable=False)

    # 索引
    __table_args__ = (
        Index('idx_admin_logs_user', 'user_id', 'created_at'),
        Index('idx_admin_logs_action', 'action'),
    )
