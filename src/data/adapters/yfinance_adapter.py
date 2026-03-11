"""
YFinance数据源适配器
作为AKShare的后备数据源
"""
import time
import yfinance as yf
import pandas as pd
import numpy as np
from typing import Dict, List
from datetime import datetime, timedelta


class YFinanceAdapter:
    """YFinance API适配器（后备数据源）"""

    def __init__(self):
        """初始化适配器"""
        # 网络配置
        import os
        self.timeout = int(os.getenv('YFINANCE_TIMEOUT', '30'))
        self.max_retries = int(os.getenv('YFINANCE_MAX_RETRIES', '3'))

    def _convert_symbol(self, symbol: str) -> str:
        """转换A股代码为Yahoo Finance格式"""
        if symbol.startswith(('60', '68')):
            # 上海证券交易所：600000.SS
            return f"{symbol}.SS"
        else:
            # 深圳证券交易所：000001.SZ
            return f"{symbol}.SZ"

    def get_daily_data(self, symbol: str, days: int = 30) -> pd.DataFrame:
        """
        获取股票日线数据

        Args:
            symbol: 股票代码，如'600519'
            days: 获取天数

        Returns:
            包含OHLCV数据的DataFrame

        Raises:
            Exception: 当数据获取失败时
        """
        last_error = None

        # 重试机制
        for attempt in range(self.max_retries):
            try:
                yf_symbol = self._convert_symbol(symbol)
                ticker = yf.Ticker(yf_symbol)

                # 计算开始日期
                start_date = datetime.now() - timedelta(days=days * 2)

                # 获取数据
                df = ticker.history(start=start_date, end=datetime.now())

                if df.empty:
                    raise ValueError(f"未获取到股票 {symbol} 的数据")

                # 重置索引，日期作为列
                df = df.reset_index()

                # 重命名列以匹配项目格式
                df = df.rename(columns={
                    'Date': 'date',
                    'Open': 'open',
                    'High': 'high',
                    'Low': 'low',
                    'Close': 'close',
                    'Volume': 'volume'
                })

                # 选择需要的列
                df = df[['date', 'open', 'high', 'low', 'close', 'volume']].copy()

                # 数据清洗
                df = df.dropna()
                df = df.sort_values('date')

                # 只保留最近N天数据
                if len(df) > days:
                    df = df.tail(days)

                # 计算技术指标
                df = self._calculate_technical_indicators(df)

                return df.reset_index(drop=True)

            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    # 等待后重试
                    time.sleep(1 + attempt)  # 1, 2, 3秒
                    continue
                else:
                    # 最后一次尝试失败
                    break

        # 所有重试都失败
        raise Exception(f"YFinance获取股票 {symbol} 数据失败: {str(last_error)}")

    def _calculate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算技术指标"""
        # 计算移动平均线
        df['ma5'] = df['close'].rolling(5).mean()
        df['ma20'] = df['close'].rolling(20).mean()

        # 计算MACD
        exp12 = df['close'].ewm(span=12).mean()
        exp26 = df['close'].ewm(span=26).mean()
        df['macd'] = exp12 - exp26
        df['macd_signal'] = df['macd'].ewm(span=9).mean()
        df['macd_histogram'] = df['macd'] - df['macd_signal']

        # 计算RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))

        return df

    def get_stock_list(self) -> List[Dict]:
        """
        获取股票列表

        Raises:
            Exception: YFinance不提供完整的A股列表
        """
        raise Exception("YFinance不提供完整的A股列表，请使用AKShare或其他数据源")

    def get_capital_flow(self, symbol: str) -> Dict:
        """获取资金流向数据

        Raises:
            Exception: YFinance不提供资金流向数据
        """
        raise Exception("YFinance不提供资金流向数据，请使用AKShare或其他数据源")

    def get_market_sentiment(self, symbol: str) -> Dict:
        """获取市场情绪数据

        Raises:
            Exception: YFinance不提供市场情绪数据
        """
        raise Exception("YFinance不提供市场情绪数据，请使用AKShare或其他数据源")