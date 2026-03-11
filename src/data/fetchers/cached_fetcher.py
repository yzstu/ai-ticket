"""
缓存增强版数据获取器
集成缓存功能的数据获取器
先从缓存查询，缓存未命中再从API获取，并自动回写缓存
"""
import os
import time
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import pandas as pd

from .fetcher import DataFetcher
from .cache_manager import StockCacheManager, CacheConfig
from .cache_scheduler import create_scheduler, CacheTaskConfig

logger = logging.getLogger(__name__)


class CachedDataFetcher:
    """缓存增强版数据获取器"""

    def __init__(
        self,
        use_cache: bool = True,
        cache_dir: str = "./cache",
        auto_cache: bool = True,
        cache_ttl_hours: int = 24,  # 缓存有效期(小时)
        fallback_to_api: bool = True,  # 缓存未命中时是否回退到API
    ):
        """
        初始化缓存数据获取器

        Args:
            use_cache: 是否启用缓存
            cache_dir: 缓存目录
            auto_cache: 是否自动缓存API数据
            cache_ttl_hours: 缓存有效期
            fallback_to_api: 缓存未命中时回退到API
        """
        self.use_cache = use_cache
        self.cache_ttl_hours = cache_ttl_hours
        self.fallback_to_api = fallback_to_api
        self.auto_cache = auto_cache

        # 初始化基础数据获取器
        self.data_fetcher = DataFetcher()

        # 初始化缓存管理器
        self.cache_manager = None
        if self.use_cache:
            cache_config = CacheConfig(
                cache_dir=cache_dir,
                max_cache_days=30,
                auto_cleanup=True,
                compress_data=False
            )
            self.cache_manager = StockCacheManager(cache_config)
            logger.info(f"缓存数据获取器初始化完成，缓存目录: {cache_dir}")

        # 统计信息
        self._stats = {
            'total_requests': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'api_requests': 0,
            'cache_writes': 0,
        }

    def get_stock_list(self, use_cache_first: bool = True) -> List[Dict]:
        """
        获取股票列表（支持缓存）

        Args:
            use_cache_first: 是否优先使用缓存

        Returns:
            List of stock information
        """
        self._stats['total_requests'] += 1

        if self.use_cache and use_cache_first:
            # 尝试从缓存获取（这里简化处理，实际可以缓存股票列表）
            logger.debug("使用缓存获取股票列表")

        # 从API获取
        logger.debug("从API获取股票列表")
        self._stats['api_requests'] += 1

        try:
            stock_list = self.data_fetcher.get_stock_list()

            # 自动缓存股票基础信息
            if self.use_cache and self.auto_cache and stock_list:
                self.cache_manager.cache_stock_info(stock_list)
                logger.info(f"已缓存{len(stock_list)}只股票基础信息")

            return stock_list

        except Exception as e:
            logger.error(f"获取股票列表失败: {e}")
            raise

    def get_daily_data(
        self,
        stock_code: str,
        days: int = 30,
        force_refresh: bool = False
    ) -> Optional[pd.DataFrame]:
        """
        获取日线数据（优先从缓存）

        Args:
            stock_code: 股票代码
            days: 数据天数
            force_refresh: 是否强制刷新（跳过缓存）

        Returns:
            DataFrame with daily data, or None if not found
        """
        self._stats['total_requests'] += 1

        # 如果启用缓存且不强制刷新，先尝试从缓存获取
        if self.use_cache and not force_refresh:
            today = datetime.now().strftime('%Y-%m-%d')
            cached_data = self.cache_manager.get_cached_daily_data(stock_code, today)

            if cached_data:
                self._stats['cache_hits'] += 1
                logger.debug(f"缓存命中 {stock_code}")

                # 转换缓存数据为DataFrame
                try:
                    df = pd.DataFrame([cached_data])
                    return df
                except Exception as e:
                    logger.warning(f"解析缓存数据失败: {e}")

            self._stats['cache_misses'] += 1
            logger.debug(f"缓存未命中 {stock_code}")

        # 缓存未命中或禁用缓存，从API获取
        if self.fallback_to_api:
            logger.debug(f"从API获取 {stock_code} 的日线数据")
            self._stats['api_requests'] += 1

            try:
                df = self.data_fetcher.get_daily_data(stock_code, days)

                # 自动缓存数据
                if self.use_cache and self.auto_cache and df is not None and not df.empty:
                    today = datetime.now().strftime('%Y-%m-%d')
                    latest_data = df.iloc[-1].to_dict()

                    success = self.cache_manager.cache_daily_data(stock_code, today, latest_data)
                    if success:
                        self._stats['cache_writes'] += 1
                        logger.debug(f"已缓存 {stock_code} 的日线数据")

                return df

            except Exception as e:
                logger.error(f"从API获取 {stock_code} 数据失败: {e}")
                return None

        return None

    def get_capital_flow(
        self,
        stock_code: str,
        force_refresh: bool = False
    ) -> Optional[Dict]:
        """
        获取资金流向数据（优先从缓存）

        Args:
            stock_code: 股票代码
            force_refresh: 是否强制刷新

        Returns:
            Capital flow data dict, or None if not found
        """
        self._stats['total_requests'] += 1

        if self.use_cache and not force_refresh:
            today = datetime.now().strftime('%Y-%m-%d')
            cached_data = self.cache_manager.get_cached_capital_flow(stock_code, today)

            if cached_data:
                self._stats['cache_hits'] += 1
                logger.debug(f"资金流向缓存命中 {stock_code}")
                return cached_data

            self._stats['cache_misses'] += 1
            logger.debug(f"资金流向缓存未命中 {stock_code}")

        if self.fallback_to_api:
            logger.debug(f"从API获取 {stock_code} 的资金流向数据")
            self._stats['api_requests'] += 1

            try:
                data = self.data_fetcher.get_capital_flow(stock_code)

                # 自动缓存数据
                if self.use_cache and self.auto_cache and data:
                    today = datetime.now().strftime('%Y-%m-%d')
                    success = self.cache_manager.cache_capital_flow(stock_code, today, data)
                    if success:
                        self._stats['cache_writes'] += 1
                        logger.debug(f"已缓存 {stock_code} 的资金流向数据")

                return data

            except Exception as e:
                logger.error(f"从API获取 {stock_code} 资金流向失败: {e}")
                return None

        return None

    def get_market_sentiment(
        self,
        stock_code: str,
        force_refresh: bool = False
    ) -> Optional[Dict]:
        """
        获取市场情绪数据（优先从缓存）

        Args:
            stock_code: 股票代码
            force_refresh: 是否强制刷新

        Returns:
            Market sentiment data dict, or None if not found
        """
        self._stats['total_requests'] += 1

        if self.use_cache and not force_refresh:
            today = datetime.now().strftime('%Y-%m-%d')
            cached_data = self.cache_manager.get_cached_market_sentiment(stock_code, today)

            if cached_data:
                self._stats['cache_hits'] += 1
                logger.debug(f"市场情绪缓存命中 {stock_code}")
                return cached_data

            self._stats['cache_misses'] += 1
            logger.debug(f"市场情绪缓存未命中 {stock_code}")

        if self.fallback_to_api:
            logger.debug(f"从API获取 {stock_code} 的市场情绪数据")
            self._stats['api_requests'] += 1

            try:
                data = self.data_fetcher.get_market_sentiment(stock_code)

                # 自动缓存数据
                if self.use_cache and self.auto_cache and data:
                    today = datetime.now().strftime('%Y-%m-%d')
                    success = self.cache_manager.cache_market_sentiment(stock_code, today, data)
                    if success:
                        self._stats['cache_writes'] += 1
                        logger.debug(f"已缓存 {stock_code} 的市场情绪数据")

                return data

            except Exception as e:
                logger.error(f"从API获取 {stock_code} 市场情绪失败: {e}")
                return None

        return None

    def batch_get_daily_data(
        self,
        stock_codes: List[str],
        days: int = 30,
        use_cache_first: bool = True,
        max_workers: int = 4
    ) -> Dict[str, Optional[pd.DataFrame]]:
        """
        批量获取日线数据（支持缓存）

        Args:
            stock_codes: 股票代码列表
            days: 数据天数
            use_cache_first: 是否优先使用缓存
            max_workers: 并发线程数

        Returns:
            Dict mapping stock_code to DataFrame
        """
        results = {}
        cache_hits = 0
        api_requests = 0

        # 导入ThreadPoolExecutor
        from concurrent.futures import ThreadPoolExecutor, as_completed

        # 定义获取单个股票数据的函数
        def get_single_stock_data(stock_code: str) -> tuple:
            if use_cache_first and self.use_cache:
                today = datetime.now().strftime('%Y-%m-%d')
                cached_data = self.cache_manager.get_cached_daily_data(stock_code, today)

                if cached_data:
                    return stock_code, cached_data, 'cache', None

            # 从API获取
            try:
                df = self.data_fetcher.get_daily_data(stock_code, days)
                if df is not None and not df.empty and self.use_cache and self.auto_cache:
                    today = datetime.now().strftime('%Y-%m-%d')
                    latest_data = df.iloc[-1].to_dict()
                    self.cache_manager.cache_daily_data(stock_code, today, latest_data)

                return stock_code, df, 'api', None

            except Exception as e:
                return stock_code, None, 'error', str(e)

        # 并发执行
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_stock = {
                executor.submit(get_single_stock_data, code): code
                for code in stock_codes
            }

            for future in as_completed(future_to_stock):
                stock_code, data, source, error = future.result()
                results[stock_code] = data

                if source == 'cache':
                    cache_hits += 1
                elif source == 'api':
                    api_requests += 1

        # 更新统计
        self._stats['cache_hits'] += cache_hits
        self._stats['api_requests'] += api_requests
        self._stats['total_requests'] += len(stock_codes)

        logger.info(
            f"批量获取完成: 总数{len(stock_codes)}, "
            f"缓存命中{cache_hits}, API请求{api_requests}"
        )

        return results

    def get_cache_stats(self) -> Dict:
        """获取缓存统计信息"""
        stats = self._stats.copy()

        # 计算命中率
        total_requests = stats['total_requests']
        if total_requests > 0:
            stats['cache_hit_rate'] = stats['cache_hits'] / total_requests * 100
        else:
            stats['cache_hit_rate'] = 0

        # 添加缓存管理器统计
        if self.use_cache and self.cache_manager:
            cache_stats = self.cache_manager.get_cache_stats()
            stats['cache_manager_stats'] = cache_stats

        return stats

    def clear_cache(self) -> bool:
        """清空所有缓存"""
        if not self.use_cache or not self.cache_manager:
            logger.warning("缓存未启用")
            return False

        success = self.cache_manager.clear_all_cache()
        if success:
            logger.info("所有缓存已清空")

        return success

    def cleanup_expired_cache(self) -> int:
        """清理过期缓存"""
        if not self.use_cache or not self.cache_manager:
            return 0

        deleted_count = self.cache_manager.cleanup_expired_cache()
        logger.info(f"清理了{deleted_count}条过期缓存记录")

        return deleted_count

    def export_cache(self, output_path: str, days: int = 7) -> bool:
        """导出缓存数据"""
        if not self.use_cache or not self.cache_manager:
            logger.warning("缓存未启用")
            return False

        return self.cache_manager.export_cache_to_json(output_path, days)

    def enable_auto_cache(self):
        """启用自动缓存"""
        self.auto_cache = True
        logger.info("自动缓存已启用")

    def disable_auto_cache(self):
        """禁用自动缓存"""
        self.auto_cache = False
        logger.info("自动缓存已禁用")

    def start_cache_scheduler(
        self,
        cache_time: str = "16:30",
        cleanup_time: str = "02:00",
        batch_size: int = 100,
        max_workers: int = 4
    ):
        """
        启动缓存定时任务

        Args:
            cache_time: 每日缓存时间 (HH:MM)
            cleanup_time: 每日清理时间 (HH:MM)
            batch_size: 批处理大小
            max_workers: 最大工作线程数
        """
        if not self.use_cache:
            logger.warning("缓存未启用，无法启动定时任务")
            return None

        # 检查APScheduler
        try:
            from apscheduler.schedulers.background import BackgroundScheduler
        except ImportError:
            logger.error("APScheduler未安装，无法启动定时任务")
            logger.info("请运行: pip install apscheduler")
            return None

        # 创建调度器
        scheduler = create_scheduler(
            cache_dir=self.cache_manager.config.cache_dir,
            cache_time=cache_time,
            cleanup_time=cleanup_time,
            batch_size=batch_size,
            max_workers=max_workers
        )

        # 启动调度器
        scheduler.start()

        logger.info(f"缓存定时任务已启动，每天{cache_time}执行缓存，{cleanup_time}执行清理")

        return scheduler


def create_cached_fetcher(
    use_cache: bool = True,
    cache_dir: str = "./cache",
    auto_cache: bool = True,
    cache_ttl_hours: int = 24,
    fallback_to_api: bool = True
) -> CachedDataFetcher:
    """
    创建缓存数据获取器的便捷函数

    Args:
        use_cache: 是否启用缓存
        cache_dir: 缓存目录
        auto_cache: 是否自动缓存API数据
        cache_ttl_hours: 缓存有效期
        fallback_to_api: 缓存未命中时回退到API

    Returns:
        CachedDataFetcher: 缓存数据获取器实例
    """
    return CachedDataFetcher(
        use_cache=use_cache,
        cache_dir=cache_dir,
        auto_cache=auto_cache,
        cache_ttl_hours=cache_ttl_hours,
        fallback_to_api=fallback_to_api
    )