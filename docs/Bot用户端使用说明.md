# Bot 用户端功能使用说明

## 已完成的功能

### ✅ 核心模块

1. **工具函数模块** (`utils/`)
   - `deep_link.py` - 深链接生成和解析
   - `pagination.py` - 分页工具

2. **中间件** (`bot/middlewares/`)
   - `auth.py` - 用户认证中间件
     - 自动注册新用户
     - 检查封禁状态
     - 更新最后活跃时间
     - 注入用户信息到 handler

3. **键盘布局** (`bot/keyboards/`)
   - `inline.py` - 内联键盘
     - 分页键盘
     - 搜索结果键盘
     - 合集信息键盘

4. **用户处理器** (`bot/handlers/user.py`)
   - `/start` - 欢迎消息和深链接访问
   - `/search` - 搜索合集
   - `/help` - 帮助信息
   - `/myinfo` - 个人信息
   - 分页浏览回调处理
   - 合集信息查看

5. **主程序** (`bot/main.py`)
   - Bot 初始化
   - 中间件注册
   - 路由注册
   - 日志配置

## 功能特性

### 1. 深链接访问
- 格式: `t.me/yourbot?start=abc123`
- 自动解析参数
- 权限检查（VIP 合集）
- 合集不存在提示

### 2. 分页浏览
- 每页 10 个媒体
- 上一页/下一页按钮
- 页码显示
- 首页快速跳转
- 合集信息查看

### 3. 搜索功能
- 关键词搜索
- 模糊匹配名称、标签、描述
- 权限过滤（VIP 合集）
- 最多显示 10 个结果
- 点击按钮直接查看

### 4. 用户体验
- 自动注册新用户
- 封禁用户拦截
- 友好的错误提示
- 清晰的按钮布局
- 媒体组批量发送

## 测试步骤

### 1. 准备环境

```bash
# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env，填入 BOT_TOKEN 等配置

# 初始化数据库
python scripts/init_db.py

# 创建超级管理员
python scripts/create_admin.py --telegram-id YOUR_ID
```

### 2. 启动 Bot

```bash
python bot/main.py
```

### 3. 测试功能

#### 测试欢迎消息
1. 在 Telegram 中找到你的 Bot
2. 发送 `/start`
3. 应该看到欢迎消息

#### 测试搜索功能
1. 发送 `/search 测试`
2. 应该看到搜索结果（如果有数据）

#### 测试帮助命令
1. 发送 `/help`
2. 应该看到帮助信息

#### 测试个人信息
1. 发送 `/myinfo`
2. 应该看到你的用户信息

#### 测试深链接（需要先创建合集）
1. 创建一个测试合集（通过管理员功能或直接插入数据库）
2. 发送 `/start abc123`（替换为实际的深链接码）
3. 应该看到合集内容和分页按钮

## 数据库测试数据

如果需要测试，可以手动插入一些测试数据：

```python
# 创建测试合集的脚本
import asyncio
from database import init_db
from database.crud import create_collection, create_media
from database.connection import async_session_maker
from database.models import AccessLevel

async def create_test_data():
    async with async_session_maker() as db:
        # 创建测试合集
        collection = await create_collection(
            db,
            name="测试合集",
            deep_link_code="test123",
            description="这是一个测试合集",
            tags=["测试", "示例"],
            access_level=AccessLevel.PUBLIC,
            created_by=1  # 替换为你的用户 ID
        )

        print(f"✅ 创建测试合集成功: {collection.id}")
        print(f"   深链接: t.me/yourbot?start=test123")

asyncio.run(create_test_data())
```

## 注意事项

1. **Bot Token**: 确保在 `.env` 中配置了正确的 `BOT_TOKEN`
2. **数据库**: 确保 PostgreSQL 正在运行且连接配置正确
3. **Redis**: 虽然当前代码未使用 Redis，但后续功能会需要
4. **日志**: Bot 会在控制台和 `bot.log` 文件中输出日志

## 下一步开发

用户端功能已完成，接下来可以开发：

1. **管理员功能** - 上传合集、编辑、删除
2. **搬运系统** - 自动搬运媒体
3. **Web 后台** - 可视化管理界面

## 文件结构

```
BlackHoleBot/
├── bot/
│   ├── handlers/
│   │   ├── __init__.py
│   │   └── user.py          ✅ 用户端处理器
│   ├── keyboards/
│   │   ├── __init__.py
│   │   └── inline.py        ✅ 内联键盘
│   ├── middlewares/
│   │   ├── __init__.py
│   │   └── auth.py          ✅ 认证中间件
│   ├── __init__.py
│   └── main.py              ✅ Bot 主程序
├── utils/
│   ├── __init__.py
│   ├── deep_link.py         ✅ 深链接工具
│   └── pagination.py        ✅ 分页工具
├── database/                ✅ 数据库模块（已完成）
├── config.py                ✅ 配置文件
└── requirements.txt         ✅ 依赖列表
```

## 常见问题

### Q: Bot 无法启动？
A: 检查 `BOT_TOKEN` 是否正确，数据库是否连接成功。

### Q: 发送命令没有响应？
A: 查看日志文件 `bot.log`，检查是否有错误信息。

### Q: 媒体组发送失败？
A: 确保 `file_id` 有效，检查 Telegram API 限制。

### Q: 搜索没有结果？
A: 确保数据库中有合集数据，检查权限过滤逻辑。
