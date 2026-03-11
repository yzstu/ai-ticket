"""
FastAPI项目 - 依赖注入
管理所有核心组件的依赖注入
"""
from typing import Generator, Optional, Any
from fastapi import Depends, HTTPException, status
from src.data.fetcher import DataFetcher
from src.data.cached_fetcher import CachedDataFetcher, create_cached_fetcher
from src.data.cache_manager import StockCacheManager, CacheConfig
from src.data.cache_scheduler import CacheTaskScheduler, CacheTaskConfig
from src.data.stock_selector import StockSelector
from src.providers.local_analyzer import create_local_analyzer
import logging

# 回测相关依赖导入
try:
    from src.data.backtest_database import BacktestDatabase as BTDatabase
    from src.data.price_history import PriceHistoryProvider as PHProvider
    BACKTEST_MODULES_AVAILABLE = True
except ImportError:
    BACKTEST_MODULES_AVAILABLE = False
    logger.warning("回测模块未找到，某些功能将不可用")

logger = logging.getLogger(__name__)


# 数据获取器依赖
def get_data_fetcher() -> Generator[DataFetcher, None, None]:
    """获取传统数据获取器"""
    fetcher = DataFetcher()
    try:
        yield fetcher
    finally:
        pass


# 缓存数据获取器依赖
def get_cached_fetcher(
    use_cache: bool = True,
    cache_dir: str = "./cache",
    auto_cache: bool = True,
    cache_ttl_hours: int = 24,
    fallback_to_api: bool = True
) -> Generator[CachedDataFetcher, None, None]:
    """获取缓存数据获取器"""
    fetcher = create_cached_fetcher(
        use_cache=use_cache,
        cache_dir=cache_dir,
        auto_cache=auto_cache,
        cache_ttl_hours=cache_ttl_hours,
        fallback_to_api=fallback_to_api
    )
    try:
        yield fetcher
    finally:
        pass


# 缓存管理器依赖
def get_cache_manager(
    cache_dir: str = "./cache",
    max_cache_days: int = 30,
    auto_cleanup: bool = True,
    compress_data: bool = False
) -> Generator[StockCacheManager, None, None]:
    """获取缓存管理器"""
    config = CacheConfig(
        cache_dir=cache_dir,
        max_cache_days=max_cache_days,
        auto_cleanup=auto_cleanup,
        compress_data=compress_data
    )
    manager = StockCacheManager(config)
    try:
        yield manager
    finally:
        pass


# 调度器依赖（单例模式）
_scheduler_instance: Optional[CacheTaskScheduler] = None


def get_scheduler(
    cache_dir: str = "./cache",
    cache_time: str = "16:30",
    cleanup_time: str = "02:00",
    batch_size: int = 100,
    max_workers: int = 4
) -> Generator[CacheTaskScheduler, None, None]:
    """获取调度器（单例模式）"""
    global _scheduler_instance

    if _scheduler_instance is None:
        config = CacheTaskConfig(
            cache_dir=cache_dir,
            cache_time=cache_time,
            cleanup_time=cleanup_time,
            batch_size=batch_size,
            max_workers=max_workers
        )
        _scheduler_instance = CacheTaskScheduler(config)
        logger.info("调度器实例已创建")

    try:
        yield _scheduler_instance
    finally:
        # 不在这里关闭调度器，保持其运行
        pass


# 本地分析器依赖
def get_local_analyzer() -> Generator:
    """获取本地分析器"""
    analyzer = create_local_analyzer()
    try:
        yield analyzer
    finally:
        pass


# 股票选择器依赖
def get_stock_selector(
    mode: str = "top_n",
    max_results: int = 10,
    custom_stocks: Optional[list] = None,
    code_range: Optional[tuple] = None
) -> StockSelector:
    """获取股票选择器"""
    params = {}

    if custom_stocks:
        params['custom_stocks'] = custom_stocks

    if code_range:
        params['code_range'] = code_range

    if mode == "top_n":
        params['max_results'] = max_results

    selector = StockSelector(selection_mode=mode, **params)
    return selector


# 应用配置依赖
class AppConfig:
    """应用配置"""
    def __init__(
        self,
        use_cache: bool = True,
        cache_dir: str = "./cache",
        auto_cache: bool = True,
        use_parallel: bool = True,
        default_max_workers: int = 0,
        default_batch_size: int = 100
    ):
        self.use_cache = use_cache
        self.cache_dir = cache_dir
        self.auto_cache = auto_cache
        self.use_parallel = use_parallel
        self.default_max_workers = default_max_workers
        self.default_batch_size = default_batch_size


def get_app_config() -> AppConfig:
    """获取应用配置"""
    return AppConfig()


# 异常处理
class APIException(HTTPException):
    """API自定义异常"""
    def __init__(self, status_code: int, error: str, detail: Optional[str] = None):
        super().__init__(
            status_code=status_code,
            detail=detail or error,
        )
        self.error = error


def raise_api_exception(status_code: int, error: str, detail: Optional[str] = None):
    """抛出API异常"""
    raise APIException(status_code=status_code, error=error, detail=detail)


# 验证器
def validate_stock_code(stock_code: str) -> str:
    """验证股票代码格式"""
    if not stock_code or len(stock_code) != 6:
        raise_api_exception(
            status_code=400,
            error="Invalid stock code",
            detail="Stock code must be 6 digits"
        )
    return stock_code


def validate_selection_mode(mode: str) -> str:
    """验证选择模式"""
    valid_modes = ["top_n", "custom", "range", "all", "blue_chips", "growth_stocks", "kechuang"]
    if mode not in valid_modes:
        raise_api_exception(
            status_code=400,
            error="Invalid selection mode",
            detail=f"Mode must be one of: {', '.join(valid_modes)}"
        )
    return mode


def validate_cache_config(cache_dir: str, max_cache_days: int) -> tuple:
    """验证缓存配置"""
    import os

    if not os.path.exists(cache_dir):
        try:
            os.makedirs(cache_dir, exist_ok=True)
        except Exception as e:
            raise_api_exception(
                status_code=500,
                error="Cache directory creation failed",
                detail=str(e)
            )

    if max_cache_days < 1:
        raise_api_exception(
            status_code=400,
            error="Invalid cache days",
            detail="max_cache_days must be greater than 0"
        )

    return cache_dir, max_cache_days


# 工具函数
def format_error_response(error: str, detail: Optional[str] = None) -> dict:
    """格式化错误响应"""
    from datetime import datetime
    return {
        "error": error,
        "detail": detail,
        "timestamp": datetime.now().isoformat()
    }


def format_success_response(data: Any) -> dict:
    """格式化成功响应"""
    return {
        "success": True,
        "data": data
    }


# 异步依赖（如果需要）
async def get_async_data():
    """异步数据依赖示例"""
    # 这里可以放置异步获取数据的逻辑
    await asyncio.sleep(0.1)
    return {"async": True}


# =================== 回测相关依赖 ===================

def get_backtest_db_dependency() -> BTDatabase:
    """获取回测数据库实例"""
    if not BACKTEST_MODULES_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="回测功能不可用，模块未正确安装"
        )
    from src.data.backtest_database import get_backtest_db
    return get_backtest_db()


def get_price_provider_dependency() -> PHProvider:
    """获取价格数据提供商实例"""
    if not BACKTEST_MODULES_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="回测功能不可用，模块未正确安装"
        )
    from src.data.price_history import get_price_provider
    return get_price_provider()