# A股短线选股AI系统 - FastAPI服务使用指南

## 📖 概述

FastAPI服务提供了RESTful API接口，让你可以轻松调用股票分析功能。服务包含以下主要功能：

- 📊 股票数据获取 - 获取股票列表、日线数据、资金流向、市场情绪
- 🤖 智能股票分析 - AI驱动的股票分析，支持多种选择模式
- 💾 数据缓存管理 - 高效的本地缓存系统
- ⏰ 定时任务调度 - 自动化的数据缓存和清理

## 🚀 快速开始

### 1. 启动服务

```bash
# 安装依赖
pip install -r requirements.txt

# 启动服务
python run.py --host 0.0.0.0 --port 8000 --reload

# 或者使用uvicorn直接启动
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

服务启动后，访问：
- **API文档**: http://localhost:8000/docs
- **ReDoc文档**: http://localhost:8000/redoc
- **健康检查**: http://localhost:8000/system/health

### 2. 基本使用示例

#### 获取股票列表

```bash
curl -X GET "http://localhost:8000/stocks/list"
```

#### 执行股票分析

```bash
curl -X POST "http://localhost:8000/analysis/daily" \
  -H "Content-Type: application/json" \
  -d '{
    "selection_mode": "top_n",
    "max_results": 10,
    "use_parallel": true,
    "use_cache": true
  }'
```

## 📚 API端点详解

### 股票数据 API (`/stocks`)

| 方法 | 端点 | 描述 |
|------|------|------|
| GET | `/stocks/list` | 获取所有股票列表 |
| GET | `/stocks/{code}/daily` | 获取单只股票日线数据 |
| GET | `/stocks/{code}/capital-flow` | 获取资金流向数据 |
| GET | `/stocks/{code}/sentiment` | 获取市场情绪数据 |
| GET | `/stocks/info/{code}` | 获取股票基本信息 |
| POST | `/stocks/batch/daily` | 批量获取股票数据 |

#### 示例：获取股票列表

```python
import requests

response = requests.get("http://localhost:8000/stocks/list")
stocks = response.json()
print(f"股票数量: {len(stocks)}")
for stock in stocks[:5]:
    print(f"{stock['code']}: {stock['name']}")
```

#### 示例：获取单只股票数据

```python
response = requests.get(
    "http://localhost:8000/stocks/600519/daily",
    params={"days": 30, "use_cache": True}
)
data = response.json()
print(f"数据记录数: {data['data_count']}")
```

### 股票分析 API (`/analysis`)

| 方法 | 端点 | 描述 |
|------|------|------|
| POST | `/analysis/daily` | 执行每日股票分析 |
| GET | `/analysis/top` | 获取Top-N推荐股票 |
| GET | `/analysis/sector/{sector}` | 分析指定板块股票 |
| GET | `/analysis/custom` | 分析自定义股票列表 |

#### 支持的板块代码

- `blue_chips`: 蓝筹股 (600000-600999)
- `tech_stocks`: 科技股 (000001-000999)
- `growth_stocks`: 创业板 (300001-300999)
- `kechuang`: 科创板 (688001-688999)

#### 示例：分析Top-N股票

```python
response = requests.post(
    "http://localhost:8000/analysis/daily",
    json={
        "selection_mode": "top_n",
        "max_results": 10,
        "use_parallel": True,
        "max_workers": 8,
        "use_cache": True
    }
)
result = response.json()
print(f"推荐股票数: {result['data']['total_recommended']}")
```

#### 示例：分析自定义股票列表

```python
response = requests.get(
    "http://localhost:8000/analysis/custom",
    params={
        "stock_codes": "600519,000001,600036,000858",
        "use_parallel": True
    }
)
result = response.json()
for stock in result['data']['recommended_stocks']:
    print(f"{stock['code']}: {stock['score']:.2f} - {stock['recommendation']}")
```

#### 示例：分析蓝筹股板块

```python
response = requests.get(
    "http://localhost:8000/analysis/sector/blue_chips",
    params={"n": 20, "use_parallel": True}
)
result = response.json()
print(f"板块: {result['data']['sector']}")
print(f"代码范围: {result['data']['code_range']}")
```

### 缓存管理 API (`/cache`)

| 方法 | 端点 | 描述 |
|------|------|------|
| GET | `/cache/stats` | 获取缓存统计信息 |
| POST | `/cache/cleanup` | 清理过期缓存 |
| POST | `/cache/export` | 导出缓存数据 |
| DELETE | `/cache/clear` | 清空所有缓存 |
| GET | `/cache/info` | 获取缓存配置信息 |
| GET | `/cache/health` | 检查缓存系统健康状态 |

#### 示例：查看缓存统计

```python
response = requests.get("http://localhost:8000/cache/stats")
stats = response.json()
print(f"命中率: {stats['cache_hit_rate']:.1f}%")
print(f"总请求: {stats['total_requests']}")
print(f"数据库大小: {stats['db_size_mb']} MB")
```

#### 示例：清理过期缓存

```python
response = requests.post(
    "http://localhost:8000/cache/cleanup",
    json={"dry_run": False}
)
result = response.json()
print(f"删除了 {result['deleted_count']} 条记录")
```

### 定时任务 API (`/scheduler`)

| 方法 | 端点 | 描述 |
|------|------|------|
| POST | `/scheduler/start` | 启动定时缓存任务 |
| POST | `/scheduler/stop` | 停止定时任务 |
| GET | `/scheduler/status` | 获取调度器状态 |
| GET | `/scheduler/stats` | 获取调度器统计 |
| POST | `/scheduler/manual-cache` | 手动执行缓存 |
| GET | `/scheduler/jobs` | 获取调度任务列表 |
| GET | `/scheduler/config` | 获取调度器配置 |

#### 示例：启动定时任务

```python
response = requests.post(
    "http://localhost:8000/scheduler/start",
    json={
        "config": {
            "cache_time": "16:30",
            "cleanup_time": "02:00",
            "batch_size": 100,
            "max_workers": 8
        }
    }
)
result = response.json()
print(f"任务ID: {result['data']['scheduler_id']}")
```

#### 示例：手动执行缓存

```python
response = requests.post(
    "http://localhost:8000/scheduler/manual-cache",
    json={
        "stock_codes": ["600519", "000001", "600036"],
        "batch_size": 50,
        "max_workers": 4
    }
)
result = response.json()
print(f"成功缓存: {result['cached_stocks']}")
```

### 系统管理 API (`/system`)

| 方法 | 端点 | 描述 |
|------|------|------|
| GET | `/system/health` | 系统健康检查 |
| GET | `/system/info` | 获取系统信息 |
| GET | `/system/version` | 获取系统版本 |
| GET | `/system/metrics` | 获取性能指标 |
| GET | `/system/logs` | 获取系统日志 |
| GET | `/system/config` | 获取系统配置 |

#### 示例：健康检查

```python
response = requests.get("http://localhost:8000/system/health")
health = response.json()
print(f"状态: {health['status']}")
for service, status in health['services'].items():
    print(f"  {service}: {status}")
```

## 📊 请求/响应示例

### 分析请求示例

```json
{
  "selection_mode": "top_n",
  "max_results": 10,
  "custom_stocks": ["600519", "000001", "600036"],
  "use_parallel": true,
  "max_workers": 8,
  "thread_timeout": 30,
  "batch_size": 100,
  "use_cache": true
}
```

### 分析响应示例

```json
{
  "success": true,
  "data": {
    "date": "2026-02-08",
    "recommended_stocks": [
      {
        "code": "600519",
        "name": "贵州茅台",
        "score": 85.5,
        "recommendation": "买入",
        "technical_score": 82.0,
        "sentiment_score": 70.0,
        "capital_score": 75.0,
        "price": 1680.50,
        "volume_increase": 35.2,
        "rsi": 58.3,
        "explanation": "综合评分: 85.5, 建议: 买入"
      }
    ],
    "total_analyzed": 500,
    "total_recommended": 10,
    "analysis_type": "parallel",
    "cache_enabled": true,
    "cache_stats": {
      "cache_hit_rate": 95.5,
      "total_requests": 500
    }
  }
}
```

## 🔧 配置选项

### 环境变量

| 变量名 | 默认值 | 描述 |
|--------|--------|------|
| `ENV` | development | 运行环境 (development/production) |
| `CACHE_DIR` | ./cache | 缓存目录 |
| `CACHE_TIME` | 16:30 | 定时缓存时间 |
| `CLEANUP_TIME` | 02:00 | 定时清理时间 |
| `BATCH_SIZE` | 100 | 批处理大小 |
| `MAX_WORKERS` | 8 | 最大工作线程数 |

### 启动参数

```bash
python run.py \
  --host 0.0.0.0 \
  --port 8000 \
  --reload \
  --workers 4 \
  --log-level info \
  --env production \
  --cache-dir ./cache
```

## 📈 性能优化建议

### 1. 启用缓存

始终启用缓存以获得最佳性能：

```json
{
  "use_cache": true
}
```

### 2. 使用并行分析

对于大量股票分析，启用并行处理：

```json
{
  "use_parallel": true,
  "max_workers": 8,
  "batch_size": 200
}
```

### 3. 合理设置批处理大小

- 小数据集 (<100只): batch_size=50
- 中数据集 (100-500只): batch_size=100
- 大数据集 (>500只): batch_size=200

### 4. 监控缓存命中率

定期检查缓存统计：

```bash
curl -X GET "http://localhost:8000/cache/stats"
```

理想命中率 > 90%

## 🐳 Docker部署（可选）

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### docker-compose.yml

```yaml
version: '3.8'

services:
  stock-ai-api:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./cache:/app/cache
    environment:
      - ENV=production
      - CACHE_DIR=/app/cache
    restart: unless-stopped
```

### 启动Docker

```bash
docker-compose up -d
```

## 🔐 安全建议

### 1. 生产环境配置

- 设置 `ENV=production`
- 限制CORS允许的域名
- 使用HTTPS（通过反向代理）
- 启用日志记录和监控

### 2. API密钥管理

如需身份验证，可以使用以下方案：

- API Key认证
- JWT Token认证
- OAuth2认证

### 3. 限流配置

可以使用以下中间件实现限流：

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
```

## 📝 常见问题

### Q: 如何处理API限流？

A: 实现指数退避重试机制。

### Q: 服务内存占用过高？

A: 调整批处理大小和并发数。

### Q: 缓存数据过大？

A: 定期清理过期缓存或缩短缓存保留时间。

## 📞 技术支持

- **文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/system/health
- **日志**: http://localhost:8000/system/logs

## 🎯 总结

FastAPI服务提供了完整的股票分析功能，包括：

- ✅ RESTful API接口
- ✅ 自动API文档
- ✅ 数据缓存系统
- ✅ 定时任务调度
- ✅ 性能监控
- ✅ 健康检查

通过这个API服务，你可以轻松集成股票分析功能到你的应用中！