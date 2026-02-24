# web/websocket.py
"""
WebSocket 实时通信
"""

from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, Set
from jose import jwt, JWTError
import json

from config import settings

class ConnectionManager:
    """WebSocket 连接管理器"""

    def __init__(self):
        self.active_connections: Dict[int, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        """
        连接 WebSocket

        Args:
            websocket: WebSocket 连接
            user_id: 用户 ID
        """
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)

    def disconnect(self, websocket: WebSocket, user_id: int):
        """
        断开 WebSocket

        Args:
            websocket: WebSocket 连接
            user_id: 用户 ID
        """
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

    async def send_to_user(self, user_id: int, message: dict):
        """
        发送消息给特定用户

        Args:
            user_id: 用户 ID
            message: 消息内容
        """
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_text(json.dumps(message))
                except:
                    pass

    async def broadcast(self, message: dict):
        """
        广播消息给所有连接

        Args:
            message: 消息内容
        """
        for connections in self.active_connections.values():
            for connection in connections:
                try:
                    await connection.send_text(json.dumps(message))
                except:
                    pass

    async def broadcast_to_admins(self, message: dict):
        """
        广播消息给所有管理员

        Args:
            message: 消息内容
        """
        # 简化版本：广播给所有连接的用户
        # 实际应该检查用户角色
        await self.broadcast(message)


# 全局连接管理器实例
manager = ConnectionManager()


async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket 端点

    Args:
        websocket: WebSocket 连接
    """
    # 从查询参数获取 token
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=1008, reason="Missing token")
        return

    # 验证 token
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        user_id = payload.get("user_id")
        if not user_id:
            await websocket.close(code=1008, reason="Invalid token")
            return
    except JWTError:
        await websocket.close(code=1008, reason="Invalid token")
        return

    # 连接
    await manager.connect(websocket, user_id)

    try:
        while True:
            # 接收消息（保持连接）
            data = await websocket.receive_text()
            # 可以在这里处理客户端发送的消息
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)


# 辅助函数：在其他地方调用以发送通知

async def notify_task_progress(task_id: int, progress: dict):
    """
    通知任务进度

    Args:
        task_id: 任务 ID
        progress: 进度信息
    """
    await manager.broadcast_to_admins({
        "type": "task_progress",
        "task_id": task_id,
        "progress": progress
    })


async def notify_task_status(task_id: int, status: str, message: str):
    """
    通知任务状态变更

    Args:
        task_id: 任务 ID
        status: 新状态
        message: 消息
    """
    await manager.broadcast_to_admins({
        "type": "task_status",
        "task_id": task_id,
        "status": status,
        "message": message
    })


async def notify_user_registered(user_data: dict):
    """
    通知新用户注册

    Args:
        user_data: 用户数据
    """
    await manager.broadcast_to_admins({
        "type": "user_registered",
        "user": user_data
    })
