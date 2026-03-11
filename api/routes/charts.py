"""
FastAPI项目 - 股票图表数据API路由
处理股票历史数据获取相关的API端点
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional, Dict, Any
import logging
import pandas as pd

from api.models import ErrorResponse
from api.deps import validate_stock_code, format_error_response, format_success_response

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/charts", tags=["charts"])


def _format_stock_code(stock_code: str) -> str:
    """
    将A股代码转换为yfinance格式

    - 深市股票（00/30开头）添加 .SZ
    - 沪市股票（60/68开头）添加 .SH

    Args:
        stock_code: 6位股票代码

    Returns:
        格式化的股票代码（如 000001.SZ）
    """
    if stock_code.startswith(('00', '30')):
        return f"{stock_code}.SZ"
    elif stock_code.startswith(('60', '68')):
        return f"{stock_code}.SH"
    else:
        # 默认按深市处理
        return f"{stock_code}.SZ"


def _fetch_stock_history(stock_code: str, days: int = 30) -> Optional[pd.DataFrame]:
    """
    使用yfinance获取股票历史数据

    Args:
        stock_code: 股票代码（格式：000001.SZ 或 600000.SH）
        days: 获取天数

    Returns:
        DataFrame 包含 OHLCV 数据
    """
    try:
        import yfinance as yf

        ticker = yf.Ticker(stock_code)
        df = ticker.history(period=f"{days}d")

        if df.empty:
            return None

        # 重置索引，转换日期格式
        df = df.reset_index()
        df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d')

        # 选择需要的列并重命名
        df = df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']]
        df.columns = ['date', 'open', 'high', 'low', 'close', 'volume']

        # 转换数值类型
        df['open'] = pd.to_numeric(df['open'], errors='coerce')
        df['high'] = pd.to_numeric(df['high'], errors='coerce')
        df['low'] = pd.to_numeric(df['low'], errors='coerce')
        df['close'] = pd.to_numeric(df['close'], errors='coerce')
        df['volume'] = pd.to_numeric(df['volume'], errors='coerce')

        return df

    except Exception as e:
        logger.error(f"获取股票历史数据失败 ({stock_code}, {days}天): {e}")
        return None


@router.get(
    "/{stock_code}/history",
    summary="获取股票历史数据"
)
async def get_stock_history(
    stock_code: str,
    days: int = Query(30, ge=7, le=90, description="数据天数（7-90天）"),
    fetcher_cached=None  # 保留参数兼容性
):
    """
    获取指定股票的历史数据（OHLCV）

    - **stock_code**: 股票代码（6位数字）
    - **days**: 数据天数（7-90天，默认30天）

    返回数据：
    - code: 股票代码
    - name: 股票名称
    - current_price: 当前价格
    - change_percent: 涨跌幅
    - history: 历史数据列表
    """
    # 验证股票代码
    stock_code = validate_stock_code(stock_code)

    try:
        # 获取股票基本信息（用于获取股票名称）
        stock_name = "未知"
        try:
            from api.deps import get_cached_fetcher
            fetcher = get_cached_fetcher()
            stock_list = fetcher.get_stock_list()
            stock_info = next(
                (s for s in stock_list if s['code'] == stock_code),
                None
            )
            if stock_info:
                stock_name = stock_info.get('name', '未知')
        except Exception:
            pass

        # 格式化股票代码用于yfinance
        ticker_code = _format_stock_code(stock_code)

        # 获取历史数据
        df = _fetch_stock_history(ticker_code, days)

        if df is None or df.empty:
            raise HTTPException(
                status_code=404,
                detail=format_error_response(
                    error="Stock history not found",
                    detail=f"No history data found for stock {stock_code}"
                )
            )

        # 计算涨跌幅
        current_price = float(df['close'].iloc[-1]) if not df.empty else 0
        previous_close = float(df['close'].iloc[-2]) if len(df) > 1 else current_price
        change_percent = ((current_price - previous_close) / previous_close * 100) if previous_close > 0 else 0

        # 转换数据格式
        history = df.to_dict('records')

        return format_success_response({
            "code": stock_code,
            "name": stock_name,
            "current_price": round(current_price, 2),
            "change_percent": round(change_percent, 2),
            "history": history
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch stock history for {stock_code}: {e}")
        raise HTTPException(
            status_code=500,
            detail=format_error_response(
                error="Failed to fetch stock history",
                detail=str(e)
            )
        )


@router.get(
    "/{stock_code}/multiple-periods",
    summary="获取多时间段历史数据（用于切换时间范围）"
)
async def get_stock_multiple_periods(
    stock_code: str,
    fetcher_cached=None
):
    """
    获取多时间段的历史数据，方便用户切换时间范围

    - **stock_code**: 股票代码（6位数字）

    返回数据：
    - code: 股票代码
    - data: 包含7天、30天、90天数据的字典
    """
    stock_code = validate_stock_code(stock_code)

    try:
        ticker_code = _format_stock_code(stock_code)

        result = {}
        periods = [7, 30, 90]

        for days in periods:
            df = _fetch_stock_history(ticker_code, days)
            if df is not None and not df.empty:
                result[f"{days}d"] = df.to_dict('records')
            else:
                result[f"{days}d"] = []

        return format_success_response({
            "code": stock_code,
            "data": result
        })

    except Exception as e:
        logger.error(f"Failed to fetch multiple periods for {stock_code}: {e}")
        raise HTTPException(
            status_code=500,
            detail=format_error_response(
                error="Failed to fetch multiple periods",
                detail=str(e)
            )
        )
