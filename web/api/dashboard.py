# web/api/dashboard.py
"""
仪表盘 API
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text

from database.connection import get_db
from database.models import User, Collection, Media, TransferTask, AccessLevel, TaskStatus, UserRole
from web.schemas import DashboardStats, RecentActivity, ActivityItem
from web.dependencies import require_admin

router = APIRouter()


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    获取仪表盘统计数据

    需要管理员权限
    """
    # 总用户数
    total_users = await db.scalar(select(func.count(User.id)))

    # VIP 用户数 - 使用原始 SQL 避免枚举类型问题
    total_vip_users = await db.scalar(
        text("SELECT COUNT(id) FROM users WHERE role = 'VIP'")
    )

    # 总合集数
    total_collections = await db.scalar(select(func.count(Collection.id)))

    # 总媒体数
    total_media = await db.scalar(select(func.count(Media.id)))

    # 公开合集数
    public_collections = await db.scalar(
        text("SELECT COUNT(id) FROM collections WHERE access_level = 'PUBLIC'")
    )

    # VIP 合集数
    vip_collections = await db.scalar(
        text("SELECT COUNT(id) FROM collections WHERE access_level = 'VIP'")
    )

    # 活跃任务数
    active_tasks = await db.scalar(
        text("SELECT COUNT(id) FROM transfer_tasks WHERE status IN ('RUNNING', 'PENDING')")
    )

    # 已完成任务数
    completed_tasks = await db.scalar(
        text("SELECT COUNT(id) FROM transfer_tasks WHERE status = 'COMPLETED'")
    )

    return DashboardStats(
        total_users=total_users or 0,
        total_vip_users=total_vip_users or 0,
        total_collections=total_collections or 0,
        total_media=total_media or 0,
        public_collections=public_collections or 0,
        vip_collections=vip_collections or 0,
        active_tasks=active_tasks or 0,
        completed_tasks=completed_tasks or 0
    )


@router.get("/recent-activity", response_model=RecentActivity)
async def get_recent_activity(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    获取最近活动

    需要管理员权限
    """
    from database.models import AdminLog

    # 获取最近的管理员日志
    result = await db.execute(
        select(AdminLog)
        .order_by(AdminLog.created_at.desc())
        .limit(20)
    )
    logs = result.scalars().all()

    activities = []
    for log in logs:
        # 根据操作类型生成描述
        description = ""
        if log.action == "create_collection":
            collection_name = log.details.get("collection_name", "未知")
            description = f"创建了合集「{collection_name}」"
        elif log.action == "delete_collection":
            description = "删除了一个合集"
        elif log.action == "approve_transfer_task":
            collection_name = log.details.get("collection_name", "未知")
            description = f"审核通过搬运任务，创建合集「{collection_name}」"
        elif log.action == "create_transfer_task":
            description = "创建了搬运任务"
        else:
            description = f"执行了操作: {log.action}"

        # 获取用户名
        user_result = await db.execute(
            select(User).where(User.id == log.user_id)
        )
        user = user_result.scalar_one_or_none()
        username = user.username if user and user.username else "未知用户"

        activities.append(ActivityItem(
            id=log.id,
            type=log.action,
            user=username,
            description=description,
            created_at=log.created_at
        ))

    return RecentActivity(activities=activities)
