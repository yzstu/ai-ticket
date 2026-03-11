"""
Output Formatter Module
Formats results for different consumption methods
"""
import json
from typing import Dict, List, Any

def format_as_markdown_table(results: Dict[str, Any]) -> str:
    """
    Format results as markdown table

    Args:
        results: Analysis results

    Returns:
        Markdown formatted table
    """
    if not results.get("recommended_stocks"):
        return "## 今日股票推荐\n\n暂无符合条件的股票推荐。"

    # Table header
    table = "## 今日股票推荐\n\n"
    table += f"分析日期: {results.get('date', '')}\n\n"
    table += "| 股票代码 | 名称 | 当前价 | 评分 | 技术分 | 情绪分 | 资金分 | 成交量增 | RSI | 推荐理由 |\n"
    table += "|----------|------|--------|------|--------|--------|--------|----------|-----|----------|\n"

    # Table rows
    for stock in results["recommended_stocks"]:
        table += f"| {stock['code']} | {stock['name']} | {stock['price']} | {stock['score']} | "
        table += f"{stock['technical_score']} | {stock['sentiment_score']} | {stock['capital_score']} | "
        table += f"{stock['volume_increase']}% | {stock['rsi']} | {stock['explanation']} |\n"

    return table

def format_as_json(results: Dict[str, Any]) -> str:
    """
    Format results as JSON

    Args:
        results: Analysis results

    Returns:
        JSON formatted string
    """
    return json.dumps(results, indent=2, ensure_ascii=False)

def format_as_detailed_report(results: Dict[str, Any]) -> str:
    """
    Format results as detailed report

    Args:
        results: Analysis results

    Returns:
        Detailed report string
    """
    if not results.get("recommended_stocks"):
        return "=== A股短线交易推荐报告 ===\n\n暂无符合条件的股票推荐。"

    report = f"=== A股短线交易推荐报告 ===\n\n"
    report += f"分析日期: {results.get('date', '')}\n"
    report += f"分析股票数量: {results.get('total_analyzed', 0)}\n"
    report += f"推荐股票数量: {results.get('total_recommended', 0)}\n\n"

    report += "=== 推荐股票列表 ===\n\n"

    for i, stock in enumerate(results["recommended_stocks"], 1):
        report += f"{i}. {stock['name']} ({stock['code']})\n"
        report += f"   评分: {stock['score']}\n"
        report += f"   当前价格: {stock['price']}\n"
        report += f"   技术得分: {stock['technical_score']}\n"
        report += f"   市场情绪得分: {stock['sentiment_score']}\n"
        report += f"   资金流向得分: {stock['capital_score']}\n"
        report += f"   成交量增幅: {stock['volume_increase']}%\n"
        report += f"   RSI指标: {stock['rsi']}\n"
        report += f"   推荐理由: {stock['explanation']}\n\n"

    return report

def format_recommendation(stock_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format a single stock recommendation with trading parameters

    Args:
        stock_data: Stock analysis data

    Returns:
        Formatted recommendation with trading parameters
    """
    current_price = stock_data.get("price", 0)

    # Calculate trading parameters
    buy_range = {
        "lower": round(current_price * 0.98, 2),  # 2% below current price
        "upper": round(current_price * 1.02, 2)   # 2% above current price
    }

    target_price = round(current_price * 1.05, 2)  # 5% target
    stop_loss = round(current_price * 0.95, 2)    # 5% stop loss
    holding_period = "1-3天"

    return {
        "股票代码": stock_data.get("code", ""),
        "名称": stock_data.get("name", ""),
        "买入区间": f"{buy_range['lower']}-{buy_range['upper']}",
        "目标价": target_price,
        "防守价": stop_loss,
        "持有期": holding_period,
        "推荐理由": stock_data.get("explanation", "")
    }