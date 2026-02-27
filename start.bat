@echo off
REM BlackHoleBot 快速启动脚本 (Windows)

echo ================================
echo BlackHoleBot 快速启动
echo ================================
echo.

REM 检查 Docker
docker --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 错误: 未安装 Docker
    echo 请先安装 Docker Desktop: https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)

echo ✅ Docker 已安装
echo.

REM 检查 .env 文件
if not exist .env (
    echo ⚠️  未找到 .env 文件
    echo 正在从 .env.example 创建...
    copy .env.example .env
    echo.
    echo ⚠️  请编辑 .env 文件并填写必要配置：
    echo    - BOT_TOKEN
    echo    - BOT_USERNAME
    echo    - SESSION_ENCRYPTION_KEY
    echo    - SECRET_KEY
    echo.
    echo 生成密钥命令：
    echo   SESSION_ENCRYPTION_KEY: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    echo   SECRET_KEY: python -c "import secrets; print(secrets.token_urlsafe(32))"
    echo.
    pause
)

echo ✅ 配置文件已就绪
echo.

REM 构建镜像
echo 📦 构建 Docker 镜像...
docker compose build

echo.
echo 🚀 启动服务...
docker compose up -d

echo.
echo ⏳ 等待服务启动...
timeout /t 5 /nobreak >nul

REM 检查服务状态
echo.
echo 📊 服务状态：
docker compose ps

echo.
echo 🔧 初始化数据库...
docker compose exec -T bot alembic upgrade head

echo.
echo ================================
echo ✅ 启动完成！
echo ================================
echo.
echo 下一步操作：
echo 1. 创建管理员账号：
echo    docker compose exec bot python scripts/create_admin.py
echo.
echo 2. 添加 Session 账号（用于搬运功能）：
echo    docker compose exec bot python scripts/add_session.py
echo.
echo 3. 查看日志：
echo    docker compose logs -f bot
echo    docker compose logs -f web
echo.
echo 4. 在 Telegram 中测试 Bot：
echo    发送 /start 命令
echo.
echo 管理命令：
echo   停止服务: docker compose down
echo   重启服务: docker compose restart
echo   查看状态: docker compose ps
echo.
pause
