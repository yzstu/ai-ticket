"""
缓存增强版交易智能体
集成数据缓存功能的股票分析系统
优先使用缓存数据，缓存未命中时从API获取，并自动回写缓存
"""
import os
import logging
from typing import Dict, List, Any, Optional
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from langchain_core.runnables import RunnableParallel, RunnablePassthrough
from src.providers.local_analyzer import create_local_analyzer
from src.tools import (
    get_daily_stock_data,
    get_stock_list,
    evaluate_strategy,
    apply_risk_filters,
    generate_explanation
)
from src.data.fetcher import DataFetcher
from src.data.cached_fetcher import CachedDataFetcher, create_cached_fetcher
from src.strategy.engine import calculate_technical_indicators
from src.data.stock_selector import StockSelector, create_selector_from_env
from src.data.parallel_analyzer import ParallelAnalyzer, AnalysisConfig, AnalysisFunctionFactory
import pandas as pd

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_trading_agent(use_cache: bool = True):
    """
    创建交易智能体（支持缓存）

    Args:
        use_cache: 是否启用缓存

    Returns:
        配置好的交易智能体
    """
    if use_cache:
        # 使用缓存数据获取器
        data_fetcher = create_cached_fetcher(
            use_cache=True,
            cache_dir="./cache",
            auto_cache=True,
            cache_ttl_hours=24,
            fallback_to_api=True
        )
        logger.info("使用缓存数据获取器")
    else:
        # 使用传统数据获取器
        data_fetcher = DataFetcher()
        logger.info("使用传统数据获取器")

    # 初始化本地分析器
    analyzer = create_local_analyzer()

    # 创建简单的链使用本地分析器
    return analyzer, data_fetcher


def run_daily_analysis_with_cache(
    stock_selector: Optional[StockSelector] = None,
    max_stocks_to_analyze: int = 0,
    use_parallel: bool = True,
    max_workers: int = 0,
    thread_timeout: int = 30,
    batch_size: int = 100,
    use_cache: bool = True,  # 新增：是否启用缓存
    start_cache_scheduler: bool = False,  # 新增：是否启动定时缓存任务
    cache_time: str = "16:30",  # 新增：缓存时间
    cleanup_time: str = "02:00"  # 新增：清理时间
) -> Dict[str, Any]:
    """
    使用缓存的每日股票分析

    Args:
        stock_selector: 股票选择器（可选，默认从环境变量创建）
        max_stocks_to_analyze: 最大分析股票数量（0表示全部）
        use_parallel: 是否使用多线程并行分析（默认True）
        max_workers: 最大线程数（0表示自动检测）
        thread_timeout: 线程超时时间（秒）
        batch_size: 批处理大小
        use_cache: 是否启用缓存
        start_cache_scheduler: 是否启动定时缓存任务
        cache_time: 定时缓存时间
        cleanup_time: 定时清理时间

    Returns:
        Analysis results with recommendations
    """
    # 初始化股票选择器
    if stock_selector is None:
        stock_selector = create_selector_from_env()

    # 打印配置
    config_summary = stock_selector.get_config_summary()
    print(f"\n📊 股票选择配置：")
    print(f"   选择模式：{config_summary['selection_mode']}")
    if config_summary.get('parameters'):
        for key, value in config_summary['parameters'].items():
            print(f"   {key}: {value}")

    # 打印缓存配置
    print(f"\n💾 缓存配置：")
    print(f"   启用缓存: {'是' if use_cache else '否'}")
    if use_cache:
        print(f"   自动缓存: 是")
        print(f"   定时任务: {'是' if start_cache_scheduler else '否'}")
        if start_cache_scheduler:
            print(f"   缓存时间: {cache_time}")
            print(f"   清理时间: {cleanup_time}")

    # 打印并行处理配置
    print(f"\n⚡ 并行处理配置：")
    print(f"   启用并行: {'是' if use_parallel else '否'}")
    if use_parallel:
        print(f"   线程数: {max_workers if max_workers > 0 else '自动检测'}")
        print(f"   超时时间: {thread_timeout}秒")
        print(f"   批处理大小: {batch_size}")

    # 获取数据获取器
    if use_cache:
        analyzer, data_fetcher = create_trading_agent(use_cache=True)

        # 启动定时任务（可选）
        scheduler = None
        if start_cache_scheduler:
            try:
                scheduler = data_fetcher.start_cache_scheduler(
                    cache_time=cache_time,
                    cleanup_time=cleanup_time,
                    batch_size=min(batch_size, 200),  # 缓存任务使用较小的batch
                    max_workers=min(max_workers, 8) if max_workers > 0 else 4
                )
                print(f"\n✅ 定时缓存任务已启动")
                print(f"   每天 {cache_time} 执行缓存")
                print(f"   每天 {cleanup_time} 执行清理")
            except Exception as e:
                logger.warning(f"启动定时任务失败: {e}")
    else:
        analyzer, data_fetcher = create_trading_agent(use_cache=False)

    # 获取股票列表
    all_stocks = data_fetcher.get_stock_list()

    # 应用股票选择
    selected_stocks = stock_selector.filter_stocks(all_stocks)
    if not selected_stocks:
        print("⚠️ 没有选中的股票，请检查选择配置")
        return {
            "date": pd.Timestamp.now().strftime("%Y-%m-%d"),
            "recommended_stocks": [],
            "total_analyzed": 0,
            "total_recommended": 0,
            "selection_config": config_summary,
            "analysis_type": "parallel" if use_parallel else "serial",
            "cache_enabled": use_cache
        }

    # 限制股票数量
    stocks = selected_stocks
    if max_stocks_to_analyze > 0 and max_stocks_to_analyze < len(selected_stocks):
        stocks = selected_stocks[:max_stocks_to_analyze]

    total_stocks = len(stocks)
    print(f"\n🔍 开始分析 {total_stocks} 只股票...")

    if use_cache:
        print("   优先从缓存获取数据...")

    if use_parallel:
        # 使用并行分析
        results = _analyze_stocks_parallel_with_cache(
            stocks,
            data_fetcher,
            config={
                'max_workers': max_workers,
                'thread_timeout': thread_timeout,
                'batch_size': batch_size
            }
        )
    else:
        # 使用串行分析
        results = _analyze_stocks_serial_with_cache(stocks, data_fetcher)

    # 排序和筛选
    results.sort(key=lambda x: x["score"], reverse=True)

    # 应用最终选择
    if stock_selector.selection_mode == "top_n":
        final_results = results[:stock_selector.max_results]
    else:
        final_results = results

    # 打印分析类型和统计
    analysis_type = "并行" if use_parallel else "串行"
    cache_status = "+缓存" if use_cache else ""
    print(f"\n✅ {analysis_type}分析{cache_status}完成：")
    print(f"   筛选出 {len(final_results)} 只推荐股票（从 {len(results)} 只合格股票中）")

    # 打印缓存统计
    if use_cache:
        cache_stats = data_fetcher.get_cache_stats()
        print(f"\n💾 缓存统计：")
        print(f"   命中率: {cache_stats.get('cache_hit_rate', 0):.1f}%")
        print(f"   总请求: {cache_stats.get('total_requests', 0)}")
        print(f"   缓存命中: {cache_stats.get('cache_hits', 0)}")
        print(f"   API请求: {cache_stats.get('api_requests', 0)}")

    return {
        "date": pd.Timestamp.now().strftime("%Y-%m-%d"),
        "recommended_stocks": final_results,
        "total_analyzed": total_stocks,
        "total_recommended": len(final_results),
        "selection_config": config_summary,
        "analysis_type": "parallel" if use_parallel else "serial",
        "cache_enabled": use_cache,
        "cache_stats": cache_stats if use_cache else None
    }


def _analyze_stocks_parallel_with_cache(stocks: List[Dict], data_fetcher: CachedDataFetcher, config: Dict) -> List[Dict]:
    """使用缓存的并行分析股票"""
    # 创建并行分析器
    parallel_analyzer = ParallelAnalyzer(
        AnalysisConfig(
            max_workers=config.get('max_workers', 0),
            thread_timeout=config.get('thread_timeout', 30),
            batch_size=config.get('batch_size', 100)
        )
    )

    # 创建分析函数（使用缓存数据获取器）
    analysis_func = _create_cache_aware_analysis_func(data_fetcher)

    # 执行并行分析
    analysis_results = parallel_analyzer.analyze_stocks_parallel(
        stocks,
        analysis_func,
        description="并行股票分析(缓存增强)"
    )

    # 过滤成功的结果
    results = []
    for result in analysis_results:
        if result.success and result.data:
            results.append(result.data)

    # 打印统计信息
    parallel_analyzer.print_summary()

    return results


def _analyze_stocks_serial_with_cache(stocks: List[Dict], data_fetcher: CachedDataFetcher) -> List[Dict]:
    """使用缓存的串行分析股票"""
    results = []
    analyzer = create_local_analyzer()
    total_stocks = len(stocks)

    for i, stock in enumerate(stocks):
        try:
            if (i + 1) % 100 == 0:
                print(f"进度：{i + 1}/{total_stocks} 只股票已分析 ({((i + 1) / total_stocks * 100):.1f}%)")
        except Exception:
            pass

        try:
            # 使用缓存数据获取器
            stock_code = stock["code"]

            # 获取日线数据（优先从缓存）
            daily_data = data_fetcher.get_daily_data(stock_code, days=30, force_refresh=False)
            if daily_data is None or daily_data.empty:
                # 缓存未命中，尝试从API获取
                daily_data = data_fetcher.get_daily_data(stock_code, days=30, force_refresh=True)

            if daily_data is None or daily_data.empty:
                continue

            # 转换DataFrame为字典格式
            stock_data = daily_data.iloc[-1].to_dict() if not daily_data.empty else {}

            # 风险过滤
            risk_result = apply_risk_filters.invoke({"stock_data": stock_data})
            if not risk_result["pass_risk_filter"]:
                continue

            # 策略评估
            evaluation = evaluate_strategy.invoke({"stock_data": stock_data})

            # 使用本地分析器进行综合分析
            try:
                technical_indicators = {
                    "rsi": stock_data.get("rsi", 50),
                    "macd": stock_data.get("macd", 0),
                    "macd_histogram": stock_data.get("macd_histogram", 0),
                    "ma5": stock_data.get("ma5", 0),
                    "ma20": stock_data.get("ma20", 0)
                }

                capital_flow = data_fetcher.get_capital_flow(stock_code, force_refresh=False)
                if capital_flow is None:
                    capital_flow = data_fetcher.get_capital_flow(stock_code, force_refresh=True) or {}

                sentiment = data_fetcher.get_market_sentiment(stock_code, force_refresh=False)
                if sentiment is None:
                    sentiment = data_fetcher.get_market_sentiment(stock_code, force_refresh=True) or {}

                # 综合分析
                analysis_result = analyzer.analyze_stock(
                    stock_code,
                    {
                        "price": stock_data.get("close", 0),
                        "volume": stock_data.get("volume", 0),
                        "avg_volume": stock_data.get("avg_volume", 0),
                        "volatility": stock_data.get("volatility", 0.02),
                        "price_change_5d": stock_data.get("price_change_5d", 0),
                        "trend_strength": stock_data.get("trend_strength", 0.5)
                    },
                    technical_indicators,
                    capital_flow,
                    sentiment
                )

                # 添加结果
                final_score = analysis_result.get("final_score", evaluation.get("score", 0))
                if evaluation["recommendation"] == "BUY" or final_score > 50:
                    # 计算量比
                    avg_volume = stock_data.get("avg_volume", 0)
                    volume_ratio = round(stock_data.get("volume", 0) / avg_volume, 2) if avg_volume > 0 else 0.0

                    results.append({
                        "code": stock_code,
                        "name": stock["name"],
                        "score": final_score,
                        "recommendation": analysis_result.get("recommendation", evaluation["recommendation"]),
                        "technical_score": evaluation["technical_score"],
                        "sentiment_score": evaluation["sentiment_score"],
                        "capital_score": evaluation["capital_score"],
                        "price": round(stock_data.get("close", 0), 2),
                        "volume": int(stock_data.get("volume", 0)),
                        "avg_volume": int(avg_volume),
                        "volume_ratio": volume_ratio,
                        "price_change": round(stock_data.get("price_change", 0), 2),
                        "volume_increase": round(stock_data.get("volume_increase", 0), 2),
                        "rsi": round(stock_data.get("rsi", 50), 2),
                        "explanation": f"综合评分: {final_score:.1f}, 建议: {analysis_result.get('recommendation', 'N/A')}"
                    })

            except Exception as e:
                logger.warning(f"Local analyzer failed for {stock_code}: {e}")
                # 降级到基本评估
                if evaluation["recommendation"] == "BUY" or evaluation["score"] > 50:
                    # 计算量比
                    avg_volume = stock_data.get("avg_volume", 0)
                    volume_ratio = round(stock_data.get("volume", 0) / avg_volume, 2) if avg_volume > 0 else 0.0

                    results.append({
                        "code": stock_code,
                        "name": stock["name"],
                        "score": evaluation["score"],
                        "recommendation": evaluation["recommendation"],
                        "technical_score": evaluation["technical_score"],
                        "sentiment_score": evaluation["sentiment_score"],
                        "capital_score": evaluation["capital_score"],
                        "price": round(stock_data.get("close", 0), 2),
                        "volume": int(stock_data.get("volume", 0)),
                        "avg_volume": int(avg_volume),
                        "volume_ratio": volume_ratio,
                        "price_change": round(stock_data.get("price_change", 0), 2),
                        "volume_increase": round(stock_data.get("volume_increase", 0), 2),
                        "rsi": round(stock_data.get("rsi", 50), 2),
                        "explanation": "基于基本技术分析"
                    })

        except Exception as e:
            print(f"Error analyzing {stock['code']}: {e}")
            continue

    return results


def _create_cache_aware_analysis_func(data_fetcher: CachedDataFetcher):
    """创建支持缓存的分析函数"""
    from src.tools import evaluate_strategy, apply_risk_filters

    def analyze_single_stock(stock: Dict) -> Dict:
        """分析单只股票（使用缓存）"""
        code = stock['code']
        name = stock['name']

        try:
            # 获取日线数据（优先从缓存）
            daily_data = data_fetcher.get_daily_data(code, days=30, force_refresh=False)
            if daily_data is None or daily_data.empty:
                daily_data = data_fetcher.get_daily_data(code, days=30, force_refresh=True)

            if daily_data is None or daily_data.empty:
                raise Exception("无法获取日线数据")

            # 转换DataFrame为字典
            stock_data = daily_data.iloc[-1].to_dict() if not daily_data.empty else {}

            # 风险过滤
            risk_result = apply_risk_filters.invoke({"stock_data": stock_data})
            if not risk_result["pass_risk_filter"]:
                raise Exception(f"未通过风险过滤: {risk_result['risk_issues']}")

            # 策略评估
            evaluation = evaluate_strategy.invoke({"stock_data": stock_data})

            # 获取资金流向（优先从缓存）
            capital_flow = data_fetcher.get_capital_flow(code, force_refresh=False)
            if capital_flow is None:
                capital_flow = data_fetcher.get_capital_flow(code, force_refresh=True) or {}

            # 获取市场情绪（优先从缓存）
            sentiment = data_fetcher.get_market_sentiment(code, force_refresh=False)
            if sentiment is None:
                sentiment = data_fetcher.get_market_sentiment(code, force_refresh=True) or {}

            # 综合分析
            analyzer = create_local_analyzer()
            analysis_result = analyzer.analyze_stock(
                code,
                {
                    "price": stock_data.get("close", 0),
                    "volume": stock_data.get("volume", 0),
                    "avg_volume": stock_data.get("avg_volume", 0),
                    "volatility": stock_data.get("volatility", 0.02),
                    "price_change_5d": stock_data.get("price_change_5d", 0),
                    "trend_strength": stock_data.get("trend_strength", 0.5)
                },
                {
                    "rsi": stock_data.get("rsi", 50),
                    "macd": stock_data.get("macd", 0),
                    "macd_histogram": stock_data.get("macd_histogram", 0),
                    "ma5": stock_data.get("ma5", 0),
                    "ma20": stock_data.get("ma20", 0)
                },
                capital_flow,
                sentiment
            )

            final_score = analysis_result.get("final_score", evaluation.get("score", 0))

            # 计算量比
            avg_volume = stock_data.get("avg_volume", 0)
            volume_ratio = round(stock_data.get("volume", 0) / avg_volume, 2) if avg_volume > 0 else 0.0

            return {
                "code": code,
                "name": name,
                "score": final_score,
                "recommendation": analysis_result.get("recommendation", evaluation["recommendation"]),
                "technical_score": evaluation["technical_score"],
                "sentiment_score": evaluation["sentiment_score"],
                "capital_score": evaluation["capital_score"],
                "price": round(stock_data.get("close", 0), 2),
                "volume": int(stock_data.get("volume", 0)),
                "avg_volume": int(avg_volume),
                "volume_ratio": volume_ratio,
                "price_change": round(stock_data.get("price_change", 0), 2),
                "volume_increase": round(stock_data.get("volume_increase", 0), 2),
                "rsi": round(stock_data.get("rsi", 50), 2),
                "explanation": f"综合评分: {final_score:.1f}, 建议: {analysis_result.get('recommendation', 'N/A')}"
            }

        except Exception as e:
            raise Exception(f"分析失败: {str(e)}")

    return analyze_single_stock


def run_daily_analysis(
    stock_selector: Optional[StockSelector] = None,
    max_stocks_to_analyze: int = 0,
    use_parallel: bool = True,
    max_workers: int = 0,
    thread_timeout: int = 30,
    batch_size: int = 100,
    use_cache: bool = True  # 默认启用缓存
) -> Dict[str, Any]:
    """
    运行每日股票分析（向后兼容的接口）

    Args:
        stock_selector: 股票选择器
        max_stocks_to_analyze: 最大分析股票数量
        use_parallel: 是否使用并行分析
        max_workers: 最大线程数
        thread_timeout: 线程超时时间
        batch_size: 批处理大小
        use_cache: 是否启用缓存

    Returns:
        分析结果
    """
    return run_daily_analysis_with_cache(
        stock_selector=stock_selector,
        max_stocks_to_analyze=max_stocks_to_analyze,
        use_parallel=use_parallel,
        max_workers=max_workers,
        thread_timeout=thread_timeout,
        batch_size=batch_size,
        use_cache=use_cache,
        start_cache_scheduler=False  # 在分析函数中不启动定时任务
    )