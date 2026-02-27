# BlackHoleBot - Debian 12 部署指南

本文档提供在 Debian 12 系统上部署 BlackHoleBot 的完整步骤。

## 目录

- [系统要求](#系统要求)
- [准备工作](#准备工作)
- [方式一：Docker 部署（推荐）](#方式一docker-部署推荐)
- [方式二：手动部署](#方式二手动部署)
- [配置 Nginx 反向代理](#配置-nginx-反向代理)
- [SSL 证书配置](#ssl-证书配置)
- [数据库备份](#数据库备份)
- [监控与维护](#监控与维护)
- [故障排查](#故障排查)

---

## 系统要求

### 硬件要求
- **CPU**: 2 核心或以上
- **内存**: 2GB RAM 最低，4GB 推荐
- **硬盘**: 20GB 可用空间（根据媒体数量调整）
- **网络**: 稳定的互联网连接

### 软件要求
- **操作系统**: Debian 12 (Bookworm)
- **Python**: 3.11+ (手动部署)
- **PostgreSQL**: 15+
- **Redis**: 7+
- **Docker**: 24.0+ (Docker 部署)

---

## 准备工作

### 1. 更新系统

```bash
sudo apt update && sudo apt upgrade -y
```

### 2. 安装基础工具

```bash
sudo apt install -y curl wget git vim ufw
```

### 3. 配置防火墙

```bash
# 允许 SSH
sudo ufw allow 22/tcp

# 允许 HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# 启用防火墙
sudo ufw enable
```

### 4. 创建部署用户（可选但推荐）

```bash
# 创建专用用户
sudo adduser blackholebot

# 添加到 sudo 组（如需要）
sudo usermod -aG sudo blackholebot

# 切换到该用户
su - blackholebot
```

### 5. 获取 Telegram 凭证

在开始部署前，请准备以下信息：

1. **Bot Token**:
   - 访问 [@BotFather](https://t.me/BotFather)
   - 发送 `/newbot` 创建新 Bot
   - 保存返回的 Token

2. **Bot Username**:
   - 创建 Bot 时设置的用户名（如 `@YourBot`）

3. **Telegram API 凭证**（用于搬运功能）:
   - 访问 https://my.telegram.org
   - 登录后进入 "API development tools"
   - 创建应用获取 `api_id` 和 `api_hash`

4. **管理员 Telegram ID**:
   - 访问 [@userinfobot](https://t.me/userinfobot)
   - 发送任意消息获取你的 User ID

---

## 方式一：Docker 部署（推荐）

Docker 部署是最简单、最可靠的方式，适合生产环境。

### 1. 安装 Docker

```bash
# 安装 Docker 官方 GPG 密钥
sudo apt install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/debian/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# 添加 Docker 仓库
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# 安装 Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# 启动 Docker
sudo systemctl enable docker
sudo systemctl start docker

# 将当前用户添加到 docker 组（避免每次使用 sudo）
sudo usermod -aG docker $USER

# 重新登录以应用组权限
exit
# 重新 SSH 登录
```

### 2. 克隆项目

```bash
cd /opt
sudo git clone https://github.com/yourusername/BlackHoleBot.git
sudo chown -R $USER:$USER BlackHoleBot
cd BlackHoleBot
```

### 3. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑配置文件
nano .env
```

填写以下必需配置：

```env
# Bot 配置
BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz  # 替换为你的 Bot Token
BOT_USERNAME=YourBot                              # 替换为你的 Bot 用户名
TELEGRAM_BOT_USERNAME=YourBot                     # 同上

# 数据库配置
DATABASE_URL=postgresql+asyncpg://blackholebot:your_db_password@postgres:5432/blackholebot

# Redis 配置
REDIS_URL=redis://:your_redis_password@redis:6379/0

# 安全配置 - 生成密钥
SESSION_ENCRYPTION_KEY=生成的密钥（见下方）
SECRET_KEY=生成的密钥（见下方）

# Web 配置
WEB_HOST=0.0.0.0
WEB_PORT=8000
WEB_DOMAIN=https://your-domain.com  # 如果有域名

# 可选：私有频道
PRIVATE_CHANNEL=-1001234567890  # 替换为你的频道 ID
```

**生成安全密钥**：

```bash
# 生成 SESSION_ENCRYPTION_KEY
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# 生成 SECRET_KEY
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

**配置 Docker 环境变量**：

```bash
# 编辑 docker-compose.yml 中的密码
nano docker-compose.yml
```

修改以下行：
```yaml
POSTGRES_PASSWORD: ${DB_PASSWORD:-your_strong_password}
# 和
command: redis-server --requirepass your_strong_redis_password
```

同时更新 `.env` 中的对应密码。

### 4. 构建并启动服务

```bash
# 构建镜像
docker compose build

# 启动所有服务
docker compose up -d

# 查看服务状态
docker compose ps
```

### 5. 初始化数据库

```bash
# 运行数据库迁移
docker compose exec bot alembic upgrade head
```

### 6. 创建管理员账号

```bash
docker compose exec bot python scripts/create_admin.py
```

按提示输入你的 Telegram User ID。

### 7. 添加 Session 账号（用于搬运功能）

```bash
docker compose exec bot python scripts/add_session.py
```

按提示输入：
- 手机号（国际格式，如 `+8613800138000`）
- API ID
- API Hash
- 验证码（发送到手机）
- 两步验证密码（如果启用）
- 优先级（1-10，数字越大优先级越高）

### 8. 验证部署

```bash
# 查看 Bot 日志
docker compose logs -f bot

# 查看 Web 日志
docker compose logs -f web

# 测试 Bot
# 在 Telegram 中找到你的 Bot，发送 /start
```

### 9. Docker 常用命令

```bash
# 查看所有容器状态
docker compose ps

# 查看日志
docker compose logs -f [service_name]

# 重启服务
docker compose restart [service_name]

# 停止所有服务
docker compose down

# 停止并删除数据卷（危险！会删除数据）
docker compose down -v

# 更新代码后重新构建
git pull
docker compose build
docker compose up -d

# 进入容器
docker compose exec bot bash
docker compose exec postgres psql -U blackholebot
```

---

## 方式二：手动部署

如果不使用 Docker，可以手动部署。

### 1. 安装 Python 3.11

```bash
# Debian 12 默认是 Python 3.11
sudo apt install -y python3 python3-pip python3-venv python3-dev

# 验证版本
python3 --version  # 应该是 3.11.x
```

### 2. 安装 PostgreSQL

```bash
# 安装 PostgreSQL
sudo apt install -y postgresql postgresql-contrib

# 启动服务
sudo systemctl enable postgresql
sudo systemctl start postgresql

# 创建数据库和用户
sudo -u postgres psql << EOF
CREATE DATABASE blackholebot;
CREATE USER blackholebot WITH PASSWORD 'your_strong_password';
GRANT ALL PRIVILEGES ON DATABASE blackholebot TO blackholebot;
\c blackholebot
GRANT ALL ON SCHEMA public TO blackholebot;
EOF
```

### 3. 安装 Redis

```bash
# 安装 Redis
sudo apt install -y redis-server

# 配置 Redis
sudo nano /etc/redis/redis.conf
```

修改以下配置：
```conf
# 设置密码
requirepass your_strong_redis_password

# 只监听本地
bind 127.0.0.1

# 启用持久化
save 900 1
save 300 10
save 60 10000
```

重启 Redis：
```bash
sudo systemctl restart redis-server
sudo systemctl enable redis-server
```

### 4. 克隆项目

```bash
cd /opt
sudo git clone https://github.com/yourusername/BlackHoleBot.git
sudo chown -R $USER:$USER BlackHoleBot
cd BlackHoleBot
```

### 5. 创建虚拟环境

```bash
python3 -m venv venv
source venv/bin/activate
```

### 6. 安装依赖

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 7. 配置环境变量

```bash
cp .env.example .env
nano .env
```

填写配置（参考 Docker 部署部分），注意数据库和 Redis 地址改为 `localhost`：

```env
DATABASE_URL=postgresql+asyncpg://blackholebot:your_db_password@localhost:5432/blackholebot
REDIS_URL=redis://:your_redis_password@localhost:6379/0
```

### 8. 初始化数据库

```bash
alembic upgrade head
```

### 9. 创建管理员

```bash
python scripts/create_admin.py
```

### 10. 配置 Systemd 服务

创建 Bot 服务：

```bash
sudo nano /etc/systemd/system/blackholebot.service
```

内容：
```ini
[Unit]
Description=BlackHoleBot Telegram Bot
After=network.target postgresql.service redis-server.service
Wants=postgresql.service redis-server.service

[Service]
Type=simple
User=blackholebot
Group=blackholebot
WorkingDirectory=/opt/BlackHoleBot
Environment="PATH=/opt/BlackHoleBot/venv/bin"
ExecStart=/opt/BlackHoleBot/venv/bin/python bot/main.py
Restart=always
RestartSec=10
StandardOutput=append:/opt/BlackHoleBot/logs/bot.log
StandardError=append:/opt/BlackHoleBot/logs/bot.error.log

[Install]
WantedBy=multi-user.target
```

创建 Web 服务：

```bash
sudo nano /etc/systemd/system/blackholebot-web.service
```

内容：
```ini
[Unit]
Description=BlackHoleBot Web API
After=network.target postgresql.service redis-server.service
Wants=postgresql.service redis-server.service

[Service]
Type=simple
User=blackholebot
Group=blackholebot
WorkingDirectory=/opt/BlackHoleBot
Environment="PATH=/opt/BlackHoleBot/venv/bin"
ExecStart=/opt/BlackHoleBot/venv/bin/python web/main.py
Restart=always
RestartSec=10
StandardOutput=append:/opt/BlackHoleBot/logs/web.log
StandardError=append:/opt/BlackHoleBot/logs/web.error.log

[Install]
WantedBy=multi-user.target
```

创建日志目录：
```bash
mkdir -p /opt/BlackHoleBot/logs
```

启动服务：
```bash
sudo systemctl daemon-reload
sudo systemctl enable blackholebot blackholebot-web
sudo systemctl start blackholebot blackholebot-web
```

查看状态：
```bash
sudo systemctl status blackholebot
sudo systemctl status blackholebot-web
```

查看日志：
```bash
sudo journalctl -u blackholebot -f
sudo journalctl -u blackholebot-web -f
```

---

## 配置 Nginx 反向代理

如果需要通过域名访问 Web 后台，配置 Nginx。

### 1. 安装 Nginx

```bash
sudo apt install -y nginx
```

### 2. 创建配置文件

```bash
sudo nano /etc/nginx/sites-available/blackholebot
```

内容：
```nginx
server {
    listen 80;
    server_name your-domain.com;  # 替换为你的域名

    # 限制请求大小（用于文件上传）
    client_max_body_size 100M;

    # API 路由
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # 超时设置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # WebSocket 路由
    location /ws {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

        # WebSocket 超时
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
    }

    # 安全头
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
}
```

### 3. 启用配置

```bash
# 创建软链接
sudo ln -s /etc/nginx/sites-available/blackholebot /etc/nginx/sites-enabled/

# 测试配置
sudo nginx -t

# 重载 Nginx
sudo systemctl reload nginx
```

---

## SSL 证书配置

使用 Let's Encrypt 免费 SSL 证书。

### 1. 安装 Certbot

```bash
sudo apt install -y certbot python3-certbot-nginx
```

### 2. 获取证书

```bash
sudo certbot --nginx -d your-domain.com
```

按提示操作：
- 输入邮箱
- 同意服务条款
- 选择是否重定向 HTTP 到 HTTPS（推荐选择 2）

### 3. 自动续期

Certbot 会自动配置续期，验证：

```bash
sudo systemctl status certbot.timer
```

手动测试续期：
```bash
sudo certbot renew --dry-run
```

---

## 数据库备份

### 1. 创建备份脚本

```bash
sudo nano /opt/BlackHoleBot/backup.sh
```

内容：
```bash
#!/bin/bash

# 配置
BACKUP_DIR="/opt/backups/blackholebot"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="blackholebot"
DB_USER="blackholebot"
KEEP_DAYS=7

# 创建备份目录
mkdir -p $BACKUP_DIR

# Docker 部署备份
if command -v docker &> /dev/null; then
    docker compose exec -T postgres pg_dump -U $DB_USER $DB_NAME | gzip > $BACKUP_DIR/db_$DATE.sql.gz
else
    # 手动部署备份
    PGPASSWORD='your_db_password' pg_dump -U $DB_USER -h localhost $DB_NAME | gzip > $BACKUP_DIR/db_$DATE.sql.gz
fi

# 删除旧备份
find $BACKUP_DIR -name "db_*.sql.gz" -mtime +$KEEP_DAYS -delete

echo "Backup completed: $BACKUP_DIR/db_$DATE.sql.gz"
```

设置权限：
```bash
chmod +x /opt/BlackHoleBot/backup.sh
```

### 2. 配置定时任务

```bash
crontab -e
```

添加：
```cron
# 每天凌晨 2 点备份
0 2 * * * /opt/BlackHoleBot/backup.sh >> /opt/BlackHoleBot/logs/backup.log 2>&1
```

### 3. 恢复备份

```bash
# Docker 部署
gunzip < /opt/backups/blackholebot/db_20240228_020000.sql.gz | docker compose exec -T postgres psql -U blackholebot blackholebot

# 手动部署
gunzip < /opt/backups/blackholebot/db_20240228_020000.sql.gz | PGPASSWORD='your_db_password' psql -U blackholebot -h localhost blackholebot
```

---

## 监控与维护

### 1. 系统监控脚本

创建简单的健康检查脚本：

```bash
sudo nano /opt/BlackHoleBot/healthcheck.sh
```

内容：
```bash
#!/bin/bash

TELEGRAM_BOT_TOKEN="your_bot_token"
TELEGRAM_CHAT_ID="your_admin_telegram_id"

send_alert() {
    curl -s -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendMessage" \
        -d chat_id=$TELEGRAM_CHAT_ID \
        -d text="⚠️ BlackHoleBot Alert: $1"
}

# 检查 Bot 服务
if ! systemctl is-active --quiet blackholebot; then
    send_alert "Bot service is down!"
fi

# 检查 Web 服务
if ! systemctl is-active --quiet blackholebot-web; then
    send_alert "Web service is down!"
fi

# 检查磁盘空间
DISK_USAGE=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ $DISK_USAGE -gt 80 ]; then
    send_alert "Disk usage is at ${DISK_USAGE}%"
fi

# 检查数据库连接
if ! PGPASSWORD='your_db_password' psql -U blackholebot -h localhost -c "SELECT 1" > /dev/null 2>&1; then
    send_alert "Database connection failed!"
fi
```

设置定时检查：
```bash
chmod +x /opt/BlackHoleBot/healthcheck.sh
crontab -e
```

添加：
```cron
# 每 5 分钟检查一次
*/5 * * * * /opt/BlackHoleBot/healthcheck.sh
```

### 2. 日志轮转

```bash
sudo nano /etc/logrotate.d/blackholebot
```

内容：
```
/opt/BlackHoleBot/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 blackholebot blackholebot
}
```

### 3. 性能监控命令

```bash
# 查看系统资源
htop

# 查看数据库连接
sudo -u postgres psql -c "SELECT count(*) FROM pg_stat_activity WHERE datname='blackholebot';"

# 查看 Redis 内存
redis-cli -a your_redis_password INFO memory

# 查看磁盘使用
df -h

# 查看网络连接
ss -tunlp | grep -E '(8000|5432|6379)'
```

---

## 故障排查

### Bot 无法启动

**检查日志**：
```bash
# Docker
docker compose logs bot

# Systemd
sudo journalctl -u blackholebot -n 100
```

**常见问题**：
1. Bot Token 错误 - 检查 `.env` 中的 `BOT_TOKEN`
2. 数据库连接失败 - 检查 PostgreSQL 是否运行
3. Redis 连接失败 - 检查 Redis 是否运行和密码

### Web API 无法访问

**检查端口**：
```bash
sudo netstat -tlnp | grep 8000
```

**检查防火墙**：
```bash
sudo ufw status
```

**检查 Nginx**：
```bash
sudo nginx -t
sudo systemctl status nginx
```

### 数据库连接失败

**检查 PostgreSQL 状态**：
```bash
sudo systemctl status postgresql
```

**测试连接**：
```bash
PGPASSWORD='your_password' psql -U blackholebot -h localhost -c "SELECT 1"
```

**查看连接数**：
```bash
sudo -u postgres psql -c "SELECT * FROM pg_stat_activity WHERE datname='blackholebot';"
```

### Redis 连接失败

**检查 Redis 状态**：
```bash
sudo systemctl status redis-server
```

**测试连接**：
```bash
redis-cli -a your_redis_password ping
```

### 搬运任务失败

**检查 Session 账号**：
```bash
# 通过 Web 后台查看 Session 列表
# 或查看数据库
sudo -u postgres psql blackholebot -c "SELECT id, phone_number, is_active FROM session_accounts;"
```

**查看任务日志**：
- 在 Bot 中发送 `/task_info {task_id}`

**常见原因**：
1. Session 账号失效 - 重新添加账号
2. API 限流 - 等待冷却或添加更多账号
3. 频道权限不足 - 确保账号已加入频道

### 内存不足

**查看内存使用**：
```bash
free -h
```

**优化建议**：
1. 增加 swap 空间
2. 限制 PostgreSQL 连接数
3. 调整 Redis 最大内存
4. 升级服务器配置

---

## 更新部署

### Docker 部署更新

```bash
cd /opt/BlackHoleBot

# 拉取最新代码
git pull

# 重新构建镜像
docker compose build

# 停止旧容器
docker compose down

# 运行数据库迁移
docker compose run --rm bot alembic upgrade head

# 启动新容器
docker compose up -d

# 查看日志确认
docker compose logs -f
```

### 手动部署更新

```bash
cd /opt/BlackHoleBot

# 激活虚拟环境
source venv/bin/activate

# 拉取最新代码
git pull

# 更新依赖
pip install -r requirements.txt

# 运行数据库迁移
alembic upgrade head

# 重启服务
sudo systemctl restart blackholebot blackholebot-web

# 查看日志
sudo journalctl -u blackholebot -f
```

---

## 安全加固

### 1. SSH 安全

```bash
sudo nano /etc/ssh/sshd_config
```

修改：
```
PermitRootLogin no
PasswordAuthentication no  # 使用密钥登录
Port 2222  # 更改默认端口
```

重启 SSH：
```bash
sudo systemctl restart sshd
```

### 2. 安装 Fail2ban

```bash
sudo apt install -y fail2ban

sudo nano /etc/fail2ban/jail.local
```

内容：
```ini
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[sshd]
enabled = true
```

启动：
```bash
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

### 3. 定期更新

```bash
# 创建更新脚本
sudo nano /opt/update-system.sh
```

内容：
```bash
#!/bin/bash
apt update
apt upgrade -y
apt autoremove -y
```

定时执行：
```bash
sudo chmod +x /opt/update-system.sh
sudo crontab -e
```

添加：
```cron
# 每周日凌晨 3 点更新系统
0 3 * * 0 /opt/update-system.sh >> /var/log/system-update.log 2>&1
```

---

## 总结

完成以上步骤后，你的 BlackHoleBot 应该已经成功部署并运行。

**关键检查点**：
- ✅ Bot 可以响应 `/start` 命令
- ✅ Web 后台可以访问（如果配置了）
- ✅ 数据库连接正常
- ✅ Redis 连接正常
- ✅ 日志正常输出
- ✅ 备份脚本正常运行

**下一步**：
1. 添加 Session 账号用于搬运功能
2. 配置私有频道（可选）
3. 设置监控告警
4. 定期检查日志和备份

如有问题，请查看日志文件或提交 Issue。
