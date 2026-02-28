# web/api/tasks.py
"""
搬运任务管理 API
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import json

from database.connection import get_db, redis_client
from database.crud import (
    create_transfer_task,
    get_transfer_task,
    get_transfer_tasks,
    update_transfer_task,
    create_collection,
    create_media,
    update_collection,
    create_admin_log
)
from database.models import TaskStatus, AccessLevel
from web.schemas import (
    TaskCreate,
    TaskListResponse,
    TaskResponse,
    TaskApproveRequest,
    SuccessResponse
)
from web.dependencies import require_admin
from utils.task_queue import task_queue
from utils.deep_link import generate_unique_deep_link_code
from utils.channel_sender import send_collection_to_channel
from config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    获取搬运任务列表

    需要管理员权限
    """
    skip = (page - 1) * limit

    # 转换 status
    status_filter = None
    if status:
        try:
            status_filter = TaskStatus(status)
        except ValueError:
            pass

    tasks, total = await get_transfer_tasks(
        db,
        skip=skip,
        limit=limit,
        status=status_filter
    )

    return TaskListResponse(
        tasks=[TaskResponse.from_orm(t) for t in tasks],
        total=total,
        page=page,
        limit=limit
    )


@router.post("", response_model=dict)
async def create_task(
    task_data: TaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    创建搬运任务

    需要管理员权限
    """
    # 处理日期字符串，转换为 datetime 对象
    from datetime import datetime, date

    filter_date_from = None
    filter_date_to = None

    if task_data.filter_date_from:
        if isinstance(task_data.filter_date_from, str):
            # 将日期字符串转换为 datetime 对象（时间设为 00:00:00）
            filter_date_from = datetime.strptime(task_data.filter_date_from, "%Y-%m-%d")
        elif isinstance(task_data.filter_date_from, date):
            filter_date_from = datetime.combine(task_data.filter_date_from, datetime.min.time())
        else:
            filter_date_from = task_data.filter_date_from

    if task_data.filter_date_to:
        if isinstance(task_data.filter_date_to, str):
            # 将日期字符串转换为 datetime 对象（时间设为 23:59:59）
            filter_date_to = datetime.strptime(task_data.filter_date_to, "%Y-%m-%d")
            filter_date_to = filter_date_to.replace(hour=23, minute=59, second=59)
        elif isinstance(task_data.filter_date_to, date):
            filter_date_to = datetime.combine(task_data.filter_date_to, datetime.max.time())
        else:
            filter_date_to = task_data.filter_date_to

    # 创建任务
    task = await create_transfer_task(
        db,
        task_name=task_data.task_name,
        source_chat_id=task_data.source_chat_id,
        source_chat_username=task_data.source_chat_username,
        filter_keywords=task_data.filter_keywords,
        filter_type=task_data.filter_type,
        filter_date_from=filter_date_from,
        filter_date_to=filter_date_to,
        created_by=current_user.id
    )

    # 添加到任务队列
    await task_queue.add_task(task.id)

    # 记录日志
    await create_admin_log(
        db,
        user_id=current_user.id,
        action="create_transfer_task",
        details={
            "task_id": task.id,
            "task_name": task.task_name
        }
    )

    logger.info(
        f"[Web] 管理员 {current_user.id} 创建搬运任务: task_id={task.id}, "
        f"name={task.task_name}, source={task_data.source_chat_username or task_data.source_chat_id}, "
        f"filter_type={task_data.filter_type}"
    )

    return {
        "success": True,
        "task_id": task.id,
        "message": "任务已创建，等待执行"
    }


@router.get("/{task_id}", response_model=dict)
async def get_task_detail(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    获取任务详情

    需要管理员权限
    """
    task = await get_transfer_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 构建响应
    response = {
        "id": task.id,
        "task_name": task.task_name,
        "source_chat_id": task.source_chat_id,
        "source_chat_username": task.source_chat_username,
        "filter_keywords": task.filter_keywords,
        "filter_type": task.filter_type,
        "status": task.status.value,
        "progress_current": task.progress_current,
        "progress_total": task.progress_total,
        "session_account_id": task.session_account_id,
        "created_at": task.created_at.isoformat(),
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "logs": [
            {
                "id": log.id,
                "log_type": log.log_type,
                "message": log.message,
                "created_at": log.created_at.isoformat()
            }
            for log in task.logs[-20:]  # 最近 20 条日志
        ]
    }

    return response


@router.post("/{task_id}/approve", response_model=dict)
async def approve_task(
    task_id: int,
    approve_data: TaskApproveRequest,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    审核任务并创建合集

    需要管理员权限
    """
    # 获取任务
    task = await get_transfer_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if task.status != TaskStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="只能审核已完成的任务")

    # 从 Redis 获取文件列表
    redis_key = f"task:{task_id}:files"
    file_data_list = await redis_client.lrange(redis_key, 0, -1)

    if not file_data_list:
        raise HTTPException(status_code=400, detail="没有找到文件数据")

    media_list = [json.loads(data_str) for data_str in file_data_list]
    logger.info(f"[Web] 管理员 {current_user.id} 审核任务 {task_id}，文件数: {len(media_list)}")

    # 生成深链接码
    deep_link_code = await generate_unique_deep_link_code(db)

    # 转换 access_level
    try:
        access_level = AccessLevel(approve_data.access_level)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的访问权限")

    # 创建合集
    collection = await create_collection(
        db,
        name=approve_data.name,
        deep_link_code=deep_link_code,
        description=approve_data.description,
        tags=approve_data.tags,
        access_level=access_level,
        created_by=current_user.id
    )

    # 批量插入媒体（跳过重复文件）
    inserted_count = 0
    for index, media_data in enumerate(media_list):
        try:
            await create_media(
                db,
                collection_id=collection.id,
                file_id=media_data["file_id"],
                file_unique_id=media_data["file_unique_id"],
                file_type=media_data["file_type"],
                order_index=index,
                file_size=media_data.get("file_size"),
                caption=media_data.get("caption")
            )
            inserted_count += 1
        except Exception as e:
            # 跳过重复的文件
            if "duplicate key" in str(e) or "UniqueViolationError" in str(e):
                logger.warning(f"跳过重复文件: {media_data['file_unique_id']}")
                await db.rollback()  # 回滚失败的事务
                continue
            else:
                raise

    # 更新合集媒体数量（使用实际插入的数量）
    await update_collection(db, collection.id, media_count=inserted_count)

    logger.info(f"[Web] 任务 {task_id} 共 {len(media_list)} 个文件，成功插入 {inserted_count} 个")

    # 发送到私有频道
    await send_collection_to_channel(None, media_list, collection.name)

    # 清空 Redis
    await redis_client.delete(redis_key)

    # 记录日志
    await create_admin_log(
        db,
        user_id=current_user.id,
        action="approve_transfer_task",
        details={
            "task_id": task_id,
            "collection_id": collection.id,
            "collection_name": collection.name,
            "media_count": len(media_list)
        }
    )

    logger.info(
        f"[Web] 任务 {task_id} 审核通过，合集已创建: collection_id={collection.id}, "
        f"name={collection.name}, media_count={len(media_list)}"
    )

    return {
        "success": True,
        "collection_id": collection.id,
        "deep_link_code": deep_link_code,
        "message": "合集创建成功"
    }


@router.delete("/{task_id}", response_model=SuccessResponse)
async def delete_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    删除任务

    需要管理员权限
    """
    from database.models import TransferTask
    from sqlalchemy import delete as sql_delete

    task = await get_transfer_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 删除任务
    await db.execute(
        sql_delete(TransferTask).where(TransferTask.id == task_id)
    )
    await db.commit()

    # 记录日志
    await create_admin_log(
        db,
        user_id=current_user.id,
        action="delete_transfer_task",
        details={"task_id": task_id}
    )

    logger.info(f"[Web] 管理员 {current_user.id} 删除任务 {task_id}")

    return SuccessResponse(message="任务已删除")
