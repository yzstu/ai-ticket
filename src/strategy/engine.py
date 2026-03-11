"""
Strategy Engine Module
Applies multi-factor analysis to score and rank stocks
"""
from typing import Dict, List
from langchain_core.tools import tool
import pandas as pd
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# 动态权重配置
WEIGHT_CONFIGS = {
    'bull': {
        'technical': 0.50,
        'sentiment': 0.30,
        'capital': 0.20
    },
    'bear': {
        'technical': 0.70,
        'sentiment': 0.10,
        'capital': 0.20
    },
    'volatile': {
        'technical': 0.40,
        'sentiment': 0.20,
        'capital': 0.40
    }
}


def get_market_index(index_code: str = '000001') -> pd.DataFrame:
    """
    获取市场指数数据（用于市场环境判断）

    Args:
        index_code: 指数代码，默认000001（上证指数）

    Returns:
        DataFrame with index data
    """
    try:
        import akshare as ak

        # 获取近120天的数据用于判断
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=120)).strftime('%Y%m%d')

        index_data = ak.stock_zh_a_hist(
            symbol=index_code,
            period='daily',
            start_date=start_date,
            end_date=end_date
        )

        # 重命名列以保持一致性
        index_data.rename(columns={
            '日期': 'date',
            '开盘': 'open',
            '收盘': 'close',
            '最高': 'high',
            '最低': 'low',
            '成交量': 'volume'
        }, inplace=True)

        return index_data

    except ImportError:
        logger.warning("akshare未安装，返回模拟数据")
        # 返回模拟数据（用于开发测试）
        dates = pd.date_range(end=datetime.now(), periods=60, freq='D')
        import numpy as np
        mock_data = pd.DataFrame({
            'date': dates,
            'close': 3000 + np.cumsum(np.random.randn(60) * 10),
            'open': 3000 + np.cumsum(np.random.randn(60) * 10),
            'high': 3010 + np.cumsum(np.random.randn(60) * 10),
            'low': 2990 + np.cumsum(np.random.randn(60) * 10),
            'volume': np.random.randint(1000000, 5000000, 60)
        })
        return mock_data
    except Exception as e:
        logger.error(f"获取指数数据失败: {e}")
        # 返回空DataFrame
        return pd.DataFrame()


def detect_market_condition(index_data: pd.DataFrame) -> str:
    """
    判断当前市场环境

    Args:
        index_data: 指数数据DataFrame

    Returns:
        'bull' - 牛市（均线多头，趋势向上）
        'bear' - 熊市（均线空头，趋势向下）
        'volatile' - 震荡市
    """
    if index_data.empty or len(index_data) < 60:
        logger.warning("指数数据不足，使用默认配置（震荡市）")
        return 'volatile'

    try:
        close = index_data['close']

        # 计算移动平均线
        ma5 = close.rolling(window=5).mean()
        ma20 = close.rolling(window=20).mean()
        ma60 = close.rolling(window=60).mean()

        # 获取最新值
        current_ma5 = ma5.iloc[-1]
        current_ma20 = ma20.iloc[-1]
        current_ma60 = ma60.iloc[-1]

        # 获取前一日的值用于趋势判断
        prev_ma5 = ma5.iloc[-2]
        prev_ma20 = ma20.iloc[-2]

        # 趋势强度判断
        price_now = close.iloc[-1]
        price_20d_ago = close.iloc[-20] if len(close) >= 20 else close.iloc[0]
        price_change_20d = (price_now - price_20d_ago) / price_20d_ago * 100

        logger.info(f"MA5: {current_ma5:.2f}, MA20: {current_ma20:.2f}, MA60: {current_ma60:.2f}, "
                   f"20日涨跌: {price_change_20d:.2f}%")

        # 均线多头排列（牛市）
        if current_ma5 > current_ma20 > current_ma60 and current_ma5 > prev_ma5:
            logger.info("检测到市场环境：牛市（均线多头排列）")
            return 'bull'
        # 均线空头排列（熊市）
        elif current_ma5 < current_ma20 < current_ma60 and current_ma5 < prev_ma5:
            logger.info("检测到市场环境：熊市（均线空头排列）")
            return 'bear'
        # 震荡市
        else:
            logger.info("检测到市场环境：震荡市（均线纠缠）")
            return 'volatile'

    except Exception as e:
        logger.error(f"市场环境判断失败: {e}")
        return 'volatile'

@tool
def evaluate_strategy(stock_data: Dict) -> Dict:
    """
    Evaluate stock based on multi-factor strategy with dynamic weights

    Args:
        stock_data: Dictionary with stock information

    Returns:
        Strategy evaluation with score and recommendation
    """
    # ========== 步骤1: 市场环境判断 ==========
    market_condition = 'volatile'  # 默认值
    weights = WEIGHT_CONFIGS['volatile']  # 默认权重

    try:
        # 获取上证指数数据用于市场环境判断
        index_data = get_market_index('000001')
        market_condition = detect_market_condition(index_data)
        weights = WEIGHT_CONFIGS[market_condition]
        logger.info(f"市场环境: {market_condition}, 权重配置: {weights}")
    except Exception as e:
        logger.warning(f"市场环境判断失败，使用默认配置: {e}")

    # ========== 步骤2: 技术面评分（使用动态权重） ==========
    technical_score = 0
    technical_factors = []
    max_technical_score = 100

    if stock_data.get('macd_golden_cross'):
        technical_score += 30
        technical_factors.append("MACD金叉")

    if stock_data.get('rsi') and stock_data['rsi'] < 30:
        technical_score += 20
        technical_factors.append("RSI超卖")

    if stock_data.get('volume_increase') and stock_data['volume_increase'] > 50:
        technical_score += 10
        technical_factors.append("成交量放大")

    # 技术面评分标准化到权重范围
    technical_weighted_score = (technical_score / max_technical_score) * 100 * weights['technical']

    # ========== 步骤3: 市场情绪评分（使用动态权重） ==========
    sentiment_score = 0
    sentiment_factors = []
    max_sentiment_score = 100

    sentiment_value = stock_data.get('sentiment_score', 50)
    if sentiment_value > 70:
        sentiment_score = sentiment_value
        sentiment_factors.append("市场情绪积极")
    elif sentiment_value < 30:
        sentiment_score = sentiment_value
        sentiment_factors.append("市场情绪消极")

    # 情绪面评分标准化到权重范围
    sentiment_weighted_score = (sentiment_score / max_sentiment_score) * 100 * weights['sentiment']

    # ========== 步骤4: 资金流向评分（使用动态权重） ==========
    capital_score = 0
    capital_factors = []
    max_capital_score = 100

    # 主力资金流入/流出
    main_inflow = stock_data.get('main_net_inflow', 0)
    if abs(main_inflow) > 10000000:  # 超过1000万
        # 转换为0-100的评分
        if main_inflow > 0:
            capital_score = min((main_inflow / 100000000) * 100, 100)  # 1亿流入=100分
            capital_factors.append("主力资金净流入")
        else:
            capital_score = max((main_inflow / 100000000) * 100, -100)
            capital_factors.append("主力资金净流出")

    # 资金面评分标准化到权重范围
    capital_weighted_score = (capital_score / max_capital_score) * 100 * weights['capital']

    # ========== 步骤5: 综合评分 ==========
    total_score = technical_weighted_score + sentiment_weighted_score + capital_weighted_score

    # ========== 步骤6: 生成建议 ==========
    # 根据市场环境和评分生成建议
    if market_condition == 'bull':
        # 牛市环境：更积极
        recommendation = "BUY" if total_score > 65 else ("HOLD" if total_score > 40 else "SELL")
    elif market_condition == 'bear':
        # 熊市环境：更保守
        recommendation = "BUY" if total_score > 75 else ("HOLD" if total_score > 50 else "SELL")
    else:  # volatile
        # 震荡市：中等标准
        recommendation = "BUY" if total_score > 70 else ("HOLD" if total_score > 45 else "SELL")

    result = {
        "score": round(total_score, 2),
        "technical_score": round(technical_score, 2),
        "sentiment_score": round(sentiment_score, 2),
        "capital_score": round(capital_score, 2),
        "technical_factors": technical_factors,
        "sentiment_factors": sentiment_factors,
        "capital_factors": capital_factors,
        "recommendation": recommendation,
        "market_condition": market_condition,
        "weight_config": weights,
        "analysis_note": f"基于{market_condition}市场环境的动态权重分析"
    }

    logger.info(f"策略评估完成: 市场={market_condition}, 总分={total_score:.2f}, 建议={recommendation}")

    return result

@tool
def apply_risk_filters(stock_data: Dict) -> Dict:
    """
    Apply risk control filters to stock data

    Args:
        stock_data: Dictionary with stock information

    Returns:
        Risk assessment result
    """
    risk_issues = []

    # Check for ST/*ST stocks (mock implementation)
    if stock_data.get("name", "").startswith("*ST") or stock_data.get("name", "").startswith("ST"):
        risk_issues.append("ST股风险")

    # Check for extreme volatility (mock implementation)
    if abs(stock_data.get("close", 0) - stock_data.get("open", 0)) / stock_data.get("open", 1) > 0.08:
        risk_issues.append("高波动风险")

    # Check for minimum market cap (mock implementation)
    # In real implementation, you would check actual market cap
    # Here we'll just assume some stocks don't meet criteria

    return {
        "pass_risk_filter": len(risk_issues) == 0,
        "risk_issues": risk_issues
    }

def calculate_technical_indicators(data: pd.DataFrame) -> Dict:
    """
    Calculate technical indicators from price data

    Args:
        data: DataFrame with price data

    Returns:
        Dictionary with technical indicators
    """
    if len(data) < 2:
        return {}

    latest = data.iloc[-1]
    previous = data.iloc[-2]

    indicators = {
        "rsi": latest.get("rsi", 50),
        "macd_histogram": latest.get("macd_histogram", 0),
        "macd_golden_cross": latest.get("macd_histogram", 0) > 0 and previous.get("macd_histogram", 0) <= 0,
        "volume_increase": ((latest["volume"] - previous["volume"]) / previous["volume"]) * 100 if previous["volume"] > 0 else 0
    }

    return indicators