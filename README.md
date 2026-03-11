# A-Share Short-term Trading AI Agent

An AI-powered trading agent for Chinese A-share market that identifies short-term trading opportunities using technical analysis, market sentiment, and capital flow data.

## Features

- **Multi-factor Analysis**: Combines technical indicators, market sentiment, and capital flow
- **Risk Control**: Filters out ST stocks and high-volatility stocks
- **Local LLM Integration**: Uses Ollama for natural language explanations (no API fees)
- **Multiple Output Formats**: JSON, Markdown tables, detailed reports

## Architecture

```
┌─────────────────┐       ┌─────────────────┐       ┌────────────────────┐
│                 │       │                 │       │                    │
│   Data Fetcher  ├───────┤ Strategy Engine ├───────┤ Local Analyzer     │
│                 │       │                 │       │ (Ollama + ML/DL)   │
└───────▲───────┬─┘       └────────┬────────┘       └───────┬────────────┘
        │       │                  │                        │
        │       │                  │                        │
┌───────┴───────▼──────┐    ┌──────▼──────┐          ┌──────▼──────┐
│ External Data Sources│    │ Risk Control│          │ Output      │
│ (akshare/yfinance)   │    │ Rules Engine│          │ Formatter   │
└──────────────────────┘    └─────────────┘          └─────────────┘
```

## Installation

1. **Install Ollama**:
   ```bash
   curl -fsSL https://ollama.ai/install.sh | sh
   ollama pull qwen3-coder:480b-cloud
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

## Usage

### Daily Analysis
```bash
python src/main.py
```

### Output Formats
```bash
# Markdown table (default)
python src/main.py markdown

# JSON output
python src/main.py json

# Detailed report
python src/main.py detailed

# Trading recommendations
python src/main.py recommendations
```

## Project Structure

```
src/
├── agents/          # Trading agent orchestrator
├── data/            # Data fetching and filtering
├── strategy/        # Strategy engine
├── tools/           # LangChain tools
├── output/          # Output formatting
├── providers/       # Local AI providers (Ollama)
└── main.py          # Entry point
```

## Dependencies

- Python 3.13+
- Ollama (local LLM)
- LangChain 0.2+
- Pandas & NumPy
- Optional: akshare, yfinance (for real data)

## Configuration

Environment variables:
- `OLLAMA_URL`: Ollama service URL (default: http://localhost:11434)
- `OLLAMA_MODEL`: Model name (default: qwen3-coder:480b-cloud)
- `TUSHARE_TOKEN`: Tushare token for real market data (optional)
- `LOG_LEVEL`: Logging level (default: INFO)

## Risk Control Rules

1. **Stock Filtering**:
   - Exclude ST/*ST stocks
   - Exclude stocks with daily change > 8%
   - Exclude stocks with < 1 billion market cap

2. **Position Management**:
   - Maximum 5 stocks per day
   - Position sizing based on volatility
   - Daily portfolio exposure cap at 80%

3. **Loss Control**:
   - Stop loss at -5% from entry
   - Maximum holding period 3 days
   - Daily loss limit 3% of portfolio value

## Local AI Features

- **Zero API Costs**: Uses local Ollama models
- **Multiple Model Support**: Qwen3 Coder, DeepSeek V3, GLM-4, etc.
- **Multi-model Fusion**: Combines LLM, ML, and DL models
- **Fast Response**: Local processing for quick analysis
- **Data Privacy**: Complete data locality

## Documentation Index

### 📚 Core Documentation

#### Data Flow
- **DATA_FLOW.md** - Complete data processing flow documentation
- **DATA_PROCESSING_SUMMARY.md** - Data flow summary with examples
- **ASCII_FLOW.md** - ASCII flow diagrams (text-based)
- **MERMAID_FLOW.md** - Mermaid flow diagrams (GitHub compatible)

#### Stock Selection
- **OPTIMIZATION_SUMMARY.md** - Stock selection optimization summary
- **QUICKSTART.md** - Quick start guide for stock selection

#### Parallel Analysis
- **PARALLEL_OPTIMIZATION.md** - Parallel analysis optimization guide
- **PARALLEL_QUICKSTART.md** - 5-minute quick start for parallel analysis

### 🎬 Examples & Demos

#### Stock Selection
```bash
# Complete demo
python examples/stock_selection_demo.py

# Quick demo
python quick_demo.py

# Tests
python test_stock_selection.py
```

#### Parallel Analysis
```bash
# Performance demo
python examples/parallel_analysis_demo.py

# Auto configuration
python setup_parallel.py

# Tests
python test_parallel_analysis.py
```

#### Backtesting
```bash
# Run backtest
python backtest_system.py

# Enhanced demo
python examples/backtest_enhanced_demo.py
```

### ⚙️ Configuration

#### Environment Variables
```bash
# Enable parallel analysis
export ENABLE_PARALLEL_ANALYSIS="true"
export PARALLEL_WORKERS="8"
export THREAD_TIMEOUT="30"
export BATCH_SIZE="100"

# Stock selection mode
export STOCK_SELECTION_MODE="custom"
export CUSTOM_STOCKS="000001,600519,600036"
```

### 🚀 Quick Start

#### Basic Usage
```python
from src.agents.trading_agent import run_daily_analysis
from src.data.stock_selector import StockSelector

# Custom stock list
selector = StockSelector(
    selection_mode="custom",
    custom_stocks=["600519", "000001", "600036"]
)

# Run with parallel analysis
result = run_daily_analysis(
    stock_selector=selector,
    use_parallel=True,
    max_workers=8
)

print(f"Recommended stocks: {result['total_recommended']}")
```

#### Blue-Chip Analysis
```python
# Analyze blue-chip stocks (600000-600999)
selector = StockSelector(
    selection_mode="range",
    code_range=("600000", "600999")
)

result = run_daily_analysis(
    stock_selector=selector,
    use_parallel=True,
    max_workers=16,
    batch_size=200
)
```

### 📊 Key Performance Metrics

- **Screening Efficiency**: 5000 → 500 (rule-based) → 50 (AI) → 5-10 (recommended)
- **Parallel Speedup**: 4-5x faster
- **Backtest Success Rate**: 60-70%

### 🎓 Learning Path

1. **Beginner**: Read `QUICKSTART.md` → Run `python quick_demo.py`
2. **Intermediate**: Read `DATA_FLOW.md` → Run `examples/stock_selection_demo.py`
3. **Advanced**: Read `PARALLEL_OPTIMIZATION.md` → Use `python setup_parallel.py`

### 🔍 Common Use Cases

#### Analyze Specific Stocks
```python
selector = StockSelector(
    selection_mode="custom",
    custom_stocks=["600519", "000001", "600036"]
)
```

#### Analyze Sector (e.g., Blue-Chips)
```python
selector = StockSelector(
    selection_mode="range",
    code_range=("600000", "600999")
)
```

#### High-Performance Configuration
```python
result = run_daily_analysis(
    stock_selector=selector,
    use_parallel=True,
    max_workers=16,          # 16 threads
    thread_timeout=45,       # 45s timeout
    batch_size=200,          # Large batches
    max_stocks_to_analyze=1000
)
```

### 📞 Support

- **Documentation**: Check README.md sections above
- **Examples**: Run scripts in `examples/` directory
- **Tests**: Run test suites in `test_*.py` files

For more details, see:
- `docs/stock_selection_optimization.md`
- `docs/parallel_analysis_config.md`