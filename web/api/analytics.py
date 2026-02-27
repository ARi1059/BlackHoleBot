# web/api/analytics.py
"""
用户行为分析 API
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db
from database.crud import (
    get_popular_collections,
    get_user_activity_stats,
    get_user_activities
)
from web.dependencies import require_admin
from typing import List, Dict, Any

router = APIRouter()


@router.get("/popular-collections")
async def get_popular_collections_endpoint(
    limit: int = Query(10, ge=1, le=50),
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    获取最受欢迎的合集

    需要管理员权限
    """
    collections = await get_popular_collections(db, limit=limit, days=days)

    return {
        "collections": collections,
        "period_days": days,
        "total": len(collections)
    }


@router.get("/users/{user_id}/activities")
async def get_user_activities_endpoint(
    user_id: int,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    activity_type: str = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    获取用户活动记录

    需要管理员权限
    """
    skip = (page - 1) * limit
    activities, total = await get_user_activities(
        db,
        user_id=user_id,
        skip=skip,
        limit=limit,
        activity_type=activity_type
    )

    # 格式化活动记录
    formatted_activities = []
    for activity in activities:
        formatted_activities.append({
            "id": activity.id,
            "activity_type": activity.activity_type,
            "collection_id": activity.collection_id,
            "extra_data": activity.extra_data,
            "created_at": activity.created_at.isoformat()
        })

    return {
        "activities": formatted_activities,
        "total": total,
        "page": page,
        "limit": limit
    }


@router.get("/users/{user_id}/stats")
async def get_user_activity_stats_endpoint(
    user_id: int,
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    获取用户活动统计

    需要管理员权限
    """
    stats = await get_user_activity_stats(db, user_id=user_id, days=days)

    return stats
