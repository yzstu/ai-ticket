"""
定时任务调度器
每天收盘后自动缓存股票数据到本地
支持定时任务配置、任务监控、错误处理等功能
"""
import os
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Callable, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.interval import IntervalTrigger
    AP_SCHEDULER_AVAILABLE = True
except ImportError:
    AP_SCHEDULER_AVAILABLE = False
    logging.warning("APScheduler未安装，将使用简单定时器")

from src.data.cache.cache_manager import StockCacheManager, CacheConfig
from src.data.fetchers.fetcher import DataFetcher

logger = logging.getLogger(__name__)


class CacheTaskConfig:
    """缓存任务配置"""

    def __init__(
        self,
        # 缓存配置
        cache_dir: str = "./cache",
        max_cache_days: int = 30,
        auto_cleanup: bool = True,
        compress_data: bool = False,

        # 任务配置
        cache_time: str = "16:30",  # 每天缓存时间 (HH:MM)
        cleanup_time: str = "02:00",  # 每天清理时间 (HH:MM)
        batch_size: int = 100,  # 批处理大小
        max_workers: int = 4,  # 并发工作线程数
        retry_count: int = 3,  # 失败重试次数
        retry_delay: int = 60,  # 重试延迟(秒)

        # 监控配置
        enable_monitoring: bool = True,
        log_level: str = "INFO",
    ):
        self.cache_dir = cache_dir
        self.max_cache_days = max_cache_days
        self.auto_cleanup = auto_cleanup
        self.compress_data = compress_data

        self.cache_time = cache_time
        self.cleanup_time = cleanup_time
        self.batch_size = batch_size
        self.max_workers = max_workers
        self.retry_count = retry_count
        self.retry_delay = retry_delay

        self.enable_monitoring = enable_monitoring
        self.log_level = log_level


class CacheTaskScheduler:
    """缓存任务调度器 - 增强版"""

    def __init__(self, config: CacheTaskConfig):
        """
        初始化调度器

        Args:
            config: 任务配置
        """
        self.config = config
        self.cache_manager = None
        self.data_fetcher = None
        self.scheduler = None
        self._stop_event = threading.Event()
        self._stats = {
            'total_cache_tasks': 0,
            'successful_cache_tasks': 0,
            'failed_cache_tasks': 0,
            'total_cache_records': 0,
            'start_time': None,
            'last_cache_time': None,
            'is_running': False,
        }

        # 任务记录
        self._task_history = []
        self._max_history = 100

        # 日志缓冲
        self._log_buffer = []
        self._max_log_buffer = 1000  # 最大保存1000条日志

        # 初始化组件
        self._init_components()

    def _log_to_buffer(self, level: str, message: str):
        """记录日志到缓冲区"""
        try:
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'level': level,
                'message': message,
                'source': 'scheduler'
            }
            self._log_buffer.append(log_entry)

            # 限制缓冲区大小
            if len(self._log_buffer) > self._max_log_buffer:
                self._log_buffer.pop(0)
        except Exception as e:
            logger.error(f"Failed to log to buffer: {e}")

    def _init_components(self):
        """初始化组件"""
        # 初始化缓存管理器
        cache_config = CacheConfig(
            cache_dir=self.config.cache_dir,
            max_cache_days=self.config.max_cache_days,
            auto_cleanup=self.config.auto_cleanup,
            compress_data=self.config.compress_data,
        )
        self.cache_manager = StockCacheManager(cache_config)

        # 初始化数据获取器
        self.data_fetcher = DataFetcher()

        # 初始化调度器
        if AP_SCHEDULER_AVAILABLE:
            self.scheduler = BackgroundScheduler()
            logger.info("使用APScheduler调度器")
        else:
            logger.warning("APScheduler不可用，将使用简单定时器")

    def start(self):
        """启动调度器"""
        logger.info("启动缓存任务调度器")
        self._log_to_buffer("INFO", "启动缓存任务调度器")

        # 更新启动时间
        self._stats['start_time'] = datetime.now()

        if AP_SCHEDULER_AVAILABLE and self.scheduler:
            # 添加每日缓存任务
            cache_hour, cache_minute = map(int, self.config.cache_time.split(':'))
            self.scheduler.add_job(
                func=self._daily_cache_job,
                trigger=CronTrigger(hour=cache_hour, minute=cache_minute),
                id='daily_cache',
                name='每日股票数据缓存',
                max_instances=1,
                coalesce=True,
            )
            logger.info(f"已设置每日缓存任务: {self.config.cache_time}")

            # 添加每日清理任务
            cleanup_hour, cleanup_minute = map(int, self.config.cleanup_time.split(':'))
            self.scheduler.add_job(
                func=self._cleanup_job,
                trigger=CronTrigger(hour=cleanup_hour, minute=cleanup_minute),
                id='daily_cleanup',
                name='每日缓存清理',
                max_instances=1,
                coalesce=True,
            )
            logger.info(f"已设置每日清理任务: {self.config.cleanup_time}")

            # 启动调度器
            self.scheduler.start()
            self._stats['is_running'] = True
            logger.info("调度器已启动")
            self._log_to_buffer("INFO", "调度器已启动")
        else:
            # 使用简单定时器
            self._start_simple_scheduler()

    def _start_simple_scheduler(self):
        """启动简单定时器（无APScheduler时）"""
        logger.info("使用简单定时器模式")

        # 计算下次缓存时间
        now = datetime.now()
        cache_hour, cache_minute = map(int, self.config.cache_time.split(':'))
        next_cache = now.replace(hour=cache_hour, minute=cache_minute, second=0, microsecond=0)

        if next_cache <= now:
            next_cache += timedelta(days=1)

        cache_delay = (next_cache - now).total_seconds()
        logger.info(f"首次缓存将在 {cache_delay/3600:.1f} 小时后执行")

        # 计算下次清理时间
        cleanup_hour, cleanup_minute = map(int, self.config.cleanup_time.split(':'))
        next_cleanup = now.replace(hour=cleanup_hour, minute=cleanup_minute, second=0, microsecond=0)

        if next_cleanup <= now:
            next_cleanup += timedelta(days=1)

        cleanup_delay = (next_cleanup - now).total_seconds()

        # 启动定时任务
        def run_scheduler():
            cache_timer = None
            cleanup_timer = None

            def schedule_cache():
                self._daily_cache_job()
                schedule_next_cache()

            def schedule_cleanup():
                self._cleanup_job()
                schedule_next_cleanup()

            def schedule_next_cache():
                nonlocal cache_timer
                now = datetime.now()
                next_time = now.replace(hour=cache_hour, minute=cache_minute, second=0, microsecond=0)
                if next_time <= now:
                    next_time += timedelta(days=1)
                delay = (next_time - now).total_seconds()
                cache_timer = threading.Timer(delay, schedule_cache)
                cache_timer.start()

            def schedule_next_cleanup():
                nonlocal cleanup_timer
                now = datetime.now()
                next_time = now.replace(hour=cleanup_hour, minute=cleanup_minute, second=0, microsecond=0)
                if next_time <= now:
                    next_time += timedelta(days=1)
                delay = (next_time - now).total_seconds()
                cleanup_timer = threading.Timer(delay, schedule_cleanup)
                cleanup_timer.start()

            # 启动第一个任务
            if cache_delay <= cleanup_delay:
                threading.Timer(cache_delay, schedule_cache).start()
                threading.Timer(cleanup_delay, schedule_cleanup).start()
            else:
                threading.Timer(cleanup_delay, schedule_cleanup).start()
                threading.Timer(cache_delay, schedule_cache).start()

        run_scheduler()
        self._stats['is_running'] = True
        logger.info("调度器已启动")
        self._log_to_buffer("INFO", "调度器已启动")

    def stop(self):
        """停止调度器"""
        logger.info("停止缓存任务调度器")

        self._stop_event.set()

        if AP_SCHEDULER_AVAILABLE and self.scheduler:
            self.scheduler.shutdown(wait=False)
            logger.info("调度器已停止")

    def _daily_cache_job(self):
        """每日缓存任务"""
        logger.info("开始执行每日缓存任务")
        self._log_to_buffer("INFO", "开始执行每日缓存任务")

        start_time = datetime.now()
        task_stats = {
            'start_time': start_time,
            'total_stocks': 0,
            'cached_stocks': 0,
            'failed_stocks': 0,
            'errors': []
        }

        try:
            # 获取所有股票列表
            logger.info("获取股票列表...")
            stock_list = self.data_fetcher.get_stock_list()
            task_stats['total_stocks'] = len(stock_list)
            logger.info(f"共需缓存{len(stock_list)}只股票")

            # 分批处理
            batches = [
                stock_list[i:i + self.config.batch_size]
                for i in range(0, len(stock_list), self.config.batch_size)
            ]

            total_batches = len(batches)
            logger.info(f"分{total_batches}批处理，每批最多{self.config.batch_size}只股票")

            for batch_idx, batch in enumerate(batches, 1):
                logger.info(f"正在处理第{batch_idx}/{total_batches}批...")
                batch_success = self._process_cache_batch(batch)
                task_stats['cached_stocks'] += batch_success
                task_stats['failed_stocks'] += len(batch) - batch_success

                # 批次间隔
                if batch_idx < total_batches:
                    time.sleep(1)

            # 更新统计数据
            self._stats['total_cache_tasks'] += 1
            self._stats['successful_cache_tasks'] += 1
            self._stats['total_cache_records'] += task_stats['cached_stocks']
            self._stats['last_cache_time'] = datetime.now()

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            logger.info(
                f"缓存任务完成! 总耗时: {duration:.1f}秒, "
                f"成功: {task_stats['cached_stocks']}, "
                f"失败: {task_stats['failed_stocks']}"
            )
            self._log_to_buffer(
                "INFO",
                f"缓存任务完成 - 成功: {task_stats['cached_stocks']}, 失败: {task_stats['failed_stocks']}, 耗时: {duration:.1f}秒"
            )

        except Exception as e:
            task_stats['errors'].append(str(e))
            self._stats['failed_cache_tasks'] += 1
            logger.error(f"缓存任务执行失败: {e}", exc_info=True)

        # 记录任务统计
        self._log_task_stats('daily_cache', task_stats)

    def _process_cache_batch(self, stock_batch: List[Dict]) -> int:
        """
        处理一批股票的缓存

        Args:
            stock_batch: 股票批次

        Returns:
            int: 成功缓存的股票数量
        """
        success_count = 0

        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            # 提交所有任务
            future_to_stock = {
                executor.submit(self._cache_single_stock, stock): stock
                for stock in stock_batch
            }

            # 收集结果
            for future in as_completed(future_to_stock):
                stock = future_to_stock[future]
                try:
                    result = future.result(timeout=30)
                    if result:
                        success_count += 1
                except Exception as e:
                    logger.warning(f"缓存股票失败 {stock['code']}: {e}")

        return success_count

    def _process_cache_batch_with_options(
        self,
        stock_batch: List[Dict],
        batch_size: int = None,
        max_workers: int = None,
        data_types: Optional[List[str]] = None,
        skip_existing: bool = True,
        force_update: bool = False
    ) -> tuple:
        """
        处理一批股票的缓存（带选项）

        Args:
            stock_batch: 股票批次
            batch_size: 批处理大小
            max_workers: 最大工作线程数
            data_types: 数据类型列表
            skip_existing: 跳过已有缓存
            force_update: 强制更新

        Returns:
            tuple: (成功数量, 失败数量, 跳过数量, 失败列表, 成功列表)
        """
        success_count = 0
        failed_count = 0
        skipped_count = 0
        failed_list = []
        cached_list = []

        max_workers = max_workers or self.config.max_workers

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_stock = {
                executor.submit(
                    self._cache_single_stock_with_options,
                    stock,
                    data_types=data_types,
                    skip_existing=skip_existing,
                    force_update=force_update
                ): stock
                for stock in stock_batch
            }

            # 收集结果
            for future in as_completed(future_to_stock):
                stock = future_to_stock[future]
                try:
                    result = future.result(timeout=30)
                    if result['status'] == 'success':
                        success_count += 1
                        cached_list.append(stock['code'])
                    elif result['status'] == 'skipped':
                        skipped_count += 1
                    else:
                        failed_count += 1
                        failed_list.append({
                            'stock_code': stock['code'],
                            'error': result.get('error', 'Unknown error')
                        })
                except Exception as e:
                    failed_count += 1
                    logger.warning(f"缓存股票失败 {stock['code']}: {e}")
                    failed_list.append({
                        'stock_code': stock['code'],
                        'error': str(e)
                    })

        return success_count, failed_count, skipped_count, failed_list, cached_list

    def _cache_single_stock(self, stock: Dict) -> bool:
        """
        缓存单只股票的数据

        Args:
            stock: 股票信息

        Returns:
            bool: 是否成功
        """
        stock_code = stock['code']
        stock_name = stock['name']
        today = datetime.now().strftime('%Y-%m-%d')

        # 重试机制
        for attempt in range(self.config.retry_count):
            try:
                # 获取日线数据
                daily_data = self.data_fetcher.get_daily_data(stock_code, days=30)
                if daily_data is not None and not daily_data.empty:
                    # 转换DataFrame为字典
                    latest_data = daily_data.iloc[-1].to_dict()
                    self.cache_manager.cache_daily_data(stock_code, today, latest_data)

                # 获取资金流向数据
                capital_flow = self.data_fetcher.get_capital_flow(stock_code)
                if capital_flow:
                    self.cache_manager.cache_capital_flow(stock_code, today, capital_flow)

                # 获取市场情绪数据
                sentiment = self.data_fetcher.get_market_sentiment(stock_code)
                if sentiment:
                    self.cache_manager.cache_market_sentiment(stock_code, today, sentiment)

                return True

            except Exception as e:
                if attempt < self.config.retry_count - 1:
                    logger.warning(f"缓存失败，重试 {attempt + 1}/{self.config.retry_count}: {e}")
                    time.sleep(self.config.retry_delay)
                else:
                    logger.error(f"缓存失败，已达到最大重试次数: {e}")

        return False

    def _cache_single_stock_with_options(
        self,
        stock: Dict,
        data_types: Optional[List[str]] = None,
        skip_existing: bool = True,
        force_update: bool = False
    ) -> Dict:
        """
        缓存单只股票的数据（带选项）

        Args:
            stock: 股票信息
            data_types: 数据类型列表（daily/capital_flow/sentiment）
            skip_existing: 跳过已有缓存
            force_update: 强制更新

        Returns:
            Dict: {'status': 'success'|'skipped'|'failed', 'error'?: str}
        """
        stock_code = stock['code']
        stock_name = stock.get('name', '')
        today = datetime.now().strftime('%Y-%m-%d')

        # 默认数据类型
        if data_types is None:
            data_types = ['daily', 'capital_flow', 'sentiment']

        # 检查是否有现有缓存
        has_cache = False
        if skip_existing and not force_update:
            # 检查各类缓存是否存在
            for data_type in data_types:
                if data_type == 'daily':
                    if self.cache_manager.get_cached_daily_data(stock_code, today):
                        has_cache = True
                        break
                elif data_type == 'capital_flow':
                    if self.cache_manager.get_cached_capital_flow(stock_code, today):
                        has_cache = True
                        break
                elif data_type == 'sentiment':
                    if self.cache_manager.get_cached_market_sentiment(stock_code, today):
                        has_cache = True
                        break

            if has_cache:
                return {'status': 'skipped', 'reason': 'Existing cache found and skip_existing=True'}

        # 重试机制
        for attempt in range(self.config.retry_count):
            try:
                cached_any = False
                errors = []

                # 缓存日线数据
                if 'daily' in data_types:
                    try:
                        daily_data = self.data_fetcher.get_daily_data(stock_code, days=30)
                        if daily_data is not None and not daily_data.empty:
                            latest_data = daily_data.iloc[-1].to_dict()
                            self.cache_manager.cache_daily_data(stock_code, today, latest_data)
                            cached_any = True
                    except Exception as e:
                        error_msg = f"日线数据获取失败: {e}"
                        errors.append(error_msg)
                        logger.warning(f"{stock_code}: {error_msg}")

                # 缓存资金流向数据
                if 'capital_flow' in data_types:
                    try:
                        capital_flow = self.data_fetcher.get_capital_flow(stock_code)
                        if capital_flow:
                            self.cache_manager.cache_capital_flow(stock_code, today, capital_flow)
                            cached_any = True
                    except Exception as e:
                        error_msg = f"资金流向数据获取失败: {e}"
                        errors.append(error_msg)
                        logger.warning(f"{stock_code}: {error_msg}")

                # 缓存市场情绪数据
                if 'sentiment' in data_types:
                    try:
                        sentiment = self.data_fetcher.get_market_sentiment(stock_code)
                        if sentiment:
                            self.cache_manager.cache_market_sentiment(stock_code, today, sentiment)
                            cached_any = True
                    except Exception as e:
                        error_msg = f"市场情绪数据获取失败: {e}"
                        errors.append(error_msg)
                        logger.warning(f"{stock_code}: {error_msg}")

                # 如果至少成功缓存了一种数据类型，则认为成功
                if cached_any:
                    return {'status': 'success'}
                else:
                    # 所有数据类型都失败了
                    if attempt < self.config.retry_count - 1:
                        logger.warning(f"{stock_code}: 缓存失败，重试 {attempt + 1}/{self.config.retry_count}")
                        time.sleep(self.config.retry_delay)
                    else:
                        return {
                            'status': 'failed',
                            'error': '所有数据类型都获取失败: ' + '; '.join(errors)
                        }

            except Exception as e:
                if attempt < self.config.retry_count - 1:
                    logger.warning(f"{stock_code}: 缓存失败，重试 {attempt + 1}/{self.config.retry_count}: {e}")
                    time.sleep(self.config.retry_delay)
                else:
                    logger.error(f"{stock_code}: 缓存失败，已达到最大重试次数: {e}")
                    return {
                        'status': 'failed',
                        'error': f'缓存失败: {str(e)}'
                    }

        # 如果到达这里，说明所有重试都失败了
        return {
            'status': 'failed',
            'error': '达到最大重试次数，缓存失败'
        }

    def _cleanup_job(self):
        """清理任务"""
        logger.info("开始执行清理任务")
        self._log_to_buffer("INFO", "开始执行清理任务")

        try:
            deleted_count = self.cache_manager.cleanup_expired_cache()
            logger.info(f"清理任务完成，删除{deleted_count}条过期记录")
            self._log_to_buffer("INFO", f"清理任务完成，删除{deleted_count}条过期记录")
        except Exception as e:
            logger.error(f"清理任务执行失败: {e}", exc_info=True)
            self._log_to_buffer("ERROR", f"清理任务执行失败: {str(e)}")

    def _log_task_stats(self, task_name: str, stats: Dict):
        """记录任务统计"""
        logger.info(f"\n=== {task_name} 任务统计 ===")
        logger.info(f"开始时间: {stats['start_time']}")
        logger.info(f"总股票数: {stats['total_stocks']}")
        logger.info(f"成功缓存: {stats['cached_stocks']}")
        logger.info(f"失败数量: {stats['failed_stocks']}")

        if stats['errors']:
            logger.info(f"错误数量: {len(stats['errors'])}")
            for error in stats['errors'][:5]:  # 只记录前5个错误
                logger.info(f"  - {error}")

        end_time = datetime.now()
        duration = (end_time - stats['start_time']).total_seconds()
        logger.info(f"总耗时: {duration:.1f}秒")
        logger.info("=" * 30)

    def get_stats(self) -> Dict:
        """获取调度器统计信息"""
        stats = self._stats.copy()

        # 添加缓存统计
        if self.cache_manager:
            cache_stats = self.cache_manager.get_cache_stats()
            stats['cache_stats'] = cache_stats

        # 添加运行时间
        if stats['start_time']:
            runtime = datetime.now() - stats['start_time']
            stats['runtime_hours'] = runtime.total_seconds() / 3600

        return stats

    def get_recent_logs(self, lines: int = 100) -> List[Dict]:
        """
        获取最近的日志记录

        Args:
            lines: 获取最近多少条日志

        Returns:
            List[Dict]: 日志列表，最新的在前面
        """
        try:
            # 获取最新的日志
            recent_logs = self._log_buffer[-lines:] if lines < len(self._log_buffer) else self._log_buffer
            # 倒序排列，最新的在前
            return list(reversed(recent_logs))
        except Exception as e:
            logger.error(f"Failed to get recent logs: {e}")
            return []

    def run_cache_manually(
        self,
        stock_codes: Optional[List[str]] = None,
        batch_size: Optional[int] = None,
        max_workers: Optional[int] = None,
        data_types: Optional[List[str]] = None,
        skip_existing: bool = True,
        force_update: bool = False
    ) -> Dict:
        """
        手动运行缓存任务

        Args:
            stock_codes: 指定股票代码列表，为None则缓存所有股票
            batch_size: 批处理大小
            max_workers: 最大工作线程数
            data_types: 数据类型列表（daily/capital_flow/sentiment）
            skip_existing: 跳过已有缓存
            force_update: 强制更新

        Returns:
            Dict: 任务执行统计
        """
        logger.info("手动执行缓存任务")

        start_time = datetime.now()

        # 获取股票列表
        if stock_codes:
            stock_list = [{'code': code, 'name': ''} for code in stock_codes]
        else:
            stock_list = self.data_fetcher.get_stock_list()

        logger.info(f"手动缓存{len(stock_list)}只股票")

        # 使用提供的配置或默认配置
        batch_size = batch_size or self.config.batch_size
        max_workers = max_workers or self.config.max_workers

        # 执行缓存
        task_stats = {
            'start_time': start_time,
            'total_stocks': len(stock_list),
            'cached_stocks': 0,
            'failed_stocks': 0,
            'skipped_stocks': 0,
            'failed_list': [],
            'cached_list': []
        }

        # 批量处理股票
        success_count, failed_count, skipped_count, failed_list, cached_list = \
            self._process_cache_batch_with_options(
                stock_list,
                batch_size=batch_size,
                max_workers=max_workers,
                data_types=data_types,
                skip_existing=skip_existing,
                force_update=force_update
            )

        task_stats['cached_stocks'] = success_count
        task_stats['failed_stocks'] = failed_count
        task_stats['skipped_stocks'] = skipped_count
        task_stats['failed_list'] = failed_list
        task_stats['cached_list'] = cached_list

        logger.info(
            f"手动缓存完成! 总耗时: {(datetime.now() - start_time).total_seconds():.1f}秒, "
            f"成功: {success_count}, 失败: {failed_count}, 跳过: {skipped_count}"
        )

        return task_stats

    def export_cache(self, output_path: str, days: int = 7) -> bool:
        """
        导出缓存数据

        Args:
            output_path: 输出文件路径
            days: 导出最近几天的数据

        Returns:
            bool: 是否成功导出
        """
        if not self.cache_manager:
            logger.error("缓存管理器未初始化")
            return False

        logger.info(f"导出缓存数据到 {output_path}")
        return self.cache_manager.export_cache_to_json(output_path, days)


def create_scheduler(
    cache_dir: str = "./cache",
    cache_time: str = "16:30",
    cleanup_time: str = "02:00",
    batch_size: int = 100,
    max_workers: int = 4
) -> CacheTaskScheduler:
    """
    创建调度器的便捷函数

    Args:
        cache_dir: 缓存目录
        cache_time: 缓存时间 (HH:MM)
        cleanup_time: 清理时间 (HH:MM)
        batch_size: 批处理大小
        max_workers: 最大工作线程数

    Returns:
        CacheTaskScheduler: 调度器实例
    """
    config = CacheTaskConfig(
        cache_dir=cache_dir,
        cache_time=cache_time,
        cleanup_time=cleanup_time,
        batch_size=batch_size,
        max_workers=max_workers,
    )

    return CacheTaskScheduler(config)