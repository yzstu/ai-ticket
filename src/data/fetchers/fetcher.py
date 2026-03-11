"""
Data Fetcher Module
Fetches real-time and historical market data from external APIs
"""
import os
from typing import Dict, List, Optional
from langchain_core.tools import tool
import pandas as pd
import numpy as np
from .adapters.akshare_adapter import AKShareAdapter
from .adapters.yfinance_adapter import YFinanceAdapter

class DataFetcher:
    """Data fetcher for A-share market data"""

    def __init__(self):
        """Initialize data fetcher with real data sources"""
        self.tushare_token = os.getenv("TUSHARE_TOKEN")
        self.siliconflow_api_key = os.getenv("SILICONFLOW_API_KEY")

        # 初始化数据源适配器
        self.ak_adapter = AKShareAdapter()
        self.yf_adapter = YFinanceAdapter()

        # 尝试导入akshare
        try:
            import akshare
            self.has_akshare = True
        except ImportError:
            self.has_akshare = False
            print("AKShare未安装，将使用YFinance作为后备数据源")

        # 尝试导入yfinance
        try:
            import yfinance
            self.has_yfinance = True
        except ImportError:
            self.has_yfinance = False
            print("YFinance未安装，数据源功能可能受限")

    def get_stock_list(self) -> List[Dict]:
        """
        Get list of A-share stocks

        Returns:
            List of stock information

        Raises:
            Exception: When all data sources fail
        """
        errors = []

        # 优先使用AKShare
        if self.has_akshare:
            try:
                return self.ak_adapter.get_stock_list()
            except Exception as e:
                errors.append(f"AKShare: {str(e)}")

        # 如果AKShare不可用，使用YFinance（后备方案）
        if self.has_yfinance:
            try:
                return self.yf_adapter.get_stock_list()
            except Exception as e:
                errors.append(f"YFinance: {str(e)}")

        # 如果所有数据源都失败，抛出异常
        raise Exception(f"无法获取股票列表，所有数据源失败: {'; '.join(errors)}")

    def get_daily_data(self, stock_code: str, days: int = 30) -> pd.DataFrame:
        """
        Get daily OHLCV data for a stock

        Args:
            stock_code: Stock symbol
            days: Number of days of data to fetch

        Returns:
            DataFrame with OHLCV data

        Raises:
            Exception: When all data sources fail
        """
        errors = []

        # 优先使用AKShare
        if self.has_akshare:
            try:
                return self.ak_adapter.get_daily_data(stock_code, days)
            except Exception as e:
                errors.append(f"AKShare: {str(e)}")

        # 如果AKShare不可用，使用YFinance（后备方案）
        if self.has_yfinance:
            try:
                return self.yf_adapter.get_daily_data(stock_code, days)
            except Exception as e:
                errors.append(f"YFinance: {str(e)}")

        # 如果所有数据源都失败，抛出异常
        raise Exception(f"无法获取股票 {stock_code} 的日线数据，所有数据源失败: {'; '.join(errors)}")


    def get_capital_flow(self, stock_code: str) -> Dict:
        """
        Get capital flow data for a stock

        Args:
            stock_code: Stock symbol

        Returns:
            Dictionary with capital flow information

        Raises:
            Exception: When all data sources fail
        """
        errors = []

        # 优先使用AKShare（提供真实的资金流向数据）
        if self.has_akshare:
            try:
                data = self.ak_adapter.get_capital_flow(stock_code)
                # 检查数据是否有效（所有值都接近0说明数据不可用）
                if abs(data.get('main_net_inflow', 0)) < 1 and \
                   abs(data.get('retail_net_inflow', 0)) < 1 and \
                   abs(data.get('foreign_net_inflow', 0)) < 1:
                    errors.append("AKShare: 数据为0，可能不可用")
                else:
                    return data
            except Exception as e:
                errors.append(f"AKShare: {str(e)}")

        # 如果AKShare不可用，使用YFinance（模拟数据）
        if self.has_yfinance:
            try:
                return self.yf_adapter.get_capital_flow(stock_code)
            except Exception as e:
                errors.append(f"YFinance: {str(e)}")

        # 如果所有数据源都失败，抛出异常
        raise Exception(f"无法获取股票 {stock_code} 的资金流向数据，所有数据源失败: {'; '.join(errors)}")

    def get_market_sentiment(self, stock_code: str) -> Dict:
        """
        Get market sentiment for a stock

        Args:
            stock_code: Stock symbol

        Returns:
            Dictionary with sentiment information

        Raises:
            Exception: When all data sources fail
        """
        errors = []

        # 优先使用AKShare（提供真实的市场情绪数据）
        if self.has_akshare:
            try:
                data = self.ak_adapter.get_market_sentiment(stock_code)
                # 检查数据是否有效
                sentiment_score = data.get('sentiment_score', 0)
                if sentiment_score == 0 or sentiment_score > 100 or sentiment_score < 0:
                    errors.append("AKShare: 数据无效")
                else:
                    return data
            except Exception as e:
                errors.append(f"AKShare: {str(e)}")

        # 如果AKShare不可用，使用YFinance（模拟数据）
        if self.has_yfinance:
            try:
                return self.yf_adapter.get_market_sentiment(stock_code)
            except Exception as e:
                errors.append(f"YFinance: {str(e)}")

        # 如果所有数据源都失败，抛出异常
        raise Exception(f"无法获取股票 {stock_code} 的市场情绪数据，所有数据源失败: {'; '.join(errors)}")

# Tool definitions
@tool
def get_daily_stock_data(stock_code: str) -> Dict:
    """
    Fetch daily OHLCV data for a specific stock

    Args:
        stock_code: Stock symbol (e.g., "600519")

    Returns:
        Dictionary containing stock data
    """
    fetcher = DataFetcher()
    data = fetcher.get_daily_data(stock_code)
    latest_data = data.iloc[-1].to_dict()
    latest_data["code"] = stock_code

    # Add indicators to latest data
    if len(data) > 1:
        macd_golden_cross = latest_data.get("macd_histogram", 0) > 0 and data.iloc[-2]["macd_histogram"] <= 0
        if data.iloc[-2]["volume"] > 0:
            volume_increase = ((latest_data["volume"] - data.iloc[-2]["volume"]) / data.iloc[-2]["volume"]) * 100
        else:
            volume_increase = 0
    else:
        macd_golden_cross = False
        volume_increase = 0

    latest_data["macd_golden_cross"] = macd_golden_cross
    latest_data["volume_increase"] = volume_increase

    # Add capital flow and sentiment data
    capital_flow = fetcher.get_capital_flow(stock_code)
    sentiment = fetcher.get_market_sentiment(stock_code)

    latest_data.update(capital_flow)
    latest_data.update(sentiment)

    # Ensure name is included
    stock_list = fetcher.get_stock_list()
    for stock in stock_list:
        if stock["code"] == stock_code:
            latest_data["name"] = stock["name"]
            break

    return latest_data

@tool
def get_stock_list() -> List[Dict]:
    """
    Get list of A-share stocks

    Returns:
        List of stock information
    """
    fetcher = DataFetcher()
    return fetcher.get_stock_list()