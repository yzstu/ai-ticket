#!/usr/bin/env python
"""
异步任务系统完整测试脚本
"""
import sys
import time
import json
import requests
from datetime import datetime

BASE_URL = "http://localhost:8000"

def test_analysis_async():
    """测试分析异步模式"""
    print("\n=== 测试分析异步模式 ===")
    data = {
        "selection_mode": "top_n",
        "max_results": 3
    }
    response = requests.post(f"{BASE_URL}/analysis/daily?async_mode=true", json=data)
    print(f"状态码: {response.status_code}")
    result = response.json()
    print(f"响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
    return result.get('task_id')

def test_backtest_async():
    """测试回测异步模式"""
    print("\n=== 测试回测异步模式 ===")
    data = {
        "stock_codes": ["600519", "000001"],
        "start_date": "2024-01-01",
        "end_date": "2024-12-31"
    }
    response = requests.post(f"{BASE_URL}/backtest/batch?async_mode=true", json=data)
    print(f"状态码: {response.status_code}")
    result = response.json()
    print(f"响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
    return result.get('task_id')

def test_cache_async():
    """测试缓存异步模式"""
    print("\n=== 测试缓存异步模式 ===")
    data = {
        "mode": "top_n",
        "max_count": 5
    }
    response = requests.post(f"{BASE_URL}/scheduler/manual-cache?async_mode=true", json=data)
    print(f"状态码: {response.status_code}")
    result = response.json()
    print(f"响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
    return result.get('task_id')

def test_task_operations(task_id):
    """测试任务操作"""
    print(f"\n=== 测试任务操作 (ID: {task_id}) ===")

    # 获取任务详情
    response = requests.get(f"{BASE_URL}/tasks/{task_id}")
    print(f"获取任务详情 - 状态码: {response.status_code}")
    if response.status_code == 200:
        print(f"任务详情: {json.dumps(response.json(), indent=2, ensure_ascii=False)[:200]}...")

    # 等待一段时间再检查状态
    time.sleep(5)

    # 再次获取任务详情
    response = requests.get(f"{BASE_URL}/tasks/{task_id}")
    if response.status_code == 200:
        task = response.json()
        print(f"任务状态: {task.get('status')}")
        print(f"进度: {task.get('progress_percent', 0)}%")
        if task.get('status') == 'RUNNING':
            # 暂停任务
            print("\n暂停任务...")
            response = requests.post(f"{BASE_URL}/tasks/{task_id}/pause")
            print(f"暂停结果: {response.json()}")

            # 恢复任务
            time.sleep(2)
            print("\n恢复任务...")
            response = requests.post(f"{BASE_URL}/tasks/{task_id}/resume")
            print(f"恢复结果: {response.json()}")

def test_list_tasks():
    """测试任务列表"""
    print("\n=== 测试任务列表 ===")
    response = requests.get(f"{BASE_URL}/tasks")
    print(f"状态码: {response.status_code}")
    tasks = response.json()
    print(f"任务总数: {len(tasks)}")
    for task in tasks[:3]:
        print(f"- {task.get('task_name')}: {task.get('status')}")

def test_statistics():
    """测试统计信息"""
    print("\n=== 测试统计信息 ===")
    response = requests.get(f"{BASE_URL}/tasks/statistics")
    print(f"状态码: {response.status_code}")
    stats = response.json()
    print(f"统计信息: {json.dumps(stats, indent=2, ensure_ascii=False)}")

def test_running_tasks():
    """测试运行中任务"""
    print("\n=== 测试运行中任务 ===")
    response = requests.get(f"{BASE_URL}/tasks/running")
    print(f"状态码: {response.status_code}")
    running = response.json()
    print(f"运行中任务数: {len(running)}")
    for task in running:
        print(f"- {task.get('task_name')}: {task.get('status')}")

def main():
    """主测试流程"""
    print("=" * 60)
    print("异步任务系统 - 完整功能测试")
    print("=" * 60)

    # 检查服务器状态
    try:
        response = requests.get(f"{BASE_URL}/api/info")
        print(f"\n✅ 服务器运行正常: {response.json().get('message')}")
    except Exception as e:
        print(f"\n❌ 服务器连接失败: {e}")
        return

    # 测试任务创建
    analysis_task_id = test_analysis_async()
    backtest_task_id = test_backtest_async()
    cache_task_id = test_cache_async()

    # 测试任务列表和统计
    test_list_tasks()
    test_statistics()
    test_running_tasks()

    # 测试任务操作
    if analysis_task_id:
        test_task_operations(analysis_task_id)

    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)

if __name__ == "__main__":
    main()