"""
FastAPI项目 - 分析相关API路由
处理股票分析相关的API端点
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List
import logging
import time

from api.models import (
    AnalysisRequest,
    AnalysisResponse,
    ErrorResponse
)
from api.deps import (
    get_stock_selector,
    validate_selection_mode,
    get_cached_fetcher,
    format_error_response,
    format_success_response
)
from src.agents.cached_trading_agent import run_daily_analysis_with_cache
from src.analysis.quick_analyzer import fast_analyze_stocks, create_quick_analysis_result

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.post(
    "/daily",
    response_model=AnalysisResponse,
    summary="每日股票分析"
)
async def analyze_stocks(
    request: AnalysisRequest,
    fetcher_cached=Depends(get_cached_fetcher)
):
    """
    执行每日股票分析并返回推荐结果

    - **selection_mode**: 股票选择模式 (top_n/custom/range/all)
    - **max_results**: 最大分析股票数
    - **custom_stocks**: 自定义股票列表（mode=custom时使用）
    - **code_range_start**: 代码范围起始（mode=range时使用）
    - **code_range_end**: 代码范围结束（mode=range时使用）
    - **use_parallel**: 是否使用并行分析
    - **max_workers**: 最大线程数（0=自动）
    - **thread_timeout**: 线程超时时间
    - **batch_size**: 批处理大小
    - **use_cache**: 是否启用缓存
    """
    try:
        # 验证选择模式
        mode = validate_selection_mode(request.selection_mode)

        # 对于全部股票模式，限制最大分析数量
        if mode == "all" and request.max_results > 500:
            raise HTTPException(
                status_code=400,
                detail=format_error_response(
                    error="Max results exceeded",
                    detail="全部股票模式最多分析500只股票，请调整max_results参数"
                )
            )

        # 板块股票模式的特殊处理
        if mode in ["blue_chips", "growth_stocks", "kechuang"]:
            mode = "range"  # 转换为范围模式

        # 构建股票选择器参数
        selector_kwargs = {}

        if mode == "custom" and request.custom_stocks:
            # 验证自定义股票列表
            for code in request.custom_stocks:
                from api.deps import validate_stock_code
                validate_stock_code(code)
            selector_kwargs['custom_stocks'] = request.custom_stocks
            selector_kwargs['max_results'] = len(request.custom_stocks)
        elif mode == "range":
            # 处理板块模式
            if request.selection_mode in ["blue_chips", "growth_stocks", "kechuang"]:
                # 板块代码范围定义
                sector_ranges = {
                    "blue_chips": ("600000", "600999"),
                    "growth_stocks": ("300001", "300999"),
                    "kechuang": ("688001", "688999")
                }
                code_range = sector_ranges[request.selection_mode]
                selector_kwargs['code_range'] = code_range
            else:
                # 自定义范围模式
                if not request.code_range_start or not request.code_range_end:
                    raise HTTPException(
                        status_code=400,
                        detail=format_error_response(
                            error="Invalid range",
                            detail="code_range_start and code_range_end are required for range mode"
                        )
                    )

                # 验证代码范围格式
                from api.deps import validate_stock_code
                validate_stock_code(request.code_range_start)
                validate_stock_code(request.code_range_end)

                selector_kwargs['code_range'] = (
                    request.code_range_start,
                    request.code_range_end
                )
        elif mode == "top_n":
            selector_kwargs['max_results'] = request.max_results

        # 创建股票选择器
        from api.deps import get_stock_selector
        stock_selector = get_stock_selector(
            mode=mode,
            max_results=request.max_results,
            custom_stocks=selector_kwargs.get('custom_stocks'),
            code_range=selector_kwargs.get('code_range')
        )

        # 检查是否使用快速模式
        # 快速模式: max_results < 50 并且 use_fast_mode = True
        use_fast_mode = request.max_results <= 50

        if use_fast_mode:
            logger.info(f"使用快速分析模式，分析 {request.max_results} 只股票")
            # 执行快速分析
            all_stocks = fetcher_cached.get_stock_list()
            selected_stocks = stock_selector.filter_stocks(all_stocks)

            # 限制股票数量
            stocks = selected_stocks
            if request.max_results > 0 and request.max_results < len(selected_stocks):
                stocks = selected_stocks[:request.max_results]

            logger.info(f"开始快速分析 {len(stocks)} 只股票")
            start_time = time.time()

            # 执行快速分析
            results = fast_analyze_stocks(stocks, fetcher_cached)

            # Top-N模式特殊处理：如果没有推荐结果，返回前N个高分股票
            if mode == "top_n" and len(results) < request.max_results:
                logger.warning(f"Top-N模式推荐股票不足({len(results)}只)，补充前{request.max_results}只高分股票")
                # 排序并取前N个
                results.sort(key=lambda x: x.get('score', 0), reverse=True)
                top_results = results[:request.max_results]
            else:
                top_results = results

            # 创建结果
            result = create_quick_analysis_result(
                results=top_results,
                analyzed_count=len(stocks),
                config={
                    "selection_mode": request.selection_mode,
                    "max_results": request.max_results,
                    "use_parallel": False,  # 快速模式不使用并行
                    "analysis_type": "fast"
                }
            )

            duration = time.time() - start_time
            logger.info(f"快速分析完成，耗时 {duration:.2f} 秒")
        else:
            logger.info(f"使用标准分析模式，分析最多 {request.max_results} 只股票")
            # 执行标准分析
            result = run_daily_analysis_with_cache(
                stock_selector=stock_selector,
                max_stocks_to_analyze=request.max_results if request.selection_mode != "all" else 0,
                use_parallel=request.use_parallel,
                max_workers=request.max_workers if request.max_workers > 0 else 8,  # 默认8线程
                thread_timeout=request.thread_timeout,
                batch_size=request.batch_size if request.batch_size > 0 else 100,  # 默认100批大小
                use_cache=request.use_cache,
                start_cache_scheduler=False  # 在API中不启动定时任务
            )

        return AnalysisResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=format_error_response(
                error="Analysis failed",
                detail=str(e)
            )
        )


@router.get(
    "/top",
    response_model=AnalysisResponse,
    summary="获取Top-N推荐股票"
)
async def get_top_stocks(
    n: int = Query(10, ge=1, le=100, description="获取前N只股票"),
    use_parallel: bool = Query(True, description="是否使用并行分析"),
    max_workers: int = Query(0, ge=0, le=32, description="最大线程数"),
    use_cache: bool = Query(True, description="是否启用缓存"),
    fetcher_cached=Depends(get_cached_fetcher)
):
    """
    获取评分最高的前N只股票

    - **n**: 获取前N只股票
    - **use_parallel**: 是否使用并行分析
    - **max_workers**: 最大线程数
    - **use_cache**: 是否启用缓存
    """
    try:
        from api.deps import get_stock_selector

        # 创建Top-N股票选择器
        stock_selector = get_stock_selector(
            mode="top_n",
            max_results=n
        )

        # 执行分析
        result = run_daily_analysis_with_cache(
            stock_selector=stock_selector,
            max_stocks_to_analyze=0,
            use_parallel=use_parallel,
            max_workers=max_workers,
            thread_timeout=30,
            batch_size=100,
            use_cache=use_cache,
            start_cache_scheduler=False
        )

        return AnalysisResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Top stocks analysis failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=format_error_response(
                error="Top stocks analysis failed",
                detail=str(e)
            )
        )


@router.get(
    "/sector/{sector_code}",
    response_model=AnalysisResponse,
    summary="分析指定板块股票"
)
async def analyze_sector(
    sector_code: str,
    n: int = Query(20, ge=1, le=100, description="分析该板块前N只股票"),
    use_parallel: bool = Query(True, description="是否使用并行分析"),
    max_workers: int = Query(0, ge=0, le=32, description="最大线程数"),
    use_cache: bool = Query(True, description="是否启用缓存"),
    fetcher_cached=Depends(get_cached_fetcher)
):
    """
    分析指定板块的股票

    支持的板块代码:
    - blue_chips: 蓝筹股 (600000-600999)
    - tech_stocks: 科技股 (000001-000999)
    - growth_stocks: 创业板 (300001-300999)
    - kechuang: 科创板 (688001-688999)
    """
    try:
        # 定义板块代码范围
        sector_ranges = {
            "blue_chips": ("600000", "600999"),
            "tech_stocks": ("000001", "000999"),
            "growth_stocks": ("300001", "300999"),
            "kechuang": ("688001", "688999")
        }

        if sector_code.lower() not in sector_ranges:
            raise HTTPException(
                status_code=400,
                detail=format_error_response(
                    error="Invalid sector code",
                    detail=f"Supported sectors: {', '.join(sector_ranges.keys())}"
                )
            )

        start_code, end_code = sector_ranges[sector_code.lower()]

        from api.deps import get_stock_selector

        # 创建板块股票选择器
        stock_selector = get_stock_selector(
            mode="range",
            code_range=(start_code, end_code)
        )

        # 执行分析
        result = run_daily_analysis_with_cache(
            stock_selector=stock_selector,
            max_stocks_to_analyze=n,
            use_parallel=use_parallel,
            max_workers=max_workers,
            thread_timeout=30,
            batch_size=100,
            use_cache=use_cache,
            start_cache_scheduler=False
        )

        # 添加板块信息到响应中
        result['sector'] = sector_code
        result['code_range'] = f"{start_code}-{end_code}"

        return AnalysisResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Sector analysis failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=format_error_response(
                error="Sector analysis failed",
                detail=str(e)
            )
        )


@router.get(
    "/custom",
    response_model=AnalysisResponse,
    summary="分析自定义股票列表"
)
async def analyze_custom_stocks(
    stock_codes: str = Query(..., description="股票代码列表，用逗号分隔"),
    use_parallel: bool = Query(True, description="是否使用并行分析"),
    max_workers: int = Query(0, ge=0, le=32, description="最大线程数"),
    use_cache: bool = Query(True, description="是否启用缓存"),
    fetcher_cached=Depends(get_cached_fetcher)
):
    """
    分析指定的股票列表

    - **stock_codes**: 股票代码列表，用逗号分隔，例如: 600519,000001,600036
    - **use_parallel**: 是否使用并行分析
    - **max_workers**: 最大线程数
    - **use_cache**: 是否启用缓存
    """
    try:
        # 解析股票代码列表
        stock_list = [code.strip() for code in stock_codes.split(',')]

        if not stock_list:
            raise HTTPException(
                status_code=400,
                detail=format_error_response(
                    error="Empty stock list",
                    detail="stock_codes cannot be empty"
                )
            )

        # 验证股票代码
        from api.deps import validate_stock_code
        for code in stock_list:
            validate_stock_code(code)

        from api.deps import get_stock_selector

        # 创建自定义股票选择器
        stock_selector = get_stock_selector(
            mode="custom",
            custom_stocks=stock_list
        )

        # 执行分析
        result = run_daily_analysis_with_cache(
            stock_selector=stock_selector,
            max_stocks_to_analyze=0,
            use_parallel=use_parallel,
            max_workers=max_workers,
            thread_timeout=30,
            batch_size=100,
            use_cache=use_cache,
            start_cache_scheduler=False
        )

        # 添加自定义股票信息到响应中
        result['custom_stocks'] = stock_list
        result['custom_stock_count'] = len(stock_list)

        return AnalysisResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Custom stocks analysis failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=format_error_response(
                error="Custom stocks analysis failed",
                detail=str(e)
            )
        )