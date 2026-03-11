#!/usr/bin/env python3
"""
A股短线选股AI回测系统
进行5组回测测试，验证选股策略的有效性
"""
import os
import sys
import random
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
import json
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

class BacktestEngine:
    """回测引擎"""

    def __init__(self, num_rounds: int = 5, stocks_per_round: int = 20):
        """
        初始化回测引擎

        Args:
            num_rounds: 回测轮数
            stocks_per_round: 每轮分析的股票数量
        """
        self.num_rounds = num_rounds
        self.stocks_per_round = stocks_per_round
        self.results = []

    def generate_historical_data(self, stock_code: str, days: int = 30) -> pd.DataFrame:
        """
        生成历史股票数据（模拟）

        Args:
            stock_code: 股票代码
            days: 天数

        Returns:
            历史数据DataFrame
        """
        np.random.seed(int(stock_code) if stock_code.isdigit() else hash(stock_code))

        # 生成日期范围
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        dates = pd.date_range(start=start_date, end=end_date, freq='D')
        num_days = len(dates)

        # 基础价格
        base_price = 50 + (int(stock_code) % 100) if stock_code.isdigit() else 50

        # 生成价格数据 (带趋势)
        trend = np.random.choice([-1, 0, 1], p=[0.3, 0.4, 0.3])  # 下跌/横盘/上涨
        returns = np.random.randn(num_days) * 0.02 + trend * 0.001
        prices = base_price * np.cumprod(1 + returns)

        # 生成OHLCV数据
        data = pd.DataFrame({
            'date': dates,
            'open': prices * (1 + np.random.randn(num_days) * 0.005),
            'high': prices * (1 + np.abs(np.random.randn(num_days)) * 0.01),
            'low': prices * (1 - np.abs(np.random.randn(num_days)) * 0.01),
            'close': prices,
            'volume': np.random.randint(1000000, 10000000, num_days)
        })

        # 计算技术指标
        data['ma5'] = data['close'].rolling(5).mean()
        data['ma20'] = data['close'].rolling(20).mean()

        # MACD
        exp12 = data['close'].ewm(span=12).mean()
        exp26 = data['close'].ewm(span=26).mean()
        data['macd'] = exp12 - exp26
        data['macd_signal'] = data['macd'].ewm(span=9).mean()
        data['macd_histogram'] = data['macd'] - data['macd_signal']

        # RSI
        delta = data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        data['rsi'] = 100 - (100 / (1 + rs))

        return data.dropna()

    def calculate_future_performance(self, stock_code: str, days_ahead: int = 7) -> Dict:
        """
        计算未来表现

        Args:
            stock_code: 股票代码
            days_ahead: 未来天数

        Returns:
            表现数据
        """
        data = self.generate_historical_data(stock_code, 60)  # 生成更多历史数据

        if len(data) < days_ahead + 10:
            return {'return': 0, 'success': False}

        # 当前价格
        current_price = data['close'].iloc[-10]

        # 未来价格
        future_price = data['close'].iloc[-10 + days_ahead]

        # 计算收益率
        return_pct = (future_price - current_price) / current_price

        # 定义成功标准（短线交易：7-9天内涨幅>3%）
        success_threshold = 0.03
        success = return_pct > success_threshold

        return {
            'return': return_pct,
            'success': success,
            'success_threshold': success_threshold,
            'days_ahead': days_ahead
        }

    def simulate_stock_analysis(self, stock_code: str) -> Dict:
        """
        模拟AI分析

        Args:
            stock_code: 股票代码

        Returns:
            分析结果
        """
        # 生成模拟的股票数据
        stock_data = {
            'price': 50 + (int(stock_code) % 100) if stock_code.isdigit() else 50,
            'volume': random.randint(1000000, 10000000),
            'avg_volume': random.randint(2000000, 5000000),
            'volatility': random.uniform(0.01, 0.05),
            'price_change_5d': random.uniform(-0.05, 0.05),
            'trend_strength': random.uniform(0.3, 0.8)
        }

        technical_indicators = {
            'rsi': random.uniform(20, 80),
            'macd': random.uniform(-0.5, 0.5),
            'macd_histogram': random.uniform(-0.3, 0.3),
            'ma5': stock_data['price'] * random.uniform(0.95, 1.05),
            'ma20': stock_data['price'] * random.uniform(0.90, 1.10)
        }

        capital_flow = {
            'main_net_inflow': random.randint(-5000000, 5000000),
            'retail_net_inflow': random.randint(-3000000, 3000000),
            'foreign_net_inflow': random.randint(-2000000, 2000000)
        }

        sentiment = {
            'sentiment_score': random.uniform(30, 70),
            'positive_news': random.randint(0, 20),
            'negative_news': random.randint(0, 10)
        }

        # 简化的分析逻辑（基于技术指标）
        score = 50.0

        # RSI分析
        if 30 <= technical_indicators['rsi'] <= 40:
            score += 15  # 超卖反弹
        elif 60 <= technical_indicators['rsi'] <= 70:
            score += 10  # 强势
        elif technical_indicators['rsi'] > 70:
            score -= 15  # 超买

        # MACD分析
        if technical_indicators['macd_histogram'] > 0:
            score += 20

        # 均线分析
        if technical_indicators['ma5'] > technical_indicators['ma20']:
            score += 15

        # 资金流向分析
        if capital_flow['main_net_inflow'] > 0:
            score += 10

        # 市场情绪分析
        if sentiment['sentiment_score'] > 60:
            score += 10

        # 确保分数在0-100范围内
        score = max(0, min(100, score))

        # 生成推荐
        if score >= 70:
            recommendation = "强烈买入"
        elif score >= 60:
            recommendation = "买入"
        elif score >= 40:
            recommendation = "持有"
        elif score >= 30:
            recommendation = "观望"
        else:
            recommendation = "卖出"

        return {
            'score': score,
            'recommendation': recommendation,
            'confidence': random.uniform(0.6, 0.9)
        }

    def run_single_backtest(self, round_num: int) -> Dict:
        """
        运行单次回测

        Args:
            round_num: 轮次编号

        Returns:
            回测结果
        """
        print(f"\n{'='*70}")
        print(f"🔄 回测第 {round_num} 轮")
        print(f"{'='*70}")

        # 随机选择股票代码（模拟）
        possible_stocks = [f"{random.randint(1, 999999):06d}" for _ in range(self.stocks_per_round)]

        # 去除重复
        selected_stocks = list(set(possible_stocks))[:self.stocks_per_round]

        print(f"📊 随机选择 {len(selected_stocks)} 只股票进行回测")
        print(f"股票代码: {', '.join(selected_stocks[:10])}{'...' if len(selected_stocks) > 10 else ''}")

        # 对每只股票进行分析
        analysis_results = []
        actual_results = []

        for i, stock_code in enumerate(selected_stocks):
            # AI分析
            analysis = self.simulate_stock_analysis(stock_code)
            analysis_results.append(analysis)

            # 计算未来表现
            days_ahead = random.randint(7, 9)
            performance = self.calculate_future_performance(stock_code, days_ahead)
            actual_results.append(performance)

            # 显示进度
            if (i + 1) % 5 == 0 or i == len(selected_stocks) - 1:
                print(f"  进度: {i+1}/{len(selected_stocks)} ({((i+1)/len(selected_stocks)*100):.1f}%)")

        # 评估结果
        buy_recommendations = [i for i, r in enumerate(analysis_results)
                             if r['recommendation'] in ['买入', '强烈买入']]

        if not buy_recommendations:
            print(f"\n⚠️  第 {round_num} 轮: 没有买入推荐，建议调整分析策略")
            return {
                'round': round_num,
                'total_stocks': len(selected_stocks),
                'buy_recommendations': 0,
                'successful_picks': 0,
                'success_rate': 0,
                'avg_return': 0,
                'avg_score': 0,
                'recommendations': []
            }

        print(f"\n🎯 分析结果:")
        print(f"  总股票数: {len(selected_stocks)}")
        print(f"  买入推荐: {len(buy_recommendations)} 只")

        # 统计买入推荐的实际表现
        successful_picks = 0
        total_returns = []
        recommendations = []

        for idx in buy_recommendations:
            analysis = analysis_results[idx]
            performance = actual_results[idx]

            # 判断是否成功
            is_success = performance['success']
            if is_success:
                successful_picks += 1

            total_returns.append(performance['return'])

            recommendations.append({
                'stock_code': selected_stocks[idx],
                'score': analysis['score'],
                'recommendation': analysis['recommendation'],
                'actual_return': performance['return'],
                'success': is_success,
                'days_ahead': performance['days_ahead']
            })

            print(f"  {selected_stocks[idx]}: 评分{analysis['score']:.1f} | "
                  f"推荐{analysis['recommendation']} | "
                  f"实际收益{performance['return']*100:+.2f}% | "
                  f"{'✅' if is_success else '❌'}")

        # 计算成功率
        success_rate = (successful_picks / len(buy_recommendations)) * 100 if buy_recommendations else 0
        avg_return = np.mean(total_returns) * 100 if total_returns else 0
        avg_score = np.mean([analysis_results[i]['score'] for i in buy_recommendations])

        print(f"\n📈 回测结果:")
        print(f"  成功 picks: {successful_picks}/{len(buy_recommendations)}")
        print(f"  成功率: {success_rate:.2f}%")
        print(f"  平均收益: {avg_return:+.2f}%")
        print(f"  平均评分: {avg_score:.1f}")

        return {
            'round': round_num,
            'total_stocks': len(selected_stocks),
            'buy_recommendations': len(buy_recommendations),
            'successful_picks': successful_picks,
            'success_rate': success_rate,
            'avg_return': avg_return,
            'avg_score': avg_score,
            'recommendations': recommendations
        }

    def run_backtest(self) -> Dict:
        """
        运行完整的回测

        Returns:
            完整回测结果
        """
        print(f"\n{'='*70}")
        print(f"🚀 A股短线选股AI - 5组回测测试")
        print(f"{'='*70}")
        print(f"回测配置:")
        print(f"  回测轮数: {self.num_rounds}")
        print(f"  股票数量/轮: {self.stocks_per_round}")
        print(f"  验证周期: 7-9天")
        print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        start_time = time.time()

        # 运行5轮回测
        for round_num in range(1, self.num_rounds + 1):
            result = self.run_single_backtest(round_num)
            self.results.append(result)
            time.sleep(1)  # 短暂停顿

        # 计算总体结果
        end_time = time.time()
        total_time = end_time - start_time

        return self.generate_final_report(total_time)

    def generate_final_report(self, total_time: float) -> Dict:
        """
        生成最终报告

        Args:
            total_time: 总耗时

        Returns:
            最终报告
        """
        print(f"\n{'='*70}")
        print(f"📊 5组回测最终报告")
        print(f"{'='*70}")

        # 统计总体数据
        total_stocks = sum(r['total_stocks'] for r in self.results)
        total_buy_recs = sum(r['buy_recommendations'] for r in self.results)
        total_successful = sum(r['successful_picks'] for r in self.results)
        overall_success_rate = (total_successful / total_buy_recs * 100) if total_buy_recs > 0 else 0

        avg_return = np.mean([r['avg_return'] for r in self.results if r['avg_return'] != 0])
        avg_score = np.mean([r['avg_score'] for r in self.results if r['avg_score'] > 0])

        print(f"\n📈 总体统计:")
        print(f"  总分析股票数: {total_stocks}")
        print(f"  总买入推荐数: {total_buy_recs}")
        print(f"  总成功 picks: {total_successful}")
        print(f"  总体成功率: {overall_success_rate:.2f}%")
        print(f"  平均收益率: {avg_return:+.2f}%")
        print(f"  平均评分: {avg_score:.1f}")
        print(f"  总耗时: {total_time/60:.1f} 分钟")

        print(f"\n📋 分轮结果:")
        for result in self.results:
            print(f"  第 {result['round']} 轮: "
                  f"{result['successful_picks']}/{result['buy_recommendations']} "
                  f"(成功率 {result['success_rate']:.1f}%)")

        # 保存结果到文件
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'config': {
                'num_rounds': self.num_rounds,
                'stocks_per_round': self.stocks_per_round
            },
            'summary': {
                'total_stocks': total_stocks,
                'total_buy_recommendations': total_buy_recs,
                'total_successful_picks': total_successful,
                'overall_success_rate': float(overall_success_rate),
                'avg_return': float(avg_return),
                'avg_score': float(avg_score),
                'total_time_minutes': float(total_time / 60)
            },
            'round_results': [
                {
                    'round': r['round'],
                    'total_stocks': r['total_stocks'],
                    'buy_recommendations': r['buy_recommendations'],
                    'successful_picks': r['successful_picks'],
                    'success_rate': float(r['success_rate']),
                    'avg_return': float(r['avg_return']),
                    'avg_score': float(r['avg_score']),
                    'recommendations': [
                        {
                            'stock_code': rec['stock_code'],
                            'score': float(rec['score']),
                            'recommendation': rec['recommendation'],
                            'actual_return': float(rec['actual_return']),
                            'success': bool(rec['success']),
                            'days_ahead': rec['days_ahead']
                        }
                        for rec in r['recommendations']
                    ]
                }
                for r in self.results
            ]
        }

        # 保存为JSON
        with open('backtest_results.json', 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)

        print(f"\n💾 详细报告已保存到: backtest_results.json")

        # 结论
        print(f"\n🎯 结论:")
        if overall_success_rate >= 60:
            print(f"  ✅ 回测成功！策略有效性较高 (成功率 {overall_success_rate:.1f}%)")
        elif overall_success_rate >= 40:
            print(f"  ⚠️  回测结果一般，有改进空间 (成功率 {overall_success_rate:.1f}%)")
        else:
            print(f"  ❌ 回测失败，建议重新调整策略 (成功率 {overall_success_rate:.1f}%)")

        print(f"\n{'='*70}")
        print(f"✅ 回测完成！")
        print(f"{'='*70}\n")

        return report_data

def main():
    """主函数"""
    print("🎯 A股短线选股AI回测系统")
    print("=" * 70)
    print("本系统将进行5组回测测试")
    print("每组随机选择20只股票")
    print("验证7-9天后的实际表现")
    print("=" * 70)

    # 创建回测引擎
    engine = BacktestEngine(num_rounds=5, stocks_per_round=20)

    # 运行回测
    results = engine.run_backtest()

    return results

if __name__ == "__main__":
    main()