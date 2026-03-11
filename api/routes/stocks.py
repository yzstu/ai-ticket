"""
FastAPI项目 - 股票相关API路由
处理股票数据获取相关的API端点
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
import pandas as pd

from api.models import (
    StockInfo,
    DailyDataRequest,
    CapitalFlowRequest,
    MarketSentimentRequest,
    BatchDailyDataRequest,
    BatchDailyDataResponse,
    ErrorResponse
)
from api.deps import (
    get_data_fetcher,
    get_cached_fetcher,
    validate_stock_code,
    format_error_response,
    format_success_response
)

router = APIRouter(prefix="/stocks", tags=["stocks"])


@router.get(
    "/list",
    response_model=List[StockInfo],
    summary="获取股票列表"
)
async def get_stock_list(
    use_cache: bool = Query(True, description="是否使用缓存"),
    fetcher_cached=Depends(get_cached_fetcher),
    fetcher_regular=Depends(get_data_fetcher)
):
    """
    获取所有股票列表

    - **use_cache**: 是否使用缓存，默认为True

    返回股票代码和名称列表
    """
    try:
        if use_cache:
            stock_list = fetcher_cached.get_stock_list()
        else:
            stock_list = fetcher_regular.get_stock_list()

        return stock_list
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=format_error_response(
                error="Failed to fetch stock list",
                detail=str(e)
            )
        )


@router.get(
    "/{stock_code}/daily",
    summary="获取单只股票日线数据"
)
async def get_daily_data(
    stock_code: str,
    days: int = Query(30, ge=1, le=365, description="数据天数"),
    use_cache: bool = Query(True, description="是否使用缓存"),
    force_refresh: bool = Query(False, description="是否强制刷新"),
    fetcher_cached=Depends(get_cached_fetcher)
):
    """
    获取指定股票的日线数据

    - **stock_code**: 股票代码（6位数字）
    - **days**: 数据天数（1-365天）
    - **use_cache**: 是否使用缓存
    - **force_refresh**: 是否强制从API刷新
    """
    # 验证股票代码
    stock_code = validate_stock_code(stock_code)

    try:
        if use_cache:
            # 使用缓存数据获取器
            data = fetcher_cached.get_daily_data(
                stock_code=stock_code,
                days=days,
                force_refresh=force_refresh
            )
        else:
            # 使用传统数据获取器
            from api.deps import get_data_fetcher
            from src.data.fetcher import DataFetcher
            fetcher = DataFetcher()
            data = fetcher.get_daily_data(stock_code, days)

        if data is None or data.empty:
            raise HTTPException(
                status_code=404,
                detail=format_error_response(
                    error="Stock data not found",
                    detail=f"No data found for stock {stock_code}"
                )
            )

        # 转换为JSON格式
        result = {
            "stock_code": stock_code,
            "days": days,
            "data_count": len(data),
            "data": data.to_dict('records') if isinstance(data, pd.DataFrame) else []
        }

        return format_success_response(result)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=format_error_response(
                error="Failed to fetch daily data",
                detail=str(e)
            )
        )


@router.get(
    "/{stock_code}/capital-flow",
    summary="获取资金流向数据"
)
async def get_capital_flow(
    stock_code: str,
    use_cache: bool = Query(True, description="是否使用缓存"),
    force_refresh: bool = Query(False, description="是否强制刷新"),
    fetcher_cached=Depends(get_cached_fetcher)
):
    """
    获取指定股票的资金流向数据

    - **stock_code**: 股票代码（6位数字）
    - **use_cache**: 是否使用缓存
    - **force_refresh**: 是否强制从API刷新
    """
    stock_code = validate_stock_code(stock_code)

    try:
        if use_cache:
            data = fetcher_cached.get_capital_flow(
                stock_code=stock_code,
                force_refresh=force_refresh
            )
        else:
            from api.deps import get_data_fetcher
            from src.data.fetcher import DataFetcher
            fetcher = DataFetcher()
            data = fetcher.get_capital_flow(stock_code)

        if data is None:
            raise HTTPException(
                status_code=404,
                detail=format_error_response(
                    error="Capital flow data not found",
                    detail=f"No capital flow data found for stock {stock_code}"
                )
            )

        return format_success_response({
            "stock_code": stock_code,
            "data": data
        })

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=format_error_response(
                error="Failed to fetch capital flow",
                detail=str(e)
            )
        )


@router.get(
    "/{stock_code}/sentiment",
    summary="获取市场情绪数据"
)
async def get_market_sentiment(
    stock_code: str,
    use_cache: bool = Query(True, description="是否使用缓存"),
    force_refresh: bool = Query(False, description="是否强制刷新"),
    fetcher_cached=Depends(get_cached_fetcher)
):
    """
    获取指定股票的市场情绪数据

    - **stock_code**: 股票代码（6位数字）
    - **use_cache**: 是否使用缓存
    - **force_refresh**: 是否强制从API刷新
    """
    stock_code = validate_stock_code(stock_code)

    try:
        if use_cache:
            data = fetcher_cached.get_market_sentiment(
                stock_code=stock_code,
                force_refresh=force_refresh
            )
        else:
            from api.deps import get_data_fetcher
            from src.data.fetcher import DataFetcher
            fetcher = DataFetcher()
            data = fetcher.get_market_sentiment(stock_code)

        if data is None:
            raise HTTPException(
                status_code=404,
                detail=format_error_response(
                    error="Sentiment data not found",
                    detail=f"No sentiment data found for stock {stock_code}"
                )
            )

        return format_success_response({
            "stock_code": stock_code,
            "data": data
        })

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=format_error_response(
                error="Failed to fetch sentiment data",
                detail=str(e)
            )
        )


@router.post(
    "/batch/daily",
    response_model=BatchDailyDataResponse,
    summary="批量获取股票日线数据"
)
async def batch_get_daily_data(
    request: BatchDailyDataRequest,
    fetcher_cached=Depends(get_cached_fetcher)
):
    """
    批量获取多只股票的日线数据

    - **stock_codes**: 股票代码列表
    - **days**: 数据天数
    - **use_cache_first**: 是否优先使用缓存
    - **max_workers**: 最大并发线程数
    """
    try:
        # 验证股票代码
        for code in request.stock_codes:
            validate_stock_code(code)

        # 执行批量获取
        results = fetcher_cached.batch_get_daily_data(
            stock_codes=request.stock_codes,
            days=request.days,
            use_cache_first=request.use_cache_first,
            max_workers=request.max_workers
        )

        # 统计结果
        successful = sum(1 for v in results.values() if v is not None)
        cache_hits = fetcher_cached._stats.get('cache_hits', 0)
        api_requests = fetcher_cached._stats.get('api_requests', 0)

        return BatchDailyDataResponse(
            results=results,
            total_requested=len(request.stock_codes),
            successful=successful,
            cache_hits=cache_hits,
            api_requests=api_requests
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=format_error_response(
                error="Failed to batch fetch daily data",
                detail=str(e)
            )
        )


@router.get(
    "/info/{stock_code}",
    summary="获取股票基本信息"
)
async def get_stock_info(
    stock_code: str,
    fetcher_cached=Depends(get_cached_fetcher)
):
    """
    获取指定股票的基本信息

    - **stock_code**: 股票代码（6位数字）
    """
    stock_code = validate_stock_code(stock_code)

    try:
        # 获取股票列表并查找指定股票
        stock_list = fetcher_cached.get_stock_list()
        stock_info = next(
            (stock for stock in stock_list if stock['code'] == stock_code),
            None
        )

        if not stock_info:
            raise HTTPException(
                status_code=404,
                detail=format_error_response(
                    error="Stock not found",
                    detail=f"Stock {stock_code} not found in the list"
                )
            )

        return format_success_response(stock_info)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=format_error_response(
                error="Failed to fetch stock info",
                detail=str(e)
            )
        )