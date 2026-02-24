# BlackHoleBot 项目文档

## 项目概述

BlackHoleBot 是一个基于 Telegram 的资源存储和分享机器人，支持通过深链接分享媒体资源，具备完整的用户权限管理、搬运系统和 Web 管理后台。

## 文档目录

1. [数据库设计](./01-数据库设计.md) - 数据库表结构、索引设计和关系
2. [用户端功能](./02-用户端功能.md) - 深链接访问、分页浏览、搜索功能
3. [管理员上传功能](./03-管理员上传功能.md) - 手动上传合集、编辑和管理
4. [搬运系统](./04-搬运系统.md) - 自动搬运、限流控制、任务管理
5. [权限管理](./05-权限管理.md) - 用户角色、权限控制、操作日志
6. [Web 后台](./06-Web后台.md) - API 设计、前端页面、实时通信
7. [部署配置](./07-部署配置.md) - 服务器配置、部署流程、监控备份

## 核心功能

### 用户端
- 通过深链接直接访问合集
- 分页浏览媒体（每页 10 个）
- 模糊搜索合集
- VIP 合集权限控制

### 管理端
- 手动上传创建合集
- 编辑合集信息
- 批量删除合集
- 用户权限管理
- 系统设置

### 搬运系统
- 多账号自动搬运
- 智能限流控制
- 自动账号切换
- 任务队列管理
- Web 可视化操作

### Web 后台
- Telegram Login 认证
- 仪表盘统计
- 合集管理
- 用户管理
- 搬运任务管理
- Session 账号管理
- 实时进度推送

## 技术栈

### 后端
- **Python 3.10+**
- **aiogram 3.x** - Telegram Bot 框架
- **Telethon** - Telegram 用户客户端（搬运）
- **FastAPI** - Web API 框架
- **SQLAlchemy** - ORM
- **PostgreSQL** - 主数据库
- **Redis** - 缓存和临时存储

### 前端
- **Vue 3 / React** - 前端框架
- **Element Plus / Ant Design** - UI 组件库
- **Axios** - HTTP 客户端
- **WebSocket** - 实时通信

### 部署
- **Nginx** - 反向代理
- **Let's Encrypt** - HTTPS 证书
- **Systemd** - 进程管理
- **Ubuntu 20.04+** - 服务器系统

## 项目结构

```
BlackHoleBot/
├── bot/                      # Telegram Bot
│   ├── handlers/            # 消息处理器
│   │   ├── user.py         # 用户端功能
│   │   ├── admin.py        # 管理员功能
│   │   └── collection.py   # 合集相关
│   ├── middlewares/        # 中间件
│   ├── keyboards/          # 键盘布局
│   ├── states.py           # FSM 状态机
│   └── main.py             # Bot 入口
│
├── web/                     # Web 管理后台
│   ├── api/                # FastAPI 路由
│   │   ├── auth.py        # 认证
│   │   ├── collections.py # 合集管理
│   │   ├── users.py       # 用户管理
│   │   ├── tasks.py       # 搬运任务
│   │   └── sessions.py    # Session 管理
│   ├── frontend/          # 前端代码
│   └── main.py            # Web 入口
│
├── transfer/               # 搬运模块
│   ├── client_manager.py  # Telethon 客户端管理
│   ├── task_executor.py   # 任务执行器
│   ├── task_queue.py      # 任务队列
│   ├── rate_limiter.py    # 限流控制
│   └── session_selector.py # Session 选择
│
├── database/
│   ├── models.py          # SQLAlchemy 模型
│   ├── crud.py            # 数据库操作
│   └── connection.py      # 数据库连接
│
├── utils/
│   ├── security.py        # 加密/解密
│   ├── deep_link.py       # 深链接生成
│   └── pagination.py      # 分页工具
│
├── docs/                  # 项目文档
├── config.py              # 配置文件
├── requirements.txt       # Python 依赖
├── .env.example           # 环境变量示例
└── README.md              # 项目说明
```

## 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/your-repo/BlackHoleBot.git
cd BlackHoleBot
```

### 2. 安装依赖

```bash
# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装 Python 依赖
pip install -r requirements.txt

# 安装前端依赖
cd web/frontend
npm install
cd ../..
```

### 3. 配置环境变量

```bash
cp .env.example .env
nano .env
```

填入必要的配置：
- `BOT_TOKEN` - Telegram Bot Token
- `DATABASE_URL` - PostgreSQL 连接字符串
- `REDIS_URL` - Redis 连接字符串
- `SESSION_ENCRYPTION_KEY` - Session 加密密钥
- `SECRET_KEY` - JWT 密钥

### 4. 初始化数据库

```bash
alembic upgrade head
```

### 5. 启动服务

```bash
# 启动 Bot
python bot/main.py

# 启动 Web API（另一个终端）
uvicorn web.main:app --reload

# 启动前端开发服务器（另一个终端）
cd web/frontend
npm run dev
```

## 开发指南

### 添加新功能

1. 在对应模块创建新文件
2. 实现功能逻辑
3. 添加路由/处理器
4. 编写测试
5. 更新文档

### 数据库迁移

```bash
# 创建迁移
alembic revision --autogenerate -m "描述"

# 执行迁移
alembic upgrade head

# 回滚
alembic downgrade -1
```

### 代码规范

- 使用 Black 格式化代码
- 使用 isort 排序导入
- 使用 flake8 检查代码质量
- 使用 mypy 进行类型检查

```bash
# 格式化
black .

# 排序导入
isort .

# 检查
flake8 .
mypy .
```

## 常见问题

### Q: Bot 无法接收消息？
A: 检查 Bot Token 是否正确，确保 Bot 已启动并连接到 Telegram API。

### Q: 数据库连接失败？
A: 检查 PostgreSQL 是否运行，DATABASE_URL 配置是否正确。

### Q: 搬运任务卡住？
A: 查看任务日志，可能是 API 限流或 Session 账号失效。

### Q: Web 后台无法登录？
A: 确保用户角色为 admin 或 super_admin，检查 JWT 配置。

## 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 许可证

MIT License

## 联系方式

- 项目地址: https://github.com/your-repo/BlackHoleBot
- 问题反馈: https://github.com/your-repo/BlackHoleBot/issues

## 更新日志

### v1.0.0 (2024-01-15)
- 初始版本发布
- 实现核心功能
- 完成文档编写
