"""
回测系统股票选择扩展
为回测系统添加灵活的股票选择功能
"""
import sys
import os
sys.path.append('/Users/baldwin/PycharmProjects/ai-ticket')

from src.data.stock_selector import StockSelector, PRESET_CONFIGS
from src.data.fetcher import DataFetcher
from backtest_system import BacktestEngine


class EnhancedBacktestEngine(BacktestEngine):
    """增强版回测引擎 - 支持灵活股票选择"""

    def __init__(self, num_rounds: int = 5, stocks_per_round: int = 20, stock_selector=None):
        """
        初始化增强版回测引擎

        Args:
            num_rounds: 回测轮数
            stocks_per_round: 每轮分析的股票数量
            stock_selector: 股票选择器（可选）
        """
        super().__init__(num_rounds, stocks_per_round)
        self.stock_selector = stock_selector or StockSelector(selection_mode="top_n", max_results=stocks_per_round)

    def select_stocks_for_round(self, round_num: int) -> list:
        """
        为指定轮次选择股票

        Args:
            round_num: 回测轮次编号

        Returns:
            选中的股票代码列表
        """
        mode = self.stock_selector.selection_mode

        if mode == "custom":
            # 自定义股票列表
            selected_stocks = self.stock_selector.custom_stocks[:self.stocks_per_round]
        elif mode == "range":
            # 从代码范围中随机选择
            start, end = self.stock_selector.code_range
            selected_stocks = self._generate_random_codes_from_range(start, end, self.stocks_per_round)
        elif mode == "top_n":
            # 使用策略从股票池中选取（这里简化为随机选择）
            selected_stocks = self._generate_random_codes_from_range("000001", "999999", self.stocks_per_round)
            # 在实际应用中，这里会根据AI评分选择
        else:
            # 默认随机选择
            selected_stocks = [f"{random.randint(1, 999999):06d}" for _ in range(self.stocks_per_round)]

        print(f"📊 第 {round_num} 轮选择模式: {mode}")
        print(f"   选中 {len(selected_stocks)} 只股票")

        return selected_stocks[:self.stocks_per_round]

    def _generate_random_codes_from_range(self, start_code: str, end_code: str, count: int) -> list:
        """从指定范围随机生成股票代码"""
        start = int(start_code)
        end = int(end_code)
        codes = []

        for _ in range(count):
            code = random.randint(start, end)
            codes.append(f"{code:06d}")

        return list(set(codes))  # 去重

    def run_round_with_selector(self, round_num: int) -> dict:
        """
        使用股票选择器运行回测轮次

        Args:
            round_num: 轮次编号

        Returns:
            回测结果
        """
        print(f"\n{'='*70}")
        print(f"🔄 回测第 {round_num} 轮")
        print(f"{'='*70}")

        # 使用选择器选择股票
        selected_stocks = self.select_stocks_for_round(round_num)

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

        # 统计结果
        success_count = sum(1 for a, p in zip(analysis_results, actual_results) if a == p)
        success_rate = success_count / len(selected_stocks) * 100

        print(f"\n✅ 第 {round_num} 轮回测结果:")
        print(f"   总股票数: {len(selected_stocks)}")
        print(f"   预测成功: {success_count}")
        print(f"   成功率: {success_rate:.2f}%")

        round_result = {
            "round": round_num,
            "stocks": selected_stocks,
            "total_stocks": len(selected_stocks),
            "successful_predictions": success_count,
            "success_rate": success_rate,
            "selection_mode": self.stock_selector.selection_mode
        }

        self.results.append(round_result)
        return round_result

    def run_full_backtest_with_selector(self):
        """运行完整回测（使用股票选择器）"""
        print("\n" + "🚀" * 35)
        print("    增强版回测系统 - 灵活股票选择")
        print("🚀" * 35 + "\n")

        print(f"回测配置:")
        print(f"  轮数: {self.num_rounds}")
        print(f"  每轮股票数: {self.stocks_per_round}")
        print(f"  选择模式: {self.stock_selector.selection_mode}")

        start_time = time.time()

        for round_num in range(1, self.num_rounds + 1):
            self.run_round_with_selector(round_num)

        # 汇总结果
        total_stocks = sum(r["total_stocks"] for r in self.results)
        total_success = sum(r["successful_predictions"] for r in self.results)
        avg_success_rate = total_success / total_stocks * 100 if total_stocks > 0 else 0

        print(f"\n{'='*70}")
        print(f"📈 汇总回测结果")
        print(f"{'='*70}")
        print(f"总轮数: {self.num_rounds}")
        print(f"总股票数: {total_stocks}")
        print(f"总成功: {total_success}")
        print(f"平均成功率: {avg_success_rate:.2f}%")
        print(f"总耗时: {time.time() - start_time:.2f} 秒")

        # 按选择模式统计
        mode_stats = {}
        for result in self.results:
            mode = result["selection_mode"]
            if mode not in mode_stats:
                mode_stats[mode] = {"rounds": 0, "total_stocks": 0, "total_success": 0}
            mode_stats[mode]["rounds"] += 1
            mode_stats[mode]["total_stocks"] += result["total_stocks"]
            mode_stats[mode]["total_success"] += result["successful_predictions"]

        print(f"\n按选择模式统计:")
        for mode, stats in mode_stats.items():
            rate = stats["total_success"] / stats["total_stocks"] * 100 if stats["total_stocks"] > 0 else 0
            print(f"  {mode}: {stats['rounds']}轮, 成功率 {rate:.2f}%")

        return self.results


def demo_backtest_with_custom_selection():
    """演示：使用自定义股票列表进行回测"""
    print("\n" + "="*80)
    print("📊 演示 1: 使用自定义股票列表进行回测")
    print("="*80)

    # 创建自定义股票选择器
    selector = StockSelector(
        selection_mode="custom",
        custom_stocks=["000001", "000002", "600519", "600036", "000858"]
    )

    # 创建增强版回测引擎
    engine = EnhancedBacktestEngine(num_rounds=3, stocks_per_round=5, stock_selector=selector)

    # 运行回测
    results = engine.run_full_backtest_with_selector()

    return results


def demo_backtest_with_range_selection():
    """演示：使用代码范围选择进行回测"""
    print("\n" + "="*80)
    print("📊 演示 2: 使用蓝筹股范围（600000-600999）进行回测")
    print("="*80)

    # 创建蓝筹股范围选择器
    selector = StockSelector(
        selection_mode="range",
        code_range=("600000", "600999")
    )

    # 创建增强版回测引擎
    engine = EnhancedBacktestEngine(num_rounds=3, stocks_per_round=10, stock_selector=selector)

    # 运行回测
    results = engine.run_full_backtest_with_selector()

    return results


def demo_backtest_with_preset():
    """演示：使用预设配置进行回测"""
    print("\n" + "="*80)
    print("📊 演示 3: 使用预设配置（top10）进行回测")
    print("="*80)

    # 使用预设配置
    config = PRESET_CONFIGS["top10"]
    selector = StockSelector(**config)

    # 创建增强版回测引擎
    engine = EnhancedBacktestEngine(num_rounds=3, stocks_per_round=10, stock_selector=selector)

    # 运行回测
    results = engine.run_full_backtest_with_selector()

    return results


def main():
    """主函数"""
    print("\n" + "🎯" * 40)
    print("     回测系统股票选择功能演示")
    print("🎯" * 40 + "\n")

    try:
        # 演示1：自定义股票列表
        demo_backtest_with_custom_selection()

        # 演示2：代码范围选择
        demo_backtest_with_range_selection()

        # 演示3：预设配置
        demo_backtest_with_preset()

        print("\n" + "="*80)
        print("✅ 所有回测演示完成！")
        print("="*80)

        print("\n📌 总结:")
        print("1. 自定义列表：适用于分析特定关注的股票")
        print("2. 代码范围：适用于按板块分析（如蓝筹股等）")
        print("3. 预设配置：可快速切换常用配置")

    except Exception as e:
        print(f"\n❌ 演示过程中出现错误：{e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()