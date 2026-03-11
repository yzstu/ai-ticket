"""
FastAPI项目 - 缓存管理API路由
处理缓存管理相关的API端点
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
import os
import logging

from api.models import (
    CacheStatsResponse,
    CacheCleanupRequest,
    CacheCleanupResponse,
    CacheExportRequest,
    CacheExportResponse,
    ErrorResponse
)
from api.deps import (
    get_cache_manager,
    get_cached_fetcher,
    validate_cache_config,
    format_error_response,
    format_success_response
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/cache", tags=["cache"])


@router.get(
    "/stats",
    response_model=CacheStatsResponse,
    summary="获取缓存统计信息"
)
async def get_cache_stats(
    cache_dir: str = Query("./cache", description="缓存目录"),
    fetcher_cached=Depends(get_cached_fetcher)
):
    """
    获取缓存系统的详细统计信息

    - **cache_dir**: 缓存目录路径
    """
    try:
        # 验证缓存配置
        cache_dir, _ = validate_cache_config(cache_dir, 30)

        # 获取缓存统计
        cache_stats = fetcher_cached.get_cache_stats()

        # 解析嵌套的统计信息
        cm_stats = cache_stats.get('cache_manager_stats', {})
        hit_counts = cm_stats.get('hit_counts', {})

        return CacheStatsResponse(
            total_requests=cache_stats.get('total_requests', 0),
            cache_hits=cache_stats.get('cache_hits', 0),
            cache_misses=cache_stats.get('cache_misses', 0),
            cache_hit_rate=cache_stats.get('cache_hit_rate', 0.0),
            api_requests=cache_stats.get('api_requests', 0),
            cache_writes=cache_stats.get('cache_writes', 0),
            daily_data_count=cm_stats.get('daily_data_count', 0),
            capital_flow_count=cm_stats.get('capital_flow_count', 0),
            sentiment_count=cm_stats.get('sentiment_count', 0),
            db_size_mb=cm_stats.get('db_size_mb', 0.0)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get cache stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=format_error_response(
                error="Failed to get cache stats",
                detail=str(e)
            )
        )


@router.post(
    "/cleanup",
    response_model=CacheCleanupResponse,
    summary="清理过期缓存数据"
)
async def cleanup_cache(
    request: CacheCleanupRequest,
    cache_dir: str = Query("./cache", description="缓存目录"),
    max_cache_days: int = Query(30, ge=1, le=365, description="缓存保留天数"),
    fetcher_cached=Depends(get_cached_fetcher)
):
    """
    清理过期的缓存数据

    - **dry_run**: 是否仅预览不执行，默认为False
    - **cache_dir**: 缓存目录路径
    - **max_cache_days**: 缓存保留天数
    """
    try:
        # 验证缓存配置
        cache_dir, max_cache_days = validate_cache_config(cache_dir, max_cache_days)

        if request.dry_run:
            # 仅预览，返回模拟结果
            return CacheCleanupResponse(
                deleted_count=0,
                message="Dry run mode - no actual cleanup performed"
            )

        # 执行清理
        deleted_count = fetcher_cached.cleanup_expired_cache()

        return CacheCleanupResponse(
            deleted_count=deleted_count,
            message=f"Successfully cleaned up {deleted_count} expired cache records"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Cache cleanup failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=format_error_response(
                error="Cache cleanup failed",
                detail=str(e)
            )
        )


@router.post(
    "/export",
    response_model=CacheExportResponse,
    summary="导出缓存数据"
)
async def export_cache(
    request: CacheExportRequest,
    cache_dir: str = Query("./cache", description="缓存目录"),
    fetcher_cached=Depends(get_cached_fetcher)
):
    """
    导出缓存数据到JSON文件

    - **output_path**: 输出文件路径
    - **days**: 导出最近几天的数据
    """
    try:
        # 验证输出路径
        output_dir = os.path.dirname(request.output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        # 执行导出
        success = fetcher_cached.export_cache(
            output_path=request.output_path,
            days=request.days
        )

        if success:
            return CacheExportResponse(
                success=True,
                output_path=request.output_path,
                message=f"Cache data successfully exported to {request.output_path}"
            )
        else:
            raise HTTPException(
                status_code=500,
                detail=format_error_response(
                    error="Export failed",
                    detail="Failed to export cache data"
                )
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Cache export failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=format_error_response(
                error="Cache export failed",
                detail=str(e)
            )
        )


@router.delete(
    "/clear",
    summary="清空所有缓存数据"
)
async def clear_all_cache(
    confirm: bool = Query(False, description="确认清空所有缓存"),
    cache_dir: str = Query("./cache", description="缓存目录"),
    fetcher_cached=Depends(get_cached_fetcher)
):
    """
    清空所有缓存数据

    ⚠️ 注意：这是一个危险操作，会删除所有缓存数据！

    - **confirm**: 必须设置为True才能执行
    - **cache_dir**: 缓存目录路径
    """
    if not confirm:
        raise HTTPException(
            status_code=400,
            detail=format_error_response(
                error="Confirmation required",
                detail="Set confirm=true to proceed with clearing all cache data"
            )
        )

    try:
        success = fetcher_cached.clear_cache()

        if success:
            return format_success_response({
                "message": "All cache data has been cleared successfully"
            })
        else:
            raise HTTPException(
                status_code=500,
                detail=format_error_response(
                    error="Clear cache failed",
                    detail="Failed to clear cache data"
                )
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Clear cache failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=format_error_response(
                error="Clear cache failed",
                detail=str(e)
            )
        )


@router.get(
    "/info",
    summary="获取缓存配置信息"
)
async def get_cache_info(
    cache_dir: str = Query("./cache", description="缓存目录"),
    fetcher_cached=Depends(get_cached_fetcher)
):
    """
    获取缓存系统的配置信息

    - **cache_dir**: 缓存目录路径
    """
    try:
        from api.deps import get_app_config
        config = get_app_config()

        return format_success_response({
            "cache_enabled": config.use_cache,
            "cache_dir": cache_dir,
            "auto_cache": fetcher_cached.auto_cache,
            "cache_ttl_hours": fetcher_cached.cache_ttl_hours,
            "fallback_to_api": fetcher_cached.fallback_to_api
        })

    except Exception as e:
        logger.error(f"Failed to get cache info: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=format_error_response(
                error="Failed to get cache info",
                detail=str(e)
            )
        )


@router.get(
    "/health",
    summary="检查缓存系统健康状态"
)
async def cache_health_check(
    cache_dir: str = Query("./cache", description="缓存目录"),
    fetcher_cached=Depends(get_cached_fetcher)
):
    """
    检查缓存系统是否正常工作

    - **cache_dir**: 缓存目录路径
    """
    try:
        # 验证缓存目录
        cache_dir, _ = validate_cache_config(cache_dir, 30)

        # 检查数据库文件
        db_path = os.path.join(cache_dir, "stock_cache.db")
        db_exists = os.path.exists(db_path)

        # 获取统计信息
        stats = fetcher_cached.get_cache_stats()

        health_status = {
            "status": "healthy" if db_exists else "not_initialized",
            "cache_dir": cache_dir,
            "database_exists": db_exists,
            "total_requests": stats.get('total_requests', 0),
            "cache_hit_rate": stats.get('cache_hit_rate', 0.0),
            "last_check": "healthy" in ["healthy", "not_initialized"]
        }

        if health_status["last_check"]:
            return format_success_response(health_status)
        else:
            raise HTTPException(
                status_code=503,
                detail=format_error_response(
                    error="Cache health check failed",
                    detail="Cache system is not working properly"
                )
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Cache health check failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=format_error_response(
                error="Cache health check failed",
                detail=str(e)
            )
        )