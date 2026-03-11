#!/usr/bin/env python
"""
异步任务系统演示脚本
展示系统的主要功能
"""
import sys
import time
import json
import requests
from datetime import datetime

BASE_URL = "http://localhost:8000"

def print_section(title):
    """打印章节标题"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)

def print_step(step, description):
    """打印步骤"""
    print(f"\n{step}. {description}")

def demo_system_status():
    """演示系统状态"""
    print_section("系统状态检查")

    response = requests.get(f"{BASE_URL}/api/info")
    info = response.json()
    print(f"✅ 系统名称: {info.get('message')}")
    print(f"✅ API版本: {info.get('version')}")
    print(f"✅ 文档地址: {BASE_URL}{info.get('docs')}")

    # 检查任务统计
    response = requests.get(f"{BASE_URL}/tasks/statistics")
    stats = response.json()
    print(f"\n📊 任务统计:")
    print(f"   - 总任务数: {stats.get('total_tasks', 0)}")
    print(f"   - 运行中: {stats.get('running_tasks', 0)}")
    print(f"   - 已完成: {stats.get('completed_tasks', 0)}")
    print(f"   - 成功率: {stats.get('success_rate', 0):.1f}%")

def demo_create_analysis_task():
    """演示创建分析任务"""
    print_section("演示：创建异步分析任务")

    print_step(1, "创建分析任务（Top-5股票）")
    data = {
        "selection_mode": "top_n",
        "max_results": 5
    }
    response = requests.post(f"{BASE_URL}/analysis/daily?async_mode=true", json=data)
    result = response.json()
    task_id = result.get('task_id')
    print(f"✅ 任务已创建，ID: {task_id[:8]}...")
    print(f"   状态: {result.get('status')}")
    print(f"   查看地址: {result.get('check_url')}")

    return task_id

def demo_monitor_task(task_id):
    """演示监控任务"""
    print_step(2, "监控任务执行")

    for i in range(10):
        time.sleep(2)
        response = requests.get(f"{BASE_URL}/tasks/{task_id}")
        if response.status_code == 200:
            task = response.json()
            status = task.get('status')
            progress = task.get('progress_percent', 0)
            current = task.get('current_item', 'N/A')

            print(f"   [{i+1}] 状态: {status:10s} 进度: {progress:5.1f}%  当前: {current}")
            if status in ['COMPLETED', 'FAILED', 'CANCELLED']:
                print(f"✅ 任务 {status}")
                if task.get('result'):
                    print(f"   结果: {json.dumps(task['result'], ensure_ascii=False)[:200]}...")
                break
        else:
            print(f"   [{i+1}] 任务未找到（可能已完成）")
            break

def demo_task_operations():
    """演示任务操作"""
    print_section("演示：任务操作")

    # 获取运行中的任务
    response = requests.get(f"{BASE_URL}/tasks/running")
    running_tasks = response.json()

    if running_tasks:
        task = running_tasks[0]
        task_id = task.get('task_id')
        print_step(1, f"操作运行中任务: {task.get('task_name')[:30]}...")
        print(f"   任务ID: {task_id[:8]}...")
        print(f"   当前状态: {task.get('status')}")

        # 尝试暂停任务
        print_step(2, "暂停任务")
        response = requests.post(f"{BASE_URL}/tasks/{task_id}/pause")
        result = response.json()
        print(f"   结果: {result.get('message', 'Failed')}")

        time.sleep(2)

        # 尝试恢复任务
        print_step(3, "恢复任务")
        response = requests.post(f"{BASE_URL}/tasks/{task_id}/resume")
        result = response.json()
        print(f"   结果: {result.get('message', 'Failed')}")
    else:
        print("当前没有运行中的任务")

def demo_task_history():
    """演示任务历史"""
    print_section("演示：任务历史")

    response = requests.get(f"{BASE_URL}/tasks?limit=5")
    tasks = response.json()

    print(f"最近5个任务:")
    for i, task in enumerate(tasks, 1):
        status = task.get('status')
        name = task.get('task_name')
        created = task.get('created_at', '')[:19]
        status_icon = {
            'COMPLETED': '✅',
            'RUNNING': '🔄',
            'FAILED': '❌',
            'PENDING': '⏳',
            'CANCELLED': '🚫'
        }.get(status, '❓')

        print(f"  {i}. {status_icon} {name[:40]:40s} [{status:10s}] {created}")

def demo_quick_create():
    """演示快速创建任务"""
    print_section("演示：快速创建任务")

    # 创建分析任务
    print_step(1, "快速创建分析任务")
    response = requests.post(f"{BASE_URL}/tasks/create-analysis", json={
        "selection_mode": "top_n",
        "max_results": 3
    })
    result = response.json()
    print(f"✅ 分析任务已创建: {result.get('task_name')}")
    print(f"   状态: {result.get('status')}")

    # 创建缓存任务
    print_step(2, "快速创建缓存任务")
    response = requests.post(f"{BASE_URL}/tasks/create-cache", json={
        "stocks": ["600519", "000001", "600036"],
        "cache_dir": "./cache"
    })
    result = response.json()
    print(f"✅ 缓存任务已创建: {result.get('task_name')}")
    print(f"   状态: {result.get('status')}")

def demo_web_interface():
    """演示Web界面"""
    print_section("演示：Web界面")

    print("✅ 前端界面地址:")
    print(f"   - 主界面: {BASE_URL}/web")
    print(f"   - 任务中心: {BASE_URL}/web (点击'任务中心'标签)")
    print(f"\n✅ API文档:")
    print(f"   - Swagger UI: {BASE_URL}/docs")
    print(f"   - ReDoc: {BASE_URL}/redoc")

def main():
    """主演示流程"""
    print("\n" + "╔" + "=" * 58 + "╗")
    print("║" + " " * 10 + "异步任务系统功能演示" + " " * 23 + "║")
    print("╚" + "=" * 58 + "╝")

    try:
        # 1. 系统状态
        demo_system_status()

        # 2. 创建分析任务
        task_id = demo_create_analysis_task()

        # 3. 监控任务
        demo_monitor_task(task_id)

        # 4. 任务操作
        demo_task_operations()

        # 5. 任务历史
        demo_task_history()

        # 6. 快速创建
        demo_quick_create()

        # 7. Web界面
        demo_web_interface()

        print_section("演示完成")
        print("感谢使用异步任务系统！")
        print("\n如需查看更多功能，请访问:")
        print(f"  - 前端界面: {BASE_URL}/web")
        print(f"  - API文档: {BASE_URL}/docs")

    except Exception as e:
        print(f"\n❌ 演示过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()