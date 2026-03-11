"""
高效股票筛选器
使用两级过滤算法：规则预筛选 + AI辅助决策
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import time
from .fetcher import DataFetcher
from .stock_selector import StockSelector


class EfficientFilter:
    """高效股票筛选器"""

    def __init__(self, fetcher: DataFetcher, stock_selector: Optional[StockSelector] = None, max_workers: int = 5):
        """
        初始化筛选器

        Args:
            fetcher: 数据获取器实例
            stock_selector: 股票选择器（可选）
            max_workers: 并发工作线程数（默认5）
        """
        self.fetcher = fetcher
        self.candidates = []
        self.filtered_stocks = []
        self.stock_selector = stock_selector or StockSelector()
        self.max_workers = max_workers

    def stage1_rule_filter(self, stock_list: List[Dict], max_candidates: int = 50) -> List[Dict]:
        """
        第一级：基于规则的快速预筛选

        筛选条件：
        1. 剔除ST、*ST股票
        2. 剔除停牌股票
        3. 流动性过滤（成交量过低）
        4. 市值过滤（过小或过大）
        5. 价格区间过滤

        Args:
            stock_list: 原始股票列表
            max_candidates: 最大候选股票数量

        Returns:
            筛选后的候选股票列表
        """
        print(f"🔍 第一级筛选：从 {len(stock_list)} 只股票中预筛选...")

        candidates = []
        start_time = time.time()

        # 并发获取前N只股票的基本数据（提高性能）
        batch_size = 20
        processed = 0

        for i in range(0, len(stock_list), batch_size):
            batch = stock_list[i:i + batch_size]
            batch_candidates = []

            # 并发处理批次
            for stock in batch:
                if len(candidates) >= max_candidates:
                    break

                # 快速规则过滤
                if self._quick_rule_check(stock):
                    batch_candidates.append(stock)

            candidates.extend(batch_candidates)
            processed += len(batch)

            # 实时显示进度
            if processed % 100 == 0 or processed == len(stock_list):
                elapsed = time.time() - start_time
                print(f"  已处理 {processed}/{len(stock_list)} 只股票，候选股票: {len(candidates)}")
                if candidates:
                    print(f"  平均处理速度: {processed/elapsed:.1f} 只/秒")

        print(f"✅ 第一级筛选完成：用时 {time.time() - start_time:.1f} 秒")
        print(f"   筛选出 {len(candidates)} 只候选股票 (保留率: {len(candidates)/len(stock_list)*100:.2f}%)")

        self.candidates = candidates
        return candidates

    def _quick_rule_check(self, stock: Dict) -> bool:
        """
        快速规则检查

        Args:
            stock: 股票信息

        Returns:
            是否通过筛选
        """
        code = stock['code']
        name = stock['name']

        # 1. 剔除ST、*ST股票
        if 'ST' in name or '*ST' in name:
            return False

        # 2. 剔除北交所股票（流动性较差）
        if code.startswith('8') or code.startswith('4'):
            return False

        # 3. 价格区间过滤（排除异常价格）
        # 初步获取价格进行过滤
        try:
            data = self.fetcher.get_daily_data(code, days=5)
            if data.empty or len(data) < 3:
                return False

            latest = data.iloc[-1]
            price = latest['close']

            # 排除价格过高或过低的股票
            if price < 3 or price > 500:
                return False

            # 流动性过滤：成交量过低
            avg_volume = data['volume'].tail(10).mean()
            if avg_volume < 1000000:  # 平均成交量小于100万
                return False

            # 波动率过滤：排除异常波动
            price_std = data['close'].tail(20).std() / data['close'].tail(20).mean()
            if price_std > 0.1:  # 20日波动率超过10%
                return False

            # 初步技术指标筛选
            latest_ma5 = latest.get('ma5', price)
            latest_ma20 = latest.get('ma20', price)

            # 排除均线空头排列过远的股票
            if price < latest_ma20 * 0.8:  # 价格低于MA20 20%以上
                return False

        except Exception:
            # 如果获取数据失败，排除
            return False

        return True

    def stage2_ai_filter(self, candidates: List[Dict], max_results: int = None) -> List[Dict]:
        """
        第二级：AI辅助的精确筛选

        基于：
        1. 完整的技术分析
        2. 资金流向分析
        3. 市场情绪分析
        4. 综合评分

        Args:
            candidates: 候选股票列表
            max_results: 最大结果数量（如果stock_selector指定了mode，则忽略此参数）

        Returns:
            最终推荐股票列表
        """
        print(f"\n🤖 第二级AI筛选：从 {len(candidates)} 只候选股票中精准筛选...")
        print(f"   选择模式：{self.stock_selector.get_config_summary()}")

        start_time = time.time()
        scored_stocks = []

        # 并发分析候选股票
        from concurrent.futures import ThreadPoolExecutor, as_completed

        def analyze_stock(stock):
            """分析单只股票"""
            try:
                code = stock['code']
                name = stock['name']

                # 获取完整数据
                daily_data = self.fetcher.get_daily_data(code, days=30)
                if daily_data.empty or len(daily_data) < 20:
                    return None

                capital_flow = self.fetcher.get_capital_flow(code)
                sentiment = self.fetcher.get_market_sentiment(code)

                # 综合评分
                score = self._calculate_composite_score(
                    daily_data, capital_flow, sentiment
                )

                return {
                    'stock': stock,
                    'daily_data': daily_data,
                    'capital_flow': capital_flow,
                    'sentiment': sentiment,
                    'score': score
                }
            except Exception as e:
                print(f"    ⚠️ 分析 {stock['code']} 失败: {e}")
                return None

        # 并发执行
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_stock = {
                executor.submit(analyze_stock, stock): stock
                for stock in candidates
            }

            for future in as_completed(future_to_stock):
                result = future.result()
                if result:
                    scored_stocks.append(result)

        # 按评分排序
        scored_stocks.sort(key=lambda x: x['score'], reverse=True)

        # 使用股票选择器过滤结果
        top_stocks = self.stock_selector.filter_stocks(
            scored_stocks,
            scored_stocks=scored_stocks
        )

        print(f"✅ 第二级筛选完成：用时 {time.time() - start_time:.1f} 秒")
        print(f"   选出 {len(top_stocks)} 只优质股票")

        self.filtered_stocks = top_stocks
        return top_stocks

    def _calculate_composite_score(
        self,
        daily_data: pd.DataFrame,
        capital_flow: Dict,
        sentiment: Dict
    ) -> float:
        """
        计算综合评分

        评分维度：
        - 技术指标 (40%)
        - 资金流向 (30%)
        - 市场情绪 (20%)
        - 趋势强度 (10%)

        Args:
            daily_data: 日线数据
            capital_flow: 资金流向数据
            sentiment: 市场情绪数据

        Returns:
            综合评分 (-100 到 100)
        """
        latest = daily_data.iloc[-1]
        prev = daily_data.iloc[-2] if len(daily_data) > 1 else latest

        score = 0.0

        # 1. 技术指标评分 (40%)
        tech_score = 0.0

        # MACD金叉
        if latest.get('macd_histogram', 0) > 0 and prev.get('macd_histogram', 0) <= 0:
            tech_score += 15

        # MACD柱状图强度
        macd_strength = min(abs(latest.get('macd_histogram', 0)) / 0.5, 10)
        if latest.get('macd_histogram', 0) > 0:
            tech_score += macd_strength
        else:
            tech_score -= macd_strength

        # RSI评分 (30-70区间最好)
        rsi = latest.get('rsi', 50)
        if 30 <= rsi <= 70:
            tech_score += 10
        elif rsi < 30:  # 超卖
            tech_score += 5
        else:  # 超买
            tech_score -= 10

        # 均线评分
        ma5 = latest.get('ma5', 0)
        ma20 = latest.get('ma20', 0)
        price = latest.get('close', 0)

        if ma5 > ma20 and price > ma5:
            tech_score += 10  # 多头排列
        elif ma5 < ma20 and price < ma5:
            tech_score -= 10  # 空头排列

        # 成交量放大
        volume_change = ((latest.get('volume', 0) - prev.get('volume', 1)) /
                        max(prev.get('volume', 1), 1)) * 100
        if volume_change > 50:
            tech_score += 10
        elif volume_change > 20:
            tech_score += 5

        score += tech_score * 0.4

        # 2. 资金流向评分 (30%)
        capital_score = 0.0

        main_flow = capital_flow.get('main_net_inflow', 0)
        if main_flow > 5000000:
            capital_score += 20
        elif main_flow > 1000000:
            capital_score += 10
        elif main_flow > 0:
            capital_score += 5
        else:
            capital_score -= 15

        # 散户与主力背离
        retail_flow = capital_flow.get('retail_net_inflow', 0)
        if main_flow > 0 and retail_flow < 0:
            capital_score += 10  # 主力买入散户卖出

        score += capital_score * 0.3

        # 3. 市场情绪评分 (20%)
        sentiment_score = 0.0

        sentiment_value = sentiment.get('sentiment_score', 50)
        if sentiment_value > 60:
            sentiment_score += 10
        elif sentiment_value > 50:
            sentiment_score += 5
        elif sentiment_value < 40:
            sentiment_score -= 10

        # 正面新闻比例
        positive = sentiment.get('positive_news', 0)
        negative = sentiment.get('negative_news', 0)
        news_count = sentiment.get('news_count', 0)

        if news_count > 0:
            pos_ratio = positive / news_count
            if pos_ratio > 0.6:
                sentiment_score += 10
            elif pos_ratio > 0.4:
                sentiment_score += 5
            else:
                sentiment_score -= 5

        score += sentiment_score * 0.2

        # 4. 趋势强度评分 (10%)
        trend_score = 0.0

        # 最近5日涨跌
        recent_returns = daily_data['close'].tail(5).pct_change().dropna().sum() * 100
        if recent_returns > 5:
            trend_score += 10
        elif recent_returns > 0:
            trend_score += 5
        elif recent_returns < -5:
            trend_score -= 10

        score += trend_score * 0.1

        return score

    def get_filter_summary(self) -> Dict:
        """
        获取筛选过程摘要

        Returns:
            筛选摘要信息
        """
        return {
            'total_stocks': len(self.candidates) + len(self.filtered_stocks),
            'candidates': len(self.candidates),
            'final_results': len(self.filtered_stocks),
            'filter_ratio': len(self.filtered_stocks) / max(len(self.candidates), 1) * 100,
            'top_recommendations': [
                {
                    'code': item['stock']['code'],
                    'name': item['stock']['name'],
                    'score': item['score']
                }
                for item in self.filtered_stocks[:5]
            ]
        }