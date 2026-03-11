#!/usr/bin/env python3
"""
FastAPI项目 - API客户端示例
演示如何使用API接口调用股票分析功能
"""
import requests
import json
from typing import List, Dict, Any
import time


class StockAIServiceClient:
    """股票AI服务API客户端"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        """
        初始化客户端

        Args:
            base_url: API服务地址
        """
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()

    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        response = self.session.get(f"{self.base_url}/system/health")
        response.raise_for_status()
        return response.json()

    def get_stock_list(self, use_cache: bool = True) -> List[Dict]:
        """获取股票列表"""
        response = self.session.get(
            f"{self.base_url}/stocks/list",
            params={"use_cache": use_cache}
        )
        response.raise_for_status()
        return response.json()

    def get_daily_data(self, stock_code: str, days: int = 30, **params) -> Dict[str, Any]:
        """获取日线数据"""
        response = self.session.get(
            f"{self.base_url}/stocks/{stock_code}/daily",
            params={"days": days, **params}
        )
        response.raise_for_status()
        return response.json()['data']

    def analyze_stocks(self, **params) -> Dict[str, Any]:
        """执行股票分析"""
        response = self.session.post(
            f"{self.base_url}/analysis/daily",
            json=params
        )
        response.raise_for_status()
        return response.json()['data']

    def get_top_stocks(self, n: int = 10, **params) -> Dict[str, Any]:
        """获取Top-N推荐股票"""
        response = self.session.get(
            f"{self.base_url}/analysis/top",
            params={"n": n, **params}
        )
        response.raise_for_status()
        return response.json()['data']

    def analyze_sector(self, sector: str, n: int = 20, **params) -> Dict[str, Any]:
        """分析指定板块"""
        response = self.session.get(
            f"{self.base_url}/analysis/sector/{sector}",
            params={"n": n, **params}
        )
        response.raise_for_status()
        return response.json()['data']

    def analyze_custom_stocks(self, stock_codes: List[str], **params) -> Dict[str, Any]:
        """分析自定义股票列表"""
        stock_codes_str = ','.join(stock_codes)
        response = self.session.get(
            f"{self.base_url}/analysis/custom",
            params={"stock_codes": stock_codes_str, **params}
        )
        response.raise_for_status()
        return response.json()['data']

    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        response = self.session.get(f"{self.base_url}/cache/stats")
        response.raise_for_status()
        return response.json()

    def cleanup_cache(self, dry_run: bool = False) -> Dict[str, Any]:
        """清理缓存"""
        response = self.session.post(
            f"{self.base_url}/cache/cleanup",
            json={"dry_run": dry_run}
        )
        response.raise_for_status()
        return response.json()

    def start_scheduler(self, **config) -> Dict[str, Any]:
        """启动定时任务"""
        response = self.session.post(
            f"{self.base_url}/scheduler/start",
            json={"config": config}
        )
        response.raise_for_status()
        return response.json()

    def get_scheduler_status(self) -> Dict[str, Any]:
        """获取调度器状态"""
        response = self.session.get(f"{self.base_url}/scheduler/status")
        response.raise_for_status()
        return response.json()

    def manual_cache(self, stock_codes: List[str] = None, **params) -> Dict[str, Any]:
        """手动执行缓存"""
        response = self.session.post(
            f"{self.base_url}/scheduler/manual-cache",
            json={
                "stock_codes": stock_codes,
                **params
            }
        )
        response.raise_for_status()
        return response.json()


def demo_basic_usage():
    """基本使用示例"""
    print("\n" + "="*60)
    print("示例1: 基本使用")
    print("="*60)

    client = StockAIServiceClient()

    # 健康检查
    print("\n1. 健康检查")
    health = client.health_check()
    print(f"   系统状态: {health['status']}")
    print(f"   服务组件: {health['services']}")

    # 获取股票列表
    print("\n2. 获取股票列表")
    stocks = client.get_stock_list()
    print(f"   股票总数: {len(stocks)}")
    print(f"   示例股票: {stocks[0] if stocks else 'N/A'}")

    # 获取单只股票数据
    print("\n3. 获取单只股票数据")
    stock_code = "600519"
    data = client.get_daily_data(stock_code, days=5)
    print(f"   股票代码: {stock_code}")
    print(f"   数据记录数: {data['data_count']}")


def demo_stock_analysis():
    """股票分析示例"""
    print("\n" + "="*60)
    print("示例2: 股票分析")
    print("="*60)

    client = StockAIServiceClient()

    # 分析Top-N股票
    print("\n1. 分析Top-N股票")
    result = client.get_top_stocks(n=5, use_cache=True)
    print(f"   分析日期: {result['date']}")
    print(f"   推荐股票数: {result['total_recommended']}")
    print(f"   分析类型: {result['analysis_type']}")

    if result['recommended_stocks']:
        top_stock = result['recommended_stocks'][0]
        print(f"\n   最佳推荐: {top_stock['code']} {top_stock['name']}")
        print(f"   评分: {top_stock['score']:.2f}")
        print(f"   建议: {top_stock['recommendation']}")
        print(f"   价格: {top_stock['price']}")

    # 分析自定义股票列表
    print("\n2. 分析自定义股票列表")
    custom_stocks = ["600519", "000001", "600036", "000858"]
    result = client.analyze_custom_stocks(
        stock_codes=custom_stocks,
        use_parallel=True,
        use_cache=True
    )
    print(f"   自定义股票数: {result['custom_stock_count']}")
    print(f"   推荐股票数: {result['total_recommended']}")


def demo_sector_analysis():
    """板块分析示例"""
    print("\n" + "="*60)
    print("示例3: 板块分析")
    print("="*60)

    client = StockAIServiceClient()

    # 分析蓝筹股
    print("\n1. 分析蓝筹股板块")
    result = client.analyze_sector(
        sector="blue_chips",
        n=10,
        use_parallel=True
    )
    print(f"   板块: {result['sector']}")
    print(f"   代码范围: {result['code_range']}")
    print(f"   推荐股票数: {result['total_recommended']}")


def demo_cache_management():
    """缓存管理示例"""
    print("\n" + "="*60)
    print("示例4: 缓存管理")
    print("="*60)

    client = StockAIServiceClient()

    # 查看缓存统计
    print("\n1. 查看缓存统计")
    stats = client.get_cache_stats()
    print(f"   总请求数: {stats['total_requests']}")
    print(f"   缓存命中: {stats['cache_hits']}")
    print(f"   命中率: {stats['cache_hit_rate']:.1f}%")
    print(f"   数据库大小: {stats['db_size_mb']} MB")

    # 清理过期缓存（预览模式）
    print("\n2. 清理过期缓存（预览）")
    result = client.cleanup_cache(dry_run=True)
    print(f"   预览结果: {result['message']}")


def demo_scheduler_management():
    """定时任务管理示例"""
    print("\n" + "="*60)
    print("示例5: 定时任务管理")
    print("="*60)

    client = StockAIServiceClient()

    # 查看调度器状态
    print("\n1. 查看调度器状态")
    status = client.get_scheduler_status()
    print(f"   运行状态: {'运行中' if status['running'] else '已停止'}")
    print(f"   任务数量: {status['has_jobs']}")

    # 手动执行缓存
    print("\n2. 手动执行缓存任务")
    custom_stocks = ["600519", "000001", "600036"]
    result = client.manual_cache(
        stock_codes=custom_stocks,
        batch_size=10,
        max_workers=2
    )
    print(f"   总股票数: {result['total_stocks']}")
    print(f"   成功缓存: {result['cached_stocks']}")
    print(f"   失败数量: {result['failed_stocks']}")


def demo_performance_test():
    """性能测试示例"""
    print("\n" + "="*60)
    print("示例6: 性能测试")
    print("="*60)

    client = StockAIServiceClient()

    # 测试1: 无缓存查询
    print("\n1. 测试无缓存查询性能")
    start_time = time.time()
    for i in range(3):
        client.get_daily_data("600519", days=5, use_cache=False)
    duration_no_cache = (time.time() - start_time) / 3
    print(f"   平均耗时: {duration_no_cache:.3f}秒")

    # 测试2: 缓存查询
    print("\n2. 测试缓存查询性能")
    start_time = time.time()
    for i in range(3):
        client.get_daily_data("600519", days=5, use_cache=True)
    duration_cache = (time.time() - start_time) / 3
    print(f"   平均耗时: {duration_cache:.3f}秒")

    # 性能对比
    if duration_cache > 0:
        speedup = duration_no_cache / duration_cache
        print(f"\n   性能提升: {speedup:.1f}倍")


def demo_error_handling():
    """错误处理示例"""
    print("\n" + "="*60)
    print("示例7: 错误处理")
    print("="*60)

    client = StockAIServiceClient()

    # 测试无效股票代码
    print("\n1. 测试无效股票代码")
    try:
        client.get_daily_data("999999", days=5)
    except requests.exceptions.HTTPError as e:
        print(f"   捕获错误: {e.response.status_code}")
        print(f"   错误信息: {e.response.json()}")

    # 测试无效的板块代码
    print("\n2. 测试无效的板块代码")
    try:
        client.analyze_sector("invalid_sector", n=10)
    except requests.exceptions.HTTPError as e:
        print(f"   捕获错误: {e.response.status_code}")
        print(f"   错误信息: {e.response.json()}")


def main():
    """主演示函数"""
    print("\n" + "🎯" * 30)
    print("      FastAPI服务API客户端演示")
    print("🎯" * 30 + "\n")

    print("本演示将展示:")
    print("1. 基本使用 - 健康检查、获取数据")
    print("2. 股票分析 - Top-N、自定义列表")
    print("3. 板块分析 - 蓝筹股、科技股等")
    print("4. 缓存管理 - 统计、清理")
    print("5. 定时任务 - 启动、手动执行")
    print("6. 性能测试 - 缓存效果对比")
    print("7. 错误处理 - 异常捕获")

    try:
        # 运行所有演示
        demo_basic_usage()
        demo_stock_analysis()
        demo_sector_analysis()
        demo_cache_management()
        demo_scheduler_management()
        demo_performance_test()
        demo_error_handling()

        print("\n" + "="*60)
        print("✅ 所有演示完成！")
        print("="*60)

        print("\n💡 使用提示:")
        print("1. 确保API服务正在运行: python run.py")
        print("2. API文档地址: http://localhost:8000/docs")
        print("3. 健康检查地址: http://localhost:8000/system/health")

        print("\n📚 更多信息:")
        print("  - API文档: http://localhost:8000/docs")
        print("  - 使用指南: API_GUIDE.md")

    except requests.exceptions.ConnectionError:
        print("\n❌ 无法连接到API服务")
        print("请确保服务正在运行: python run.py")
    except Exception as e:
        print(f"\n❌ 演示过程中出现错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()