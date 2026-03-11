"""
股票选择功能演示脚本
展示如何使用新的灵活股票选择功能
"""
import os
import sys
sys.path.append('/Users/baldwin/PycharmProjects/ai-ticket')

from src.data.stock_selector import (
    StockSelector,
    create_selector_from_env,
    PRESET_CONFIGS
)
from src.agents.trading_agent import run_daily_analysis
import json


def demo_top_n_selection():
    """演示 Top-N 选择模式"""
    print("=" * 80)
    print("📊 演示 1: Top-N 选择模式（选择评分最高的前5只股票）")
    print("=" * 80)

    selector = StockSelector(selection_mode="top_n", max_results=5)
    print(f"配置：{json.dumps(selector.get_config_summary(), indent=2, ensure_ascii=False)}")

    # 可以直接在run_daily_analysis中使用
    result = run_daily_analysis(stock_selector=selector, max_stocks_to_analyze=500)
    print(f"\n✅ 结果：")
    print(f"   筛选出 {result['total_recommended']} 只股票")
    for stock in result['recommended_stocks']:
        print(f"   {stock['code']} {stock['name']} - 评分: {stock['score']:.2f}")

    return result


def demo_custom_stocks_selection():
    """演示自定义股票列表模式"""
    print("\n" + "=" * 80)
    print("📊 演示 2: 自定义股票列表模式（分析指定股票）")
    print("=" * 80)

    custom_stocks = ["000001", "000002", "600519", "600036", "000858"]
    selector = StockSelector(selection_mode="custom", custom_stocks=custom_stocks)
    print(f"配置：{json.dumps(selector.get_config_summary(), indent=2, ensure_ascii=False)}")

    result = run_daily_analysis(stock_selector=selector)
    print(f"\n✅ 结果：")
    print(f"   筛选出 {result['total_recommended']} 只股票")
    for stock in result['recommended_stocks']:
        print(f"   {stock['code']} {stock['name']} - 评分: {stock['score']:.2f}")

    return result


def demo_range_selection():
    """演示代码范围选择模式"""
    print("\n" + "=" * 80)
    print("📊 演示 3: 代码范围选择模式（分析600000-600999蓝筹股）")
    print("=" * 80)

    selector = StockSelector(selection_mode="range", code_range=("600000", "600999"))
    print(f"配置：{json.dumps(selector.get_config_summary(), indent=2, ensure_ascii=False)}")

    result = run_daily_analysis(stock_selector=selector, max_stocks_to_analyze=100)
    print(f"\n✅ 结果：")
    print(f"   筛选出 {result['total_recommended']} 只股票")
    for stock in result['recommended_stocks']:
        print(f"   {stock['code']} {stock['name']} - 评分: {stock['score']:.2f}")

    return result


def demo_env_variable_selection():
    """演示通过环境变量配置"""
    print("\n" + "=" * 80)
    print("📊 演示 4: 通过环境变量配置（使用预设配置）")
    print("=" * 80)

    # 设置环境变量
    os.environ['STOCK_SELECTION_MODE'] = 'custom'
    os.environ['CUSTOM_STOCKS'] = '000001,600519,600036,000858'

    # 从环境变量创建选择器
    selector = create_selector_from_env()
    print(f"配置：{json.dumps(selector.get_config_summary(), indent=2, ensure_ascii=False)}")

    result = run_daily_analysis(stock_selector=selector)
    print(f"\n✅ 结果：")
    print(f"   筛选出 {result['total_recommended']} 只股票")
    for stock in result['recommended_stocks']:
        print(f"   {stock['code']} {stock['name']} - 评分: {stock['score']:.2f}")

    return result


def demo_preset_configs():
    """演示预设配置"""
    print("\n" + "=" * 80)
    print("📊 演示 5: 使用预设配置（top5）")
    print("=" * 80)

    preset_name = "top5"
    config = PRESET_CONFIGS[preset_name]
    print(f"预设配置名称：{preset_name}")
    print(f"配置详情：{json.dumps(config, indent=2, ensure_ascii=False)}")

    selector = StockSelector(**config)
    print(f"选择器配置：{json.dumps(selector.get_config_summary(), indent=2, ensure_ascii=False)}")

    result = run_daily_analysis(stock_selector=selector, max_stocks_to_analyze=500)
    print(f"\n✅ 结果：")
    print(f"   筛选出 {result['total_recommended']} 只股票")
    for stock in result['recommended_stocks']:
        print(f"   {stock['code']} {stock['name']} - 评分: {stock['score']:.2f}")

    return result


def main():
    """主演示函数"""
    print("\n" + "🎯" * 40)
    print("        股票选择功能演示")
    print("     灵活的自定义选择方案")
    print("🎯" * 40 + "\n")

    try:
        # 演示1: Top-N 选择
        demo_top_n_selection()

        # 演示2: 自定义股票列表
        demo_custom_stocks_selection()

        # 演示3: 代码范围选择
        demo_range_selection()

        # 演示4: 环境变量配置
        demo_env_variable_selection()

        # 演示5: 预设配置
        demo_preset_configs()

        print("\n" + "=" * 80)
        print("✅ 所有演示完成！")
        print("=" * 80)

        print("\n📌 使用说明：")
        print("1. Top-N 模式：适用于快速筛选最佳股票")
        print("2. 自定义列表：适用于分析特定关注的股票")
        print("3. 代码范围：适用于按板块分析（如蓝筹股、科技股等）")
        print("4. 环境变量：便于通过配置快速切换模式")
        print("5. 预设配置：常用的配置可以直接使用")

    except Exception as e:
        print(f"\n❌ 演示过程中出现错误：{e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()