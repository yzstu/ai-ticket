# A股短线选股AI系统 - FastAPI服务

基于FastAPI的高性能股票分析Web服务，提供RESTful API接口，支持股票数据获取、智能分析和缓存管理。

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动服务

```bash
# 开发模式
python run.py --reload

# 生产模式
python run.py --env production --workers 4

# 自定义配置
python run.py --host 0.0.0.0 --port 8000 --workers 8
```

### 3. 访问服务

- **API文档**: http://localhost:8000/docs
- **ReDoc文档**: http://localhost:8000/redoc
- **健康检查**: http://localhost:8000/system/health

## 📚 功能特性

### 股票数据 API (`/stocks`)
- ✅ 获取股票列表
- ✅ 获取日线数据
- ✅ 获取资金流向
- ✅ 获取市场情绪
- ✅ 批量数据获取

### 股票分析 API (`/analysis`)
- ✅ AI驱动的股票分析
- ✅ Top-N推荐
- ✅ 板块分析（蓝筹股、科技股、创业板、科创板）
- ✅ 自定义股票列表分析
- ✅ 并行处理支持
- ✅ 缓存加速

### 缓存管理 API (`/cache`)
- ✅ 缓存统计信息
- ✅ 过期数据清理
- ✅ 缓存数据导出
- ✅ 健康状态检查
- ✅ 智能缓存策略

### 定时任务 API (`/scheduler`)
- ✅ 每日自动缓存
- ✅ 定时数据清理
- ✅ 手动执行缓存
- ✅ 任务状态监控
- ✅ 调度配置管理

### 系统管理 API (`/system`)
- ✅ 系统健康检查
- ✅ 性能指标监控
- ✅ 配置信息查看
- ✅ 日志管理

## 📊 API端点一览

### 股票数据

```bash
# 获取股票列表
GET /stocks/list

# 获取日线数据
GET /stocks/{code}/daily

# 获取资金流向
GET /stocks/{code}/capital-flow

# 获取市场情绪
GET /stocks/{code}/sentiment

# 批量获取数据
POST /stocks/batch/daily
```

### 股票分析

```bash
# 每日股票分析
POST /analysis/daily

# Top-N推荐
GET /analysis/top?n=10

# 板块分析
GET /analysis/sector/{sector}?n=20

# 自定义股票分析
GET /analysis/custom?stock_codes=600519,000001,600036
```

### 缓存管理

```bash
# 查看缓存统计
GET /cache/stats

# 清理过期缓存
POST /cache/cleanup

# 导出缓存数据
POST /cache/export

# 清空所有缓存
DELETE /cache/clear
```

### 定时任务

```bash
# 启动定时任务
POST /scheduler/start

# 停止定时任务
POST /scheduler/stop

# 手动执行缓存
POST /scheduler/manual-cache

# 查看任务状态
GET /scheduler/status
```

### 系统管理

```bash
# 健康检查
GET /system/health

# 系统信息
GET /system/info

# 性能指标
GET /system/metrics

# 配置信息
GET /system/config
```

## 💡 使用示例

### Python客户端

```python
import requests

# 创建客户端
client = StockAIServiceClient("http://localhost:8000")

# 获取股票列表
stocks = client.get_stock_list()
print(f"股票数量: {len(stocks)}")

# 执行分析
result = client.analyze_stocks(
    selection_mode="top_n",
    max_results=10,
    use_parallel=True,
    use_cache=True
)
print(f"推荐股票: {result['total_recommended']}")

# 查看缓存统计
stats = client.get_cache_stats()
print(f"缓存命中率: {stats['cache_hit_rate']:.1f}%")
```

### cURL示例

```bash
# 获取股票列表
curl -X GET "http://localhost:8000/stocks/list"

# 执行分析
curl -X POST "http://localhost:8000/analysis/daily" \
  -H "Content-Type: application/json" \
  -d '{
    "selection_mode": "top_n",
    "max_results": 10,
    "use_parallel": true,
    "use_cache": true
  }'

# 查看缓存统计
curl -X GET "http://localhost:8000/cache/stats"
```

## ⚙️ 配置选项

### 环境变量

```bash
# 运行环境
ENV=production

# 缓存配置
CACHE_DIR=./cache
CACHE_TIME=16:30
CLEANUP_TIME=02:00
BATCH_SIZE=100
MAX_WORKERS=8
```

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

## 📈 性能优化

### 缓存配置

启用缓存可获得**4-5倍**性能提升：

```json
{
  "use_cache": true,
  "cache_dir": "./cache",
  "auto_cache": true
}
```

### 并行分析

大规模分析建议启用并行处理：

```json
{
  "use_parallel": true,
  "max_workers": 8,
  "batch_size": 200
}
```

### 批处理大小

根据数据量调整批处理大小：
- 小数据集 (<100只): batch_size=50
- 中数据集 (100-500只): batch_size=100
- 大数据集 (>500只): batch_size=200

## 🔧 部署指南

### 开发环境

```bash
# 安装依赖
pip install -r requirements.txt

# 启动服务
python run.py --reload
```

### 生产环境

```bash
# 使用Gunicorn
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

# 或使用启动脚本
python run.py --env production --workers 4
```

### Docker部署

```bash
# 构建镜像
docker build -t stock-ai-api .

# 运行容器
docker run -p 8000:8000 \
  -v $(pwd)/cache:/app/cache \
  -e ENV=production \
  stock-ai-api
```

## 📊 监控和维护

### 健康检查

```bash
# 系统健康检查
curl http://localhost:8000/system/health

# 缓存健康检查
curl http://localhost:8000/cache/health
```

### 性能监控

```bash
# 获取性能指标
curl http://localhost:8000/system/metrics
```

### 日志查看

```bash
# 获取系统日志
curl http://localhost:8000/system/logs
```

## 🛠️ 开发工具

### API文档

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### 测试工具

```bash
# 运行API测试
python examples/api_client_demo.py

# 运行功能测试
python test_cache_system.py
```

### 代码质量

```bash
# 格式化代码
black main.py api/

# 代码检查
flake8 main.py api/
```

## 📝 最佳实践

### 1. 启用缓存

始终启用缓存以获得最佳性能：

```python
result = client.analyze_stocks(use_cache=True)
```

### 2. 合理使用并行

大数据量分析时启用并行处理：

```python
result = client.analyze_stocks(
    use_parallel=True,
    max_workers=8,
    batch_size=200
)
```

### 3. 定期监控

定期检查缓存命中率和系统状态：

```python
stats = client.get_cache_stats()
print(f"命中率: {stats['cache_hit_rate']:.1f}%")
```

### 4. 及时清理

定期清理过期缓存：

```python
client.cleanup_cache(dry_run=False)
```

## 🔐 安全建议

### 生产环境配置

1. 设置 `ENV=production`
2. 限制CORS允许的域名
3. 使用HTTPS（通过反向代理）
4. 启用访问日志和监控
5. 实施API限流（可选）

### 访问控制（可选）

如果需要身份验证，可以使用：

- API Key认证
- JWT Token认证
- OAuth2认证

## 📞 技术支持

- **API文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/system/health
- **项目文档**: API_GUIDE.md

## 🎯 总结

FastAPI服务提供了完整的股票分析功能：

- ✅ **完整的RESTful API** - 符合标准，易于集成
- ✅ **自动API文档** - Swagger UI和ReDoc
- ✅ **高性能缓存** - 4-5倍性能提升
- ✅ **并行处理** - 支持大规模数据分析
- ✅ **定时任务** - 自动化的数据管理
- ✅ **健康监控** - 完善的系统监控
- ✅ **易于部署** - 支持Docker和传统部署

现在你可以轻松地将股票分析功能集成到你的应用中！