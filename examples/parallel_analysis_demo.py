#!/usr/bin/env python3
"""
多线程并行股票分析演示
对比串行和并行分析的性能差异
"""
import sys
import os
import time
sys.path.append('/Users/baldwin/PycharmProjects/ai-ticket')

from src.agents.trading_agent import run_daily_analysis
from src.data.stock_selector import StockSelector


def demo_serial_vs_parallel():
    """演示串行 vs 并行分析"""
    print("="*80)
    print("📊 演示 1: 串行分析 vs 并行分析对比")
    print("="*80)

    # 创建测试股票列表（较小的数据集以加快演示）
    test_stocks = ["000001", "000002", "600519", "600036", "000858", "300750"]
    selector = StockSelector(
        selection_mode="custom",
        custom_stocks=test_stocks
    )

    print(f"\n测试股票列表：{', '.join(test_stocks)}")

    # 串行分析
    print("\n" + "-"*80)
    print("🔄 串行分析测试")
    print("-"*80)
    start_time = time.time()
    result_serial = run_daily_analysis(
        stock_selector=selector,
        use_parallel=False,
        max_stocks_to_analyze=100
    )
    serial_duration = time.time() - start_time

    print(f"\n⏱️ 串行分析用时：{serial_duration:.2f} 秒")

    # 并行分析（不同线程数配置）
    for workers in [2, 4, 8]:
        print("\n" + "-"*80)
        print(f"⚡ 并行分析测试 - 线程数: {workers}")
        print("-"*80)
        start_time = time.time()
        result_parallel = run_daily_analysis(
            stock_selector=selector,
            use_parallel=True,
            max_workers=workers,
            thread_timeout=30,
            batch_size=50,
            max_stocks_to_analyze=100
        )
        parallel_duration = time.time() - start_time

        speedup = serial_duration / parallel_duration if parallel_duration > 0 else 0
        print(f"\n⏱️ 并行分析用时：{parallel_duration:.2f} 秒")
        print(f"🚀 加速比：{speedup:.2f}x")

    return result_serial, result_parallel


def demo_parallel_performance():
    """演示并行性能配置"""
    print("\n" + "="*80)
    print("📊 演示 2: 不同并行配置的性能对比")
    print("="*80)

    test_stocks = ["000001", "000002", "600519", "600036", "000858", "300750", "002415"]
    selector = StockSelector(
        selection_mode="custom",
        custom_stocks=test_stocks
    )

    configs = [
        {"name": "低并发", "workers": 2, "timeout": 30, "batch": 50},
        {"name": "中并发", "workers": 4, "timeout": 30, "batch": 50},
        {"name": "高并发", "workers": 8, "timeout": 30, "batch": 50},
    ]

    results = []

    for config in configs:
        print(f"\n{'='*80}")
        print(f"测试配置：{config['name']} (线程数: {config['workers']})")
        print(f"{'='*80}")

        start_time = time.time()
        result = run_daily_analysis(
            stock_selector=selector,
            use_parallel=True,
            max_workers=config['workers'],
            thread_timeout=config['timeout'],
            batch_size=config['batch'],
            max_stocks_to_analyze=100
        )
        duration = time.time() - start_time

        results.append({
            'config': config['name'],
            'workers': config['workers'],
            'duration': duration,
            'recommended': result['total_recommended']
        })

        print(f"✅ 用时: {duration:.2f}秒, 推荐股票: {result['total_recommended']}只")

    # 性能对比
    print(f"\n{'='*80}")
    print("📈 性能对比总结")
    print(f"{'='*80}")
    for r in results:
        print(f"{r['config']:12} | 线程: {r['workers']:2d} | 用时: {r['duration']:6.2f}s | 推荐: {r['recommended']:2d}只")

    return results


def demo_auto_thread_detection():
    """演示自动线程数检测"""
    print("\n" + "="*80)
    print("📊 演示 3: 自动线程数检测")
    print("="*80)

    import os
    import multiprocessing

    cpu_count = os.cpu_count()
    auto_workers = cpu_count * 2

    print(f"CPU核心数: {cpu_count}")
    print(f"自动检测的线程数: {auto_workers} (建议值)")
    print(f"实际使用的线程数: {auto_workers}")

    test_stocks = ["000001", "000002", "600519"]
    selector = StockSelector(
        selection_mode="custom",
        custom_stocks=test_stocks
    )

    print(f"\n🚀 使用自动检测的线程数进行并行分析...")
    start_time = time.time()
    result = run_daily_analysis(
        stock_selector=selector,
        use_parallel=True,
        max_workers=0,  # 0表示自动检测
        max_stocks_to_analyze=100
    )
    duration = time.time() - start_time

    print(f"✅ 自动并行分析完成，用时: {duration:.2f}秒")
    print(f"   推荐股票: {result['total_recommended']}只")

    return result


def demo_batch_processing():
    """演示批处理功能"""
    print("\n" + "="*80)
    print("📊 演示 4: 批处理功能")
    print("="*80)

    # 创建更大的测试数据集
    test_stocks = [f"{i:06d}" for i in range(1, 51)]  # 50只股票
    selector = StockSelector(
        selection_mode="custom",
        custom_stocks=test_stocks
    )

    print(f"测试股票数量: {len(test_stocks)}只")

    # 不同批处理大小
    batch_configs = [
        {"name": "小批次", "batch": 10},
        {"name": "中批次", "batch": 25},
        {"name": "大批次", "batch": 50},
    ]

    for config in batch_configs:
        print(f"\n{'='*60}")
        print(f"批处理大小: {config['batch']}")
        print(f"{'='*60}")

        start_time = time.time()
        result = run_daily_analysis(
            stock_selector=selector,
            use_parallel=True,
            max_workers=4,
            thread_timeout=30,
            batch_size=config['batch'],
            max_stocks_to_analyze=50
        )
        duration = time.time() - start_time

        print(f"✅ {config['name']}处理完成，用时: {duration:.2f}秒")

    return True


def main():
    """主演示函数"""
    print("\n" + "🚀" * 40)
    print("       多线程并行股票分析演示")
    print("🚀" * 40 + "\n")

    try:
        # 演示1：串行 vs 并行对比
        demo_serial_vs_parallel()

        # 演示2：并行性能配置
        demo_parallel_performance()

        # 演示3：自动线程数检测
        demo_auto_thread_detection()

        # 演示4：批处理功能
        demo_batch_processing()

        print("\n" + "="*80)
        print("✅ 所有并行分析演示完成！")
        print("="*80)

        print("\n📊 总结:")
        print("1. 并行分析可以显著提升分析速度")
        print("2. 线程数应根据CPU核心数调整")
        print("3. 批处理有助于管理大量股票")
        print("4. 超时设置可防止任务卡死")
        print("5. 自动线程检测简化配置")

        print("\n💡 使用建议:")
        print("- 小数据集(<100只): 使用4-8个线程")
        print("- 中数据集(100-500只): 使用8-16个线程")
        print("- 大数据集(>500只): 使用16-32个线程")
        print("- 批处理大小: 一般设为线程数的5-10倍")

    except Exception as e:
        print(f"\n❌ 演示过程中出现错误：{e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()