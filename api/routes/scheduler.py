"""
FastAPI项目 - 定时任务管理API路由
处理定时任务调度相关的API端点
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
import logging

from api.models import (
    StartSchedulerRequest,
    SchedulerStats,
    ManualCacheRequest,
    ManualCacheResponse,
    ErrorResponse
)
from api.deps import (
    get_scheduler,
    format_error_response,
    format_success_response
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/scheduler", tags=["scheduler"])


@router.post(
    "/start",
    summary="启动定时缓存任务"
)
async def start_scheduler(
    request: StartSchedulerRequest,
    scheduler=Depends(get_scheduler)
):
    """
    启动定时缓存任务调度器

    ⚠️ 注意：这将在后台持续运行，直到服务器停止

    - **cache_time**: 每日缓存时间（HH:MM格式）
    - **cleanup_time**: 每日清理时间（HH:MM格式）
    - **batch_size**: 批处理大小
    - **max_workers**: 最大工作线程数
    """
    try:
        # 检查调度器是否已经运行
        if hasattr(scheduler, 'scheduler') and scheduler.scheduler and scheduler.scheduler.running:
            return format_success_response({
                "message": "Scheduler is already running",
                "scheduler_id": "default"
            })

        # 启动调度器
        scheduler.start()

        return format_success_response({
            "message": "Scheduler started successfully",
            "scheduler_id": "default",
            "config": request.config.dict()
        })

    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=format_error_response(
                error="Failed to start scheduler",
                detail=str(e)
            )
        )


@router.post(
    "/stop",
    summary="停止定时缓存任务"
)
async def stop_scheduler(
    scheduler=Depends(get_scheduler)
):
    """
    停止定时缓存任务调度器
    """
    try:
        scheduler.stop()

        return format_success_response({
            "message": "Scheduler stopped successfully"
        })

    except Exception as e:
        logger.error(f"Failed to stop scheduler: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=format_error_response(
                error="Failed to stop scheduler",
                detail=str(e)
            )
        )


@router.get(
    "/status",
    summary="获取调度器状态"
)
async def get_scheduler_status(
    scheduler=Depends(get_scheduler)
):
    """
    获取定时任务调度器的当前状态
    """
    try:
        # 检查调度器是否运行
        is_running = False
        task_count = 0
        next_run = None

        if hasattr(scheduler, 'scheduler') and scheduler.scheduler:
            if scheduler.scheduler.running:
                is_running = True
                jobs = scheduler.scheduler.get_jobs()
                task_count = len(jobs)
                # 获取最近的下次执行时间
                if jobs:
                    next_run = min(job.next_run_time for job in jobs if job.next_run_time)
                    next_run = next_run.isoformat() if next_run else None

        return format_success_response({
            "is_running": is_running,
            "task_count": task_count,
            "next_run": next_run,
            "has_jobs": task_count > 0
        })

    except Exception as e:
        logger.error(f"Failed to get scheduler status: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=format_error_response(
                error="Failed to get scheduler status",
                detail=str(e)
            )
        )


@router.get(
    "/stats",
    response_model=SchedulerStats,
    summary="获取调度器统计信息"
)
async def get_scheduler_stats(
    scheduler=Depends(get_scheduler)
):
    """
    获取定时任务调度器的详细统计信息
    """
    try:
        stats = scheduler.get_stats()

        return SchedulerStats(
            total_cache_tasks=stats.get('total_cache_tasks', 0),
            successful_cache_tasks=stats.get('successful_cache_tasks', 0),
            failed_cache_tasks=stats.get('failed_cache_tasks', 0),
            total_cache_records=stats.get('total_cache_records', 0),
            start_time=stats.get('start_time'),
            last_cache_time=stats.get('last_cache_time'),
            runtime_hours=stats.get('runtime_hours')
        )

    except Exception as e:
        logger.error(f"Failed to get scheduler stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=format_error_response(
                error="Failed to get scheduler stats",
                detail=str(e)
            )
        )


@router.post(
    "/manual-cache",
    response_model=ManualCacheResponse,
    summary="手动执行缓存任务"
)
async def manual_cache(
    request: ManualCacheRequest,
    scheduler=Depends(get_scheduler)
):
    """
    手动执行一次缓存任务

    - **stock_codes**: 指定股票代码列表（为空则缓存所有股票）
    - **batch_size**: 批处理大小
    - **max_workers**: 最大工作线程数
    """
    try:
        # 验证股票代码列表
        if request.stock_codes:
            from api.deps import validate_stock_code
            for code in request.stock_codes:
                validate_stock_code(code)

        # 执行手动缓存
        stats = scheduler.run_cache_manually(
            stock_codes=request.stock_codes
        )

        return ManualCacheResponse(
            total_stocks=stats['total_stocks'],
            cached_stocks=stats['cached_stocks'],
            failed_stocks=stats['failed_stocks'],
            start_time=stats['start_time']
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Manual cache failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=format_error_response(
                error="Manual cache failed",
                detail=str(e)
            )
        )


@router.get(
    "/jobs",
    summary="获取调度任务列表"
)
async def get_scheduler_jobs(
    scheduler=Depends(get_scheduler)
):
    """
    获取定时任务调度器中所有的调度任务
    """
    try:
        if not (hasattr(scheduler, 'scheduler') and scheduler.scheduler and scheduler.scheduler.running):
            return format_success_response({
                "jobs": [],
                "message": "Scheduler is not running"
            })

        jobs = scheduler.scheduler.get_jobs()

        job_list = []
        for job in jobs:
            job_list.append({
                "id": job.id,
                "name": job.name,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger)
            })

        return format_success_response({
            "jobs": job_list,
            "total_jobs": len(job_list)
        })

    except Exception as e:
        logger.error(f"Failed to get scheduler jobs: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=format_error_response(
                error="Failed to get scheduler jobs",
                detail=str(e)
            )
        )


@router.delete(
    "/jobs/{job_id}",
    summary="删除指定调度任务"
)
async def delete_scheduler_job(
    job_id: str,
    scheduler=Depends(get_scheduler)
):
    """
    删除指定ID的调度任务

    - **job_id**: 任务ID
    """
    try:
        if not (hasattr(scheduler, 'scheduler') and scheduler.scheduler and scheduler.scheduler.running):
            raise HTTPException(
                status_code=400,
                detail=format_error_response(
                    error="Scheduler not running",
                    detail="Scheduler is not currently running"
                )
            )

        # 尝试删除任务
        try:
            scheduler.scheduler.remove_job(job_id)
            return format_success_response({
                "message": f"Job {job_id} deleted successfully"
            })
        except Exception:
            raise HTTPException(
                status_code=404,
                detail=format_error_response(
                    error="Job not found",
                    detail=f"Job with id {job_id} not found"
                )
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete scheduler job: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=format_error_response(
                error="Failed to delete scheduler job",
                detail=str(e)
            )
        )


@router.get(
    "/logs",
    summary="获取调度器日志"
)
async def get_scheduler_logs(
    lines: int = Query(default=100, description="获取最近多少条日志"),
    scheduler=Depends(get_scheduler)
):
    """
    获取调度器最近的日志记录
    """
    try:
        logs = scheduler.get_recent_logs(lines)

        return format_success_response({
            "logs": logs,
            "total": len(logs),
            "requested_lines": lines
        })

    except Exception as e:
        logger.error(f"Failed to get scheduler logs: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=format_error_response(
                error="Failed to get scheduler logs",
                detail=str(e)
            )
        )


@router.get(
    "/config",
    summary="获取调度器配置"
)
async def get_scheduler_config(
    scheduler=Depends(get_scheduler)
):
    """
    获取定时任务调度器的当前配置
    """
    try:
        return format_success_response({
            "cache_time": scheduler.config.cache_time,
            "cleanup_time": scheduler.config.cleanup_time,
            "batch_size": scheduler.config.batch_size,
            "max_workers": scheduler.config.max_workers,
            "max_cache_days": scheduler.config.max_cache_days,
            "auto_cleanup": scheduler.config.auto_cleanup
        })

    except Exception as e:
        logger.error(f"Failed to get scheduler config: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=format_error_response(
                error="Failed to get scheduler config",
                detail=str(e)
            )
        )