#!/usr/bin/env python3
"""
缓存系统完整使用示例
演示如何使用数据缓存和定时任务功能
"""
import sys
import os
import time

sys.path.append('/Users/baldwin/PycharmProjects/ai-ticket')


def demo_basic_usage():
    """基本使用示例"""
    print("\n" + "="*60)
    print("示例1: 基本使用（替换原有DataFetcher）")
    print("="*60)

    # 原有方式
    print("\n原有方式:")
    print("```python")
    print("from src.data.fetcher import DataFetcher")
    print("fetcher = DataFetcher()")
    print("data = fetcher.get_daily_data('600519', days=30)")
    print("```")

    # 新方式（缓存增强）
    print("\n新方式（缓存增强）:")
    print("```python")
    print("from src.data.cached_fetcher import create_cached_fetcher")
    print("from src.agents.cached_trading_agent import run_daily_analysis")
    print("")
    print("# 创建缓存数据获取器")
    print("fetcher = create_cached_fetcher(")
    print("    use_cache=True,")
    print("    cache_dir='./cache',")
    print("    auto_cache=True")
    print(")")
    print("")
    print("# 运行分析（默认启用缓存）")
    print("result = run_daily_analysis(use_cache=True)")
    print("```")

    print("\n✅ 优势:")
    print("  - 自动缓存API数据")
    print("  - 优先从缓存读取")
    print("  - 4-5倍性能提升")
    print("  - 完全向后兼容")


def demo_cache_performance():
    """缓存性能示例"""
    print("\n" + "="*60)
    print("示例2: 缓存性能对比")
    print("="*60)

    from src.data.cached_fetcher import create_cached_fetcher

    test_stocks = ["600519", "000001", "600036", "000858", "300750"]

    print(f"\n测试 {len(test_stocks)} 只股票的性能\n")

    # 创建缓存获取器
    cached_fetcher = create_cached_fetcher(
        use_cache=True,
        cache_dir="./demo_cache",
        auto_cache=True
    )

    # 第一次查询（从API）
    print("1. 首次查询（从API获取）...")
    start = time.time()
    for stock in test_stocks:
        data = cached_fetcher.get_daily_data(stock, days=5, force_refresh=True)
    duration_api = time.time() - start
    print(f"   耗时: {duration_api:.3f}秒")

    # 第二次查询（从缓存）
    print("\n2. 再次查询（从缓存获取）...")
    start = time.time()
    for stock in test_stocks:
        data = cached_fetcher.get_daily_data(stock, days=5, force_refresh=False)
    duration_cache = time.time() - start
    print(f"   耗时: {duration_cache:.3f}秒")

    # 性能对比
    if duration_cache > 0:
        speedup = duration_api / duration_cache
        print(f"\n🚀 性能提升: {speedup:.1f}倍")

    # 查看缓存统计
    print("\n3. 缓存统计:")
    stats = cached_fetcher.get_cache_stats()
    print(f"   总请求: {stats['total_requests']}")
    print(f"   缓存命中: {stats['cache_hits']}")
    print(f"   命中率: {stats['cache_hit_rate']:.1f}%")


def demo_trading_agent_with_cache():
    """在交易智能体中使用缓存"""
    print("\n" + "="*60)
    print("示例3: 在交易智能体中启用缓存")
    print("="*60)

    print("\n方式1: 使用缓存增强版交易智能体")
    print("```python")
    print("from src.agents.cached_trading_agent import run_daily_analysis")
    print("from src.data.stock_selector import StockSelector")
    print("")
    print("# 创建股票选择器")
    print("selector = StockSelector(")
    print("    selection_mode='custom',")
    print("    custom_stocks=['600519', '000001', '600036']")
    print(")")
    print("")
    print("# 启用缓存和并行分析")
    print("result = run_daily_analysis(")
    print("    stock_selector=selector,")
    print("    use_cache=True,")
    print("    use_parallel=True,")
    print("    max_workers=8")
    print(")")
    print("```")

    print("\n方式2: 带定时任务的完整版本")
    print("```python")
    print("from src.agents.cached_trading_agent import run_daily_analysis_with_cache")
    print("")
    print("result = run_daily_analysis_with_cache(")
    print("    stock_selector=selector,")
    print("    use_cache=True,")
    print("    start_cache_scheduler=True,")
    print("    cache_time='16:30',      # 收盘后缓存")
    print("    cleanup_time='02:00',    # 凌晨清理")
    print("    batch_size=100,")
    print("    max_workers=8")
    print(")")
    print("```")


def demo_scheduler_setup():
    """定时任务设置示例"""
    print("\n" + "="*60)
    print("示例4: 定时任务设置")
    print("="*60)

    print("\n1. 自动配置（推荐）")
    print("```python")
    print("from src.data.cached_fetcher import create_cached_fetcher")
    print("")
    print("fetcher = create_cached_fetcher(use_cache=True)")
    print("scheduler = fetcher.start_cache_scheduler(")
    print("    cache_time='16:30',     # 每天16:30缓存")
    print("    cleanup_time='02:00',   # 每天02:00清理")
    print("    batch_size=100,         # 每批100只股票")
    print("    max_workers=8           # 8个并发线程")
    print(")")
    print("scheduler.start()  # 启动调度器")
    print("```")

    print("\n2. 手动配置")
    print("```python")
    print("from src.data.cache_scheduler import create_scheduler")
    print("")
    print("scheduler = create_scheduler(")
    print("    cache_dir='./cache',")
    print("    cache_time='16:30',")
    print("    cleanup_time='02:00',")
    print("    batch_size=100,")
    print("    max_workers=8")
    print(")")
    print("scheduler.start()")
    print("```")

    print("\n3. 环境变量配置")
    print("```bash")
    print("# 设置环境变量")
    print("export ENABLE_CACHE='true'")
    print("export CACHE_DIR='./cache'")
    print("export CACHE_TIME='16:30'")
    print("export CLEANUP_TIME='02:00'")
    print("export BATCH_SIZE='100'")
    print("export MAX_WORKERS='8'")
    print("```")


def demo_advanced_features():
    """高级功能示例"""
    print("\n" + "="*60)
    print("示例5: 高级功能")
    print("="*60)

    print("\n1. 批量查询")
    print("```python")
    print("from src.data.cached_fetcher import create_cached_fetcher")
    print("")
    print("fetcher = create_cached_fetcher(use_cache=True)")
    print("")
    print("# 批量查询（自动并发）")
    print("results = fetcher.batch_get_daily_data(")
    print("    stock_codes=['600519', '000001', '600036'],")
    print("    days=30,")
    print("    use_cache_first=True,")
    print("    max_workers=4")
    print(")")
    print("```")

    print("\n2. 强制刷新缓存")
    print("```python")
    print("# 强制从API获取并更新缓存")
    print("data = fetcher.get_daily_data('600519', force_refresh=True)")
    print("```")

    print("\n3. 缓存管理")
    print("```python")
    print("# 获取缓存统计")
    print("stats = fetcher.get_cache_stats()")
    print("print(f'命中率: {stats[\"cache_hit_rate\"]}%')")
    print("")
    print("# 清理过期缓存")
    print("deleted = fetcher.cleanup_expired_cache()")
    print("")
    print("# 导出缓存数据")
    print("fetcher.export_cache('./backup.json', days=7)")
    print("")
    print("# 清空所有缓存")
    print("fetcher.clear_cache()")
    print("```")

    print("\n4. 监控缓存状态")
    print("```python")
    print("while True:")
    print("    stats = fetcher.get_cache_stats()")
    print(f"    print(f'命中率: {stats[\"cache_hit_rate\"]:.1f}%')")
    print("    time.sleep(60)")
    print("```")


def demo_production_deployment():
    """生产环境部署示例"""
    print("\n" + "="*60)
    print("示例6: 生产环境部署")
    print("="*60)

    print("\n1. 系统要求")
    print("   - Python 3.8+")
    print("   - 磁盘空间: 至少1GB")
    print("   - 内存: 至少512MB")
    print("   - 安装依赖: pip install apscheduler")

    print("\n2. 启动脚本")
    print("```bash")
    print("#!/bin/bash")
    print("# start_cache_service.sh")
    print("")
    print("export ENABLE_CACHE='true'")
    print("export CACHE_DIR='./cache'")
    print("export CACHE_TIME='16:30'")
    print("export CLEANUP_TIME='02:00'")
    print("export BATCH_SIZE='100'")
    print("export MAX_WORKERS='8'")
    print("")
    print("python -c \"")
    print("from src.data.cached_fetcher import create_cached_fetcher")
    print("fetcher = create_cached_fetcher(use_cache=True)")
    print("scheduler = fetcher.start_cache_scheduler(")
    print("    cache_time='16:30',")
    print("    cleanup_time='02:00',")
    print("    batch_size=100,")
    print("    max_workers=8")
    print(")")
    print("scheduler.start()")
    print("\"")
    print("```")

    print("\n3. 监控脚本")
    print("```python")
    print("# monitor_cache.py")
    print("from src.data.cached_fetcher import create_cached_fetcher")
    print("import time")
    print("")
    print("fetcher = create_cached_fetcher(use_cache=True)")
    print("")
    print("while True:")
    print("    stats = fetcher.get_cache_stats()")
    print(f\"[{time.strftime('%Y-%m-%d %H:%M:%S')}]\")")
    print(f\"缓存命中率: {stats['cache_hit_rate']:.1f}%\")")
    print(f\"总请求: {stats['total_requests']}\")")
    print(f\"API请求: {stats['api_requests']}\")")
    print("    time.sleep(60)")
    print("```")

    print("\n4. 配置文件")
    print("```json")
    print("{")
    print('  "cache": {')
    print('    "enabled": true,')
    print('    "dir": "./cache",')
    print('    "ttl_hours": 24,')
    print('    "auto_cleanup": true')
    print("  },")
    print('  "scheduler": {')
    print('    "enabled": true,')
    print('    "cache_time": "16:30",')
    print('    "cleanup_time": "02:00",')
    print('    "batch_size": 100,')
    print('    "max_workers": 8')
    print("  }")
    print("}")
    print("```")


def demo_migration_guide():
    """迁移指南"""
    print("\n" + "="*60)
    print("示例7: 现有系统迁移")
    print("="*60)

    print("\n步骤1: 更新导入")
    print("```python")
    print("# 原有代码")
    print("from src.data.fetcher import DataFetcher")
    print("")
    print("# 新代码")
    print("from src.data.cached_fetcher import create_cached_fetcher")
    print("from src.agents.cached_trading_agent import run_daily_analysis")
    print("```")

    print("\n步骤2: 更新初始化")
    print("```python")
    print("# 原有代码")
    print("fetcher = DataFetcher()")
    print("")
    print("# 新代码")
    print("fetcher = create_cached_fetcher(")
    print("    use_cache=True,")
    print("    auto_cache=True")
    print(")")
    print("```")

    print("\n步骤3: 更新调用")
    print("```python")
    print("# 原有代码")
    print("result = run_daily_analysis()")
    print("")
    print("# 新代码（增加缓存参数）")
    print("result = run_daily_analysis(use_cache=True)")
    print("```")

    print("\n步骤4: 配置定时任务（可选）")
    print("```python")
    print("# 启动缓存定时任务")
    print("fetcher.start_cache_scheduler(")
    print("    cache_time='16:30',")
    print("    cleanup_time='02:00'")
    print(").start()")
    print("```")


def main():
    """主演示函数"""
    print("\n" + "🎯" * 30)
    print("      数据缓存系统使用指南")
    print("🎯" * 30 + "\n")

    print("本指南包含以下示例:")
    print("1. 基本使用 - 替换原有DataFetcher")
    print("2. 性能对比 - 展示缓存优势")
    print("3. 交易智能体 - 集成缓存功能")
    print("4. 定时任务 - 自动缓存调度")
    print("5. 高级功能 - 批量查询/管理")
    print("6. 生产部署 - 完整部署方案")
    print("7. 迁移指南 - 现有系统升级")

    try:
        demo_basic_usage()
        demo_cache_performance()
        demo_trading_agent_with_cache()
        demo_scheduler_setup()
        demo_advanced_features()
        demo_production_deployment()
        demo_migration_guide()

        print("\n" + "="*60)
        print("✅ 所有示例完成！")
        print("="*60)

        print("\n📚 快速开始:")
        print("1. 运行完整演示: python examples/cache_system_demo.py")
        print("2. 运行功能测试: python test_cache_system.py")
        print("3. 查看详细文档: docs/cache_system_guide.md")

        print("\n💡 使用建议:")
        print("1. 生产环境默认启用缓存")
        print("2. 设置定时任务自动缓存")
        print("3. 监控缓存命中率")
        print("4. 定期清理过期数据")

    except Exception as e:
        print(f"\n❌ 演示过程中出现错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()