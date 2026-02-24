# BlackHoleBot 快速启动指南

## 前置要求

- Python 3.10+
- PostgreSQL 14+
- Redis 7+
- Telegram Bot Token

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件，填写以下必需配置：

```env
# Bot 配置
BOT_TOKEN=your_bot_token_here
BOT_USERNAME=your_bot_username
TELEGRAM_BOT_USERNAME=your_bot_username

# 数据库配置
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/blackholebot

# Redis 配置
REDIS_URL=redis://localhost:6379/0

# 安全配置
SESSION_ENCRYPTION_KEY=生成的加密密钥
SECRET_KEY=your_secret_key
```

生成加密密钥：

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### 3. 初始化数据库

```bash
# 创建数据库
createdb blackholebot

# 运行迁移
alembic upgrade head

# 创建管理员账号
python scripts/create_admin.py
```

### 4. 启动 Bot

```bash
python bot/main.py
```

## 管理员命令速查

### 上传合集
```
/upload                      - 开始创建新合集
/add_media {code}           - 添加媒体到现有合集
/edit_collection {code}     - 编辑合集信息
/delete_collection {code}   - 删除合集
/list_collections           - 查看所有合集
/batch_delete               - 批量删除合集
```

### 搬运任务
```
/create_transfer            - 创建搬运任务
/list_tasks                 - 查看任务列表
/task_info {task_id}        - 查看任务详情
/pause_task {task_id}       - 暂停任务
/resume_task {task_id}      - 恢复任务
/approve_task {task_id}     - 审核任务并创建合集
/reject_task {task_id}      - 拒绝任务
```

### 通用命令
```
/cancel                     - 取消当前操作
```

## 使用示例

### 示例 1: 手动上传合集

```
1. 发送 /upload
2. 发送图片/视频（可多个）
3. 发送 /done
4. 输入合集名称: "可爱猫咪"
5. 输入描述: "各种可爱的猫咪图片"（或 /skip）
6. 输入标签: "猫咪 可爱 宠物"（或 /skip）
7. 选择权限: 点击 [公开] 或 [VIP]
8. 完成！获得深链接
```

### 示例 2: 创建搬运任务

```
1. 发送 /create_transfer
2. 输入频道: @channel_username 或 -1001234567890
3. 选择媒体类型: 点击 [全部媒体]
4. 输入关键词: "猫咪"（或 /skip）
5. 输入任务名称: "猫咪频道搬运"
6. 等待任务执行完成
7. 发送 /approve_task 1 审核任务
8. 按提示填写合集信息
9. 完成！获得深链接
```

## 添加 Session 账号

搬运功能需要至少一个 Telegram Session 账号。

### 方法 1: 通过 Python 脚本（推荐）

创建 `scripts/add_session.py`:

```python
import asyncio
from database.connection import get_db
from utils.session_manager import session_manager

async def main():
    phone = input("手机号（带国家码，如 +86）: ")
    api_id = int(input("API ID: "))
    api_hash = input("API Hash: ")

    # 发送验证码
    result = await session_manager.login_session(phone, api_id, api_hash)
    print(result["message"])

    if result["status"] == "code_sent":
        code = input("验证码: ")
        result = await session_manager.login_session(phone, api_id, api_hash, code=code)

        if result["status"] == "password_required":
            password = input("两步验证密码: ")
            result = await session_manager.login_session(phone, api_id, api_hash, code=code, password=password)

    if result["status"] == "success":
        async for db in get_db():
            await session_manager.add_session_account(
                db,
                phone_number=phone,
                api_id=api_id,
                api_hash=api_hash,
                session_string=result["session_string"],
                priority=0
            )
            print("✅ Session 账号添加成功！")
            break

if __name__ == "__main__":
    asyncio.run(main())
```

运行：

```bash
python scripts/add_session.py
```

### 获取 API ID 和 API Hash

1. 访问 https://my.telegram.org
2. 登录你的 Telegram 账号
3. 进入 "API development tools"
4. 创建应用获取 `api_id` 和 `api_hash`

## 常见问题

### Q: Bot 无法启动？

**A:** 检查以下几点：
- Bot Token 是否正确
- 数据库连接是否正常
- Redis 是否运行
- 依赖是否完整安装

### Q: 搬运任务一直处于 pending 状态？

**A:** 可能原因：
- 没有添加 Session 账号
- Session 账号不可用或已失效
- 检查 `/list_tasks` 查看任务状态

### Q: 如何查看日志？

**A:** 日志输出到：
- 控制台（标准输出）
- `bot.log` 文件

### Q: 限流后如何处理？

**A:** 系统会自动处理：
- Session 限流：自动切换账号
- API 限流：自动切换账号
- Bot 限流：自动暂停并恢复

### Q: 如何备份数据？

**A:** 备份以下内容：
- PostgreSQL 数据库
- Redis 数据（可选）
- `.env` 配置文件

```bash
# 备份数据库
pg_dump blackholebot > backup.sql

# 恢复数据库
psql blackholebot < backup.sql
```

## 性能优化建议

1. **数据库优化**
   - 定期清理旧日志
   - 添加适当索引
   - 使用连接池

2. **Redis 优化**
   - 设置合理的过期时间
   - 定期清理过期数据

3. **Session 账号**
   - 添加多个 Session 账号
   - 设置不同优先级
   - 定期检查账号状态

## 监控建议

1. **任务监控**
   ```bash
   # 查看运行中的任务
   /list_tasks

   # 查看任务详情
   /task_info {task_id}
   ```

2. **日志监控**
   ```bash
   # 实时查看日志
   tail -f bot.log

   # 搜索错误
   grep ERROR bot.log
   ```

3. **系统监控**
   - 监控 CPU 和内存使用
   - 监控数据库连接数
   - 监控 Redis 内存使用

## 下一步

- 阅读完整文档：[docs/](../docs/)
- 了解搬运系统：[docs/04-搬运系统.md](../docs/04-搬运系统.md)
- 配置 Web 后台：[docs/06-Web后台.md](../docs/06-Web后台.md)
- 部署到生产环境：[docs/07-部署配置.md](../docs/07-部署配置.md)

## 获取帮助

- 查看文档：`docs/` 目录
- 提交 Issue：GitHub Issues
- 查看日志：`bot.log` 文件
