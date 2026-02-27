# BlackHoleBot 项目文档

本目录包含 BlackHoleBot 的详细技术文档。

## 文档索引

### 核心文档

1. **[数据库设计](01-数据库设计.md)**
   - 数据表结构
   - 索引设计
   - 关系说明
   - 数据模型

2. **[用户端功能](02-用户端功能.md)**
   - 深度链接访问
   - 分页浏览
   - 搜索功能
   - 权限控制

3. **[管理员上传功能](03-管理员上传功能.md)**
   - 手动上传合集
   - 编辑合集信息
   - 批量管理
   - 操作流程

4. **[搬运系统](04-搬运系统.md)**
   - 自动搬运机制
   - 三层限流控制
   - 多账号管理
   - 任务队列
   - Session 管理

5. **[权限管理](05-权限管理.md)**
   - 用户角色系统
   - 权限控制
   - 封禁管理
   - 操作日志

6. **[Web 后台](06-Web后台.md)**
   - API 设计
   - 认证系统
   - 管理界面
   - WebSocket 实时通信

### 使用说明

- **[Bot 用户端使用说明](Bot用户端使用说明.md)** - 普通用户使用指南
- **[Bot 管理员功能使用说明](Bot管理员功能使用说明.md)** - 管理员操作手册

## 快速导航

### 新手入门
1. 阅读根目录 [README.md](../README.md) 了解项目概况
2. 查看 [DEPLOYMENT.md](../DEPLOYMENT.md) 进行部署
3. 阅读 [Bot管理员功能使用说明](Bot管理员功能使用说明.md) 学习管理操作

### 开发者
1. [数据库设计](01-数据库设计.md) - 了解数据结构
2. [搬运系统](04-搬运系统.md) - 理解核心功能
3. [Web 后台](06-Web后台.md) - API 开发参考

### 运维人员
1. [DEPLOYMENT.md](../DEPLOYMENT.md) - 部署指南
2. [权限管理](05-权限管理.md) - 用户管理
3. 监控和备份章节

## 技术栈

- **Bot 框架**: aiogram 3.15.0
- **Telegram 客户端**: Telethon 1.34.0
- **Web 框架**: FastAPI
- **数据库**: PostgreSQL + SQLAlchemy (异步)
- **缓存**: Redis
- **认证**: JWT + Telegram Login Widget

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
└── docs/                # 项目文档（本目录）
```

## 核心功能概览

### 管理员功能
- 手动上传创建合集
- 自动搬运频道内容
- 用户权限管理
- Web 可视化管理

### 用户功能
- 深度链接访问合集
- 分页浏览媒体
- 搜索合集
- VIP 权限访问

### 搬运系统特性
- 多账号自动切换
- 三层智能限流
- 任务队列管理
- 实时进度监控

## 贡献文档

如果你想为文档做出贡献：

1. 保持文档结构清晰
2. 使用 Markdown 格式
3. 添加代码示例
4. 更新文档索引

## 获取帮助

- 查看 [常见问题](../README.md#常见问题)
- 提交 [GitHub Issue](https://github.com/yourusername/BlackHoleBot/issues)
- 查看日志文件排查问题

## 许可证

MIT License
