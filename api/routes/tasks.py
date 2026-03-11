"""
FastAPI项目 - 任务管理API路由
处理异步任务的创建、执行、查询和管理
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from typing import List, Optional, Dict, Any
import logging

from src.async_tasks.task_models import (
    TaskModel, TaskStatus, TaskType, TaskFilter, TaskStatistics
)
from src.async_tasks.task_executor import setup_task_executor
from api.deps import format_error_response, format_success_response, get_task_manager_dependency

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tasks", tags=["tasks"])


# 初始化任务执行器
_task_executor = None

def get_task_executor():
    """获取任务执行器实例"""
    global _task_executor
    if _task_executor is None:
        task_manager = get_task_manager_dependency()
        _task_executor = setup_task_executor(task_manager)
    return _task_executor


@router.post(
    "/create",
    response_model=dict,
    summary="创建任务"
)
async def create_task(
    task_type: TaskType,
    task_name: str,
    params: Dict[str, Any],
    total_items: int = 0,
    max_retries: int = 3
):
    """
    创建新的异步任务

    - **task_type**: 任务类型 (analysis_daily/backtest_batch/scheduler_cache/sector_analyze)
    - **task_name**: 任务名称
    - **params**: 执行参数
    - **total_items**: 总项目数（可选）
    - **max_retries**: 最大重试次数（默认3）
    """
    try:
        task_manager = get_task_manager_dependency()
        task_id = await task_manager.create_task(
            task_type=task_type,
            task_name=task_name,
            params=params,
            total_items=total_items,
            max_retries=max_retries
        )

        return format_success_response({
            "task_id": task_id,
            "task_name": task_name,
            "task_type": task_type,
            "status": "PENDING",
            "check_url": f"/tasks/{task_id}"
        })

    except Exception as e:
        logger.error(f"Failed to create task: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=format_error_response("Failed to create task", str(e))
        )


@router.post(
    "/{task_id}/start",
    response_model=dict,
    summary="启动任务"
)
async def start_task(task_id: str):
    """
    启动指定的任务

    - **task_id**: 任务ID
    """
    task_manager = get_task_manager_dependency()
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=404,
            detail=format_error_response("Task not found", f"Task {task_id} does not exist")
        )

    success = await task_manager.start_task(task_id)

    if not success:
        raise HTTPException(
            status_code=400,
            detail=format_error_response(
                "Failed to start task",
                "Task may already be running or max concurrent limit reached"
            )
        )

    return format_success_response({
        "task_id": task_id,
        "status": "RUNNING",
        "message": "Task started successfully"
    })


@router.post(
    "/{task_id}/pause",
    response_model=dict,
    summary="暂停任务"
)
async def pause_task(task_id: str):
    """
    暂停正在运行的任务

    - **task_id**: 任务ID
    """
    task_manager = get_task_manager_dependency()
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=404,
            detail=format_error_response("Task not found", f"Task {task_id} does not exist")
        )

    success = await task_manager.pause_task(task_id)

    if not success:
        raise HTTPException(
            status_code=400,
            detail=format_error_response(
                "Failed to pause task",
                "Task is not running or cannot be paused"
            )
        )

    return format_success_response({
        "task_id": task_id,
        "status": "PAUSED",
        "message": "Task paused successfully"
    })


@router.post(
    "/{task_id}/resume",
    response_model=dict,
    summary="恢复任务"
)
async def resume_task(task_id: str):
    """
    恢复已暂停的任务

    - **task_id**: 任务ID
    """
    task_manager = get_task_manager_dependency()
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=404,
            detail=format_error_response("Task not found", f"Task {task_id} does not exist")
        )

    success = await task_manager.resume_task(task_id)

    if not success:
        raise HTTPException(
            status_code=400,
            detail=format_error_response(
                "Failed to resume task",
                "Task is not paused or cannot be resumed"
            )
        )

    return format_success_response({
        "task_id": task_id,
        "status": "RUNNING",
        "message": "Task resumed successfully"
    })


@router.post(
    "/{task_id}/cancel",
    response_model=dict,
    summary="取消任务"
)
async def cancel_task(task_id: str):
    """
    取消任务

    - **task_id**: 任务ID
    """
    task_manager = get_task_manager_dependency()
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=404,
            detail=format_error_response("Task not found", f"Task {task_id} does not exist")
        )

    success = await task_manager.cancel_task(task_id)

    if not success:
        raise HTTPException(
            status_code=400,
            detail=format_error_response(
                "Failed to cancel task",
                "Task cannot be cancelled"
            )
        )

    return format_success_response({
        "task_id": task_id,
        "status": "CANCELLED",
        "message": "Task cancelled successfully"
    })


@router.post(
    "/{task_id}/retry",
    response_model=dict,
    summary="重试任务"
)
async def retry_task(task_id: str):
    """
    重试失败的任务

    - **task_id**: 任务ID
    """
    task_manager = get_task_manager_dependency()
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=404,
            detail=format_error_response("Task not found", f"Task {task_id} does not exist")
        )

    success = await task_manager.retry_task(task_id)

    if not success:
        raise HTTPException(
            status_code=400,
            detail=format_error_response(
                "Failed to retry task",
                "Task is not in FAILED state or exceeded max retries"
            )
        )

    return format_success_response({
        "task_id": task_id,
        "status": "PENDING",
        "message": "Task retry scheduled"
    })


@router.get(
    "",
    response_model=List[TaskModel],
    summary="列出任务"
)
async def list_tasks(
    status: Optional[TaskStatus] = Query(None, description="状态筛选"),
    task_type: Optional[TaskType] = Query(None, description="类型筛选"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量")
):
    """
    列出任务

    - **status**: 按状态筛选（可选）
    - **task_type**: 按类型筛选（可选）
    - **limit**: 返回数量限制（默认100，最大1000）
    - **offset**: 偏移量（默认0）
    """
    task_manager = get_task_manager_dependency()
    tasks = task_manager.list_tasks(
        status=status,
        task_type=task_type,
        limit=limit
    )

    # 应用偏移量
    if offset > 0 and offset < len(tasks):
        tasks = tasks[offset:]

    return tasks


@router.get(
    "/running",
    response_model=List[TaskModel],
    summary="获取运行中的任务"
)
async def get_running_tasks():
    """
    获取所有正在运行的任务
    """
    task_manager = get_task_manager_dependency()
    return task_manager.get_running_tasks()


@router.get(
    "/statistics",
    summary="获取任务统计"
)
async def get_statistics():
    """
    获取任务系统统计信息
    """
    task_manager = get_task_manager_dependency()
    return task_manager.get_statistics()


@router.delete(
    "/cleanup",
    response_model=dict,
    summary="清理旧任务"
)
async def cleanup_tasks(days: int = Query(7, ge=1, le=365, description="保留天数")):
    """
    清理指定天数前的已完成任务

    - **days**: 保留天数（默认7天）
    """
    task_manager = get_task_manager_dependency()
    cleaned_count = task_manager.store.cleanup_old_tasks(days)

    return format_success_response({
        "cleaned_count": cleaned_count,
        "retention_days": days,
        "message": f"Cleaned {cleaned_count} old tasks"
    })


@router.get(
    "/{task_id}",
    response_model=TaskModel,
    summary="获取任务详情"
)
async def get_task_detail(task_id: str):
    """
    获取指定任务的详细信息

    - **task_id**: 任务ID
    """
    task_manager = get_task_manager_dependency()
    task = task_manager.get_task(task_id)

    if not task:
        raise HTTPException(
            status_code=404,
            detail=format_error_response("Task not found", f"Task {task_id} does not exist")
        )

    return task


# =============== 快速创建任务的便捷接口 ===============

@router.post(
    "/create-analysis",
    response_model=dict,
    summary="快速创建分析任务"
)
async def create_analysis_task(
    selection_mode: str = Query("top_n", description="选择模式"),
    max_results: int = Query(20, ge=1, le=100, description="最大结果数"),
    custom_stocks: Optional[List[str]] = Query(None, description="自定义股票列表"),
    use_parallel: bool = Query(True, description="是否使用并行分析")
):
    """
    快速创建股票分析任务
    """
    params = {
        "selection_mode": selection_mode,
        "max_results": max_results,
        "custom_stocks": custom_stocks,
        "use_parallel": use_parallel,
        "use_cache": True,
        "auto_cache": True
    }

    task_manager = get_task_manager_dependency()
    task_id = await task_manager.create_task(
        task_type=TaskType.ANALYSIS_DAILY,
        task_name=f"股票分析 - {selection_mode}",
        params=params
    )

    # 自动启动任务
    await task_manager.start_task(task_id)

    return format_success_response({
        "task_id": task_id,
        "task_name": f"股票分析 - {selection_mode}",
        "task_type": "analysis_daily",
        "status": "RUNNING",
        "check_url": f"/tasks/{task_id}"
    })


@router.post(
    "/create-backtest",
    response_model=dict,
    summary="快速创建回测任务"
)
async def create_backtest_task(
    stocks: List[str] = Body(..., description="股票代码列表"),
    start_date: str = Body(..., description="开始日期 (YYYY-MM-DD)"),
    end_date: str = Body(..., description="结束日期 (YYYY-MM-DD)"),
    initial_capital: float = Body(100000, description="初始资金")
):
    """
    快速创建批量回测任务
    """
    params = {
        "stocks": stocks,
        "start_date": start_date,
        "end_date": end_date,
        "initial_capital": initial_capital
    }

    task_manager = get_task_manager_dependency()
    task_id = await task_manager.create_task(
        task_type=TaskType.BACKTEST_BATCH,
        task_name=f"批量回测 - {len(stocks)} 只股票",
        params=params,
        total_items=len(stocks)
    )

    # 自动启动任务
    await task_manager.start_task(task_id)

    return format_success_response({
        "task_id": task_id,
        "task_name": f"批量回测 - {len(stocks)} 只股票",
        "task_type": "backtest_batch",
        "status": "RUNNING",
        "check_url": f"/tasks/{task_id}"
    })


@router.post(
    "/create-cache",
    response_model=dict,
    summary="快速创建缓存任务"
)
async def create_cache_task(
    stocks: List[str] = Body(..., description="股票代码列表"),
    cache_dir: str = Body("./cache", description="缓存目录")
):
    """
    快速创建缓存预加载任务
    """
    params = {
        "stocks": stocks,
        "cache_dir": cache_dir
    }

    task_manager = get_task_manager_dependency()
    task_id = await task_manager.create_task(
        task_type=TaskType.SCHEDULER_CACHE,
        task_name=f"缓存预加载 - {len(stocks)} 只股票",
        params=params,
        total_items=len(stocks)
    )

    # 自动启动任务
    await task_manager.start_task(task_id)

    return format_success_response({
        "task_id": task_id,
        "task_name": f"缓存预加载 - {len(stocks)} 只股票",
        "task_type": "scheduler_cache",
        "status": "RUNNING",
        "check_url": f"/tasks/{task_id}"
    })


@router.post(
    "/create-sector",
    response_model=dict,
    summary="快速创建板块分析任务"
)
async def create_sector_task(
    sector_name: str = Body(..., description="板块名称"),
    stocks: List[str] = Body(..., description="股票代码列表")
):
    """
    快速创建板块分析任务
    """
    params = {
        "sector_name": sector_name,
        "stocks": stocks
    }

    task_manager = get_task_manager_dependency()
    task_id = await task_manager.create_task(
        task_type=TaskType.SECTOR_ANALYZE,
        task_name=f"板块分析 - {sector_name}",
        params=params,
        total_items=len(stocks)
    )

    # 自动启动任务
    await task_manager.start_task(task_id)

    return format_success_response({
        "task_id": task_id,
        "task_name": f"板块分析 - {sector_name}",
        "task_type": "sector_analyze",
        "status": "RUNNING",
        "check_url": f"/tasks/{task_id}"
    })