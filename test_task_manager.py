#!/usr/bin/env python
"""
直接测试任务API
"""
import sys
sys.path.insert(0, '.')

from src.async_tasks.task_manager import get_task_manager

async def test_task_manager():
    """测试任务管理器"""
    print("测试任务管理器...")

    tm = get_task_manager()

    # 1. 测试get_statistics
    try:
        stats = tm.get_statistics()
        print(f"✓ get_statistics: {stats}")
    except Exception as e:
        print(f"✗ get_statistics failed: {e}")
        import traceback
        traceback.print_exc()

    # 2. 测试get_running_tasks
    try:
        running = tm.get_running_tasks()
        print(f"✓ get_running_tasks: {running}")
    except Exception as e:
        print(f"✗ get_running_tasks failed: {e}")
        import traceback
        traceback.print_exc()

    # 3. 测试list_tasks
    try:
        tasks = tm.list_tasks()
        print(f"✓ list_tasks: {len(tasks)} tasks")
    except Exception as e:
        print(f"✗ list_tasks failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_task_manager())