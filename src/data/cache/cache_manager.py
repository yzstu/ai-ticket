"""
股票数据缓存管理器
基于SQLite实现的本地数据缓存系统
支持自动缓存更新、缓存查询、缓存失效策略等功能
"""
import os
import sqlite3
import json
import time
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from contextlib import contextmanager
import logging
from threading import Lock
import hashlib


logger = logging.getLogger(__name__)


class CacheConfig:
    """缓存配置"""

    def __init__(
        self,
        cache_dir: str = "./cache",
        db_name: str = "stock_cache.db",
        max_cache_days: int = 30,  # 缓存保留天数
        auto_cleanup: bool = True,  # 自动清理过期数据
        cleanup_interval: int = 24,  # 清理间隔(小时)
        compress_data: bool = False,  # 压缩数据
        enable_wal_mode: bool = True,  # 启用WAL模式提升并发性能
    ):
        self.cache_dir = cache_dir
        self.db_path = os.path.join(cache_dir, db_name)
        self.max_cache_days = max_cache_days
        self.auto_cleanup = auto_cleanup
        self.cleanup_interval = cleanup_interval
        self.compress_data = compress_data
        self.enable_wal_mode = enable_wal_mode

        # 确保缓存目录存在
        os.makedirs(cache_dir, exist_ok=True)


class StockCacheManager:
    """股票数据缓存管理器"""

    def __init__(self, config: CacheConfig):
        """
        初始化缓存管理器

        Args:
            config: 缓存配置
        """
        self.config = config
        self._lock = Lock()
        self._init_database()
        logger.info(f"缓存管理器初始化完成: {self.config.db_path}")

    def _init_database(self):
        """初始化数据库表结构"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 股票基础信息表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS stock_info (
                    code TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    market TEXT,
                    industry TEXT,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 日线数据缓存表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS daily_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    stock_code TEXT NOT NULL,
                    trade_date DATE NOT NULL,
                    data_json TEXT NOT NULL,  -- JSON格式存储OHLCV和技术指标
                    data_hash TEXT NOT NULL,  -- 数据哈希值，用于检测变化
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(stock_code, trade_date)
                )
            """)

            # 资金流向数据缓存表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS capital_flow (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    stock_code TEXT NOT NULL,
                    trade_date DATE NOT NULL,
                    data_json TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(stock_code, trade_date)
                )
            """)

            # 市场情绪数据缓存表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS market_sentiment (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    stock_code TEXT NOT NULL,
                    trade_date DATE NOT NULL,
                    data_json TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(stock_code, trade_date)
                )
            """)

            # 缓存统计表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cache_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cache_type TEXT NOT NULL,  -- daily_data/capital_flow/sentiment
                    stock_code TEXT NOT NULL,
                    trade_date DATE NOT NULL,
                    hit_count INTEGER DEFAULT 0,
                    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(cache_type, stock_code, trade_date)
                )
            """)

            # 创建索引
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_daily_data_code_date ON daily_data(stock_code, trade_date)",
                "CREATE INDEX IF NOT EXISTS idx_daily_data_updated ON daily_data(updated_at)",
                "CREATE INDEX IF NOT EXISTS idx_capital_flow_code_date ON capital_flow(stock_code, trade_date)",
                "CREATE INDEX IF NOT EXISTS idx_sentiment_code_date ON market_sentiment(stock_code, trade_date)",
                "CREATE INDEX IF NOT EXISTS idx_stats_type_code_date ON cache_stats(cache_type, stock_code, trade_date)",
            ]

            for index_sql in indexes:
                cursor.execute(index_sql)

            # 启用WAL模式提升并发性能
            if self.config.enable_wal_mode:
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA synchronous=NORMAL")
                cursor.execute("PRAGMA cache_size=10000")
                cursor.execute("PRAGMA temp_store=memory")

            conn.commit()
            logger.info("数据库表结构初始化完成")

    @contextmanager
    def _get_connection(self):
        """获取数据库连接（上下文管理器）"""
        conn = sqlite3.connect(
            self.config.db_path,
            timeout=30.0,
            check_same_thread=False
        )
        try:
            yield conn
        finally:
            conn.close()

    def _calculate_hash(self, data: Any) -> str:
        """计算数据哈希值"""
        data_str = json.dumps(data, sort_keys=True, default=str) if isinstance(data, dict) else str(data)
        return hashlib.md5(data_str.encode()).hexdigest()

    def _compress_data(self, data: str) -> bytes:
        """压缩数据（如果启用）"""
        if not self.config.compress_data:
            return data.encode()

        try:
            import zlib
            return zlib.compress(data.encode())
        except ImportError:
            logger.warning("zlib不可用，使用未压缩数据")
            return data.encode()

    def _decompress_data(self, data: bytes) -> str:
        """解压数据"""
        if not self.config.compress_data:
            return data.decode()

        try:
            import zlib
            return zlib.decompress(data).decode()
        except (ImportError, zlib.error):
            logger.warning("解压失败，尝试直接解码")
            return data.decode()

    def cache_stock_info(self, stock_info_list: List[Dict]):
        """
        缓存股票基础信息

        Args:
            stock_info_list: 股票信息列表
        """
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                for stock in stock_info_list:
                    cursor.execute("""
                        INSERT OR REPLACE INTO stock_info
                        (code, name, market, industry, last_updated)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        stock['code'],
                        stock['name'],
                        stock.get('market'),
                        stock.get('industry'),
                        datetime.now()
                    ))

                conn.commit()
                logger.info(f"已缓存{len(stock_info_list)}只股票基础信息")

    def cache_daily_data(self, stock_code: str, trade_date: str, data: Dict) -> bool:
        """
        缓存日线数据

        Args:
            stock_code: 股票代码
            trade_date: 交易日期 (YYYY-MM-DD)
            data: 数据字典

        Returns:
            bool: 是否成功缓存
        """
        with self._lock:
            try:
                data_hash = self._calculate_hash(data)

                with self._get_connection() as conn:
                    cursor = conn.cursor()

                    # 检查数据是否已存在且未变化
                    cursor.execute("""
                        SELECT data_hash FROM daily_data
                        WHERE stock_code = ? AND trade_date = ?
                    """, (stock_code, trade_date))

                    existing = cursor.fetchone()
                    if existing and existing[0] == data_hash:
                        # 数据未变化，更新访问时间
                        cursor.execute("""
                            UPDATE daily_data SET last_accessed = CURRENT_TIMESTAMP
                            WHERE stock_code = ? AND trade_date = ?
                        """, (stock_code, trade_date))
                        conn.commit()
                        return True

                    # 存储或更新数据
                    data_json = json.dumps(data, default=str, ensure_ascii=False)
                    data_bytes = self._compress_data(data_json)

                    cursor.execute("""
                        INSERT OR REPLACE INTO daily_data
                        (stock_code, trade_date, data_json, data_hash, updated_at)
                        VALUES (?, ?, ?, ?, ?)
                    """, (stock_code, trade_date, data_bytes, data_hash, datetime.now()))

                    conn.commit()

                    # 更新缓存统计
                    self._update_cache_stats('daily_data', stock_code, trade_date)

                    return True

            except Exception as e:
                logger.error(f"缓存日线数据失败 {stock_code} {trade_date}: {e}")
                return False

    def cache_capital_flow(self, stock_code: str, trade_date: str, data: Dict) -> bool:
        """缓存资金流向数据"""
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()

                    data_json = json.dumps(data, default=str, ensure_ascii=False)
                    data_bytes = self._compress_data(data_json)

                    cursor.execute("""
                        INSERT OR REPLACE INTO capital_flow
                        (stock_code, trade_date, data_json, updated_at)
                        VALUES (?, ?, ?, ?)
                    """, (stock_code, trade_date, data_bytes, datetime.now()))

                    conn.commit()
                    self._update_cache_stats('capital_flow', stock_code, trade_date)
                    return True

            except Exception as e:
                logger.error(f"缓存资金流向失败 {stock_code} {trade_date}: {e}")
                return False

    def cache_market_sentiment(self, stock_code: str, trade_date: str, data: Dict) -> bool:
        """缓存市场情绪数据"""
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()

                    data_json = json.dumps(data, default=str, ensure_ascii=False)
                    data_bytes = self._compress_data(data_json)

                    cursor.execute("""
                        INSERT OR REPLACE INTO market_sentiment
                        (stock_code, trade_date, data_json, updated_at)
                        VALUES (?, ?, ?, ?)
                    """, (stock_code, trade_date, data_bytes, datetime.now()))

                    conn.commit()
                    self._update_cache_stats('sentiment', stock_code, trade_date)
                    return True

            except Exception as e:
                logger.error(f"缓存市场情绪失败 {stock_code} {trade_date}: {e}")
                return False

    def get_cached_daily_data(self, stock_code: str, trade_date: str) -> Optional[Dict]:
        """
        获取缓存的日线数据

        Args:
            stock_code: 股票代码
            trade_date: 交易日期

        Returns:
            Dict: 缓存的数据，如果不存在返回None
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT data_json, updated_at FROM daily_data
                WHERE stock_code = ? AND trade_date = ?
            """, (stock_code, trade_date))

            result = cursor.fetchone()
            if result:
                try:
                    data_bytes, updated_at = result
                    data_str = self._decompress_data(data_bytes)
                    data = json.loads(data_str)

                    # 更新访问统计
                    cursor.execute("""
                        UPDATE cache_stats
                        SET hit_count = hit_count + 1, last_accessed = CURRENT_TIMESTAMP
                        WHERE cache_type = 'daily_data' AND stock_code = ? AND trade_date = ?
                    """, (stock_code, trade_date))
                    conn.commit()

                    logger.debug(f"缓存命中 {stock_code} {trade_date}")
                    return data

                except Exception as e:
                    logger.error(f"解析缓存数据失败: {e}")
                    return None

            logger.debug(f"缓存未命中 {stock_code} {trade_date}")
            return None

    def get_cached_capital_flow(self, stock_code: str, trade_date: str) -> Optional[Dict]:
        """获取缓存的资金流向数据"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT data_json FROM capital_flow
                WHERE stock_code = ? AND trade_date = ?
            """, (stock_code, trade_date))

            result = cursor.fetchone()
            if result:
                try:
                    data_bytes = result[0]
                    data_str = self._decompress_data(data_bytes)
                    data = json.loads(data_str)

                    # 更新访问统计
                    cursor.execute("""
                        UPDATE cache_stats
                        SET hit_count = hit_count + 1, last_accessed = CURRENT_TIMESTAMP
                        WHERE cache_type = 'capital_flow' AND stock_code = ? AND trade_date = ?
                    """, (stock_code, trade_date))
                    conn.commit()

                    return data
                except Exception as e:
                    logger.error(f"解析缓存数据失败: {e}")
                    return None

            return None

    def get_cached_market_sentiment(self, stock_code: str, trade_date: str) -> Optional[Dict]:
        """获取缓存的市场情绪数据"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT data_json FROM market_sentiment
                WHERE stock_code = ? AND trade_date = ?
            """, (stock_code, trade_date))

            result = cursor.fetchone()
            if result:
                try:
                    data_bytes = result[0]
                    data_str = self._decompress_data(data_bytes)
                    data = json.loads(data_str)

                    # 更新访问统计
                    cursor.execute("""
                        UPDATE cache_stats
                        SET hit_count = hit_count + 1, last_accessed = CURRENT_TIMESTAMP
                        WHERE cache_type = 'sentiment' AND stock_code = ? AND trade_date = ?
                    """, (stock_code, trade_date))
                    conn.commit()

                    return data
                except Exception as e:
                    logger.error(f"解析缓存数据失败: {e}")
                    return None

            return None

    def _update_cache_stats(self, cache_type: str, stock_code: str, trade_date: str):
        """更新缓存统计信息"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT OR IGNORE INTO cache_stats
                (cache_type, stock_code, trade_date)
                VALUES (?, ?, ?)
            """, (cache_type, stock_code, trade_date))

            conn.commit()

    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 缓存记录数统计
            stats = {}

            for table in ['daily_data', 'capital_flow', 'market_sentiment', 'stock_info']:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                stats[f"{table}_count"] = count

            # 缓存命中率统计
            cursor.execute("""
                SELECT cache_type, SUM(hit_count) as total_hits
                FROM cache_stats
                GROUP BY cache_type
            """)

            hit_stats = {row[0]: row[1] for row in cursor.fetchall()}
            stats['hit_counts'] = hit_stats

            # 数据库大小
            db_size = os.path.getsize(self.config.db_path) if os.path.exists(self.config.db_path) else 0
            stats['db_size_mb'] = round(db_size / 1024 / 1024, 2)

            return stats

    def cleanup_expired_cache(self) -> int:
        """
        清理过期缓存数据

        Returns:
            int: 清理的记录数
        """
        if not self.config.auto_cleanup:
            return 0

        cutoff_date = datetime.now() - timedelta(days=self.config.max_cache_days)
        cutoff_str = cutoff_date.strftime('%Y-%m-%d %H:%M:%S')

        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # 清理过期数据
                total_deleted = 0

                for table in ['daily_data', 'capital_flow', 'market_sentiment']:
                    cursor.execute(f"""
                        DELETE FROM {table}
                        WHERE updated_at < ?
                    """, (cutoff_str,))

                    deleted = cursor.rowcount
                    total_deleted += deleted
                    logger.info(f"从{table}清理{deleted}条过期记录")

                # 清理统计记录
                cursor.execute("""
                    DELETE FROM cache_stats
                    WHERE last_accessed < ?
                """, (cutoff_str,))
                stats_deleted = cursor.rowcount
                total_deleted += stats_deleted

                conn.commit()

                if total_deleted > 0:
                    logger.info(f"缓存清理完成，共删除{total_deleted}条记录")
                else:
                    logger.debug("无需清理缓存")

                return total_deleted

    def clear_all_cache(self) -> bool:
        """
        清空所有缓存数据

        Returns:
            bool: 是否成功清空
        """
        with self._lock:
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()

                    for table in ['daily_data', 'capital_flow', 'market_sentiment', 'stock_info', 'cache_stats']:
                        cursor.execute(f"DELETE FROM {table}")

                    conn.commit()

                logger.info("所有缓存数据已清空")
                return True

            except Exception as e:
                logger.error(f"清空缓存失败: {e}")
                return False

    def export_cache_to_json(self, output_path: str, days: int = 7) -> bool:
        """
        导出缓存数据到JSON文件

        Args:
            output_path: 输出文件路径
            days: 导出最近几天的数据

        Returns:
            bool: 是否成功导出
        """
        try:
            start_date = datetime.now() - timedelta(days=days)
            start_str = start_date.strftime('%Y-%m-%d')

            with self._get_connection() as conn:
                # 导出日线数据
                df = pd.read_sql_query(f"""
                    SELECT stock_code, trade_date, data_json, updated_at
                    FROM daily_data
                    WHERE trade_date >= ?
                    ORDER BY stock_code, trade_date
                """, conn, params=(start_str,))

                # 解析JSON数据
                df['data'] = df['data_json'].apply(lambda x: json.loads(x))
                df = df.drop('data_json', axis=1)

                # 保存到文件
                export_data = {
                    'export_time': datetime.now().isoformat(),
                    'days': days,
                    'daily_data': df.to_dict('records')
                }

                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, ensure_ascii=False, indent=2, default=str)

                logger.info(f"缓存数据已导出到 {output_path}")
                return True

        except Exception as e:
            logger.error(f"导出缓存数据失败: {e}")
            return False


def create_cache_manager(
    cache_dir: str = "./cache",
    max_cache_days: int = 30,
    auto_cleanup: bool = True,
    compress_data: bool = False
) -> StockCacheManager:
    """
    创建缓存管理器的便捷函数

    Args:
        cache_dir: 缓存目录
        max_cache_days: 缓存保留天数
        auto_cleanup: 是否自动清理
        compress_data: 是否压缩数据

    Returns:
        StockCacheManager: 缓存管理器实例
    """
    config = CacheConfig(
        cache_dir=cache_dir,
        max_cache_days=max_cache_days,
        auto_cleanup=auto_cleanup,
        compress_data=compress_data
    )

    return StockCacheManager(config)