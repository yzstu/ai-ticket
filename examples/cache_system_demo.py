#!/usr/bin/env python3
"""
缓存系统使用示例
演示如何使用数据缓存和定时任务功能
"""
import os
import sys
import time
import logging
from datetime import datetime

sys.path.append('/Users/baldwin/PycharmProjects/ai-ticket')

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 示例1: 基本缓存使用
def demo_basic_cache():
    """基本缓存使用示例"""
    print("\n" + "="*60)
    print("示例1: 基本缓存使用")
    print("="*60)

    from src.data.cached_fetcher import create_cached_fetcher

    # 创建缓存数据获取器
    cached_fetcher = create_cached_fetcher(
        use_cache=True,
        cache_dir="./demo_cache",
        auto_cache=True,
        cache_ttl_hours=24
    )

    print("\n1. 获取股票列表")
    stock_list = cached_fetcher.get_stock_list()
    print(f"   获取到 {len(stock_list)} 只股票")
    if stock_list:
        print(f"   示例: {stock_list[0]}")

    print("\n2. 获取单只股票数据（第一次从API）")
    stock_code = "600519"
    start_time = time.time()
    daily_data = cached_fetcher.get_daily_data(stock_code, days=5)
    duration1 = time.time() - start_time
    print(f"   首次获取耗时: {duration1:.3f}秒")

    print("\n3. 再次获取相同数据（从缓存）")
    start_time = time.time()
    daily_data_cached = cached_fetcher.get_daily_data(stock_code, days=5)
    duration2 = time.time() - start_time
    print(f"   缓存获取耗时: {duration2:.3f}秒")

    if duration1 > 0:
        speedup = duration1 / duration2
        print(f"   性能提升: {speedup:.1f}倍")

    print("\n4. 获取资金流向和市场情绪")
    capital_flow = cached_fetcher.get_capital_flow(stock_code)
    sentiment = cached_fetcher.get_market_sentiment(stock_code)
    print(f"   资金流向: {capital_flow is not None}")
    print(f"   市场情绪: {sentiment is not None}")

    print("\n5. 缓存统计")
    stats = cached_fetcher.get_cache_stats()
    print(f"   总请求数: {stats['total_requests']}")
    print(f"   缓存命中: {stats['cache_hits']}")
    print(f"   缓存未命中: {stats['cache_misses']}")
    print(f"   缓存命中率: {stats['cache_hit_rate']:.1f}%")
    print(f"   API请求数: {stats['api_requests']}")
    print(f"   缓存写入数: {stats['cache_writes']}")

    if 'cache_manager_stats' in stats:
        cms = stats['cache_manager_stats']
        print(f"\n缓存管理器统计:")
        print(f"   日线数据记录: {cms.get('daily_data_count', 0)}")
        print(f"   资金流向记录: {cms.get('capital_flow_count', 0)}")
        print(f"   市场情绪记录: {cms.get('sentiment_count', 0)}")
        print(f"   数据库大小: {cms.get('db_size_mb', 0)} MB")

    return cached_fetcher


# 示例2: 批量数据获取
def demo_batch_fetch():
    """批量数据获取示例"""
    print("\n" + "="*60)
    print("示例2: 批量数据获取（支持并发）")
    print("="*60)

    from src.data.cached_fetcher import create_cached_fetcher

    cached_fetcher = create_cached_fetcher(
        use_cache=True,
        cache_dir="./demo_cache",
        auto_cache=True
    )

    # 选择测试股票列表
    test_stocks = ["000001", "000002", "600519", "600036", "000858"]
    print(f"\n批量获取 {len(test_stocks)} 只股票的数据")

    start_time = time.time()
    results = cached_fetcher.batch_get_daily_data(
        stock_codes=test_stocks,
        days=5,
        use_cache_first=True,
        max_workers=3
    )
    duration = time.time() - start_time

    print(f"批量获取完成，耗时: {duration:.3f}秒")

    success_count = sum(1 for v in results.values() if v is not None)
    print(f"成功获取: {success_count}/{len(test_stocks)} 只股票")

    # 显示前3只股票的结果
    for i, (code, df) in enumerate(list(results.items())[:3]):
        if df is not None:
            print(f"   {code}: {len(df)} 条记录")
        else:
            print(f"   {code}: 获取失败")

    # 查看缓存统计
    stats = cached_fetcher.get_cache_stats()
    print(f"\n批量获取后统计:")
    print(f"   总请求数: {stats['total_requests']}")
    print(f"   缓存命中率: {stats['cache_hit_rate']:.1f}%")


# 示例3: 定时任务调度
def demo_cache_scheduler():
    """缓存定时任务示例"""
    print("\n" + "="*60)
    print("示例3: 缓存定时任务调度")
    print("="*60)

    print("\n注意: 定时任务将在后台运行，这里演示如何配置和启动")
    print("实际使用时，程序会持续运行直到手动停止\n")

    from src.data.cache_scheduler import create_scheduler

    # 创建调度器
    scheduler = create_scheduler(
        cache_dir="./demo_cache",
        cache_time="16:30",  # 每天16:30执行缓存
        cleanup_time="02:00",  # 每天02:00执行清理
        batch_size=50,  # 每批处理50只股票
        max_workers=4  # 4个并发线程
    )

    print("调度器配置:")
    print(f"   缓存时间: 每天 16:30")
    print(f"   清理时间: 每天 02:00")
    print(f"   批处理大小: 50")
    print(f"   最大工作线程: 4")

    print("\n手动执行一次缓存任务（演示）")
    print("实际使用时，定时任务会自动执行")
    manual_stats = scheduler.run_cache_manually(stock_codes=["000001", "000002", "600519"])
    print(f"手动缓存完成:")
    print(f"   总股票数: {manual_stats['total_stocks']}")
    print(f"   成功缓存: {manual_stats['cached_stocks']}")
    print(f"   失败数量: {manual_stats['failed_stocks']}")

    # 如果需要启动定时任务（会阻塞当前线程），取消下面这行的注释
    # scheduler.start()

    print("\n要启动定时任务，请运行:")
    print("   scheduler.start()  # 这会阻塞当前线程")


# 示例4: 缓存管理操作
def demo_cache_management():
    """缓存管理操作示例"""
    print("\n" + "="*60)
    print("示例4: 缓存管理操作")
    print("="*60)

    from src.data.cache_manager import create_cache_manager

    # 创建缓存管理器
    cache_manager = create_cache_manager(
        cache_dir="./demo_cache",
        max_cache_days=7,  # 保留7天
        auto_cleanup=True,
        compress_data=False
    )

    print("1. 查看缓存统计")
    stats = cache_manager.get_cache_stats()
    print(f"   日线数据记录: {stats.get('daily_data_count', 0)}")
    print(f"   资金流向记录: {stats.get('capital_flow_count', 0)}")
    print(f"   市场情绪记录: {stats.get('sentiment_count', 0)}")
    print(f"   数据库大小: {stats.get('db_size_mb', 0)} MB")

    print("\n2. 清理过期缓存")
    deleted_count = cache_manager.cleanup_expired_cache()
    print(f"   删除了 {deleted_count} 条过期记录")

    print("\n3. 导出缓存数据")
    export_path = "./demo_cache_export.json"
    success = cache_manager.export_cache_to_json(export_path, days=1)
    if success:
        print(f"   缓存数据已导出到: {export_path}")
    else:
        print("   导出失败")

    print("\n4. 清空所有缓存")
    confirm = input("   确认清空所有缓存? (y/N): ")
    if confirm.lower() == 'y':
        success = cache_manager.clear_all_cache()
        if success:
            print("   所有缓存已清空")
    else:
        print("   取消清空操作")


# 示例5: 性能对比测试
def demo_performance_comparison():
    """性能对比测试"""
    print("\n" + "="*60)
    print("示例5: 缓存性能对比测试")
    print("="*60)

    from src.data.cached_fetcher import create_cached_fetcher
    from src.data.fetcher import DataFetcher

    test_stocks = ["600519", "000001", "600036", "000858", "300750"]
    iterations = 3

    print(f"测试 {len(test_stocks)} 只股票，重复 {iterations} 次\n")

    # 测试1: 无缓存
    print("测试1: 无缓存模式")
    fetcher_no_cache = DataFetcher()

    start_time = time.time()
    for _ in range(iterations):
        for stock_code in test_stocks:
            try:
                data = fetcher_no_cache.get_daily_data(stock_code, days=5)
            except:
                pass
    duration_no_cache = (time.time() - start_time) / iterations
    print(f"   平均耗时: {duration_no_cache:.3f}秒")

    # 测试2: 启用缓存
    print("\n测试2: 启用缓存模式")
    cached_fetcher = create_cached_fetcher(
        use_cache=True,
        cache_dir="./demo_cache_perf",
        auto_cache=True
    )

    # 第一次运行（冷缓存）
    start_time = time.time()
    for stock_code in test_stocks:
        cached_fetcher.get_daily_data(stock_code, days=5, force_refresh=True)
    duration_cold = time.time() - start_time
    print(f"   冷缓存耗时: {duration_cold:.3f}秒")

    # 第二次运行（热缓存）
    start_time = time.time()
    for stock_code in test_stocks:
        cached_fetcher.get_daily_data(stock_code, days=5, force_refresh=False)
    duration_hot = time.time() - start_time
    print(f"   热缓存耗时: {duration_hot:.3f}秒")

    # 性能对比
    if duration_hot > 0:
        speedup = duration_no_cache / duration_hot
        print(f"\n缓存性能提升: {speedup:.1f}倍")
        print(f"   响应时间减少: {(1 - duration_hot/duration_no_cache)*100:.1f}%")

    # 查看缓存统计
    stats = cached_fetcher.get_cache_stats()
    print(f"\n缓存统计:")
    print(f"   总请求: {stats['total_requests']}")
    print(f"   缓存命中: {stats['cache_hits']}")
    print(f"   命中率: {stats['cache_hit_rate']:.1f}%")


# 示例6: 集成到现有系统
def demo_integration():
    """集成到现有系统示例"""
    print("\n" + "="*60)
    print("示例6: 集成到现有系统")
    print("="*60)

    print("\n1. 替换原有的DataFetcher")
    print("   原有代码:")
    print("   ```python")
    print("   from src.data.fetcher import DataFetcher")
    print("   fetcher = DataFetcher()")
    print("   data = fetcher.get_daily_data('600519')")
    print("   ```")

    print("\n   新代码:")
    print("   ```python")
    print("   from src.data.cached_fetcher import create_cached_fetcher")
    print("   fetcher = create_cached_fetcher(")
    print("       use_cache=True,")
    print("       cache_dir='./cache',")
    print("       auto_cache=True")
    print("   )")
    print("   data = fetcher.get_daily_data('600519')")
    print("   ```")

    print("\n2. 配置缓存策略")
    print("   ```python")
    print("   # 高性能配置")
    print("   fetcher = create_cached_fetcher(")
    print("       use_cache=True,")
    print("       cache_dir='./fast_cache',")
    print("       auto_cache=True,")
    print("       cache_ttl_hours=12  # 12小时缓存")
    print("   )")
    print("   ```")

    print("\n3. 启动定时任务")
    print("   ```python")
    print("   scheduler = fetcher.start_cache_scheduler(")
    print("       cache_time='16:30',  # 收盘后缓存")
    print("       cleanup_time='02:00',  # 凌晨清理")
    print("       batch_size=100,")
    print("       max_workers=8")
    print("   )")
    print("   scheduler.start()  # 启动定时任务")
    print("   ```")

    print("\n4. 监控缓存状态")
    print("   ```python")
    print("   stats = fetcher.get_cache_stats()")
    print("   print(f'命中率: {stats[\"cache_hit_rate\"]}%')")
    print("   ```")

    print("\n✅ 集成完成！现有代码无需修改，只需替换初始化方式")


def main():
    """主演示函数"""
    print("\n" + "🚀" * 30)
    print("       股票数据缓存系统演示")
    print("🚀" * 30 + "\n")

    print("本演示将展示:")
    print("1. 基本缓存使用")
    print("2. 批量数据获取")
    print("3. 定时任务调度")
    print("4. 缓存管理操作")
    print("5. 性能对比测试")
    print("6. 现有系统集成")
    print()

    try:
        # 运行所有示例
        demo_basic_cache()
        demo_batch_fetch()
        demo_cache_scheduler()
        demo_cache_management()
        demo_performance_comparison()
        demo_integration()

        print("\n" + "="*60)
        print("✅ 所有演示完成！")
        print("="*60)

        print("\n📚 使用建议:")
        print("1. 生产环境建议启用缓存并设置定时任务")
        print("2. 定期查看缓存统计，监控命中率")
        print("3. 定期清理过期缓存，释放存储空间")
        print("4. 根据数据更新频率调整缓存TTL")
        print("5. 大规模数据建议使用更大的batch_size")

        print("\n📖 更多信息请参考:")
        print("   - src/data/cache_manager.py (缓存管理)")
        print("   - src/data/cache_scheduler.py (定时任务)")
        print("   - src/data/cached_fetcher.py (缓存获取器)")

    except KeyboardInterrupt:
        print("\n\n⚠️ 演示被用户中断")
    except Exception as e:
        print(f"\n\n❌ 演示过程中出现错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()