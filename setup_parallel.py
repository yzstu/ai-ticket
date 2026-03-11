#!/usr/bin/env python3
"""
并行分析配置助手
快速设置和测试多线程并行分析功能
"""
import sys
import os
import time
sys.path.append('/Users/baldwin/PycharmProjects/ai-ticket')

from src.agents.trading_agent import run_daily_analysis
from src.data.stock_selector import StockSelector
from src.data.parallel_analyzer import ParallelAnalyzer, AnalysisConfig


def detect_optimal_config():
    """检测系统并推荐最优配置"""
    import multiprocessing

    cpu_count = multiprocessing.cpu_count()

    # 尝试获取内存信息
    try:
        memory_gb = psutil.virtual_memory().total / (1024**3)
    except:
        # 如果无法获取内存信息，使用默认值
        memory_gb = 8.0

    print("🔍 系统检测结果:")
    print(f"  CPU核心数: {cpu_count}")
    print(f"  内存: {memory_gb:.1f}GB")

    # 推荐配置
    if memory_gb >= 16:
        memory_tier = "高"
        max_workers = cpu_count * 3
        batch_size = 200
        timeout = 45
    elif memory_gb >= 8:
        memory_tier = "中"
        max_workers = cpu_count * 2
        batch_size = 100
        timeout = 30
    else:
        memory_tier = "低"
        max_workers = cpu_count
        batch_size = 50
        timeout = 20

    print(f"\n📊 推荐配置 ({memory_tier}配置):")
    print(f"  线程数: {max_workers}")
    print(f"  批处理大小: {batch_size}")
    print(f"  超时时间: {timeout}秒")

    return {
        'max_workers': max_workers,
        'batch_size': batch_size,
        'timeout': timeout
    }


def apply_config(config):
    """应用配置到环境变量"""
    os.environ['PARALLEL_WORKERS'] = str(config['max_workers'])
    os.environ['THREAD_TIMEOUT'] = str(config['timeout'])
    os.environ['BATCH_SIZE'] = str(config['batch_size'])
    os.environ['ENABLE_PARALLEL_ANALYSIS'] = 'true'

    print(f"\n✅ 配置已应用到环境变量")


def quick_test():
    """快速测试"""
    print("\n" + "="*60)
    print("🚀 快速测试并行分析功能")
    print("="*60)

    # 小规模测试数据
    test_stocks = ["000001", "000002", "600519", "600036"]
    selector = StockSelector(
        selection_mode="custom",
        custom_stocks=test_stocks
    )

    print(f"\n测试股票: {', '.join(test_stocks)}")

    # 串行测试
    print("\n🔄 串行分析...")
    start = time.time()
    result_serial = run_daily_analysis(
        stock_selector=selector,
        use_parallel=False,
        max_stocks_to_analyze=10
    )
    serial_time = time.time() - start
    print(f"   用时: {serial_time:.2f}秒")

    # 并行测试
    print("\n⚡ 并行分析...")
    start = time.time()
    result_parallel = run_daily_analysis(
        stock_selector=selector,
        use_parallel=True,
        max_workers=4,
        thread_timeout=30,
        batch_size=50,
        max_stocks_to_analyze=10
    )
    parallel_time = time.time() - start

    print(f"   用时: {parallel_time:.2f}秒")

    # 性能对比
    if parallel_time > 0:
        speedup = serial_time / parallel_time
        print(f"\n📈 加速比: {speedup:.2f}x")

        if speedup > 1.5:
            print("✅ 并行分析效果显著！")
        elif speedup > 1.0:
            print("⚠️ 并行分析有一定效果")
        else:
            print("⚠️ 并行分析效果不明显（可能是数据量小）")

    return result_serial, result_parallel


def performance_benchmark():
    """性能基准测试"""
    print("\n" + "="*60)
    print("📊 性能基准测试")
    print("="*60)

    # 创建更大测试数据集
    test_stocks = [f"{i:06d}" for i in range(1, 21)]
    selector = StockSelector(
        selection_mode="custom",
        custom_stocks=test_stocks
    )

    configs = [
        {"name": "低并发", "workers": 2, "color": "🔵"},
        {"name": "中并发", "workers": 4, "color": "🟡"},
        {"name": "高并发", "workers": 8, "color": "🟢"},
    ]

    results = []

    for config in configs:
        print(f"\n{config['color']} 测试 {config['name']} (线程数: {config['workers']})")
        print("-" * 40)

        start = time.time()
        result = run_daily_analysis(
            stock_selector=selector,
            use_parallel=True,
            max_workers=config['workers'],
            thread_timeout=30,
            batch_size=50,
            max_stocks_to_analyze=20
        )
        duration = time.time() - start

        results.append({
            'name': config['name'],
            'workers': config['workers'],
            'duration': duration,
            'recommended': result['total_recommended']
        })

        print(f"   用时: {duration:.2f}秒, 推荐: {result['total_recommended']}只")

    # 总结
    print("\n" + "="*60)
    print("📊 性能测试总结")
    print("="*60)
    for r in results:
        bar = "█" * int(r['workers'])
        print(f"{r['name']:8} |{bar:8} | {r['duration']:6.2f}s")

    # 找最优配置
    best = min(results, key=lambda x: x['duration'])
    print(f"\n🏆 最优配置: {best['name']} ({best['workers']}线程)")

    return results


def save_config(config):
    """保存配置到文件"""
    config_file = "/Users/baldwin/PycharmProjects/ai-ticket/parallel_config.env"

    with open(config_file, 'w') as f:
        f.write(f"# 并行分析配置\n")
        f.write(f"# 自动生成于 {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"export ENABLE_PARALLEL_ANALYSIS=\"true\"\n")
        f.write(f"export PARALLEL_WORKERS=\"{config['max_workers']}\"\n")
        f.write(f"export THREAD_TIMEOUT=\"{config['timeout']}\"\n")
        f.write(f"export BATCH_SIZE=\"{config['batch_size']}\"\n")
        f.write(f"export RETRY_COUNT=\"2\"\n")

    print(f"\n💾 配置已保存到: {config_file}")
    print("   使用方法: source parallel_config.env")


def main():
    """主函数"""
    print("\n" + "⚙️" * 30)
    print("    并行分析配置助手")
    print("⚙️" * 30 + "\n")

    try:
        # 检查依赖
        try:
            import psutil
            has_psutil = True
        except ImportError:
            print("⚠️ 未安装psutil，部分功能可能受限")
            print("  安装命令: pip install psutil\n")
            has_psutil = False

        # 1. 检测系统
        print("步骤1: 系统检测和配置推荐")
        config = detect_optimal_config()

        # 2. 应用配置
        print("\n步骤2: 应用推荐配置")
        apply_config(config)

        # 3. 快速测试
        print("\n步骤3: 功能验证")
        quick_test()

        # 4. 性能测试
        print("\n步骤4: 性能基准测试")
        performance_benchmark()

        # 5. 保存配置
        print("\n步骤5: 保存配置")
        save_config(config)

        # 打印使用说明
        print("\n" + "="*60)
        print("✅ 配置完成！")
        print("="*60)

        print("\n📚 后续使用:")
        print("  1. 加载配置: source parallel_config.env")
        print("  2. 使用并行分析: run_daily_analysis(..., use_parallel=True)")
        print("  3. 查看详细文档: docs/parallel_analysis_config.md")
        print("  4. 运行完整演示: python examples/parallel_analysis_demo.py")

        print("\n💡 使用示例:")
        print("  result = run_daily_analysis(")
        print("      stock_selector=selector,")
        print("      use_parallel=True,")
        print(f"      max_workers={config['max_workers']},")
        print(f"      thread_timeout={config['timeout']},")
        print(f"      batch_size={config['batch_size']}")
        print("  )")

    except Exception as e:
        print(f"\n❌ 配置失败：{e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()