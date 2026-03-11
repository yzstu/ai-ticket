# 股票选择功能优化说明

## 概述

本次优化为股票选择系统增加了灵活性，支持多种股票选择方式，不再局限于固定的前N只股票选择。

## 新增功能

### 1. 多种选择模式

#### 1.1 Top-N 模式（默认）
```python
from src.data.stock_selector import StockSelector

selector = StockSelector(selection_mode="top_n", max_results=10)
```

#### 1.2 自定义股票列表
```python
selector = StockSelector(
    selection_mode="custom",
    custom_stocks=["000001", "000002", "600519", "600036", "000858"]
)
```

#### 1.3 代码范围选择
```python
# 分析600000-600999的蓝筹股
selector = StockSelector(
    selection_mode="range",
    code_range=("600000", "600999")
)

# 分析000001-000999的深市股票
selector = StockSelector(
    selection_mode="range",
    code_range=("000001", "000999")
)
```

#### 1.4 分析所有股票
```python
selector = StockSelector(selection_mode="all")
```

### 2. 通过环境变量配置

#### 2.1 Top-N 模式
```bash
export STOCK_SELECTION_MODE="top_n"
export MAX_STOCKS="5"
```

#### 2.2 自定义列表
```bash
export STOCK_SELECTION_MODE="custom"
export CUSTOM_STOCKS="000001,000002,600519,600036,000858"
```

#### 2.3 代码范围
```bash
export STOCK_SELECTION_MODE="range"
export CODE_RANGE_START="600000"
export CODE_RANGE_END="600999"
```

#### 2.4 所有股票
```bash
export STOCK_SELECTION_MODE="all"
```

### 3. 使用预设配置

```python
from src.data.stock_selector import PRESET_CONFIGS

# 使用预设配置
config = PRESET_CONFIGS["top5"]  # 或 top10, tech_stocks, blue_chips, custom_list
selector = StockSelector(**config)
```

### 4. 从配置文件加载

```python
from src.data.stock_selector import StockSelector

# 从JSON文件加载
selector = StockSelector.from_file("configs/stock_selection_examples.json")
```

## 代码修改说明

### 1. 新增文件

- `src/data/stock_selector.py` - 股票选择器核心类
- `configs/stock_selection_examples.json` - 配置示例
- `examples/stock_selection_demo.py` - 演示脚本

### 2. 修改文件

#### 2.1 `src/data/efficient_filter.py`

**修改内容：**
- 添加 `StockSelector` 导入
- `__init__` 方法增加 `stock_selector` 参数
- `stage2_ai_filter` 方法使用股票选择器替代硬编码的 `max_results`

**关键变更：**
```python
# 之前：
top_stocks = scored_stocks[:max_results]

# 现在：
top_stocks = self.stock_selector.filter_stocks(
    scored_stocks,
    scored_stocks=scored_stocks
)
```

#### 2.2 `src/agents/trading_agent.py`

**修改内容：**
- 添加 `StockSelector` 和 `create_selector_from_env` 导入
- `run_daily_analysis` 函数增加 `stock_selector` 参数
- 替代硬编码的 `top_stocks = results[:5]`

**关键变更：**
```python
# 之前：
results.sort(key=lambda x: x["score"], reverse=True)
top_stocks = results[:5]

# 现在：
results.sort(key=lambda x: x["score"], reverse=True)
if stock_selector.selection_mode == "top_n":
    final_results = results[:stock_selector.max_results]
else:
    final_results = results
```

## 使用示例

### 示例1：分析特定股票

```python
from src.agents.trading_agent import run_daily_analysis
from src.data.stock_selector import StockSelector

# 创建自定义股票选择器
selector = StockSelector(
    selection_mode="custom",
    custom_stocks=["000001", "600519", "600036"]
)

# 运行分析
result = run_daily_analysis(stock_selector=selector)
print(f"推荐股票：{result['recommended_stocks']}")
```

### 示例2：分析蓝筹股板块

```python
# 分析600000-600999的蓝筹股
selector = StockSelector(
    selection_mode="range",
    code_range=("600000", "600999")
)

result = run_daily_analysis(stock_selector=selector, max_stocks_to_analyze=100)
```

### 示例3：使用环境变量快速切换

```bash
# 在shell中设置
export STOCK_SELECTION_MODE="custom"
export CUSTOM_STOCKS="000001,000002,600519"

# Python代码中直接使用
from src.agents.trading_agent import run_daily_analysis
from src.data.stock_selector import create_selector_from_env

selector = create_selector_from_env()
result = run_daily_analysis(stock_selector=selector)
```

## 配置选项说明

| 参数 | 说明 | 示例 |
|------|------|------|
| `selection_mode` | 选择模式 | "top_n", "custom", "range", "all" |
| `custom_stocks` | 自定义股票代码列表 | ["000001", "600519"] |
| `code_range` | 代码范围 | ("600000", "600999") |
| `max_results` | 最大结果数量 | 10 |

## 常见股票代码范围参考

| 板块 | 代码范围 | 说明 |
|------|----------|------|
| 深市主板 | 000001-000999 | 深市主板股票 |
| 创业板 | 300001-300999 | 创业板股票 |
| 沪市主板 | 600000-600999 | 沪市主板股票 |
| 科创板 | 688001-688999 | 科创板股票 |

## 运行演示

```bash
cd /Users/baldwin/PycharmProjects/ai-ticket
python examples/stock_selection_demo.py
```

## 注意事项

1. **性能考虑**：自定义列表和范围选择可以显著减少分析时间
2. **数据完整性**：确保自定义股票代码格式正确（6位数字）
3. **向后兼容**：原有代码通过环境变量仍可正常工作
4. **灵活组合**：可以根据需要组合使用不同的选择模式

## 下一步改进建议

1. 添加更多预设板块配置（如行业分类）
2. 支持多个范围组合选择
3. 添加动态股票池管理
4. 集成更多市场数据源

---

📌 **快速开始**：使用 `examples/stock_selection_demo.py` 快速体验所有功能！