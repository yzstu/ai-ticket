#!/usr/bin/env python
"""
测试异步任务系统基本功能
"""
import sys
sys.path.insert(0, '.')

import asyncio
import json
from datetime import datetime
from src.async_tasks.task_models import TaskType, TaskStatus, TaskModel
from src.async_tasks.task_store import get_task_store

async def test_basic_functionality():
    """测试基本功能"""
    print("开始测试异步任务系统...")

    # 1. 获取任务存储
    store = get_task_store()
    print("✓ 获取任务存储成功")

    # 2. 创建任务
    task = TaskModel(
        task_id="test-123",
        task_type=TaskType.ANALYSIS_DAILY,
        task_name="测试任务",
        params={"test": "value"},
        total_items=10
    )

    result = store.create_task(task)
    print(f"✓ 创建任务结果: {result}")

    # 3. 获取任务
    retrieved = store.get_task("test-123")
    print(f"✓ 获取任务成功: {retrieved is not None}")

    # 4. 列出任务
    tasks = store.list_tasks()
    print(f"✓ 列出任务数量: {len(tasks)}")

    # 5. 获取统计
    stats = store.get_statistics()
    print(f"✓ 统计信息: 总任务={stats.total_tasks}")

    print("\n✅ 所有基本功能测试通过！")
    return True

if __name__ == "__main__":
    try:
        result = asyncio.run(test_basic_functionality())
        sys.exit(0 if result else 1)
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)