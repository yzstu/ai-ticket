"""
板块相关API路由
"""
from fastapi import APIRouter, Query, Depends, HTTPException
from typing import List, Optional
from datetime import datetime
import logging

from src.data.sector_fetcher import get_sector_fetcher
from api.deps import get_task_manager_dependency as get_task_manager
from src.async_tasks.task_models import TaskType

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/sector", tags=["sector"])


@router.get(
    "/list",
    summary="获取板块列表"
)
async def get_sector_list(
    limit: int = Query(50, ge=1, le=100, description="返回数量"),
    sort_by: str = Query("heat", description="排序字段: heat/change/amount"),
    min_heat: Optional[float] = Query(None, ge=0, le=100, description="最小热度过滤")
):
    """
    获取板块列表，按热度或指定字段排序

    - **limit**: 返回数量
    - **sort_by**: 排序字段 (heat/change/amount)
    - **min_heat**: 最小热度过滤（可选）
    """
    try:
        fetcher = get_sector_fetcher()
        sectors = fetcher.get_sector_list()

        # 计算热度
        for sector in sectors:
            sector['heat'] = fetcher.calculate_sector_heat(sector)
            sector['heat_level'] = fetcher._get_heat_level(sector['heat'])
            sector['heat_color'] = fetcher._get_heat_color(sector['heat'])

        # 过滤
        if min_heat is not None:
            sectors = [s for s in sectors if s['heat'] >= min_heat]

        # 排序
        if sort_by == "heat":
            sectors.sort(key=lambda x: x['heat'], reverse=True)
        elif sort_by == "change":
            sectors.sort(key=lambda x: x['change'], reverse=True)
        elif sort_by == "amount":
            sectors.sort(key=lambda x: x['amount'], reverse=True)

        return {
            "success": True,
            "data": sectors[:limit],
            "total": len(sectors),
            "sort_by": sort_by
        }

    except Exception as e:
        logger.error(f"获取板块列表失败: {e}")
        return {
            "success": False,
            "error": str(e),
            "data": []
        }


@router.get(
    "/hot",
    summary="获取热门板块"
)
async def get_hot_sectors(
    limit: int = Query(20, ge=1, le=50, description="返回数量")
):
    """
    获取热门板块（按热度排序）

    热度计算综合考虑：涨跌幅、成交额、领涨股涨幅

    - **limit**: 返回数量
    """
    try:
        fetcher = get_sector_fetcher()
        sectors = fetcher.get_hot_sectors(limit=limit)

        return {
            "success": True,
            "data": sectors,
            "total": len(sectors),
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"获取热门板块失败: {e}")
        return {
            "success": False,
            "error": str(e),
            "data": []
        }


@router.get(
    "/{sector_code}",
    summary="获取板块详情"
)
async def get_sector_detail(sector_code: str):
    """
    获取板块详情，包含板块内股票列表

    - **sector_code**: 板块代码（如 "BK0428"）
    """
    try:
        fetcher = get_sector_fetcher()

        # 获取板块股票
        stocks = fetcher.get_sector_stocks(sector_code)

        return {
            "success": True,
            "sector_code": sector_code,
            "stocks": stocks,
            "stock_count": len(stocks)
        }

    except Exception as e:
        logger.error(f"获取板块详情失败: {e}")
        return {
            "success": False,
            "error": str(e),
            "sector_code": sector_code,
            "stocks": []
        }


@router.get(
    "/{sector_name}/analyze",
    summary="分析指定板块"
)
async def analyze_sector(
    sector_name: str,
    async_mode: bool = Query(False, description="是否使用异步模式"),
    task_manager=Depends(get_task_manager)
):
    """
    分析指定板块的股票

    - **sector_name**: 板块名称
    - **async_mode**: 是否使用异步模式（新增）
    """
    try:
        fetcher = get_sector_fetcher()

        # 异步模式：创建并启动异步任务
        if async_mode:
            # 获取板块股票列表
            # 这里假设我们有获取板块股票的方法
            stocks = fetcher.get_sector_stocks_by_name(sector_name)

            # 构建任务参数
            task_params = {
                "sector_name": sector_name,
                "stocks": stocks
            }

            # 创建并启动任务
            task_id = await task_manager.create_task(
                task_type=TaskType.SECTOR_ANALYZE,
                task_name=f"板块分析 - {sector_name}",
                params=task_params,
                total_items=len(stocks) if stocks else 0
            )

            await task_manager.start_task(task_id)

            return {
                "async": True,
                "task_id": task_id,
                "message": "异步任务已创建并启动",
                "check_url": f"/tasks/{task_id}",
                "status": "RUNNING"
            }

        # 同步模式：获取板块信息并返回
        sectors = fetcher.get_sector_list()
        target_sector = next((s for s in sectors if s.get('name') == sector_name), None)

        if not target_sector:
            raise HTTPException(
                status_code=404,
                detail={"error": "Sector not found", "sector_name": sector_name}
            )

        stocks = fetcher.get_sector_stocks_by_name(sector_name)

        return {
            "success": True,
            "sector_name": sector_name,
            "sector_info": target_sector,
            "stocks": stocks,
            "stock_count": len(stocks)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"分析板块失败: {e}")
        return {
            "success": False,
            "error": str(e),
            "sector_name": sector_name
        }