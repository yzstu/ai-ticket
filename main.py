"""
FastAPI项目 - 主应用文件
整合所有API路由，创建FastAPI应用实例
"""
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.utils import get_openapi
import logging
import os

# 导入路由
from api.routes import stocks, analysis, cache, scheduler, system, backtest, sector, charts
from api.models import ErrorResponse

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="A股短线选股AI系统 API",
    description="""
    基于AI的A股短线选股分析系统API服务

    ## 功能特性

    - 📊 **股票数据获取** - 获取实时股票数据、资金流向、市场情绪
    - 🤖 **智能分析** - AI驱动的股票分析，支持并行处理
    - 💾 **数据缓存** - 高效的本地缓存系统，提升响应速度
    - ⏰ **定时任务** - 自动化的数据缓存和清理任务
    - 📈 **多种分析模式** - 支持Top-N、自定义列表、板块分析等

    ## 快速开始

    1. 获取股票列表：访问 `/stocks/list`
    2. 执行分析：访问 `/analysis/daily`
    3. 查看缓存状态：访问 `/cache/stats`
    4. 启动定时任务：访问 `/scheduler/start`

    ## API文档

    - **Swagger UI**: http://localhost:8000/docs
    - **ReDoc**: http://localhost:8000/redoc
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该设置为具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加GZip压缩中间件
app.add_middleware(GZipMiddleware, minimum_size=1000)

# 全局异常处理器
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTP异常处理器"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail.get("error") if isinstance(exc.detail, dict) else str(exc.detail),
            "detail": exc.detail.get("detail") if isinstance(exc.detail, dict) else None,
            "timestamp": exc.detail.get("timestamp") if isinstance(exc.detail, dict) else None
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """通用异常处理器"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc),
            "timestamp": exc.__class__.__name__
        }
    )


# 注册路由
app.include_router(stocks.router)
app.include_router(analysis.router)
app.include_router(cache.router)
app.include_router(scheduler.router)
app.include_router(system.router)
app.include_router(backtest.router)
app.include_router(sector.router)
app.include_router(charts.router)

# 挂载静态文件
app.mount("/static", StaticFiles(directory="static"), name="static")

# Web管理界面路由
@app.get("/web", tags=["web"])
async def web_interface():
    """Web管理界面"""
    return FileResponse("static/index.html")


# 首页路由 - 重定向到Web管理界面
@app.get("/", tags=["root"])
async def root():
    """根路径 - 重定向到Web管理界面"""
    return FileResponse("static/index.html")

# API信息路由
@app.get("/api/info", tags=["root"])
async def api_info():
    """API信息"""
    return {
        "message": "A股短线选股AI系统 API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/system/health",
        "web_interface": "/web"
    }


# 自定义OpenAPI文档
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="A股短线选股AI系统 API",
        version="1.0.0",
        description="基于AI的A股短线选股分析系统API服务",
        routes=app.routes,
    )

    # 添加自定义信息
    openapi_schema["info"]["x-logo"] = {
        "url": "https://fastapi.tiangolo.com/img/logo-margin/logo-teal.png"
    }

    # 添加服务器信息
    openapi_schema["servers"] = [
        {"url": "http://localhost:8000", "description": "开发环境"},
        {"url": "https://api.example.com", "description": "生产环境"}
    ]

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )