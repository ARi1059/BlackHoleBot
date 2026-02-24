# BlackHoleBot 部署检查清单

## 📋 部署前准备

### 1. 服务器环境
- [ ] Ubuntu 20.04+ / Debian 11+ 或其他 Linux 发行版
- [ ] Python 3.10 或更高版本
- [ ] 至少 2GB RAM
- [ ] 至少 50GB 存储空间
- [ ] 稳定的网络连接

### 2. 必需服务
- [ ] PostgreSQL 14+ 已安装并运行
- [ ] Redis 7+ 已安装并运行
- [ ] Nginx（可选，用于反向代理）

### 3. Telegram 准备
- [ ] 已创建 Telegram Bot（通过 @BotFather）
- [ ] 获取 Bot Token
- [ ] 获取 Bot Username
- [ ] 至少一个 Telegram API ID 和 API Hash（从 https://my.telegram.org 获取）
- [ ] 至少一个 Telegram 用户账号用于搬运（需要手机号）

## 🔧 安装步骤

### Step 1: 克隆项目
```bash
cd /opt
git clone <your-repo-url> BlackHoleBot
cd BlackHoleBot
```

### Step 2: 创建虚拟环境
```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 3: 安装依赖
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4: 配置环境变量
```bash
cp .env.example .env
nano .env
```

必须配置的环境变量：
```env
# Bot 配置
BOT_TOKEN=your_bot_token_here
BOT_USERNAME=your_bot_username

# 数据库配置
DATABASE_URL=postgresql+asyncpg://user:password@localhost/blackholebot

# Redis 配置
REDIS_URL=redis://localhost:6379/0

# 安全配置（使用以下命令生成）
# python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
SESSION_ENCRYPTION_KEY=your_fernet_key_here

# python -c "import secrets; print(secrets.token_urlsafe(32))"
SECRET_KEY=your_secret_key_here

# Telegram Login
TELEGRAM_BOT_USERNAME=your_bot_username

# Web 配置
WEB_HOST=0.0.0.0
WEB_PORT=8000
```

### Step 5: 创建数据库
```bash
# 登录 PostgreSQL
sudo -u postgres psql

# 创建数据库和用户
CREATE DATABASE blackholebot;
CREATE USER blackholebot_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE blackholebot TO blackholebot_user;
\q
```

### Step 6: 运行数据库迁移
```bash
alembic upgrade head
```

### Step 7: 创建管理员账号
```bash
python scripts/create_admin.py
```
按提示输入管理员的 Telegram User ID

### Step 8: 添加 Session 账号
```bash
python scripts/add_session.py
```
按提示输入：
- 手机号（国际格式，如 +8613800138000）
- API ID
- API Hash
- 验证码（发送到手机）
- 两步验证密码（如果启用）
- 优先级（1-10，数字越大优先级越高）

## 🚀 启动服务

### 方式 1: 手动启动（测试用）

终端 1 - 启动 Bot：
```bash
source venv/bin/activate
python bot/main.py
```

终端 2 - 启动 Web API：
```bash
source venv/bin/activate
python web/main.py
```

### 方式 2: 使用 Systemd（生产环境推荐）

创建 Bot 服务：
```bash
sudo nano /etc/systemd/system/blackholebot.service
```

内容：
```ini
[Unit]
Description=BlackHoleBot Telegram Bot
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=your_user
WorkingDirectory=/opt/BlackHoleBot
Environment="PATH=/opt/BlackHoleBot/venv/bin"
ExecStart=/opt/BlackHoleBot/venv/bin/python bot/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

创建 Web API 服务：
```bash
sudo nano /etc/systemd/system/blackholebot-web.service
```

内容：
```ini
[Unit]
Description=BlackHoleBot Web API
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=your_user
WorkingDirectory=/opt/BlackHoleBot
Environment="PATH=/opt/BlackHoleBot/venv/bin"
ExecStart=/opt/BlackHoleBot/venv/bin/python web/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启动服务：
```bash
sudo systemctl daemon-reload
sudo systemctl enable blackholebot
sudo systemctl enable blackholebot-web
sudo systemctl start blackholebot
sudo systemctl start blackholebot-web
```

检查状态：
```bash
sudo systemctl status blackholebot
sudo systemctl status blackholebot-web
```

查看日志：
```bash
sudo journalctl -u blackholebot -f
sudo journalctl -u blackholebot-web -f
```

## 🌐 配置 Nginx（可选）

如果需要通过域名访问 Web API：

```bash
sudo nano /etc/nginx/sites-available/blackholebot
```

内容：
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /ws {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

启用配置：
```bash
sudo ln -s /etc/nginx/sites-available/blackholebot /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

配置 HTTPS（使用 Let's Encrypt）：
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

## ✅ 部署后验证

### 1. 检查服务状态
```bash
# 检查 Bot 服务
sudo systemctl status blackholebot

# 检查 Web API 服务
sudo systemctl status blackholebot-web

# 检查 PostgreSQL
sudo systemctl status postgresql

# 检查 Redis
sudo systemctl status redis
```

### 2. 测试 Bot
- 在 Telegram 中找到你的 Bot
- 发送 `/start` 命令
- 应该收到欢迎消息

### 3. 测试 Web API
```bash
# 健康检查
curl http://localhost:8000/health

# 查看 API 文档
curl http://localhost:8000/docs
```

### 4. 测试管理员功能
- 使用管理员账号在 Bot 中发送 `/list_collections`
- 应该能看到合集列表（即使是空的）

### 5. 测试搬运功能
- 发送 `/create_transfer` 创建搬运任务
- 检查任务是否正常执行

## 🔒 安全建议

### 1. 防火墙配置
```bash
# 只开放必要端口
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable
```

### 2. 数据库安全
- 使用强密码
- 限制数据库只能本地访问
- 定期备份数据库

### 3. Redis 安全
```bash
# 编辑 Redis 配置
sudo nano /etc/redis/redis.conf

# 设置密码
requirepass your_strong_password

# 只监听本地
bind 127.0.0.1

# 重启 Redis
sudo systemctl restart redis
```

更新 .env 中的 REDIS_URL：
```env
REDIS_URL=redis://:your_strong_password@localhost:6379/0
```

### 4. 文件权限
```bash
# 设置正确的文件权限
chmod 600 .env
chmod 700 scripts/
```

### 5. 定期更新
```bash
# 定期更新系统
sudo apt update && sudo apt upgrade

# 定期更新 Python 依赖
pip install --upgrade -r requirements.txt
```

## 📊 监控和维护

### 1. 日志管理
```bash
# 查看 Bot 日志
sudo journalctl -u blackholebot -n 100

# 查看 Web API 日志
sudo journalctl -u blackholebot-web -n 100

# 实时监控日志
sudo journalctl -u blackholebot -f
```

### 2. 数据库备份
```bash
# 创建备份脚本
nano /opt/BlackHoleBot/backup.sh
```

内容：
```bash
#!/bin/bash
BACKUP_DIR="/opt/backups/blackholebot"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

# 备份数据库
pg_dump -U blackholebot_user blackholebot > $BACKUP_DIR/db_$DATE.sql

# 保留最近 7 天的备份
find $BACKUP_DIR -name "db_*.sql" -mtime +7 -delete
```

设置定时任务：
```bash
chmod +x /opt/BlackHoleBot/backup.sh
crontab -e

# 每天凌晨 2 点备份
0 2 * * * /opt/BlackHoleBot/backup.sh
```

### 3. 性能监控
```bash
# 监控系统资源
htop

# 监控 PostgreSQL
sudo -u postgres psql -c "SELECT * FROM pg_stat_activity;"

# 监控 Redis
redis-cli INFO
```

## 🐛 故障排查

### Bot 无法启动
1. 检查 Bot Token 是否正确
2. 检查网络连接
3. 查看日志：`sudo journalctl -u blackholebot -n 50`

### Web API 无法访问
1. 检查端口是否被占用：`sudo netstat -tlnp | grep 8000`
2. 检查防火墙设置
3. 查看日志：`sudo journalctl -u blackholebot-web -n 50`

### 数据库连接失败
1. 检查 PostgreSQL 是否运行：`sudo systemctl status postgresql`
2. 检查数据库连接字符串
3. 检查数据库用户权限

### Redis 连接失败
1. 检查 Redis 是否运行：`sudo systemctl status redis`
2. 检查 Redis 密码配置
3. 测试连接：`redis-cli ping`

### 搬运任务失败
1. 检查 Session 账号是否有效
2. 检查是否触发限流
3. 查看任务日志：`/task_info {task_id}`

## 📞 获取帮助

如果遇到问题：
1. 查看项目文档：`docs/` 目录
2. 查看日志文件
3. 检查配置文件
4. 查看 GitHub Issues

## ✅ 部署完成

恭喜！如果所有检查都通过，你的 BlackHoleBot 已经成功部署并运行。

现在你可以：
- 使用 Bot 管理合集
- 创建搬运任务
- 通过 Web API 管理系统
- 监控系统运行状态

祝使用愉快！🎉
