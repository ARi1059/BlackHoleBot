# database/crud.py
"""
数据库 CRUD 操作
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, or_, cast, Text
from sqlalchemy.dialects.postgresql import ARRAY, insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload
from typing import Optional, List, Dict, Any
from datetime import datetime

from .models import (
    User, Collection, Media, SessionAccount, TransferTask,
    TaskLog, Setting, AdminLog, UserActivity, UserRole, AccessLevel, TaskStatus
)


# ==================== User CRUD ====================

async def get_user(db: AsyncSession, user_id: int) -> Optional[User]:
    """根据 ID 获取用户"""
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_user_by_telegram_id(db: AsyncSession, telegram_id: int) -> Optional[User]:
    """根据 Telegram ID 获取用户"""
    result = await db.execute(select(User).where(User.telegram_id == telegram_id))
    return result.scalar_one_or_none()


async def create_user(
    db: AsyncSession,
    telegram_id: int,
    username: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    role: UserRole = UserRole.USER
) -> User:
    """创建新用户"""
    user = User(
        telegram_id=telegram_id,
        username=username,
        first_name=first_name,
        last_name=last_name,
        role=role,
        created_at=datetime.now(),
        last_active_at=datetime.now()
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def update_user_role(db: AsyncSession, user_id: int, role: UserRole) -> bool:
    """更新用户角色"""
    result = await db.execute(
        update(User).where(User.id == user_id).values(role=role)
    )
    await db.commit()
    return result.rowcount > 0


async def ban_user(db: AsyncSession, user_id: int, is_banned: bool = True) -> bool:
    """封禁/解封用户"""
    result = await db.execute(
        update(User).where(User.id == user_id).values(is_banned=is_banned)
    )
    await db.commit()
    return result.rowcount > 0


async def update_user_last_active(db: AsyncSession, user_id: int):
    """更新用户最后活跃时间"""
    await db.execute(
        update(User).where(User.id == user_id).values(last_active_at=datetime.now())
    )
    await db.commit()


async def get_users(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 20,
    role: Optional[UserRole] = None,
    search: Optional[str] = None
) -> tuple[List[User], int]:
    """获取用户列表"""
    query = select(User)

    # 过滤条件
    if role:
        query = query.where(User.role == role)
    if search:
        query = query.where(
            or_(
                User.username.ilike(f"%{search}%"),
                User.first_name.ilike(f"%{search}%")
            )
        )

    # 总数
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    # 分页
    query = query.offset(skip).limit(limit).order_by(User.created_at.desc())
    result = await db.execute(query)
    users = result.scalars().all()

    return users, total


async def get_user_with_statistics(db: AsyncSession, user_id: int) -> Optional[Dict[str, Any]]:
    """获取用户详情及统计信息"""
    user = await get_user(db, user_id)
    if not user:
        return None

    # 统计创建的合集数量
    collections_count = await db.scalar(
        select(func.count(Collection.id)).where(Collection.created_by == user.id)
    )

    # 统计创建的搬运任务数量
    tasks_count = await db.scalar(
        select(func.count(TransferTask.id)).where(TransferTask.created_by == user.id)
    )

    # 统计上传的媒体总数
    media_count = await db.scalar(
        select(func.count(Media.id))
        .select_from(Media)
        .join(Collection, Media.collection_id == Collection.id)
        .where(Collection.created_by == user.id)
    )

    return {
        "user": user,
        "statistics": {
            "collections_created": collections_count or 0,
            "transfer_tasks_created": tasks_count or 0,
            "total_media_uploaded": media_count or 0
        }
    }


async def get_admin_users(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 20
) -> tuple[List[User], int]:
    """获取管理员列表"""
    query = select(User).where(
        User.role.in_([UserRole.ADMIN, UserRole.SUPER_ADMIN])
    )

    # 总数
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    # 分页，按角色和创建时间排序
    query = (
        query
        .order_by(
            User.role.desc(),  # SUPER_ADMIN 在前
            User.created_at.asc()
        )
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    admins = result.scalars().all()

    return admins, total


async def batch_update_vip(
    db: AsyncSession,
    telegram_ids: List[int],
    grant: bool
) -> tuple[int, int, List[int]]:
    """
    批量设置/撤销VIP

    返回: (成功数量, 失败数量, 失败的telegram_ids)
    """
    from database.models import UserRole

    # 查询所有存在的用户
    result = await db.execute(
        select(User).where(User.telegram_id.in_(telegram_ids))
    )
    users = result.scalars().all()

    existing_ids = {user.telegram_id for user in users}
    failed_ids = [tid for tid in telegram_ids if tid not in existing_ids]

    # 批量更新
    target_role = UserRole.VIP if grant else UserRole.USER

    for user in users:
        # 不修改管理员角色
        if user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
            user.role = target_role

    await db.commit()

    success_count = len(users)
    failed_count = len(failed_ids)

    return success_count, failed_count, failed_ids


async def get_user_statistics_data(db: AsyncSession) -> dict:
    """获取用户统计数据"""
    from database.models import UserRole
    from datetime import datetime, timedelta

    # 角色分布
    role_dist_result = await db.execute(
        select(User.role, func.count(User.id))
        .group_by(User.role)
    )
    role_distribution = {role.value: count for role, count in role_dist_result.all()}

    # 总用户数
    total_users = await db.scalar(select(func.count(User.id)))

    # 封禁用户数
    banned_users = await db.scalar(
        select(func.count(User.id)).where(User.is_banned == True)
    )

    # 活跃用户统计
    now = datetime.now()
    daily_active = await db.scalar(
        select(func.count(User.id))
        .where(User.last_active_at >= now - timedelta(days=1))
    )
    weekly_active = await db.scalar(
        select(func.count(User.id))
        .where(User.last_active_at >= now - timedelta(days=7))
    )
    monthly_active = await db.scalar(
        select(func.count(User.id))
        .where(User.last_active_at >= now - timedelta(days=30))
    )

    # 增长趋势 - 一次查询最近30天，再拆分7天和30天
    date_30d_ago = (now - timedelta(days=29)).date()
    growth_result = await db.execute(
        select(
            func.date(User.created_at).label("reg_date"),
            func.count(User.id).label("cnt")
        )
        .where(func.date(User.created_at) >= date_30d_ago)
        .group_by(func.date(User.created_at))
    )
    growth_map = {row.reg_date: row.cnt for row in growth_result.all()}

    date_7d_ago = (now - timedelta(days=6)).date()
    growth_7d = []
    growth_30d = []
    for i in range(29, -1, -1):
        date = (now - timedelta(days=i)).date()
        entry = {"date": date.isoformat(), "new_users": growth_map.get(date, 0)}
        growth_30d.append(entry)
        if date >= date_7d_ago:
            growth_7d.append(entry)

    return {
        "role_distribution": role_distribution,
        "active_users": {
            "daily": daily_active or 0,
            "weekly": weekly_active or 0,
            "monthly": monthly_active or 0
        },
        "growth_trend": {
            "last_7_days": growth_7d,
            "last_30_days": growth_30d
        },
        "total_users": total_users or 0,
        "banned_users": banned_users or 0
    }


# ==================== Collection CRUD ====================

async def get_collection(db: AsyncSession, collection_id: int) -> Optional[Collection]:
    """根据 ID 获取合集"""
    result = await db.execute(
        select(Collection)
        .options(selectinload(Collection.media))
        .where(Collection.id == collection_id)
    )
    return result.scalar_one_or_none()


async def get_collection_by_code(db: AsyncSession, deep_link_code: str) -> Optional[Collection]:
    """根据深链接码获取合集"""
    result = await db.execute(
        select(Collection)
        .options(selectinload(Collection.media))
        .where(Collection.deep_link_code == deep_link_code)
    )
    return result.scalar_one_or_none()


async def create_collection(
    db: AsyncSession,
    name: str,
    deep_link_code: str,
    description: Optional[str] = None,
    tags: Optional[List[str]] = None,
    access_level: AccessLevel = AccessLevel.PUBLIC,
    created_by: Optional[int] = None
) -> Collection:
    """创建合集"""
    collection = Collection(
        name=name,
        description=description,
        tags=tags or [],
        deep_link_code=deep_link_code,
        access_level=access_level,
        created_by=created_by,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    db.add(collection)
    await db.commit()
    await db.refresh(collection)
    return collection


async def update_collection(
    db: AsyncSession,
    collection_id: int,
    **kwargs
) -> bool:
    """更新合集信息"""
    kwargs['updated_at'] = datetime.now()
    result = await db.execute(
        update(Collection).where(Collection.id == collection_id).values(**kwargs)
    )
    await db.commit()
    return result.rowcount > 0


async def delete_collection(db: AsyncSession, collection_id: int) -> bool:
    """删除合集"""
    result = await db.execute(
        delete(Collection).where(Collection.id == collection_id)
    )
    await db.commit()
    return result.rowcount > 0


async def search_collections(
    db: AsyncSession,
    keyword: str,
    user_role: UserRole = UserRole.USER,
    skip: int = 0,
    limit: int = 10
) -> List[Collection]:
    """搜索合集"""
    query = select(Collection)

    # 权限过滤
    if user_role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.VIP]:
        query = query.where(Collection.access_level == AccessLevel.PUBLIC)

    # 关键词搜索
    query = query.where(
        or_(
            Collection.name.ilike(f"%{keyword}%"),
            Collection.description.ilike(f"%{keyword}%"),
            Collection.tags.op('@>')(cast([keyword], ARRAY(Text)))  # PostgreSQL array contains operator with proper type casting
        )
    )

    query = query.offset(skip).limit(limit).order_by(Collection.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


async def get_collections(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 20,
    access_level: Optional[AccessLevel] = None,
    search: Optional[str] = None
) -> tuple[List[Collection], int]:
    """获取合集列表"""
    query = select(Collection)

    if access_level:
        query = query.where(Collection.access_level == access_level)
    if search:
        query = query.where(Collection.name.ilike(f"%{search}%"))

    # 总数
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    # 分页
    query = query.offset(skip).limit(limit).order_by(Collection.created_at.desc())
    result = await db.execute(query)
    collections = result.scalars().all()

    return collections, total


async def get_collections_by_role(
    db: AsyncSession,
    user_role: UserRole,
    skip: int = 0,
    limit: int = 20
) -> tuple[List[Collection], int]:
    """根据用户角色获取合集列表（显示所有合集，不进行权限过滤）"""
    query = select(Collection)

    # 不再进行权限过滤，显示所有合集
    # 权限检查将在用户点击合集时进行

    # 总数
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    # 分页
    query = query.offset(skip).limit(limit).order_by(Collection.created_at.desc())
    result = await db.execute(query)
    collections = result.scalars().all()

    return collections, total


async def get_hot_collections(
    db: AsyncSession,
    user_role: UserRole,
    skip: int = 0,
    limit: int = 5
) -> tuple[List[Collection], int]:
    """获取热门合集（按浏览次数排序，显示所有合集，支持分页）"""
    query = select(Collection)

    # 不再进行权限过滤，显示所有合集
    # 权限检查将在用户点击合集时进行

    # 总数
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    # 按浏览次数降序排序，支持分页
    query = query.order_by(Collection.view_count.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    collections = result.scalars().all()

    return collections, total


async def increment_collection_view_count(db: AsyncSession, collection_id: int) -> bool:
    """增加合集浏览次数"""
    try:
        stmt = update(Collection).where(Collection.id == collection_id).values(
            view_count=Collection.view_count + 1
        )
        await db.execute(stmt)
        await db.commit()
        return True
    except Exception:
        await db.rollback()
        return False


# ==================== Media CRUD ====================

async def create_media(
    db: AsyncSession,
    collection_id: int,
    file_id: str,
    file_unique_id: str,
    file_type: str,
    order_index: int,
    file_size: Optional[int] = None,
    caption: Optional[str] = None
) -> Media:
    """创建媒体"""
    media = Media(
        collection_id=collection_id,
        file_id=file_id,
        file_unique_id=file_unique_id,
        file_type=file_type,
        file_size=file_size,
        caption=caption,
        order_index=order_index,
        created_at=datetime.now()
    )
    db.add(media)
    await db.commit()
    await db.refresh(media)
    return media


async def bulk_create_media(
    db: AsyncSession,
    collection_id: int,
    media_list: List[Dict[str, Any]],
    batch_size: int = 500,
    order_index_offset: int = 0
) -> int:
    """
    批量创建媒体，跳过重复文件

    Args:
        db: 数据库 session
        collection_id: 合集 ID
        media_list: 媒体数据列表，每个元素包含 file_id, file_unique_id, file_type 等字段
        batch_size: 每批插入的数量，默认 500
        order_index_offset: order_index 的偏移量，用于追加媒体时从现有数量开始

    Returns:
        成功插入的数量
    """
    import logging
    logger = logging.getLogger(__name__)

    if not media_list:
        return 0

    total_inserted = 0
    now = datetime.now()

    # 分批处理，避免单次插入数据量过大
    for batch_num, i in enumerate(range(0, len(media_list), batch_size), 1):
        batch = media_list[i:i + batch_size]
        media_objects = []

        logger.info(f"准备第 {batch_num} 批数据，范围: {i} - {i + len(batch) - 1}")

        for index, media_data in enumerate(batch):
            try:
                media_objects.append({
                    "collection_id": collection_id,
                    "file_id": media_data["file_id"],
                    "file_unique_id": media_data["file_unique_id"],
                    "file_type": media_data["file_type"],
                    "file_size": media_data.get("file_size"),
                    "caption": media_data.get("caption"),
                    "order_index": order_index_offset + i + index,  # 全局索引 + 偏移量
                    "created_at": now
                })
            except Exception as e:
                logger.error(f"准备数据失败，索引 {i + index}: {str(e)}, 数据: {media_data}")
                raise

        # 使用 PostgreSQL 的 INSERT ... ON CONFLICT DO NOTHING 跳过重复
        try:
            logger.info(f"开始插入第 {batch_num} 批，共 {len(media_objects)} 条")
            stmt = insert(Media).values(media_objects)
            stmt = stmt.on_conflict_do_nothing(index_elements=["file_unique_id"])

            result = await db.execute(stmt)
            batch_inserted = result.rowcount if result.rowcount else 0
            total_inserted += batch_inserted

            logger.info(f"第 {batch_num} 批插入完成，成功插入 {batch_inserted} 条，累计 {total_inserted} 条")
        except Exception as e:
            logger.error(f"第 {batch_num} 批插入失败: {str(e)}", exc_info=True)
            # 记录失败批次的最后几条数据
            logger.error(f"失败批次最后 3 条数据: {media_objects[-3:]}")
            raise

    await db.commit()
    logger.info(f"所有批次插入完成，总计成功插入 {total_inserted} 条")
    return total_inserted


async def get_media_by_collection(
    db: AsyncSession,
    collection_id: int,
    skip: int = 0,
    limit: int = 10
) -> List[Media]:
    """获取合集的媒体列表（分页）"""
    result = await db.execute(
        select(Media)
        .where(Media.collection_id == collection_id)
        .order_by(Media.order_index)
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


async def get_media_count(db: AsyncSession, collection_id: int) -> int:
    """获取合集的媒体数量"""
    result = await db.execute(
        select(func.count()).where(Media.collection_id == collection_id)
    )
    return result.scalar()


# ==================== SessionAccount CRUD ====================

async def create_session_account(
    db: AsyncSession,
    phone_number: str,
    api_id: int,
    api_hash: str,
    session_string: str,
    priority: int = 0
) -> SessionAccount:
    """创建 Session 账号"""
    session = SessionAccount(
        phone_number=phone_number,
        api_id=api_id,
        api_hash=api_hash,
        session_string=session_string,
        priority=priority,
        created_at=datetime.now()
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


async def get_session_account(db: AsyncSession, session_id: int) -> Optional[SessionAccount]:
    """获取 Session 账号"""
    result = await db.execute(
        select(SessionAccount).where(SessionAccount.id == session_id)
    )
    return result.scalar_one_or_none()


async def get_available_session(db: AsyncSession) -> Optional[SessionAccount]:
    """获取可用的 Session 账号"""
    now = datetime.now()
    result = await db.execute(
        select(SessionAccount)
        .where(
            SessionAccount.is_active == True,
            or_(
                SessionAccount.cooldown_until == None,
                SessionAccount.cooldown_until < now
            )
        )
        .order_by(SessionAccount.priority.asc(), SessionAccount.transfer_count.asc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def update_session_account(
    db: AsyncSession,
    session_id: int,
    **kwargs
) -> bool:
    """更新 Session 账号"""
    result = await db.execute(
        update(SessionAccount).where(SessionAccount.id == session_id).values(**kwargs)
    )
    await db.commit()
    return result.rowcount > 0


async def get_all_sessions(db: AsyncSession) -> List[SessionAccount]:
    """获取所有 Session 账号"""
    result = await db.execute(select(SessionAccount).order_by(SessionAccount.priority))
    return result.scalars().all()


# ==================== TransferTask CRUD ====================

async def create_transfer_task(
    db: AsyncSession,
    task_name: str,
    source_chat_id: int,
    source_chat_username: Optional[str] = None,
    filter_keywords: Optional[List[str]] = None,
    filter_type: str = "all",
    filter_date_from: Optional[datetime] = None,
    filter_date_to: Optional[datetime] = None,
    created_by: Optional[int] = None
) -> TransferTask:
    """创建搬运任务"""
    task = TransferTask(
        task_name=task_name,
        source_chat_id=source_chat_id,
        source_chat_username=source_chat_username,
        filter_keywords=filter_keywords or [],
        filter_type=filter_type,
        filter_date_from=filter_date_from,
        filter_date_to=filter_date_to,
        created_by=created_by,
        created_at=datetime.now()
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


async def get_transfer_task(db: AsyncSession, task_id: int) -> Optional[TransferTask]:
    """获取搬运任务"""
    result = await db.execute(
        select(TransferTask)
        .options(selectinload(TransferTask.logs))
        .where(TransferTask.id == task_id)
    )
    return result.scalar_one_or_none()


async def update_transfer_task(
    db: AsyncSession,
    task_id: int,
    **kwargs
) -> bool:
    """更新搬运任务"""
    result = await db.execute(
        update(TransferTask).where(TransferTask.id == task_id).values(**kwargs)
    )
    await db.commit()
    return result.rowcount > 0


async def get_transfer_tasks(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 20,
    status: Optional[TaskStatus] = None
) -> tuple[List[TransferTask], int]:
    """获取搬运任务列表"""
    query = select(TransferTask)

    if status:
        query = query.where(TransferTask.status == status)

    # 总数
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    # 分页
    query = query.offset(skip).limit(limit).order_by(TransferTask.created_at.desc())
    result = await db.execute(query)
    tasks = result.scalars().all()

    return tasks, total


# ==================== TaskLog CRUD ====================

async def create_task_log(
    db: AsyncSession,
    task_id: int,
    log_type: str,
    message: str
) -> TaskLog:
    """创建任务日志"""
    log = TaskLog(
        task_id=task_id,
        log_type=log_type,
        message=message,
        created_at=datetime.now()
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return log


# ==================== Setting CRUD ====================

async def get_setting(db: AsyncSession, key: str) -> Optional[str]:
    """获取设置"""
    result = await db.execute(select(Setting).where(Setting.key == key))
    setting = result.scalar_one_or_none()
    return setting.value if setting else None


async def set_setting(db: AsyncSession, key: str, value: str, description: Optional[str] = None):
    """设置配置"""
    result = await db.execute(select(Setting).where(Setting.key == key))
    setting = result.scalar_one_or_none()

    if setting:
        await db.execute(
            update(Setting)
            .where(Setting.key == key)
            .values(value=value, updated_at=datetime.now())
        )
    else:
        setting = Setting(key=key, value=value, description=description)
        db.add(setting)

    await db.commit()


async def get_all_settings(db: AsyncSession) -> Dict[str, str]:
    """获取所有设置"""
    result = await db.execute(select(Setting))
    settings = result.scalars().all()
    return {s.key: s.value for s in settings}


# ==================== AdminLog CRUD ====================

async def create_admin_log(
    db: AsyncSession,
    user_id: int,
    action: str,
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
) -> AdminLog:
    """创建管理员操作日志"""
    log = AdminLog(
        user_id=user_id,
        action=action,
        details=details or {},
        ip_address=ip_address,
        user_agent=user_agent,
        created_at=datetime.now()
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return log


async def get_admin_logs(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 50,
    action: Optional[str] = None,
    user_id: Optional[int] = None
) -> tuple[List[AdminLog], int]:
    """获取管理员日志"""
    query = select(AdminLog)

    if action:
        query = query.where(AdminLog.action == action)
    if user_id:
        query = query.where(AdminLog.user_id == user_id)

    # 总数
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    # 分页
    query = query.offset(skip).limit(limit).order_by(AdminLog.created_at.desc())
    result = await db.execute(query)
    logs = result.scalars().all()

    return logs, total


# ==================== UserActivity CRUD ====================

async def create_user_activity(
    db: AsyncSession,
    user_id: int,
    activity_type: str,
    collection_id: Optional[int] = None,
    extra_data: Optional[Dict[str, Any]] = None
) -> UserActivity:
    """创建用户活动记录"""
    activity = UserActivity(
        user_id=user_id,
        activity_type=activity_type,
        collection_id=collection_id,
        extra_data=extra_data or {},
        created_at=datetime.now()
    )
    db.add(activity)
    await db.commit()
    await db.refresh(activity)
    return activity


async def get_user_activities(
    db: AsyncSession,
    user_id: int,
    skip: int = 0,
    limit: int = 50,
    activity_type: Optional[str] = None
) -> tuple[List[UserActivity], int]:
    """获取用户活动记录"""
    query = select(UserActivity).where(UserActivity.user_id == user_id)

    if activity_type:
        query = query.where(UserActivity.activity_type == activity_type)

    # 总数
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    # 分页
    query = query.offset(skip).limit(limit).order_by(UserActivity.created_at.desc())
    result = await db.execute(query)
    activities = result.scalars().all()

    return activities, total or 0


async def get_popular_collections(
    db: AsyncSession,
    limit: int = 10,
    days: int = 30
) -> List[Dict[str, Any]]:
    """获取最受欢迎的合集（基于访问次数）"""
    from datetime import timedelta

    cutoff_date = datetime.now() - timedelta(days=days)

    # 统计每个合集的访问次数
    query = select(
        UserActivity.collection_id,
        func.count(UserActivity.id).label('view_count')
    ).where(
        UserActivity.activity_type == 'view_collection',
        UserActivity.collection_id.isnot(None),
        UserActivity.created_at >= cutoff_date
    ).group_by(
        UserActivity.collection_id
    ).order_by(
        func.count(UserActivity.id).desc()
    ).limit(limit)

    result = await db.execute(query)
    stats = result.all()

    if not stats:
        return []

    # 一次性查出所有合集（避免 N+1）
    collection_ids = [cid for cid, _ in stats]
    collections_result = await db.execute(
        select(Collection).where(Collection.id.in_(collection_ids))
    )
    collections_map = {c.id: c for c in collections_result.scalars().all()}

    # 组装结果
    popular_collections = []
    for collection_id, view_count in stats:
        collection = collections_map.get(collection_id)
        if collection:
            popular_collections.append({
                'collection_id': collection_id,
                'collection_name': collection.name,
                'view_count': view_count,
                'access_level': collection.access_level.value,
                'media_count': collection.media_count
            })

    return popular_collections


async def get_user_activity_stats(
    db: AsyncSession,
    user_id: int,
    days: int = 30
) -> Dict[str, Any]:
    """获取用户活动统计"""
    from datetime import timedelta

    cutoff_date = datetime.now() - timedelta(days=days)

    # 总活动次数
    total_activities = await db.scalar(
        select(func.count(UserActivity.id))
        .where(
            UserActivity.user_id == user_id,
            UserActivity.created_at >= cutoff_date
        )
    )

    # 按活动类型分组统计
    activity_type_stats = await db.execute(
        select(
            UserActivity.activity_type,
            func.count(UserActivity.id).label('count')
        ).where(
            UserActivity.user_id == user_id,
            UserActivity.created_at >= cutoff_date
        ).group_by(UserActivity.activity_type)
    )

    activity_by_type = {row[0]: row[1] for row in activity_type_stats.all()}

    # 最常访问的合集
    most_viewed_collections = await db.execute(
        select(
            UserActivity.collection_id,
            func.count(UserActivity.id).label('count')
        ).where(
            UserActivity.user_id == user_id,
            UserActivity.activity_type == 'view_collection',
            UserActivity.collection_id.isnot(None),
            UserActivity.created_at >= cutoff_date
        ).group_by(
            UserActivity.collection_id
        ).order_by(
            func.count(UserActivity.id).desc()
        ).limit(5)
    )

    most_viewed = []
    most_viewed_data = most_viewed_collections.all()
    if most_viewed_data:
        # 一次性查出所有合集（避免 N+1）
        collection_ids = [cid for cid, _ in most_viewed_data]
        collections_result = await db.execute(
            select(Collection).where(Collection.id.in_(collection_ids))
        )
        collections_map = {c.id: c for c in collections_result.scalars().all()}

        for collection_id, count in most_viewed_data:
            collection = collections_map.get(collection_id)
            if collection:
                most_viewed.append({
                    'collection_id': collection_id,
                    'collection_name': collection.name,
                    'view_count': count
                })

    return {
        'total_activities': total_activities or 0,
        'activity_by_type': activity_by_type,
        'most_viewed_collections': most_viewed,
        'period_days': days
    }


# ==================== Broadcast CRUD ====================

async def create_broadcast_log(
    db: AsyncSession,
    admin_id: int,
    message_type: str,
    message_text: Optional[str],
    file_id: Optional[str],
    has_buttons: bool,
    total_users: int
) -> int:
    """创建广播日志"""
    from .models import BroadcastLog

    log = BroadcastLog(
        admin_id=admin_id,
        message_type=message_type,
        message_text=message_text,
        file_id=file_id,
        has_buttons=has_buttons,
        total_users=total_users
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return log.id


async def update_broadcast_log(
    db: AsyncSession,
    log_id: int,
    success_count: int,
    failed_count: int,
    completed_at: datetime,
    duration_seconds: int
) -> bool:
    """更新广播日志"""
    from .models import BroadcastLog

    result = await db.execute(
        update(BroadcastLog).where(BroadcastLog.id == log_id).values(
            success_count=success_count,
            failed_count=failed_count,
            completed_at=completed_at,
            duration_seconds=duration_seconds
        )
    )
    await db.commit()
    return result.rowcount > 0


async def get_broadcast_logs(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 20
) -> tuple[List, int]:
    """获取广播历史记录"""
    from .models import BroadcastLog

    # 获取总数
    count_result = await db.execute(select(func.count(BroadcastLog.id)))
    total = count_result.scalar()

    # 获取记录
    result = await db.execute(
        select(BroadcastLog)
        .order_by(BroadcastLog.started_at.desc())
        .offset(skip)
        .limit(limit)
    )
    logs = result.scalars().all()

    return logs, total

