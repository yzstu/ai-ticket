"""
FastAPI项目 - 系统管理API路由
处理系统状态、健康检查等API端点
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any
import logging
import os
from datetime import datetime

from api.models import (
    HealthCheck,
    SystemInfo,
    ErrorResponse
)
from api.deps import (
    get_app_config,
    get_cached_fetcher,
    get_scheduler,
    format_error_response,
    format_success_response
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/system", tags=["system"])


@router.get(
    "/health",
    response_model=HealthCheck,
    summary="系统健康检查"
)
async def health_check():
    """
    系统健康检查端点

    检查各个服务组件的运行状态
    """
    try:
        services = {
            "cache_system": "unknown",
            "scheduler": "unknown",
            "database": "unknown"
        }

        # 检查缓存系统
        try:
            from api.deps import get_cached_fetcher
            # 获取生成器并获取实际的fetcher对象
            fetcher_generator = get_cached_fetcher(use_cache=True)
            fetcher = next(fetcher_generator)  # 从生成器中获取第一个对象
            cache_stats = fetcher.get_cache_stats()
            if cache_stats.get('total_requests', 0) >= 0:
                services["cache_system"] = "healthy"
        except Exception as e:
            logger.warning(f"Cache system health check failed: {e}")
            services["cache_system"] = "unhealthy"

        # 检查调度器
        try:
            from api.deps import get_scheduler
            scheduler_generator = get_scheduler()
            scheduler = next(scheduler_generator)  # 从生成器获取实际对象

            # 检查调度器的状态
            scheduler_status = "unknown"  # 默认状态

            # 检查是否有scheduler属性（APScheduler）
            if hasattr(scheduler, 'scheduler'):
                if scheduler.scheduler is not None:
                    # APScheduler可用
                    try:
                        scheduler_status = "running" if scheduler.scheduler.running else "stopped"
                    except Exception:
                        scheduler_status = "unknown"
                else:
                    # APScheduler不可用，使用简单定时器
                    scheduler_status = "available"  # 简单定时器总是"可用"状态
            # 检查是否有其他状态指示器
            elif hasattr(scheduler, 'is_running'):
                try:
                    scheduler_status = "running" if scheduler.is_running else "stopped"
                except Exception:
                    scheduler_status = "unknown"

            # 如果调度器对象存在但无法确定状态，标记为unknown
            else:
                scheduler_status = "unknown"

            services["scheduler"] = scheduler_status

        except Exception as e:
            logger.warning(f"Scheduler health check failed: {e}")
            services["scheduler"] = "unavailable"

        # 检查数据库
        try:
            cache_dir = "./cache"
            if os.path.exists(cache_dir):
                db_path = os.path.join(cache_dir, "stock_cache.db")
                if os.path.exists(db_path):
                    services["database"] = "available"
                else:
                    services["database"] = "not_found"
            else:
                services["database"] = "not_initialized"
        except Exception as e:
            logger.warning(f"Database health check failed: {e}")
            services["database"] = "unhealthy"

        # 整体健康状态
        unhealthy_services = [k for k, v in services.items() if v == "unhealthy"]
        overall_status = "healthy" if not unhealthy_services else "degraded"

        return HealthCheck(
            status=overall_status,
            timestamp=datetime.now(),
            version="1.0.0",
            services=services
        )

    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=503,
            detail=format_error_response(
                error="Health check failed",
                detail=str(e)
            )
        )


@router.get(
    "/info",
    response_model=SystemInfo,
    summary="获取系统信息"
)
async def get_system_info(
    fetcher_cached=Depends(get_cached_fetcher),
    scheduler=Depends(get_scheduler)
):
    """
    获取系统的详细配置信息
    """
    try:
        config = get_app_config()

        # 检查调度器是否运行
        scheduler_running = False
        if hasattr(scheduler, 'scheduler') and scheduler.scheduler:
            scheduler_running = scheduler.scheduler.running

        return SystemInfo(
            cache_enabled=config.use_cache,
            cache_dir=config.cache_dir,
            parallel_enabled=config.use_parallel,
            scheduler_running=scheduler_running
        )

    except Exception as e:
        logger.error(f"Failed to get system info: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=format_error_response(
                error="Failed to get system info",
                detail=str(e)
            )
        )


@router.get(
    "/version",
    summary="获取系统版本信息"
)
async def get_version():
    """
    获取系统版本信息
    """
    return format_success_response({
        "version": "1.0.0",
        "build_time": datetime.now().isoformat(),
        "environment": "production" if os.getenv("ENV") == "production" else "development"
    })


@router.get(
    "/metrics",
    summary="获取系统性能指标"
)
async def get_system_metrics(
    fetcher_cached=Depends(get_cached_fetcher),
    scheduler=Depends(get_scheduler)
):
    """
    获取系统的性能指标和统计数据
    """
    try:
        metrics = {
            "cache_metrics": {},
            "scheduler_metrics": {},
            "system_metrics": {}
        }

        # 缓存指标
        try:
            cache_stats = fetcher_cached.get_cache_stats()
            metrics["cache_metrics"] = {
                "total_requests": cache_stats.get('total_requests', 0),
                "cache_hits": cache_stats.get('cache_hits', 0),
                "cache_misses": cache_stats.get('cache_misses', 0),
                "cache_hit_rate": round(cache_stats.get('cache_hit_rate', 0.0), 2),
                "api_requests": cache_stats.get('api_requests', 0),
                "cache_writes": cache_stats.get('cache_writes', 0)
            }

            cm_stats = cache_stats.get('cache_manager_stats', {})
            metrics["cache_metrics"].update({
                "daily_data_count": cm_stats.get('daily_data_count', 0),
                "capital_flow_count": cm_stats.get('capital_flow_count', 0),
                "sentiment_count": cm_stats.get('sentiment_count', 0),
                "db_size_mb": round(cm_stats.get('db_size_mb', 0.0), 2)
            })
        except Exception as e:
            logger.warning(f"Failed to get cache metrics: {e}")

        # 调度器指标
        try:
            scheduler_stats = scheduler.get_stats()
            metrics["scheduler_metrics"] = {
                "total_cache_tasks": scheduler_stats.get('total_cache_tasks', 0),
                "successful_cache_tasks": scheduler_stats.get('successful_cache_tasks', 0),
                "failed_cache_tasks": scheduler_stats.get('failed_cache_tasks', 0),
                "total_cache_records": scheduler_stats.get('total_cache_records', 0),
                "runtime_hours": round(scheduler_stats.get('runtime_hours', 0.0), 2)
            }
        except Exception as e:
            logger.warning(f"Failed to get scheduler metrics: {e}")

        # 系统指标
        try:
            import psutil
            metrics["system_metrics"] = {
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_usage_percent": psutil.disk_usage('/').percent,
                "process_count": len(psutil.pids())
            }
        except ImportError:
            logger.warning("psutil not available, system metrics limited")
        except Exception as e:
            logger.warning(f"Failed to get system metrics: {e}")

        return format_success_response(metrics)

    except Exception as e:
        logger.error(f"Failed to get system metrics: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=format_error_response(
                error="Failed to get system metrics",
                detail=str(e)
            )
        )


@router.get(
    "/logs",
    summary="获取最近的系统日志"
)
async def get_system_logs(
    lines: int = 100
):
    """
    获取系统最近的日志记录

    ⚠️ 注意：这只是一个简单的实现，生产环境中应该使用专业的日志系统

    - **lines**: 获取最近多少行日志
    """
    try:
        # 这里可以扩展为从实际日志文件读取
        # 现在返回模拟数据
        log_entries = []
        for i in range(min(lines, 10)):  # 限制最多10条日志
            log_entries.append({
                "timestamp": datetime.now().isoformat(),
                "level": "INFO",
                "message": f"Sample log entry {i+1}",
                "source": "api.system"
            })

        return format_success_response({
            "logs": log_entries,
            "total": len(log_entries)
        })

    except Exception as e:
        logger.error(f"Failed to get system logs: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=format_error_response(
                error="Failed to get system logs",
                detail=str(e)
            )
        )


@router.get(
    "/config",
    summary="获取系统配置"
)
async def get_full_config():
    """
    获取系统的完整配置信息
    """
    try:
        config = get_app_config()
        import os

        full_config = {
            "cache_config": {
                "use_cache": config.use_cache,
                "cache_dir": config.cache_dir,
                "auto_cache": config.auto_cache
            },
            "analysis_config": {
                "use_parallel": config.use_parallel,
                "default_max_workers": config.default_max_workers,
                "default_batch_size": config.default_batch_size
            },
            "environment": {
                "env": os.getenv("ENV", "development"),
                "python_version": os.sys.version,
                "platform": os.name
            }
        }

        return format_success_response(full_config)

    except Exception as e:
        logger.error(f"Failed to get system config: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=format_error_response(
                error="Failed to get system config",
                detail=str(e)
            )
        )


@router.post(
    "/restart",
    summary="重启系统服务"
)
async def restart_system():
    """
    重启系统服务

    ⚠️ 注意：这是一个危险操作，仅用于开发/测试环境

    在生产环境中，应该使用专门的部署和运维工具来处理服务重启
    """
    # 这里可以实现优雅关闭当前服务
    # 在FastAPI中，通常通过发送信号给主进程来实现

    return format_success_response({
        "message": "Restart command received. Note: Actual restart requires external process management.",
        "timestamp": datetime.now().isoformat()
    })