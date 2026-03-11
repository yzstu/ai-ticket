"""
FastAPI项目 - 回测相关API路由 (真实数据版本)
处理股票推荐回测和成功率分析
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

from api.models import (
    BacktestRequest,
    BacktestResult,
    BacktestSummary,
    ErrorResponse
)
from api.deps import (
    get_cached_fetcher,
    format_error_response,
    format_success_response,
    get_app_config
)
from api.deps import (
    get_cached_fetcher,
    format_error_response,
    format_success_response,
    get_app_config,
    get_backtest_db_dependency as get_backtest_db,
    get_price_provider_dependency as get_price_provider
)
from src.analytics.risk_metrics import RiskMetricsCalculator

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/backtest", tags=["backtest"])


@router.post(
    "/stock",
    response_model=BacktestResult,
    summary="单只股票回测 (真实数据)"
)
async def backtest_single_stock(
    request: BacktestRequest,
    backtest_db=Depends(get_backtest_db),
    price_provider=Depends(get_price_provider)
):
    """
    对单只股票进行回测分析（使用真实历史数据）

    - **stock_code**: 股票代码
    - **days_forward**: 向前跟踪天数
    - **min_recommendation_score**: 最小推荐评分阈值
    - **start_date**: 回测开始日期
    - **end_date**: 回测结束日期
    """
    try:
        stock_code = request.stock_code
        days_forward = request.days_forward

        # 从数据库获取推荐记录
        recommendations = backtest_db.get_recommendations(
            stock_code=stock_code,
            start_date=request.start_date,
            end_date=request.end_date,
            min_score=request.min_recommendation_score
        )

        if not recommendations:
            raise HTTPException(
                status_code=404,
                detail=format_error_response(
                    "No recommendations found",
                    f"未找到股票 {stock_code} 的推荐记录"
                )
            )

        results = []
        for rec in recommendations:
            # 计算收益率
            return_data = price_provider.calculate_returns(
                stock_code,
                rec['recommendation_date'],
                days_forward
            )

            if return_data:
                results.append(return_data)
            else:
                # 如果无法获取价格数据，跳过这条记录
                logger.warning(f"跳过无法获取价格数据的推荐: {stock_code} {rec['recommendation_date']}")

        if not results:
            raise HTTPException(
                status_code=404,
                detail=format_error_response(
                    "No valid backtest data",
                    f"股票 {stock_code} 没有可用的回测数据"
                )
            )

        # 计算汇总统计
        returns = [r['net_return'] for r in results]
        profitable_count = sum(1 for r in results if r['is_profitable'])
        total_count = len(results)
        success_rate = (profitable_count / total_count * 100) if total_count > 0 else 0
        avg_return = np.mean(returns)

        # 计算风险指标
        risk_metrics = RiskMetricsCalculator.calculate_all_metrics(returns)

        # 组织返回数据
        backtest_results = []
        for r in results:
            backtest_results.append({
                "recommendation_date": r['recommendation_date'],
                "recommendation_score": next(rec['score'] for rec in recommendations
                                           if rec['recommendation_date'] == r['recommendation_date']),
                "price_changes": [r['net_return']],  # 简化，只显示总收益
                "total_return": r['net_return'],
                "is_profitable": r['is_profitable'],
                "max_return": r['max_return_during_period'],
                "min_return": r['min_return_during_period']
            })

        return {
            "stock_code": stock_code,
            "days_forward": days_forward,
            "total_recommendations": total_count,
            "success_rate": success_rate,
            "avg_return": avg_return,
            "risk_metrics": risk_metrics,
            "results": backtest_results,
            "backtest_period": {
                "start": request.start_date or "N/A",
                "end": request.end_date or "N/A"
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Backtest failed for stock {request.stock_code}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=format_error_response("Backtest failed", str(e))
        )


@router.post(
    "/batch",
    response_model=BacktestSummary,
    summary="批量回测 (真实数据)"
)
async def backtest_batch(
    request: BacktestRequest,
    backtest_db=Depends(get_backtest_db),
    price_provider=Depends(get_price_provider)
):
    """
    批量回测多只股票（使用真实历史数据）

    - **stock_codes**: 股票代码列表
    - **days_forward**: 向前跟踪天数
    - **min_recommendation_score**: 最小推荐评分阈值
    """
    try:
        stock_codes = request.stock_codes or []
        if not stock_codes:
            # 如果没有提供股票列表，使用一些热门股票
            stock_codes = ['000001', '000002', '600000', '600036', '000858']

        days_forward = request.days_forward
        all_results = []
        stock_summaries = []

        for stock_code in stock_codes:
            try:
                # 获取该股票的回测结果
                batch_request = BacktestRequest(
                    stock_code=stock_code,
                    days_forward=days_forward,
                    min_recommendation_score=request.min_recommendation_score,
                    start_date=request.start_date,
                    end_date=request.end_date
                )

                result = await backtest_single_stock(batch_request, backtest_db, price_provider)

                stock_summaries.append({
                    "stock_code": stock_code,
                    "total_recommendations": result["total_recommendations"],
                    "success_rate": result["success_rate"],
                    "avg_return": result["avg_return"],
                    "risk_score": result.get("risk_metrics", {}).get("sharpe_ratio", 0)
                })
                all_results.extend(result["results"])

            except Exception as e:
                logger.error(f"Failed to backtest {stock_code}: {e}")
                stock_summaries.append({
                    "stock_code": stock_code,
                    "total_recommendations": 0,
                    "success_rate": 0,
                    "avg_return": 0,
                    "error": str(e)
                })

        # 计算总体统计
        successful_stocks = [s for s in stock_summaries if s["total_recommendations"] > 0]
        total_recommendations = sum(s["total_recommendations"] for s in stock_summaries)

        if successful_stocks:
            avg_success_rate = np.mean([s["success_rate"] for s in successful_stocks])
            overall_avg_return = np.mean([s["avg_return"] for s in successful_stocks])
        else:
            avg_success_rate = 0
            overall_avg_return = 0

        # 按成功率排序
        stock_summaries.sort(key=lambda x: x["success_rate"], reverse=True)

        return {
            "total_stocks": len(stock_codes),
            "total_recommendations": total_recommendations,
            "overall_success_rate": avg_success_rate,
            "overall_avg_return": overall_avg_return,
            "stock_summaries": stock_summaries,
            "backtest_period": request.start_date or "N/A",
            "days_forward": days_forward
        }

    except Exception as e:
        logger.error(f"Batch backtest failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=format_error_response("Batch backtest failed", str(e))
        )


@router.get(
    "/success-rate",
    summary="获取整体回测成功率 (真实数据)"
)
async def get_overall_success_rate(
    days_forward: int = Query(5, description="向前跟踪天数"),
    min_score: float = Query(0.7, description="最小推荐评分"),
    stock_limit: int = Query(50, description="股票数量限制"),
    backtest_db=Depends(get_backtest_db)
):
    """
    获取系统整体回测成功率统计（基于真实数据）
    """
    try:
        # 获取所有回测结果
        all_results = backtest_db.get_backtest_results(days_forward=days_forward)

        if not all_results:
            # 如果没有真实数据，返回空统计
            return {
                "score_buckets": [
                    {"min_score": 0.9, "success_rate": 0, "count": 0},
                    {"min_score": 0.8, "success_rate": 0, "count": 0},
                    {"min_score": 0.7, "success_rate": 0, "count": 0},
                    {"min_score": 0.6, "success_rate": 0, "count": 0},
                    {"min_score": 0.5, "success_rate": 0, "count": 0}
                ],
                "daily_success_rates": [],
                "time_windows": [
                    {"days": 1, "success_rate": 0},
                    {"days": 3, "success_rate": 0},
                    {"days": 5, "success_rate": 0},
                    {"days": 7, "success_rate": 0},
                    {"days": 10, "success_rate": 0},
                    {"days": 15, "success_rate": 0},
                    {"days": 30, "success_rate": 0}
                ],
                "total_recommendations": 0,
                "overall_success_rate": 0,
                "last_updated": datetime.now().isoformat(),
                "message": "暂无回测数据，请先添加推荐记录并执行回测"
            }

        # 计算评分分档统计
        score_buckets = []
        for min_score_threshold in [0.9, 0.8, 0.7, 0.6, 0.5]:
            # 这里需要根据推荐评分计算，实际实现中需要关联推荐表
            # 暂时简化处理
            bucket_results = [r for r in all_results if r['net_return'] > 0]
            success_rate = len(bucket_results) / len(all_results) * 100 if all_results else 0

            score_buckets.append({
                "min_score": min_score_threshold,
                "success_rate": success_rate,
                "count": len(bucket_results)
            })

        # 计算不同时间窗口的成功率（需要多日期的回测数据）
        time_windows = [1, 3, 5, 7, 10, 15, 30]
        window_stats = []

        for days in time_windows:
            # 获取该时间窗口的回测结果
            window_results = backtest_db.get_backtest_results(days_forward=days)
            if window_results:
                profitable = sum(1 for r in window_results if r['is_profitable'])
                success_rate = profitable / len(window_results) * 100
            else:
                success_rate = 0

            window_stats.append({
                "days": days,
                "success_rate": success_rate
            })

        # 计算每日成功率（简化处理）
        daily_success_rates = []
        base_date = datetime.now() - timedelta(days=30)
        for i in range(30):
            date = base_date + timedelta(days=i)
            # 这里需要根据实际数据计算
            # 暂时返回0
            daily_success_rates.append({
                "date": date.strftime("%Y-%m-%d"),
                "success_rate": 0
            })

        # 总体统计
        total_recommendations = len(all_results)
        profitable_count = sum(1 for r in all_results if r['is_profitable'])
        overall_success_rate = (profitable_count / total_recommendations * 100) if total_recommendations > 0 else 0

        return {
            "score_buckets": score_buckets,
            "daily_success_rates": daily_success_rates,
            "time_windows": window_stats,
            "total_recommendations": total_recommendations,
            "overall_success_rate": overall_success_rate,
            "last_updated": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to get success rate: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=format_error_response("Failed to get success rate", str(e))
        )


@router.get(
    "/recommendation-history/{stock_code}",
    summary="获取股票推荐历史"
)
async def get_recommendation_history(
    stock_code: str,
    limit: int = Query(20, description="返回记录数"),
    backtest_db=Depends(get_backtest_db)
):
    """
    获取指定股票的历史推荐记录
    """
    try:
        # 从数据库获取推荐历史
        history = backtest_db.get_recommendations(stock_code=stock_code, limit=limit)

        if not history:
            raise HTTPException(
                status_code=404,
                detail=format_error_response(
                    "No recommendation history found",
                    f"未找到股票 {stock_code} 的推荐历史"
                )
            )

        # 计算汇总统计
        total_recommendations = len(history)
        avg_score = np.mean([h['score'] for h in history])
        high_confidence_count = sum(1 for h in history if h.get('confidence', 0) > 0.8)

        # 转换数据格式
        history_data = []
        for h in history:
            history_data.append({
                "date": h['recommendation_date'],
                "score": h['score'],
                "recommendation_type": h.get('recommendation_type', 'N/A'),
                "confidence": h.get('confidence', 0),
                "price_at_recommendation": h.get('price_at_recommendation', 0),
                "reason": h.get('reason', 'N/A')
            })

        return {
            "stock_code": stock_code,
            "total_recommendations": total_recommendations,
            "history": history_data,
            "avg_score": avg_score,
            "high_confidence_count": high_confidence_count
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get recommendation history for {stock_code}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=format_error_response("Failed to get history", str(e))
        )


@router.post(
    "/seed-sample-data",
    summary="播种示例数据"
)
async def seed_sample_data(
    backtest_db=Depends(get_backtest_db)
):
    """
    播种示例推荐数据（用于测试）
    """
    try:
        backtest_db.seed_sample_data()
        return format_success_response({"message": "示例数据播种完成"})
    except Exception as e:
        logger.error(f"Failed to seed sample data: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=format_error_response("Failed to seed data", str(e))
        )


@router.post(
    "/execute-backtest",
    summary="执行完整回测"
)
async def execute_full_backtest(
    request: BacktestRequest,
    backtest_db=Depends(get_backtest_db),
    price_provider=Depends(get_price_provider)
):
    """
    执行完整的回测流程：获取推荐记录 -> 计算收益率 -> 保存结果
    """
    try:
        stock_code = request.stock_code
        days_forward = request.days_forward

        # 获取推荐记录
        recommendations = backtest_db.get_recommendations(
            stock_code=stock_code,
            start_date=request.start_date,
            end_date=request.end_date,
            min_score=request.min_recommendation_score
        )

        if not recommendations:
            raise HTTPException(
                status_code=404,
                detail=format_error_response(
                    "No recommendations found",
                    f"未找到股票 {stock_code} 的推荐记录"
                )
            )

        success_count = 0
        failed_count = 0

        for rec in recommendations:
            try:
                # 计算收益率
                return_data = price_provider.calculate_returns(
                    stock_code,
                    rec['recommendation_date'],
                    days_forward
                )

                if return_data:
                    # 保存回测结果
                    backtest_db.add_backtest_result(
                        stock_code=stock_code,
                        recommendation_date=rec['recommendation_date'],
                        entry_price=return_data['entry_price'],
                        exit_price=return_data['exit_price'],
                        exit_date=return_data['exit_date'],
                        days_forward=days_forward,
                        gross_return=return_data['gross_return'],
                        net_return=return_data['net_return'],
                        is_profitable=return_data['is_profitable'],
                        max_return=return_data['max_return_during_period'],
                        min_return=return_data['min_return_during_period']
                    )
                    success_count += 1
                else:
                    failed_count += 1

            except Exception as e:
                logger.error(f"Failed to backtest recommendation {rec['recommendation_date']}: {e}")
                failed_count += 1

        return {
            "stock_code": stock_code,
            "days_forward": days_forward,
            "total_recommendations": len(recommendations),
            "success_count": success_count,
            "failed_count": failed_count,
            "message": f"回测完成: {success_count} 成功, {failed_count} 失败"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Execute backtest failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=format_error_response("Execute backtest failed", str(e))
        )