"""
Tools Module
Collection of tools for the LangChain agent
"""
from typing import Dict, List
from langchain_core.tools import tool
from src.data.fetcher import get_daily_stock_data, get_stock_list
from src.strategy.engine import evaluate_strategy, apply_risk_filters

# Re-export tools for easier access
__all__ = [
    "get_daily_stock_data",
    "get_stock_list",
    "evaluate_strategy",
    "apply_risk_filters",
    "generate_explanation"
]

@tool
def generate_explanation(stock_data: Dict, evaluation_result: Dict) -> str:
    """
    Generate natural language explanation for trading recommendation

    Args:
        stock_data: Dictionary containing stock analysis data
        evaluation_result: Strategy evaluation result

    Returns:
        Natural language explanation
    """
    # In a real implementation, this would use an actual LLM
    # For now, we'll generate a mock explanation

    stock_code = stock_data.get("code", "Unknown")
    stock_name = stock_data.get("name", "Unknown")
    score = evaluation_result.get("score", 0)
    recommendation = evaluation_result.get("recommendation", "HOLD")

    # Build explanation based on factors
    factors = []
    if evaluation_result.get("technical_factors"):
        factors.extend(evaluation_result["technical_factors"])
    if evaluation_result.get("sentiment_factors"):
        factors.extend(evaluation_result["sentiment_factors"])
    if evaluation_result.get("capital_factors"):
        factors.extend(evaluation_result["capital_factors"])

    factor_text = "、".join(factors) if factors else "基本面稳定"

    explanation = f"{stock_name}({stock_code})综合评分为{score}分，建议{recommendation}。主要技术因子包括：{factor_text}。"

    return explanation