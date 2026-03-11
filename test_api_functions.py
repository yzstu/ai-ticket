#!/usr/bin/env python
"""
直接调用API函数测试
"""
import sys
sys.path.insert(0, '.')

import asyncio
from api.routes.tasks import get_statistics, get_running_tasks

async def test_api_functions():
    """测试API函数"""
    print("测试API函数...")

    # 1. 测试get_statistics
    try:
        result = await get_statistics()
        print(f"✓ get_statistics: {result}")
    except Exception as e:
        print(f"✗ get_statistics failed: {e}")
        import traceback
        traceback.print_exc()

    # 2. 测试get_running_tasks
    try:
        result = await get_running_tasks()
        print(f"✓ get_running_tasks: {result}")
    except Exception as e:
        print(f"✗ get_running_tasks failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_api_functions())