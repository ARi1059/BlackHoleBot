# BlackHoleBot - Telegram 媒体搬运与管理系统

BlackHoleBot 是一个功能强大的 Telegram Bot，用于自动搬运频道媒体文件、创建媒体合集，并通过深链接分享。

## 主要功能

### 1. 管理员上传功能
- 手动创建媒体合集
- 上传图片/视频
- 设置合集信息（名称、描述、标签）
- 配置访问权限（公开/VIP）
- 生成深链接分享

### 2. 搬运系统
- 多账号管理（Telethon Session）
- 自动从频道/群组批量转发媒体
- 智能限流控制（三种限流机制）
- 任务队列管理（确保单任务执行）
- 过滤条件（媒体类型、关键词、日期范围）
- 任务审核与确认

### 3. 用户端功能
- 通过深链接访问合集
- 分页浏览媒体
- 搜索合集
- VIP 权限控制

## 技术栈

- **Bot 框架**: aiogram 3.3.0
- **Telegram 客户端**: Telethon 1.34.0
- **数据库**: PostgreSQL + SQLAlchemy 2.0
- **缓存**: Redis 7+
- **Web 框架**: FastAPI
- **加密**: cryptography (Fernet)

## 安装步骤

### 1. 克隆项目

```bash
git clone https://github.com/yourusername/BlackHoleBot.git
cd BlackHoleBot
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

复制 `.env.example` 为 `.env` 并填写配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```env
# Bot 配置
BOT_TOKEN=your_bot_token_from_botfather
BOT_USERNAME=your_bot_username

# 数据库配置
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/blackholebot

# Redis 配置
REDIS_URL=redis://localhost:6379/0

# 安全配置（生成加密密钥）
SESSION_ENCRYPTION_KEY=your_fernet_key
SECRET_KEY=your_secret_key
```

生成加密密钥：

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### 4. 初始化数据库

```bash
# 创建数据库
createdb blackholebot

# 运行迁移
alembic upgrade head

# 创建管理员账号
python scripts/create_admin.py
```

### 5. 启动服务

```bash
# 启动 Bot
python bot/main.py

# 启动 Web 后台（另一个终端）
python web/main.py
```

## 使用指南

### 管理员命令

#### 上传合集
```
/upload - 开始创建新合集
/add_media {code} - 添加媒体到现有合集
/edit_collection {code} - 编辑合集信息
/delete_collection {code} - 删除合集
/list_collections - 查看所有合集
```

#### 搬运任务
```
/create_transfer - 创建搬运任务
/list_tasks - 查看任务列表
/task_info {task_id} - 查看任务详情
/pause_task {task_id} - 暂停任务
/resume_task {task_id} - 恢复任务
/approve_task {task_id} - 审核任务并创建合集
/reject_task {task_id} - 拒绝任务
```

### 用户命令
```
/start - 启动 Bot
/start {code} - 通过深链接访问合集
/search {keyword} - 搜索合集
```

## 搬运系统工作流程

1. **创建任务**: 管理员通过 `/create_transfer` 创建搬运任务
2. **任务执行**: 系统自动选择可用 Session 账号执行任务
3. **文件转发**: Telethon 客户端从源频道转发文件到 Bot
4. **Bot 接收**: Bot 接收文件并提取 file_id 存入 Redis
5. **限流控制**:
   - Session 限流：每 500 个文件冷却 3 分钟
   - API 限流：自动切换 Session 账号
   - Bot 限流：暂停转发，等待恢复
6. **任务完成**: 文件存储在 Redis 中，等待审核
7. **审核确认**: 管理员审核任务，填写合集信息
8. **创建合集**: 从 Redis 读取文件，批量插入数据库，生成深链接

## 限流控制机制

### 1. Session 账号限流（500 文件/周期）
- 每个 Session 转发 500 个文件后自动冷却 3 分钟
- 冷却期间自动切换到下一个可用 Session

### 2. API ID/Hash 限流
- 检测到 `FloodWaitError` 时自动切换 Session
- 被限流的 Session 进入冷却状态

### 3. Bot API 限流
- 检测到 `TelegramRetryAfter` 时暂停转发
- 等待已转发文件的 file_id 全部获取完成
- 限流结束后自动恢复转发

## 项目结构

```
BlackHoleBot/
├── bot/                    # Bot 相关代码
│   ├── handlers/          # 命令处理器
│   │   ├── user.py       # 用户命令
│   │   ├── admin.py      # 管理员命令
│   │   ├── transfer.py   # 文件接收
│   │   ├── transfer_admin.py    # 搬运任务管理
│   │   └── transfer_approve.py  # 任务审核
│   ├── middlewares/       # 中间件
│   ├── keyboards/         # 键盘布局
│   ├── states.py         # FSM 状态
│   └── main.py           # Bot 主程序
├── database/              # 数据库相关
│   ├── models.py         # 数据模型
│   ├── crud.py           # CRUD 操作
│   └── connection.py     # 数据库连接
├── utils/                 # 工具模块
│   ├── session_manager.py      # Session 管理
│   ├── task_queue.py          # 任务队列
│   ├── rate_limiter.py        # 限流控制
│   ├── transfer_executor.py   # 任务执行器
│   ├── encryption.py          # 加密工具
│   └── deep_link.py          # 深链接生成
├── web/                   # Web 后台
├── scripts/               # 脚本工具
├── docs/                  # 文档
├── alembic/              # 数据库迁移
├── config.py             # 配置文件
├── requirements.txt      # 依赖列表
└── .env.example         # 环境变量示例
```

## 开发文档

详细文档请查看 `docs/` 目录：

- [数据库设计](docs/01-数据库设计.md)
- [用户端功能](docs/02-用户端功能.md)
- [管理员上传功能](docs/03-管理员上传功能.md)
- [搬运系统](docs/04-搬运系统.md)
- [权限管理](docs/05-权限管理.md)
- [Web 后台](docs/06-Web后台.md)
- [部署配置](docs/07-部署配置.md)

## 贡献

欢迎提交 Issue 和 Pull Request！

## 许可证

MIT License
