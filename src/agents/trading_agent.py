"""
LangChain Agent Module
Orchestrates the workflow using LangChain framework
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
from src.strategy.engine import calculate_technical_indicators
from src.data.stock_selector import StockSelector, create_selector_from_env
from src.data.parallel_analyzer import ParallelAnalyzer, AnalysisConfig, AnalysisFunctionFactory
import pandas as pd

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define prompt template
SYSTEM_PROMPT = """
You are a professional A-share trader specializing in short-term trading strategies.
Your task is to analyze A-share stocks and recommend 3-5 stocks for short-term trading (1-3 days).

Consider the following factors:
1. Technical Analysis:
   - MACD golden cross
   - RSI < 30 (oversold conditions)
   - Volume surge (>50% increase)

2. Market Sentiment:
   - News volume and sentiment
   - Announcement impact

3. Capital Flow:
   - Main investor net inflow/outflow

Always apply risk controls:
- Exclude ST/*ST stocks
- Exclude stocks with extreme volatility (>8% daily change)
- Consider position sizing based on volatility

Provide concise, actionable recommendations with:
- Stock code and name
- Buy price range
- Target price
- Stop loss level
- Holding period (1-3 days)
- Clear rationale
"""

def create_trading_agent():
    """
    Create the trading agent with all necessary tools

    Returns:
        Configured agent chain
    """
    # Initialize tools
    tools = [
        get_daily_stock_data,
        get_stock_list,
        evaluate_strategy,
        apply_risk_filters,
        generate_explanation
    ]

    # Initialize local analyzer
    analyzer = create_local_analyzer()

    # Create a simple chain using local analyzer
    return analyzer

def run_daily_analysis(
    stock_selector: Optional[StockSelector] = None,
    max_stocks_to_analyze: int = 0,
    use_parallel: bool = True,
    max_workers: int = 0,
    thread_timeout: int = 30,
    batch_size: int = 100
) -> Dict[str, Any]:
    """
    Run daily stock analysis with flexible stock selection and parallel processing

    Args:
        stock_selector: 股票选择器（可选，默认从环境变量创建）
        max_stocks_to_analyze: 最大分析股票数量（0表示全部）
        use_parallel: 是否使用多线程并行分析（默认True）
        max_workers: 最大线程数（0表示自动检测）
        thread_timeout: 线程超时时间（秒）
        batch_size: 批处理大小

    Returns:
        Analysis results with recommendations
    """
    # Initialize stock selector
    if stock_selector is None:
        stock_selector = create_selector_from_env()

    # Print configuration
    config_summary = stock_selector.get_config_summary()
    print(f"\n📊 股票选择配置：")
    print(f"   选择模式：{config_summary['selection_mode']}")
    if config_summary.get('parameters'):
        for key, value in config_summary['parameters'].items():
            print(f"   {key}: {value}")

    # Print parallel processing config
    print(f"\n⚡ 并行处理配置：")
    print(f"   启用并行: {'是' if use_parallel else '否'}")
    if use_parallel:
        print(f"   线程数: {max_workers if max_workers > 0 else '自动检测'}")
        print(f"   超时时间: {thread_timeout}秒")
        print(f"   批处理大小: {batch_size}")

    # Get stock list
    fetcher = DataFetcher()
    all_stocks = fetcher.get_stock_list()

    # Apply stock selection
    selected_stocks = stock_selector.filter_stocks(all_stocks)
    if not selected_stocks:
        print("⚠️ 没有选中的股票，请检查选择配置")
        return {
            "date": pd.Timestamp.now().strftime("%Y-%m-%d"),
            "recommended_stocks": [],
            "total_analyzed": 0,
            "total_recommended": 0,
            "selection_config": config_summary,
            "analysis_type": "parallel" if use_parallel else "serial"
        }

    # Limit stocks to analyze if specified
    stocks = selected_stocks
    if max_stocks_to_analyze > 0 and max_stocks_to_analyze < len(selected_stocks):
        stocks = selected_stocks[:max_stocks_to_analyze]

    total_stocks = len(stocks)
    print(f"\n🔍 开始分析 {total_stocks} 只股票...")

    if use_parallel:
        # 使用并行分析
        results = _analyze_stocks_parallel(
            stocks,
            config={
                'max_workers': max_workers,
                'thread_timeout': thread_timeout,
                'batch_size': batch_size
            }
        )
    else:
        # 使用串行分析
        results = _analyze_stocks_serial(stocks)

    # Sort by score
    results.sort(key=lambda x: x["score"], reverse=True)

    # Apply final selection based on mode
    if stock_selector.selection_mode == "top_n":
        # For top_n mode, take top N from results
        final_results = results[:stock_selector.max_results]
    else:
        # For other modes, return all qualified results
        final_results = results

    # Print analysis type and stats
    analysis_type = "并行" if use_parallel else "串行"
    print(f"\n✅ {analysis_type}分析完成：")
    print(f"   筛选出 {len(final_results)} 只推荐股票（从 {len(results)} 只合格股票中）")

    return {
        "date": pd.Timestamp.now().strftime("%Y-%m-%d"),
        "recommended_stocks": final_results,
        "total_analyzed": total_stocks,
        "total_recommended": len(final_results),
        "selection_config": config_summary,
        "analysis_type": "parallel" if use_parallel else "serial"
    }


def _analyze_stocks_parallel(stocks: List[Dict], config: Dict) -> List[Dict]:
    """
    并行分析股票

    Args:
        stocks: 股票列表
        config: 并行配置

    Returns:
        分析结果列表
    """
    # 创建并行分析器
    parallel_analyzer = ParallelAnalyzer(
        AnalysisConfig(
            max_workers=config.get('max_workers', 0),
            thread_timeout=config.get('thread_timeout', 30),
            batch_size=config.get('batch_size', 100)
        )
    )

    # 创建分析函数
    analyzer = create_local_analyzer()
    analysis_func = AnalysisFunctionFactory.create_analysis_func(
        analyzer, None, None
    )

    # 执行并行分析
    analysis_results = parallel_analyzer.analyze_stocks_parallel(
        stocks,
        analysis_func,
        description="并行股票分析"
    )

    # 过滤成功的结果
    results = []
    for result in analysis_results:
        if result.success and result.data:
            results.append(result.data)

    # 打印统计信息
    parallel_analyzer.print_summary()

    return results


def _analyze_stocks_serial(stocks: List[Dict]) -> List[Dict]:
    """
    串行分析股票（保持向后兼容）

    Args:
        stocks: 股票列表

    Returns:
        分析结果列表
    """
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
            # Get stock data
            stock_data = get_daily_stock_data.invoke({"stock_code": stock["code"]})

            # Apply risk filters
            risk_result = apply_risk_filters.invoke({"stock_data": stock_data})
            if not risk_result["pass_risk_filter"]:
                continue

            # Evaluate strategy
            evaluation = evaluate_strategy.invoke({"stock_data": stock_data})

            # Use local analyzer for comprehensive analysis
            try:
                technical_indicators = {
                    "rsi": stock_data.get("rsi", 50),
                    "macd": stock_data.get("macd", 0),
                    "macd_histogram": stock_data.get("macd_histogram", 0),
                    "ma5": stock_data.get("ma5", 0),
                    "ma20": stock_data.get("ma20", 0)
                }

                capital_flow = {
                    "main_net_inflow": stock_data.get("main_net_inflow", 0),
                    "retail_net_inflow": stock_data.get("retail_net_inflow", 0),
                    "foreign_net_inflow": stock_data.get("foreign_net_inflow", 0)
                }

                sentiment = {
                    "sentiment_score": stock_data.get("sentiment_score", 50),
                    "positive_news": stock_data.get("positive_news", 0),
                    "negative_news": stock_data.get("negative_news", 0)
                }

                # Get comprehensive analysis from local analyzer
                analysis_result = analyzer.analyze_stock(
                    stock["code"],
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

                # Add to results if recommended
                final_score = analysis_result.get("final_score", evaluation.get("score", 0))
                if evaluation["recommendation"] == "BUY" or final_score > 50:
                    results.append({
                        "code": stock["code"],
                        "name": stock["name"],
                        "score": final_score,
                        "recommendation": analysis_result.get("recommendation", evaluation["recommendation"]),
                        "technical_score": evaluation["technical_score"],
                        "sentiment_score": evaluation["sentiment_score"],
                        "capital_score": evaluation["capital_score"],
                        "price": round(stock_data.get("close", 0), 2),
                        "volume_increase": round(stock_data.get("volume_increase", 0), 2),
                        "rsi": round(stock_data.get("rsi", 50), 2),
                        "explanation": f"综合评分: {final_score:.1f}, 建议: {analysis_result.get('recommendation', 'N/A')}"
                    })
            except Exception as e:
                logger.warning(f"Local analyzer failed for {stock['code']}: {e}")
                # Fallback to basic evaluation
                if evaluation["recommendation"] == "BUY" or evaluation["score"] > 50:
                    results.append({
                        "code": stock["code"],
                        "name": stock["name"],
                        "score": evaluation["score"],
                        "recommendation": evaluation["recommendation"],
                        "technical_score": evaluation["technical_score"],
                        "sentiment_score": evaluation["sentiment_score"],
                        "capital_score": evaluation["capital_score"],
                        "price": round(stock_data.get("close", 0), 2),
                        "volume_increase": round(stock_data.get("volume_increase", 0), 2),
                        "rsi": round(stock_data.get("rsi", 50), 2),
                        "explanation": "基于基本技术分析"
                    })

        except Exception as e:
            print(f"Error analyzing {stock['code']}: {e}")
            continue

    return results