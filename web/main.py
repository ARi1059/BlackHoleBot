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
from fastapi.responses import FileResponse
import uvicorn

from config import settings
from web.api import auth, dashboard, collections, users, tasks, sessions, settings as settings_api
from web.websocket import websocket_endpoint

# 创建 FastAPI 应用
app = FastAPI(
    title="BlackHoleBot API",
    description="BlackHoleBot 管理后台 API",
    version="1.0.0"
)

# 挂载静态文件
app.mount("/static", StaticFiles(directory="web/static"), name="static")

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制具体域名
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

# WebSocket
app.add_websocket_route("/ws", websocket_endpoint)


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "BlackHoleBot API",
        "version": "1.0.0",
        "docs": "/docs"
    }


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
        reload=True
    )
