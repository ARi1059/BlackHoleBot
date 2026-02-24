# Web 后台管理文档

## 概述

Web 后台是 BlackHoleBot 的可视化管理界面，提供仪表盘、合集管理、用户管理、搬运任务管理、Session 账号管理等功能。基于 FastAPI + 前端框架（Vue 3 / React）构建。

## 技术架构

### 后端技术栈

- **FastAPI** - 现代化的 Python Web 框架
- **SQLAlchemy** - ORM
- **Pydantic** - 数据验证
- **JWT** - 身份认证
- **WebSocket** - 实时通信（任务进度推送）

### 前端技术栈

**推荐方案 1: Vue 3**
- Vue 3 + Vite
- Element Plus (UI 组件库)
- Pinia (状态管理)
- Vue Router
- Axios

**推荐方案 2: React**
- React 18 + Vite
- Ant Design (UI 组件库)
- Zustand (状态管理)
- React Router
- Axios

## API 设计

### 认证相关

#### POST /api/auth/telegram
Telegram Login 认证

**请求体**:
```json
{
  "id": 123456789,
  "first_name": "John",
  "username": "john_doe",
  "photo_url": "https://...",
  "auth_date": 1234567890,
  "hash": "abc123..."
}
```

**响应**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "user": {
    "id": 123456789,
    "username": "john_doe",
    "first_name": "John",
    "role": "admin"
  }
}
```

#### GET /api/auth/me
获取当前用户信息

**响应**:
```json
{
  "id": 123456789,
  "username": "john_doe",
  "first_name": "John",
  "role": "admin",
  "created_at": "2024-01-01T00:00:00Z"
}
```

### 仪表盘相关

#### GET /api/dashboard/stats
获取统计数据

**响应**:
```json
{
  "total_users": 1250,
  "total_vip_users": 320,
  "total_collections": 85,
  "total_media": 12450,
  "public_collections": 60,
  "vip_collections": 25,
  "active_tasks": 1,
  "completed_tasks": 42
}
```

#### GET /api/dashboard/recent-activity
获取最近活动

**响应**:
```json
{
  "activities": [
    {
      "id": 1,
      "type": "collection_created",
      "user": "admin",
      "description": "创建了合集「可爱猫咪」",
      "created_at": "2024-01-01T12:00:00Z"
    },
    {
      "id": 2,
      "type": "user_registered",
      "user": "john_doe",
      "description": "新用户注册",
      "created_at": "2024-01-01T11:30:00Z"
    }
  ]
}
```

### 合集管理

#### GET /api/collections
获取合集列表

**查询参数**:
- `page`: 页码（默认 1）
- `limit`: 每页数量（默认 20）
- `search`: 搜索关键词
- `access_level`: 过滤权限（public/vip）

**响应**:
```json
{
  "collections": [
    {
      "id": 1,
      "name": "可爱猫咪合集",
      "description": "各种可爱的猫咪图片",
      "tags": ["猫咪", "可爱"],
      "deep_link_code": "abc123",
      "access_level": "vip",
      "media_count": 50,
      "created_by": "admin",
      "created_at": "2024-01-01T00:00:00Z"
    }
  ],
  "total": 85,
  "page": 1,
  "limit": 20
}
```

#### GET /api/collections/{id}
获取合集详情

**响应**:
```json
{
  "id": 1,
  "name": "可爱猫咪合集",
  "description": "各种可爱的猫咪图片",
  "tags": ["猫咪", "可爱"],
  "deep_link_code": "abc123",
  "access_level": "vip",
  "media_count": 50,
  "created_by": "admin",
  "created_at": "2024-01-01T00:00:00Z",
  "media": [
    {
      "id": 1,
      "file_id": "AgACAgIAAxkBAAI...",
      "file_type": "photo",
      "caption": "可爱的小猫",
      "order_index": 0
    }
  ]
}
```

#### PUT /api/collections/{id}
更新合集信息

**请求体**:
```json
{
  "name": "超可爱猫咪合集",
  "description": "更新后的描述",
  "tags": ["猫咪", "可爱", "萌宠"],
  "access_level": "public"
}
```

**响应**:
```json
{
  "success": true,
  "message": "更新成功"
}
```

#### DELETE /api/collections/{id}
删除合集

**响应**:
```json
{
  "success": true,
  "message": "删除成功"
}
```

#### POST /api/collections/batch-delete
批量删除合集

**请求体**:
```json
{
  "collection_ids": [1, 2, 3]
}
```

**响应**:
```json
{
  "success": true,
  "deleted_count": 3
}
```

### 用户管理

#### GET /api/users
获取用户列表

**查询参数**:
- `page`: 页码
- `limit`: 每页数量
- `role`: 过滤角色
- `search`: 搜索用户名

**响应**:
```json
{
  "users": [
    {
      "id": 1,
      "telegram_id": 123456789,
      "username": "john_doe",
      "first_name": "John",
      "role": "vip",
      "is_banned": false,
      "created_at": "2024-01-01T00:00:00Z",
      "last_active_at": "2024-01-15T12:00:00Z"
    }
  ],
  "total": 1250,
  "page": 1,
  "limit": 20
}
```

#### PUT /api/users/{id}/role
修改用户角色（仅超级管理员）

**请求体**:
```json
{
  "role": "vip"
}
```

**响应**:
```json
{
  "success": true,
  "message": "角色更新成功"
}
```

#### PUT /api/users/{id}/ban
封禁/解封用户

**请求体**:
```json
{
  "is_banned": true
}
```

**响应**:
```json
{
  "success": true,
  "message": "用户已封禁"
}
```

### 搬运任务管理

#### GET /api/tasks
获取搬运任务列表

**查询参数**:
- `page`: 页码
- `limit`: 每页数量
- `status`: 过滤状态

**响应**:
```json
{
  "tasks": [
    {
      "id": 1,
      "task_name": "搬运猫咪频道",
      "source_chat_id": -1001234567890,
      "source_chat_username": "cat_channel",
      "filter_type": "photo",
      "status": "running",
      "progress_current": 150,
      "progress_total": 500,
      "created_at": "2024-01-15T10:00:00Z",
      "started_at": "2024-01-15T10:05:00Z"
    }
  ],
  "total": 42,
  "page": 1,
  "limit": 20
}
```

#### POST /api/tasks
创建搬运任务

**请求体**:
```json
{
  "task_name": "搬运猫咪频道",
  "source_chat_id": -1001234567890,
  "source_chat_username": "cat_channel",
  "filter_keywords": ["猫", "cat"],
  "filter_type": "photo",
  "filter_date_from": "2024-01-01T00:00:00Z",
  "filter_date_to": "2024-01-31T23:59:59Z"
}
```

**响应**:
```json
{
  "success": true,
  "task_id": 1,
  "message": "任务已创建，等待执行"
}
```

#### GET /api/tasks/{id}
获取任务详情

**响应**:
```json
{
  "id": 1,
  "task_name": "搬运猫咪频道",
  "source_chat_id": -1001234567890,
  "source_chat_username": "cat_channel",
  "filter_keywords": ["猫", "cat"],
  "filter_type": "photo",
  "status": "completed",
  "progress_current": 500,
  "progress_total": 500,
  "session_account_id": 1,
  "created_at": "2024-01-15T10:00:00Z",
  "started_at": "2024-01-15T10:05:00Z",
  "completed_at": "2024-01-15T12:30:00Z",
  "logs": [
    {
      "id": 1,
      "log_type": "info",
      "message": "任务开始执行",
      "created_at": "2024-01-15T10:05:00Z"
    },
    {
      "id": 2,
      "log_type": "session_cooldown",
      "message": "Session 1 达到 500 文件限制，冷却 3 分钟",
      "created_at": "2024-01-15T11:00:00Z"
    }
  ]
}
```

#### POST /api/tasks/{id}/approve
审核并创建合集

**请求体**:
```json
{
  "name": "猫咪合集",
  "description": "从频道搬运的猫咪图片",
  "tags": ["猫咪", "可爱"],
  "access_level": "vip"
}
```

**响应**:
```json
{
  "success": true,
  "collection_id": 10,
  "deep_link_code": "xyz789",
  "message": "合集创建成功"
}
```

#### DELETE /api/tasks/{id}
删除任务

**响应**:
```json
{
  "success": true,
  "message": "任务已删除"
}
```

### Session 账号管理

#### GET /api/sessions
获取 Session 账号列表

**响应**:
```json
{
  "sessions": [
    {
      "id": 1,
      "phone_number": "+1234567890",
      "priority": 1,
      "is_active": true,
      "transfer_count": 250,
      "cooldown_until": null,
      "created_at": "2024-01-01T00:00:00Z",
      "last_used_at": "2024-01-15T12:00:00Z"
    }
  ]
}
```

#### POST /api/sessions/login
登录 Session 账号

**请求体（第一步 - 发送验证码）**:
```json
{
  "phone_number": "+1234567890",
  "api_id": 12345,
  "api_hash": "abcdef123456"
}
```

**响应**:
```json
{
  "success": true,
  "message": "验证码已发送",
  "phone_code_hash": "abc123..."
}
```

**请求体（第二步 - 验证码登录）**:
```json
{
  "phone_number": "+1234567890",
  "api_id": 12345,
  "api_hash": "abcdef123456",
  "phone_code_hash": "abc123...",
  "code": "12345"
}
```

**响应（成功）**:
```json
{
  "success": true,
  "session_id": 1,
  "message": "登录成功"
}
```

**响应（需要密码）**:
```json
{
  "success": false,
  "password_required": true,
  "message": "需要两步验证密码"
}
```

**请求体（第三步 - 两步验证）**:
```json
{
  "phone_number": "+1234567890",
  "api_id": 12345,
  "api_hash": "abcdef123456",
  "phone_code_hash": "abc123...",
  "password": "mypassword"
}
```

#### PUT /api/sessions/{id}
更新 Session 账号

**请求体**:
```json
{
  "priority": 2,
  "is_active": false
}
```

**响应**:
```json
{
  "success": true,
  "message": "更新成功"
}
```

#### DELETE /api/sessions/{id}
删除 Session 账号

**响应**:
```json
{
  "success": true,
  "message": "账号已删除"
}
```

### 系统设置

#### GET /api/settings
获取系统设置

**响应**:
```json
{
  "welcome_message": "欢迎使用 BlackHoleBot！",
  "bot_name": "BlackHoleBot",
  "max_media_per_collection": 1000
}
```

#### PUT /api/settings
更新系统设置（仅超级管理员）

**请求体**:
```json
{
  "welcome_message": "新的欢迎消息",
  "max_media_per_collection": 1500
}
```

**响应**:
```json
{
  "success": true,
  "message": "设置已更新"
}
```

## WebSocket 实时通信

### 连接

**URL**: `ws://your-domain/ws`

**认证**: 连接时需要在查询参数中传递 JWT token

```javascript
const ws = new WebSocket('ws://your-domain/ws?token=your_jwt_token');
```

### 消息格式

**任务进度更新**:
```json
{
  "type": "task_progress",
  "task_id": 1,
  "progress": {
    "current": 150,
    "total": 500,
    "percentage": 30
  }
}
```

**任务状态变更**:
```json
{
  "type": "task_status",
  "task_id": 1,
  "status": "completed",
  "message": "任务已完成"
}
```

**新用户注册**:
```json
{
  "type": "user_registered",
  "user": {
    "id": 123456789,
    "username": "new_user",
    "created_at": "2024-01-15T12:00:00Z"
  }
}
```

## 前端页面设计

### 1. 登录页面

**路由**: `/login`

**功能**:
- Telegram Login Widget
- 自动跳转到仪表盘

**组件**:
```vue
<template>
  <div class="login-page">
    <div class="login-card">
      <h1>BlackHoleBot 管理后台</h1>
      <div id="telegram-login"></div>
    </div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue';

onMounted(() => {
  // 加载 Telegram Login Widget
  const script = document.createElement('script');
  script.src = 'https://telegram.org/js/telegram-widget.js?22';
  script.setAttribute('data-telegram-login', 'your_bot_username');
  script.setAttribute('data-size', 'large');
  script.setAttribute('data-onauth', 'onTelegramAuth(user)');
  script.setAttribute('data-request-access', 'write');
  document.getElementById('telegram-login').appendChild(script);
});

window.onTelegramAuth = async (user) => {
  // 发送到后端验证
  const response = await fetch('/api/auth/telegram', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(user)
  });

  const data = await response.json();
  localStorage.setItem('token', data.access_token);
  window.location.href = '/dashboard';
};
</script>
```

### 2. 仪表盘页面

**路由**: `/dashboard`

**功能**:
- 统计卡片（用户数、合集数、媒体数）
- 最近活动列表
- 快速操作按钮

**布局**:
```
+------------------+------------------+------------------+
|   总用户数       |   总合集数       |   总媒体数       |
|     1,250        |      85          |    12,450        |
+------------------+------------------+------------------+
|                                                         |
|  最近活动                                               |
|  - admin 创建了合集「可爱猫咪」                         |
|  - john_doe 注册成为新用户                              |
|  - 搬运任务 #5 已完成                                   |
|                                                         |
+---------------------------------------------------------+
```

### 3. 合集管理页面

**路由**: `/collections`

**功能**:
- 合集列表（表格）
- 搜索和筛选
- 批量操作
- 查看/编辑/删除合集

**表格列**:
- ID
- 名称
- 描述
- 标签
- 访问权限
- 媒体数量
- 创建时间
- 操作（查看/编辑/删除）

### 4. 用户管理页面

**路由**: `/users`

**功能**:
- 用户列表（表格）
- 搜索和筛选
- 修改角色
- 封禁/解封

**表格列**:
- Telegram ID
- 用户名
- 姓名
- 角色
- 状态
- 注册时间
- 最后活跃
- 操作

### 5. 搬运任务页面

**路由**: `/tasks`

**功能**:
- 任务列表
- 创建新任务
- 查看任务详情和日志
- 实时进度显示
- 审核任务

**创建任务表单**:
```
任务名称: [输入框]
来源频道 ID: [输入框]
来源频道用户名: [输入框]
过滤类型: [下拉选择: 全部/图片/视频]
关键词: [标签输入]
日期范围: [日期选择器]

[创建任务]
```

### 6. Session 账号管理页面

**路由**: `/sessions`

**功能**:
- Session 列表
- 添加新账号（登录流程）
- 修改优先级
- 启用/禁用账号
- 删除账号

**添加账号流程**:
```
步骤 1: 输入手机号、API ID、API Hash
  ↓
步骤 2: 输入验证码
  ↓
步骤 3: （如需要）输入两步验证密码
  ↓
完成
```

### 7. 系统设置页面

**路由**: `/settings`

**功能**:
- 欢迎消息设置（支持 Markdown）
- Bot 配置
- 系统参数

## 前端代码示例

### Axios 配置

```javascript
// src/utils/request.js
import axios from 'axios';

const request = axios.create({
  baseURL: '/api',
  timeout: 10000
});

// 请求拦截器
request.interceptors.request.use(
  config => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  error => {
    return Promise.reject(error);
  }
);

// 响应拦截器
request.interceptors.response.use(
  response => response.data,
  error => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default request;
```

### API 调用示例

```javascript
// src/api/collections.js
import request from '@/utils/request';

export const getCollections = (params) => {
  return request.get('/collections', { params });
};

export const getCollectionDetail = (id) => {
  return request.get(`/collections/${id}`);
};

export const updateCollection = (id, data) => {
  return request.put(`/collections/${id}`, data);
};

export const deleteCollection = (id) => {
  return request.delete(`/collections/${id}`);
};

export const batchDeleteCollections = (ids) => {
  return request.post('/collections/batch-delete', { collection_ids: ids });
};
```

### WebSocket 使用示例

```javascript
// src/utils/websocket.js
class WebSocketClient {
  constructor() {
    this.ws = null;
    this.listeners = new Map();
  }

  connect(token) {
    this.ws = new WebSocket(`ws://your-domain/ws?token=${token}`);

    this.ws.onopen = () => {
      console.log('WebSocket 连接成功');
    };

    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      const listeners = this.listeners.get(data.type) || [];
      listeners.forEach(callback => callback(data));
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket 错误:', error);
    };

    this.ws.onclose = () => {
      console.log('WebSocket 连接关闭');
      // 自动重连
      setTimeout(() => this.connect(token), 3000);
    };
  }

  on(type, callback) {
    if (!this.listeners.has(type)) {
      this.listeners.set(type, []);
    }
    this.listeners.get(type).push(callback);
  }

  off(type, callback) {
    const listeners = this.listeners.get(type);
    if (listeners) {
      const index = listeners.indexOf(callback);
      if (index > -1) {
        listeners.splice(index, 1);
      }
    }
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
    }
  }
}

export default new WebSocketClient();
```

**使用示例**:
```javascript
// 在组件中使用
import websocket from '@/utils/websocket';

// 监听任务进度
websocket.on('task_progress', (data) => {
  console.log('任务进度:', data.progress);
  // 更新 UI
});

// 监听任务状态
websocket.on('task_status', (data) => {
  console.log('任务状态:', data.status);
});
```

## 后端实现示例

### FastAPI 主应用

```python
# web/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .api import auth, dashboard, collections, users, tasks, sessions, settings
from .websocket import websocket_endpoint

app = FastAPI(title="BlackHoleBot API")

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router, prefix="/api/auth", tags=["认证"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["仪表盘"])
app.include_router(collections.router, prefix="/api/collections", tags=["合集"])
app.include_router(users.router, prefix="/api/users", tags=["用户"])
app.include_router(tasks.router, prefix="/api/tasks", tags=["任务"])
app.include_router(sessions.router, prefix="/api/sessions", tags=["Session"])
app.include_router(settings.router, prefix="/api/settings", tags=["设置"])

# WebSocket
app.add_websocket_route("/ws", websocket_endpoint)

# 静态文件（前端构建产物）
app.mount("/", StaticFiles(directory="web/frontend/dist", html=True), name="static")
```

### 认证路由示例

```python
# web/api/auth.py
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import hashlib
import hmac
from datetime import datetime, timedelta
from jose import jwt

router = APIRouter()

class TelegramAuthData(BaseModel):
    id: int
    first_name: str
    username: str = None
    photo_url: str = None
    auth_date: int
    hash: str

def verify_telegram_auth(auth_data: dict, bot_token: str) -> bool:
    """验证 Telegram Login 数据"""
    check_hash = auth_data.pop("hash")

    data_check_string = "\n".join(
        f"{k}={v}" for k, v in sorted(auth_data.items())
    )

    secret_key = hashlib.sha256(bot_token.encode()).digest()
    calculated_hash = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256
    ).hexdigest()

    return calculated_hash == check_hash

def create_access_token(data: dict) -> str:
    """创建 JWT token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=7)
    to_encode.update({"exp": expire})

    return jwt.encode(to_encode, SECRET_KEY, algorithm="HS256")

@router.post("/telegram")
async def telegram_login(auth_data: TelegramAuthData):
    """Telegram 登录"""
    # 验证数据
    if not verify_telegram_auth(auth_data.dict(), BOT_TOKEN):
        raise HTTPException(status_code=401, detail="认证失败")

    # 获取用户
    user = await get_user_by_telegram_id(auth_data.id)
    if not user:
        raise HTTPException(status_code=403, detail="用户不存在")

    # 检查权限
    if user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="权限不足")

    # 生成 token
    token = create_access_token(
        data={"user_id": user.id, "role": user.role}
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.telegram_id,
            "username": user.username,
            "first_name": user.first_name,
            "role": user.role
        }
    }
```

### WebSocket 实现

```python
# web/websocket.py
from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, Set
import json

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)

    def disconnect(self, websocket: WebSocket, user_id: int):
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

    async def send_to_user(self, user_id: int, message: dict):
        """发送消息给特定用户"""
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                await connection.send_text(json.dumps(message))

    async def broadcast(self, message: dict):
        """广播消息给所有连接"""
        for connections in self.active_connections.values():
            for connection in connections:
                await connection.send_text(json.dumps(message))

manager = ConnectionManager()

async def websocket_endpoint(websocket: WebSocket):
    # 从查询参数获取 token
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=1008)
        return

    # 验证 token
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("user_id")
    except:
        await websocket.close(code=1008)
        return

    await manager.connect(websocket, user_id)

    try:
        while True:
            # 保持连接
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)

# 在其他地方使用
async def notify_task_progress(task_id: int, progress: dict):
    """通知任务进度"""
    await manager.broadcast({
        "type": "task_progress",
        "task_id": task_id,
        "progress": progress
    })
```

## 部署配置

### Nginx 配置

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # 重定向到 HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    # 前端静态文件
    location / {
        root /var/www/blackholebot/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # API 代理
    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    # WebSocket 代理
    location /ws {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

### Systemd 服务

```ini
# /etc/systemd/system/blackholebot-web.service
[Unit]
Description=BlackHoleBot Web API
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/var/www/blackholebot
Environment="PATH=/var/www/blackholebot/venv/bin"
ExecStart=/var/www/blackholebot/venv/bin/uvicorn web.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

## 安全建议

1. **HTTPS**: 生产环境必须使用 HTTPS
2. **CORS**: 限制允许的域名
3. **Token 过期**: JWT token 设置合理的过期时间
4. **Rate Limiting**: 使用 slowapi 限制 API 请求频率
5. **输入验证**: 使用 Pydantic 严格验证所有输入
6. **SQL 注入**: 使用 SQLAlchemy ORM 防止 SQL 注入
7. **XSS**: 前端对用户输入进行转义

## 性能优化

1. **缓存**: 使用 Redis 缓存热门数据
2. **分页**: 所有列表接口都实现分页
3. **懒加载**: 前端使用虚拟滚动加载大列表
4. **CDN**: 静态资源使用 CDN
5. **压缩**: 启用 Gzip 压缩
6. **数据库索引**: 优化查询性能

