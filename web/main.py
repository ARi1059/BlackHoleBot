# web/main.py
"""
FastAPI Web 应用主程序
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import uvicorn
import redis.asyncio as redis
import logging

from config import settings

# 配置日志
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('web.log')
    ]
)

logger = logging.getLogger(__name__)

from web.api import auth, dashboard, collections, users, tasks, sessions, settings as settings_api, analytics
from web.websocket import websocket_endpoint
from utils.transfer_executor import transfer_executor

# 创建 FastAPI 应用
app = FastAPI(
    title="BlackHoleBot API",
    description="BlackHoleBot 管理后台 API",
    version="1.0.0"
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    """捕获422验证错误并记录脱敏信息"""
    # 只记录字段位置和错误类型，不记录用户输入值
    safe_errors = [
        {"type": e.get("type"), "loc": e.get("loc"), "msg": e.get("msg")}
        for e in exc.errors()
    ]
    logger.error(f"422 验证错误 - {request.method} {request.url.path} - {safe_errors}")

    return JSONResponse(
        status_code=422,
        content={"detail": safe_errors}
    )


@app.on_event("startup")
async def startup_event():
    """应用启动时初始化"""
    # 创建 Redis 客户端
    redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

    # 设置 Redis 客户端到 transfer_executor
    transfer_executor.set_redis_client(redis_client)

    print("Web 服务已启动，Redis 客户端已初始化")


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时清理"""
    if transfer_executor.redis_client:
        await transfer_executor.redis_client.aclose()
    print("Web 服务已关闭")

# 挂载静态文件
app.mount("/static", StaticFiles(directory="web/static"), name="static")

# CORS 配置
# 根据环境变量配置允许的域名，默认只允许本地访问
allowed_origins = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

# 如果配置了 WEB_DOMAIN 环境变量，添加到允许列表
if hasattr(settings, 'WEB_DOMAIN') and settings.WEB_DOMAIN:
    allowed_origins.append(settings.WEB_DOMAIN)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router, prefix="/api/auth", tags=["认证"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["仪表盘"])
app.include_router(collections.router, prefix="/api/collections", tags=["合集管理"])
app.include_router(users.router, prefix="/api/users", tags=["用户管理"])
app.include_router(tasks.router, prefix="/api/tasks", tags=["搬运任务"])
app.include_router(sessions.router, prefix="/api/sessions", tags=["Session管理"])
app.include_router(settings_api.router, prefix="/api/settings", tags=["系统设置"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["数据分析"])

# WebSocket
app.add_websocket_route("/ws", websocket_endpoint)


@app.get("/")
async def root():
    """根路径 - 重定向到登录页面"""
    return RedirectResponse(url="/login")


@app.get("/login")
async def login_page():
    """登录页面"""
    return FileResponse("web/templates/login.html")


@app.get("/dashboard")
async def dashboard_page():
    """仪表盘页面"""
    return FileResponse("web/templates/dashboard.html")


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run(
        "web.main:app",
        host=settings.WEB_HOST,
        port=settings.WEB_PORT,
        reload=False,
        reload_excludes=["*.log", "*.db", "*.sqlite", "__pycache__", ".git"]
    )
