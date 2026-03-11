# 股票选择功能 - 快速上手

## 🎯 功能亮点

现在你可以灵活选择股票，不再局限于固定的前N只！

### ✨ 四种选择模式

1. **自定义股票列表** - 分析指定股票
2. **代码范围选择** - 按板块分析（如蓝筹股、科技股）
3. **Top-N 评分** - 自动筛选最佳股票
4. **全市场分析** - 扫描所有股票

## 🚀 快速开始

### 方式1：5秒快速体验
```bash
python quick_demo.py
```

### 方式2：测试所有功能
```bash
python test_stock_selection.py
```

### 方式3：完整功能演示
```bash
python examples/stock_selection_demo.py
```

## 💡 使用示例

### 示例1：分析特定股票
```python
from src.agents.trading_agent import run_daily_analysis
from src.data.stock_selector import StockSelector

# 创建自定义股票列表
selector = StockSelector(
    selection_mode="custom",
    custom_stocks=["000001", "600519", "600036", "000858"]
)

# 运行分析
result = run_daily_analysis(stock_selector=selector)
```

### 示例2：分析蓝筹股板块
```python
selector = StockSelector(
    selection_mode="range",
    code_range=("600000", "600999")
)
result = run_daily_analysis(stock_selector=selector)
```

### 示例3：使用环境变量
```bash
export STOCK_SELECTION_MODE="custom"
export CUSTOM_STOCKS="000001,600519,600036,000858"
```
```python
from src.data.stock_selector import create_selector_from_env
selector = create_selector_from_env()
result = run_daily_analysis(stock_selector=selector)
```

## 📊 常用代码范围

| 板块 | 代码范围 | 说明 |
|------|----------|------|
| 深市主板 | 000001-000999 | A股主板 |
| 创业板 | 300001-300999 | 创业板 |
| 沪市主板 | 600000-600999 | 蓝筹股 |
| 科创板 | 688001-688999 | 科创板 |

## 🎮 预设配置

```python
from src.data.stock_selector import PRESET_CONFIGS

# 使用预设配置
config = PRESET_CONFIGS["top5"]  # 或 top10, tech_stocks, blue_chips
selector = StockSelector(**config)
```

## 📁 文件结构

```
ai-ticket/
├── src/data/
│   └── stock_selector.py          # 核心选择器类
├── examples/
│   ├── stock_selection_demo.py    # 主功能演示
│   └── backtest_enhanced_demo.py  # 回测系统演示
├── configs/
│   └── stock_selection_examples.json  # 配置示例
├── docs/
│   └── stock_selection_optimization.md  # 详细文档
├── test_stock_selection.py        # 测试脚本
├── quick_demo.py                  # 快速演示
└── OPTIMIZATION_SUMMARY.md        # 完整总结
```

## ✅ 验证功能

所有测试通过：
- ✅ 4种选择模式
- ✅ 环境变量配置
- ✅ 预设配置
- ✅ 向后兼容

## 📚 详细文档

- `OPTIMIZATION_SUMMARY.md` - 完整功能总结
- `docs/stock_selection_optimization.md` - 详细使用文档

---

🎉 **现在就开始体验吧！** 运行 `python quick_demo.py` 查看所有功能演示。