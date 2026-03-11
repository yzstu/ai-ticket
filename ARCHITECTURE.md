# A股短线选股AI系统 - 架构文档

## 项目概览

**名称:** ai-ticket  
**定位:** 基于AI的A股短线选股分析系统  
**技术栈:** FastAPI + LangChain + Ollama (Qwen) + akshare/yfinance

---

## 目录结构

```
ai-ticket/
├── main.py                    # FastAPI 主入口
├── run.py                     # 应用启动脚本
│
├── api/                       # 🌐 API 层
│   ├── routes/                # API 路由
│   │   ├── stocks.py          # 股票数据接口
│   │   ├── analysis.py        # 分析接口
│   │   ├── cache.py           # 缓存管理
│   │   ├── scheduler.py       # 定时任务
│   │   ├── backtest.py        # 回测接口
│   │   ├── sector.py          # 板块分析
│   │   ├── charts.py          # 图表接口
│   │   ├── tasks.py           # 异步任务
│   │   ├── websockets.py      # WebSocket 通信
│   │   └── system.py          # 系统状态
│   ├── deps.py                # 依赖注入
│   ├── models.py              # API 数据模型
│   └── validators.py          # 参数验证
│
├── src/                       # 📦 核心代码
│   ├── main.py                # CLI 入口（命令行分析）
│   │
│   ├── agents/                # 🤖 AI 智能体
│   │   ├── trading_agent.py       # 交易分析 Agent
│   │   └── cached_trading_agent.py # 缓存增强版
│   │
│   ├── analysis/              # 📊 分析模块
│   │   ├── quick_analyzer.py      # 快速分析器
│   │   └── technical_indicators.py # 技术指标计算
│   │
│   ├── data/                  # 💾 数据层
│   │   ├── fetchers/              # 数据获取
│   │   │   ├── fetcher.py             # 数据获取基类
│   │   │   ├── cached_fetcher.py      # 缓存数据获取
│   │   │   ├── parallel_analyzer.py   # 并行分析
│   │   │   └── stock_selector.py      # 股票选择器
│   │   ├── cache/                 # 缓存管理
│   │   │   ├── cache_manager.py       # 缓存管理器
│   │   │   └── cache_scheduler.py     # 缓存调度器
│   │   ├── adapters/             # 数据源适配器
│   │   │   ├── akshare_adapter.py     # akshare 适配器
│   │   │   └── yfinance_adapter.py    # yfinance 适配器
│   │   ├── backtest_database.py  # 回测数据库
│   │   ├── efficient_filter.py   # 高效过滤
│   │   ├── price_history.py     # 价格历史
│   │   └── sector_fetcher.py     # 板块数据
│   │
│   ├── async_tasks/           # ⚡ 异步任务系统
│   │   ├── task_executor.py      # 任务执行器
│   │   ├── task_manager.py       # 任务管理器
│   │   ├── task_store.py         # 任务存储
│   │   └── task_models.py        # 任务模型
│   │
│   ├── providers/             # 🔌 提供者层
│   │   ├── local_analyzer.py     # 本地分析提供者
│   │   ├── ml_models.py          # 机器学习模型
│   │   └── model_trainer.py      # 模型训练器
│   │
│   ├── strategy/              # 📈 策略模块
│   │   └── engine.py             # 策略引擎
│   │
│   ├── config/                # ⚙️ 配置模块
│   │   ├── settings.py           # 应用配置 (Pydantic Settings)
│   │   ├── constants.py          # 常量定义
│   │   └── model_config.py       # 模型配置
│   │
│   ├── utils/                 # 🛠️ 工具模块
│   │   ├── logger.py             # 统一日志
│   │   └── retry.py              # 重试机制
│   │
│   └── output/                # 📤 输出模块
│       └── formatter.py          # 格式化输出
│
├── tests/                     # 🧪 测试
│   ├── api/                   # API 测试
│   ├── data/                  # 数据层测试
│   ├── agents/                # Agent 测试
│   ├── conftest.py            # pytest fixtures
│   └── test_settings.py       # 配置测试示例
│
├── models/                    # 🧠 ML 模型文件
│   ├── random_forest.joblib   # 随机森林模型
│   ├── xgboost.json           # XGBoost 模型
│   └── feature_names.json     # 特征名称
│
├── static/                    # 🎨 静态资源
│   ├── css/
│   └── js/
│
├── configs/                   # 📁 配置文件
├── cache/                     # 💿 数据缓存
├── examples/                  # 📚 示例代码
├── docs/                      # 📖 文档
│
├── requirements.txt           # 依赖清单
└── .env                       # 环境变量
```

---

## 架构层次

```
┌─────────────────────────────────────────────────────────────┐
│                     API Layer (FastAPI)                      │
│  /api/stocks  /api/analysis  /api/cache  /api/tasks  ...    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     Service Layer                            │
│  AgentService │ DataService │ TaskService │ CacheService    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     Core Layer                               │
│  Agents (AI) │ Analysis │ Strategy │ Providers │ Output     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     Data Layer                               │
│  Fetchers │ Adapters │ Cache │ Async Tasks │ ML Models      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   External Services                          │
│  akshare │ yfinance │ Ollama (LLM) │ FileSystem              │
└─────────────────────────────────────────────────────────────┘
```

---

## 核心模块说明

### 1. API 层 (`api/`)

**职责:** HTTP 接口定义、参数验证、依赖注入

| 模块 | 功能 |
|------|------|
| `routes/stocks.py` | 股票列表、实时数据 |
| `routes/analysis.py` | 短线分析、AI 分析 |
| `routes/cache.py` | 缓存状态、清理 |
| `routes/scheduler.py` | 定时任务管理 |
| `routes/backtest.py` | 策略回测 |
| `routes/tasks.py` | 异步任务管理 |
| `routes/websockets.py` | 实时推送 |

### 2. Agent 层 (`src/agents/`)

**职责:** AI 智能体封装，调用 LLM 进行股票分析

| 模块 | 功能 |
|------|------|
| `trading_agent.py` | 基础交易 Agent，LLM 交互 |
| `cached_trading_agent.py` | 增强版，整合缓存机制 |

### 3. 数据层 (`src/data/`)

**职责:** 数据获取、缓存、预处理

| 模块 | 功能 |
|------|------|
| `akshare_adapter.py` | A股数据源 (主) |
| `yfinance_adapter.py` | Yahoo Finance (辅) |
| `cache_manager.py` | 缓存生命周期管理 |
| `parallel_analyzer.py` | 多线程并行分析 |
| `stock_selector.py` | 股票筛选逻辑 |

### 4. 异步任务 (`src/async_tasks/`)

**职责:** 后台任务调度与执行

| 模块 | 功能 |
|------|------|
| `task_manager.py` | 任务队列管理 |
| `task_executor.py` | 任务执行器 |
| `task_store.py` | 任务状态持久化 |

### 5. 分析模块 (`src/analysis/`)

**职责:** 技术指标计算、分析逻辑

| 模块 | 功能 |
|------|------|
| `technical_indicators.py` | MA、MACD、RSI 等 |
| `quick_analyzer.py` | 快速批量分析 |

### 6. 提供者 (`src/providers/`)

**职责:** 分析能力提供 (本地 LLM/ML)

| 模块 | 功能 |
|------|------|
| `local_analyzer.py` | 本地模型分析 |
| `ml_models.py` | ML 模型推理 |
| `model_trainer.py` | 模型训练工具 |

---

## 数据流

```
用户请求
    │
    ▼
┌─────────────┐
│  FastAPI    │ ← 参数验证
└─────────────┘
    │
    ▼
┌─────────────┐
│  API Route  │ ← 依赖注入
└─────────────┘
    │
    ▼
┌─────────────┐
│  Service    │ ← 业务逻辑
└─────────────┘
    │
    ├──────────────────┐
    ▼                  ▼
┌─────────┐      ┌──────────┐
│  Cache  │      │  Agent   │
└─────────┘      └──────────┘
    │                  │
    ▼                  ▼
┌─────────┐      ┌──────────┐
│ Adapter │      │  Ollama  │
└─────────┘      └──────────┘
    │
    ▼
┌─────────┐
│ akshare │
└─────────┘
```

---

## 配置管理

**文件:** `src/config/settings.py`

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `API_HOST` | `0.0.0.0` | 监听地址 |
| `API_PORT` | `8000` | 服务端口 |
| `OLLAMA_MODEL` | `qwen3-coder:480b-cloud` | LLM 模型 |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama 地址 |
| `CACHE_DIR` | `./cache` | 缓存目录 |
| `CACHE_TTL_HOURS` | `24` | 缓存有效期 |
| `MAX_WORKERS` | `0` (自动) | 并行工作线程 |

---

## 依赖关系

```
FastAPI ────┐
            ├──► uvicorn (ASGI)
langchain ──┤
            ├──► akshare (A股数据)
            │
            ├──► yfinance (国际市场)
            │
            ├──► pandas/numpy (数据处理)
            │
            └──► apscheduler (定时任务)
```

---

## 启动方式

```bash
# 安装依赖
pip install -r requirements.txt

# 开发模式
python run.py

# 或直接运行
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 已完成的优化 ✅

| 优化项 | 状态 | 说明 |
|--------|------|------|
| 模块解耦 | ✅ | `src/data/` 已拆分为 `fetchers/` + `cache/` + `adapters/` |
| 配置统一 | ✅ | 使用 Pydantic Settings 重构，支持 `.env` 自动加载 |
| 测试结构 | ✅ | 创建 `tests/` 目录结构，含 conftest.py 和示例测试 |
| 日志规范 | ✅ | 创建 `src/utils/logger.py` 统一日志系统 |
| API 文档 | 📋 | 待补充 OpenAPI 示例 |

---

## 更新日志

**2026-03-11:** 项目架构优化
- 重构 `src/data/` 目录结构
- 统一配置管理
- 添加测试目录框架
- 规范化日志系统

_生成时间: 2026-03-11_