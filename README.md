# BlackHoleBot

一个功能强大的 Telegram 媒体收藏管理系统，支持自动搬运频道内容、创建媒体合集并通过深度链接分享。

## 核心功能

### 管理员功能
- **手动上传合集** - 直接通过 Telegram 上传图片/视频创建合集
- **自动搬运系统** - 使用多账号从频道批量转存媒体
- **智能限流控制** - 三层限流机制，自动切换账号
- **Web 管理后台** - 可视化管理界面，实时监控任务进度

### 用户功能
- **深度链接访问** - 通过唯一链接快速访问合集
- **分页浏览** - 流畅的媒体浏览体验
- **搜索功能** - 快速查找感兴趣的合集
- **VIP 权限** - 支持公开/VIP 两级访问控制

## 技术栈

- **Bot 框架**: aiogram 3.15.0
- **Telegram 客户端**: Telethon 1.34.0
- **Web 框架**: FastAPI
- **数据库**: PostgreSQL + SQLAlchemy (异步)
- **缓存**: Redis
- **认证**: JWT + Telegram Login Widget

## 快速开始

### 使用 Docker (推荐)

```bash
# 1. 克隆项目
git clone https://github.com/yourusername/BlackHoleBot.git
cd BlackHoleBot

# 2. 配置环境变量
cp .env.example .env
nano .env  # 填写必要配置

# 3. 启动服务
docker-compose up -d

# 4. 初始化数据库
docker-compose exec bot alembic upgrade head

# 5. 创建管理员
docker-compose exec bot python scripts/create_admin.py
```

### 手动安装

详见 [DEPLOYMENT.md](DEPLOYMENT.md) 获取完整的 Debian 12 部署指南。

## 项目结构

```
BlackHoleBot/
├── bot/                    # Telegram Bot 应用
│   ├── handlers/          # 命令处理器
│   ├── middlewares/       # 中间件
│   ├── keyboards/         # 键盘布局
│   └── main.py           # Bot 入口
├── web/                   # Web 管理后台
│   ├── api/              # REST API
│   └── main.py           # Web 入口
├── database/             # 数据库层
│   ├── models.py        # 数据模型
│   └── crud.py          # CRUD 操作
├── utils/                # 工具模块
│   ├── transfer_executor.py   # 搬运执行器
│   ├── session_manager.py     # Session 管理
│   └── rate_limiter.py        # 限流控制
├── scripts/              # 工具脚本
├── alembic/             # 数据库迁移
└── docs/                # 项目文档
```

## 管理员命令

### 合集管理
```
/upload                    - 创建新合集
/add_media {code}         - 添加媒体到现有合集
/edit_collection {code}   - 编辑合集信息
/delete_collection {code} - 删除合集
/list_collections         - 查看所有合集
```

### 搬运任务
```
/create_transfer          - 创建搬运任务
/list_tasks              - 查看任务列表
/task_info {task_id}     - 查看任务详情
/approve_task {task_id}  - 审核并创建合集
/pause_task {task_id}    - 暂停任务
/resume_task {task_id}   - 恢复任务
```

### 用户管理
```
/ban_user {user_id}      - 封禁用户
/unban_user {user_id}    - 解封用户
/set_vip {user_id}       - 设置 VIP
/user_info {user_id}     - 查看用户信息
```

## 搬运系统特性

### 三层限流机制

1. **Session 级别限流**
   - 每个账号 500 文件/周期
   - 自动冷却 3 分钟
   - 自动切换到下一个可用账号

2. **API 级别限流**
   - 检测 FloodWaitError
   - 智能切换 Session
   - 记录冷却时间

3. **Bot 级别限流**
   - 检测 TelegramRetryAfter
   - 暂停转发等待恢复
   - 确保数据完整性

### 多账号管理

- 支持添加多个 Telethon Session 账号
- 优先级调度系统
- 自动健康检查
- Session 加密存储

## 配置说明

主要环境变量：

```env
# Bot 配置
BOT_TOKEN=              # 从 @BotFather 获取
BOT_USERNAME=           # Bot 用户名

# 数据库
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/dbname

# Redis
REDIS_URL=redis://localhost:6379/0

# 安全密钥（使用下面命令生成）
SESSION_ENCRYPTION_KEY= # python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
SECRET_KEY=            # python -c "import secrets; print(secrets.token_urlsafe(32))"

# 可选配置
PRIVATE_CHANNEL=       # 私有频道 ID，自动发送合集
WEB_DOMAIN=           # Web 后台域名
```

## 文档

- [部署指南](DEPLOYMENT.md) - Debian 12 完整部署教程
- [数据库设计](docs/01-数据库设计.md) - 数据表结构说明
- [搬运系统](docs/04-搬运系统.md) - 搬运系统详细说明
- [Web 后台](docs/06-Web后台.md) - Web API 文档

## 常见问题

**Q: Bot 无法启动？**
- 检查 BOT_TOKEN 是否正确
- 确认数据库和 Redis 正常运行
- 查看日志：`docker-compose logs bot`

**Q: 搬运任务一直 pending？**
- 确认已添加 Session 账号
- 检查账号是否有效：`/list_sessions`（Web 后台）
- 查看任务日志：`/task_info {task_id}`

**Q: 如何添加 Session 账号？**
```bash
docker-compose exec bot python scripts/add_session.py
# 或通过 Web 后台的 Session 管理页面
```

**Q: 如何备份数据？**
```bash
# 备份数据库
docker-compose exec postgres pg_dump -U user dbname > backup.sql

# 备份配置
cp .env .env.backup
```

## 安全建议

1. **定期更新依赖**
   ```bash
   pip list --outdated
   pip install --upgrade -r requirements.txt
   ```

2. **使用强密码**
   - 数据库密码至少 16 位
   - Redis 设置密码保护
   - 定期轮换密钥

3. **防火墙配置**
   ```bash
   ufw allow 22/tcp   # SSH
   ufw allow 80/tcp   # HTTP
   ufw allow 443/tcp  # HTTPS
   ufw enable
   ```

4. **定期备份**
   - 每天自动备份数据库
   - 保留最近 7 天备份
   - 异地存储重要备份

## 监控与维护

### 查看日志
```bash
# Docker 方式
docker-compose logs -f bot
docker-compose logs -f web

# Systemd 方式
journalctl -u blackholebot -f
journalctl -u blackholebot-web -f
```

### 性能监控
```bash
# 查看资源使用
docker stats

# 数据库连接数
docker-compose exec postgres psql -U user -c "SELECT count(*) FROM pg_stat_activity;"

# Redis 内存使用
docker-compose exec redis redis-cli INFO memory
```

## 贡献

欢迎提交 Issue 和 Pull Request！

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 许可证

MIT License

## 致谢

- [aiogram](https://github.com/aiogram/aiogram) - 优秀的 Telegram Bot 框架
- [Telethon](https://github.com/LonamiWebs/Telethon) - 强大的 Telegram 客户端库
- [FastAPI](https://github.com/tiangolo/fastapi) - 现代化的 Web 框架
