# 异步任务系统 - 使用指南

## 🚀 快速开始

### 1. 启动系统
```bash
python main.py
```

### 2. 访问界面
- 前端界面: http://localhost:8000/web
- API文档: http://localhost:8000/docs

## 📡 API 使用

### 异步分析模式
```bash
curl -X POST "http://localhost:8000/analysis/daily?async_mode=true" \
  -H "Content-Type: application/json" \
  -d '{
    "selection_mode": "top_n",
    "max_results": 10
  }'
```

### 异步回测模式
```bash
curl -X POST "http://localhost:8000/backtest/batch?async_mode=true" \
  -H "Content-Type: application/json" \
  -d '{
    "stock_codes": ["600519", "000001"],
    "start_date": "2024-01-01",
    "end_date": "2024-12-31"
  }'
```

### 异步缓存模式
```bash
curl -X POST "http://localhost:8000/scheduler/manual-cache?async_mode=true" \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "top_n",
    "max_count": 50
  }'
```

## 🛠️ 任务管理

### 查看任务
```bash
# 所有任务
curl http://localhost:8000/tasks

# 运行中任务
curl http://localhost:8000/tasks/running

# 任务统计
curl http://localhost:8000/tasks/statistics
```

### 操作任务
```bash
# 暂停任务
curl -X POST http://localhost:8000/tasks/{task_id}/pause

# 恢复任务
curl -X POST http://localhost:8000/tasks/{task_id}/resume

# 取消任务
curl -X POST http://localhost:8000/tasks/{task_id}/cancel

# 重试任务
curl -X POST http://localhost:8000/tasks/{task_id}/retry
```

## 🎨 前端使用

1. 访问 http://localhost:8000/web
2. 点击"任务中心"标签
3. 使用快速创建按钮：
   - 📊 创建分析任务
   - 📈 创建回测任务
   - 💾 创建缓存任务
   - 🏢 创建板块任务
4. 实时查看任务进度
5. 操作任务（暂停/取消/重试）

## 📊 任务状态

| 状态 | 图标 | 说明 |
|------|------|------|
| PENDING | ⏳ | 等待执行 |
| RUNNING | 🔄 | 正在执行 |
| PAUSED | ⏸️ | 已暂停 |
| COMPLETED | ✅ | 执行完成 |
| FAILED | ❌ | 执行失败 |
| CANCELLED | 🚫 | 已取消 |

## 🔌 WebSocket

实时任务进度推送:
```
ws://localhost:8000/ws/tasks/{client_id}
```

消息格式:
```json
{
  "type": "task_progress",
  "data": {
    "task_id": "uuid",
    "progress_percent": 65.5,
    "current_item": "分析批次 3/5",
    "status": "RUNNING"
  }
}
```

## ⚙️ 配置

### 最大并发任务数
```python
# src/async_tasks/task_manager.py
_task_manager = TaskManager(max_concurrent_tasks=4)
```

### 任务清理策略
```python
# 默认保留7天，最多1000条记录
DELETE FROM tasks WHERE status IN (...) AND completed_at < datetime('now', '-7 days')
```

## 🐛 故障排除

### 查看日志
```bash
tail -f server.log | grep -E "(ERROR|Task|task)"
```

### 数据库位置
```bash
ls -la cache/tasks.db
```

### 重置任务系统
```bash
rm cache/tasks.db
# 重启服务器会自动重建
```

## 📚 更多资源

- 📖 完整报告: `FINAL_ASYNC_TASKS_REPORT.md`
- 🎬 演示脚本: `demo_async_tasks.py`
- 🧪 测试脚本: `test_async_system.py`
- 📡 API文档: http://localhost:8000/docs

---

**版本**: v1.0.0
**最后更新**: 2026-02-20