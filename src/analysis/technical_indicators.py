"""
技术指标计算模块
提供各种股票技术指标的计算方法
"""
import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


def calculate_ma(data: pd.Series, window: int) -> pd.Series:
    """
    计算移动平均线（MA）

    Args:
        data: 价格序列（通常是收盘价）
        window: 移动平均周期

    Returns:
        移动平均线序列
    """
    return data.rolling(window=window, min_periods=1).mean()


def calculate_ema(data: pd.Series, window: int) -> pd.Series:
    """
    计算指数移动平均线（EMA）

    Args:
        data: 价格序列
        window: 移动平均周期

    Returns:
        指数移动平均线序列
    """
    return data.ewm(span=window, adjust=False).mean()


def calculate_macd(
    data: pd.Series,
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9
) -> Dict[str, pd.Series]:
    """
    计算MACD指标

    Args:
        data: 价格序列（通常是收盘价）
        fast_period: 快线周期，默认12
        slow_period: 慢线周期，默认26
        signal_period: 信号线周期，默认9

    Returns:
        包含 DIF、DEA、MACD_histogram 的字典
    """
    ema_fast = calculate_ema(data, fast_period)
    ema_slow = calculate_ema(data, slow_period)

    dif = ema_fast - ema_slow
    dea = calculate_ema(dif, signal_period)
    macd_histogram = (dif - dea) * 2

    return {
        'dif': dif.fillna(0),
        'dea': dea.fillna(0),
        'macd_histogram': macd_histogram.fillna(0)
    }


def calculate_rsi(data: pd.Series, window: int = 14) -> pd.Series:
    """
    计算相对强弱指数（RSI）

    Args:
        data: 价格序列（通常是收盘价）
        window: 计算周期，默认14

    Returns:
        RSI序列
    """
    delta = data.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)

    avg_gain = gain.rolling(window=window, min_periods=1).mean()
    avg_loss = loss.rolling(window=window, min_periods=1).mean()

    # 对于后面的数据，使用EMA来平滑
    avg_gain = gain.ewm(alpha=1/window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/window, adjust=False).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    return rsi.fillna(50)


def calculate_kdj(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    n: int = 9,
    m1: int = 3,
    m2: int = 3
) -> Dict[str, pd.Series]:
    """
    计算KDJ指标

    Args:
        high: 最高价序列
        low: 最低价序列
        close: 收盘价序列
        n: RSV计算周期，默认9
        m1: K值平滑周期，默认3
        m2: D值平滑周期，默认3

    Returns:
        包含 K、D、J 值的字典
    """
    lowest_low = low.rolling(window=n, min_periods=1).min()
    highest_high = high.rolling(window=n, min_periods=1).max()

    rsv = (close - lowest_low) / (highest_high - lowest_low) * 100
    rsv = rsv.fillna(50)

    # K值：RSV的移动平均
    k = rsv.ewm(com=m1-1, adjust=False).mean()
    # D值：K值的移动平均
    d = k.ewm(com=m2-1, adjust=False).mean()
    # J值：3*K - 2*D
    j = 3 * k - 2 * d

    return {
        'k': k.fillna(50),
        'd': d.fillna(50),
        'j': j.fillna(50)
    }


def calculate_bollinger_bands(
    data: pd.Series,
    window: int = 20,
    num_std: float = 2
) -> Dict[str, pd.Series]:
    """
    计算布林带（Bollinger Bands）

    Args:
        data: 价格序列（通常是收盘价）
        window: 计算周期，默认20
        num_std: 标准差倍数，默认2

    Returns:
        包含上轨、中轨、下轨的字典
    """
    middle = calculate_ma(data, window)
    std = data.rolling(window=window, min_periods=1).std()

    upper = middle + (std * num_std)
    lower = middle - (std * num_std)

    return {
        'upper': upper.fillna(method='bfill'),
        'middle': middle.fillna(method='bfill'),
        'lower': lower.fillna(method='bfill')
    }


def calculate_atr(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    window: int = 14
) -> pd.Series:
    """
    计算平均真实范围（ATR）

    Args:
        high: 最高价序列
        low: 最低价序列
        close: 收盘价序列
        window: 计算周期，默认14

    Returns:
        ATR序列
    """
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())

    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=window, min_periods=1).mean()

    return atr


def calculate_sma(data: pd.Series, window: int) -> pd.Series:
    """
    计算简单移动平均（SMA）

    Args:
        data: 价格序列
        window: 周期

    Returns:
        SMA序列
    """
    return data.rolling(window=window, min_periods=1).mean()


def calculate_wma(data: pd.Series, window: int) -> pd.Series:
    """
    计算加权移动平均（WMA）

    Args:
        data: 价格序列
        window: 周期

    Returns:
        WMA序列
    """
    weights = np.arange(1, window + 1)
    return data.rolling(window=window).apply(
        lambda x: np.dot(x, weights) / weights.sum(),
        raw=True
    )


def calculate_cci(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    window: int = 20
) -> pd.Series:
    """
    计算商品通道指数（CCI）

    Args:
        high: 最高价序列
        low: 最低价序列
        close: 收盘价序列
        window: 计算周期，默认20

    Returns:
        CCI序列
    """
    typical_price = (high + low + close) / 3
    sma = typical_price.rolling(window=window, min_periods=1).mean()
    mad = typical_price.rolling(window=window, min_periods=1).apply(
        lambda x: np.mean(np.abs(x - x.mean()))
    )

    cci = (typical_price - sma) / (0.015 * mad)
    return cci


def calculate_volume_ma(volume: pd.Series, window: int = 5) -> pd.Series:
    """
    计算成交量移动平均

    Args:
        volume: 成交量序列
        window: 周期，默认5

    Returns:
        成交量移动平均序列
    """
    return volume.rolling(window=window, min_periods=1).mean()


def calculate_all_indicators(
    df: pd.DataFrame,
    include_indicators: Optional[List[str]] = None
) -> Dict[str, pd.Series]:
    """
    计算所有指定的技术指标

    Args:
        df: 包含 OHLCV 数据的 DataFrame，必须包含列：open, high, low, close, volume
        include_indicators: 要计算的指标列表，如 ['ma5', 'ma10', 'macd', 'rsi']

    Returns:
        包含所有指标的字典
    """
    if df is None or df.empty:
        return {}

    if 'close' not in df.columns:
        logger.warning("DataFrame缺少 'close' 列")
        return {}

    required_columns = ['close']
    if any(ind in ['kdj', 'atr', 'cci'] for ind in (include_indicators or [])):
        required_columns.extend(['high', 'low'])

    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        logger.warning(f"DataFrame缺少列: {missing_columns}")
        return {}

    indicators = {}

    # 默认计算所有常用指标
    if include_indicators is None:
        include_indicators = [
            'ma5', 'ma10', 'ma20', 'ma30', 'ma60',
            'ema5', 'ema10', 'ema20',
            'macd', 'macd_signal', 'macd_histogram',
            'rsi',
            'kdj_k', 'kdj_d', 'kdj_j',
            'boll_upper', 'boll_middle', 'boll_lower',
            'atr',
            'volume_ma5', 'volume_ma10', 'volume_ma20'
        ]

    close = df['close']

    # 计算移动平均线
    for period in [5, 10, 20, 30, 60]:
        if f'ma{period}' in include_indicators:
            indicators[f'ma{period}'] = calculate_ma(close, period)

        if f'ema{period}' in include_indicators:
            indicators[f'ema{period}'] = calculate_ema(close, period)

    # 计算MACD
    if any(x in include_indicators for x in ['macd', 'macd_signal', 'macd_histogram']):
        macd_data = calculate_macd(close)
        if 'macd' in include_indicators:
            indicators['macd'] = macd_data['dif']
        if 'macd_signal' in include_indicators:
            indicators['macd_signal'] = macd_data['dea']
        if 'macd_histogram' in include_indicators:
            indicators['macd_histogram'] = macd_data['macd_histogram']

    # 计算RSI
    if 'rsi' in include_indicators:
        indicators['rsi'] = calculate_rsi(close)

    # 计算KDJ
    if any(x in include_indicators for x in ['kdj_k', 'kdj_d', 'kdj_j']):
        if 'high' in df.columns and 'low' in df.columns:
            kdj_data = calculate_kdj(df['high'], df['low'], close)
            if 'kdj_k' in include_indicators:
                indicators['kdj_k'] = kdj_data['k']
            if 'kdj_d' in include_indicators:
                indicators['kdj_d'] = kdj_data['d']
            if 'kdj_j' in include_indicators:
                indicators['kdj_j'] = kdj_data['j']

    # 计算布林带
    if any(x in include_indicators for x in ['boll_upper', 'boll_middle', 'boll_lower']):
        boll_data = calculate_bollinger_bands(close)
        if 'boll_upper' in include_indicators:
            indicators['boll_upper'] = boll_data['upper']
        if 'boll_middle' in include_indicators:
            indicators['boll_middle'] = boll_data['middle']
        if 'boll_lower' in include_indicators:
            indicators['boll_lower'] = boll_data['lower']

    # 计算ATR
    if 'atr' in include_indicators:
        if 'high' in df.columns and 'low' in df.columns:
            indicators['atr'] = calculate_atr(df['high'], df['low'], close)

    # 计算成交量均线
    if 'volume' in df.columns:
        for period in [5, 10, 20]:
            if f'volume_ma{period}' in include_indicators:
                indicators[f'volume_ma{period}'] = calculate_volume_ma(df['volume'], period)

    return indicators


def format_indicators_for_api(indicators: Dict[str, pd.Series]) -> Dict[str, List]:
    """
    将指标数据格式化为API响应格式

    Args:
        indicators: 指标字典

    Returns:
        格式化的指标字典，所有值转换为列表
    """
    formatted = {}
    for key, value in indicators.items():
        if isinstance(value, pd.Series):
            formatted[key] = value.fillna(0).tolist()
        else:
            formatted[key] = value
    return formatted


def validate_indicators_list(indicators: str) -> List[str]:
    """
    验证和解析指标列表字符串

    Args:
        indicators: 逗号分隔的指标列表，如 "ma5,ma20,macd"

    Returns:
        验证后的指标列表
    """
    valid_indicators = [
        'ma5', 'ma10', 'ma20', 'ma30', 'ma60',
        'ema5', 'ema10', 'ema20',
        'macd', 'macd_signal', 'macd_histogram',
        'rsi',
        'kdj_k', 'kdj_d', 'kdj_j',
        'boll_upper', 'boll_middle', 'boll_lower',
        'atr',
        'volume_ma5', 'volume_ma10', 'volume_ma20'
    ]

    if not indicators:
        return ['ma5', 'ma20', 'macd', 'rsi']  # 默认指标

    indicator_list = [ind.strip() for ind in indicators.split(',')]
    validated = [ind for ind in indicator_list if ind in valid_indicators]

    if not validated:
        logger.warning(f"未识别任何有效指标，使用默认指标")
        return ['ma5', 'ma20', 'macd', 'rsi']

    return validated