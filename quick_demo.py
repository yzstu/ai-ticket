#!/usr/bin/env python3
"""
快速演示：股票选择功能
"""
import sys
import os
sys.path.append('/Users/baldwin/PycharmProjects/ai-ticket')

from src.data.stock_selector import StockSelector

print("🎯" * 40)
print("    股票选择功能快速演示")
print("🎯" * 40 + "\n")

# 演示1：自定义股票列表
print("1️⃣ 自定义股票列表模式")
print("-" * 60)
selector = StockSelector(
    selection_mode="custom",
    custom_stocks=["000001", "000002", "600519", "600036", "000858"]
)
print(f"配置：{selector.get_config_summary()}")

# 演示2：代码范围选择（蓝筹股）
print("\n2️⃣ 代码范围模式（蓝筹股）")
print("-" * 60)
selector = StockSelector(
    selection_mode="range",
    code_range=("600000", "600999")
)
print(f"配置：{selector.get_config_summary()}")

# 演示3：Top-N模式
print("\n3️⃣ Top-N模式")
print("-" * 60)
selector = StockSelector(selection_mode="top_n", max_results=5)
print(f"配置：{selector.get_config_summary()}")

# 演示4：环境变量方式
print("\n4️⃣ 环境变量配置")
print("-" * 60)
os.environ['STOCK_SELECTION_MODE'] = 'custom'
os.environ['CUSTOM_STOCKS'] = '000001,600519,600036'
from src.data.stock_selector import create_selector_from_env
selector = create_selector_from_env()
print(f"配置：{selector.get_config_summary()}")

# 演示5：预设配置
print("\n5️⃣ 预设配置")
print("-" * 60)
from src.data.stock_selector import PRESET_CONFIGS
config = PRESET_CONFIGS["top5"]
selector = StockSelector(**config)
print(f"使用预设配置 'top5'：")
print(f"配置：{selector.get_config_summary()}")

print("\n" + "="*60)
print("✅ 演示完成！所有模式均可正常使用")
print("="*60)
print("\n📚 详细文档请查看：")
print("  - OPTIMIZATION_SUMMARY.md")
print("  - docs/stock_selection_optimization.md")
print("\n🎬 完整演示请运行：")
print("  - python examples/stock_selection_demo.py")