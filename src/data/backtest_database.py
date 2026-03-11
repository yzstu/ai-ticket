"""
回测数据库管理
负责存储和管理历史推荐记录、回测结果等数据
"""
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import logging
import os

logger = logging.getLogger(__name__)


class BacktestDatabase:
    """回测数据库管理类"""

    def __init__(self, db_path: str = "./cache/backtest.db"):
        self.db_path = db_path
        self.ensure_db_dir()
        self.init_database()

    def ensure_db_dir(self):
        """确保数据库目录存在"""
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

    def init_database(self):
        """初始化数据库表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 推荐记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS recommendations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stock_code TEXT NOT NULL,
                recommendation_date TEXT NOT NULL,
                score REAL NOT NULL,
                recommendation_type TEXT,
                confidence REAL,
                price_at_recommendation REAL,
                reason TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(stock_code, recommendation_date)
            )
        ''')

        # 回测结果表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS backtest_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stock_code TEXT NOT NULL,
                recommendation_date TEXT NOT NULL,
                entry_price REAL NOT NULL,
                exit_price REAL,
                exit_date TEXT,
                days_forward INTEGER,
                gross_return REAL,
                net_return REAL,
                is_profitable BOOLEAN,
                max_return_during_period REAL,
                min_return_during_period REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(stock_code, recommendation_date, days_forward)
            )
        ''')

        # 创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_recommendations_stock_code ON recommendations(stock_code)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_recommendations_date ON recommendations(recommendation_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_backtest_stock_code ON backtest_results(stock_code)')

        conn.commit()
        conn.close()
        logger.info(f"回测数据库初始化完成: {self.db_path}")

    def add_recommendation(
        self,
        stock_code: str,
        recommendation_date: str,
        score: float,
        recommendation_type: str = None,
        confidence: float = None,
        price_at_recommendation: float = None,
        reason: str = None
    ) -> bool:
        """添加推荐记录"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT OR REPLACE INTO recommendations
                (stock_code, recommendation_date, score, recommendation_type, confidence,
                 price_at_recommendation, reason)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (stock_code, recommendation_date, score, recommendation_type,
                  confidence, price_at_recommendation, reason))

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"添加推荐记录失败: {e}")
            return False

    def get_recommendations(
        self,
        stock_code: str,
        start_date: str = None,
        end_date: str = None,
        min_score: float = None,
        limit: int = None
    ) -> List[Dict[str, Any]]:
        """获取推荐记录"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query = "SELECT * FROM recommendations WHERE stock_code = ?"
        params = [stock_code]

        if start_date:
            query += " AND recommendation_date >= ?"
            params.append(start_date)

        if end_date:
            query += " AND recommendation_date <= ?"
            params.append(end_date)

        if min_score:
            query += " AND score >= ?"
            params.append(min_score)

        query += " ORDER BY recommendation_date DESC"

        if limit:
            query += " LIMIT ?"
            params.append(limit)

        cursor.execute(query, params)
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results

    def add_backtest_result(
        self,
        stock_code: str,
        recommendation_date: str,
        entry_price: float,
        exit_price: float,
        exit_date: str,
        days_forward: int,
        gross_return: float,
        net_return: float,
        is_profitable: bool,
        max_return: float,
        min_return: float
    ) -> bool:
        """添加回测结果"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT OR REPLACE INTO backtest_results
                (stock_code, recommendation_date, entry_price, exit_price, exit_date,
                 days_forward, gross_return, net_return, is_profitable,
                 max_return_during_period, min_return_during_period)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (stock_code, recommendation_date, entry_price, exit_price, exit_date,
                  days_forward, gross_return, net_return, is_profitable,
                  max_return, min_return))

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"添加回测结果失败: {e}")
            return False

    def get_backtest_results(
        self,
        stock_code: str = None,
        days_forward: int = None
    ) -> List[Dict[str, Any]]:
        """获取回测结果"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query = "SELECT * FROM backtest_results WHERE 1=1"
        params = []

        if stock_code:
            query += " AND stock_code = ?"
            params.append(stock_code)

        if days_forward:
            query += " AND days_forward = ?"
            params.append(days_forward)

        query += " ORDER BY recommendation_date DESC"

        cursor.execute(query, params)
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results

    def get_backtest_summary(
        self,
        stock_code: str = None,
        days_forward: int = None
    ) -> Dict[str, Any]:
        """获取回测汇总统计"""
        results = self.get_backtest_results(stock_code, days_forward)

        if not results:
            return {
                'total_recommendations': 0,
                'success_rate': 0.0,
                'avg_return': 0.0,
                'avg_gross_return': 0.0,
                'max_return': 0.0,
                'min_return': 0.0,
                'max_drawdown': 0.0,
                'sharpe_ratio': 0.0,
                'volatility': 0.0
            }

        returns = [r['net_return'] for r in results]
        gross_returns = [r['gross_return'] for r in results]
        profitable_count = sum(1 for r in results if r['is_profitable'])
        total_count = len(results)

        # 计算风险指标
        max_drawdown = self._calculate_max_drawdown(returns)
        sharpe_ratio = self._calculate_sharpe_ratio(returns)
        volatility = self._calculate_volatility(returns)

        return {
            'total_recommendations': total_count,
            'success_rate': (profitable_count / total_count * 100) if total_count > 0 else 0,
            'avg_return': sum(returns) / len(returns) if returns else 0,
            'avg_gross_return': sum(gross_returns) / len(gross_returns) if gross_returns else 0,
            'max_return': max(returns) if returns else 0,
            'min_return': min(returns) if returns else 0,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'volatility': volatility
        }

    def _calculate_max_drawdown(self, returns: List[float]) -> float:
        """计算最大回撤"""
        if not returns:
            return 0.0

        cumulative = [1.0]
        for r in returns:
            cumulative.append(cumulative[-1] * (1 + r/100))

        max_drawdown = 0.0
        peak = cumulative[0]

        for value in cumulative[1:]:
            if value > peak:
                peak = value
            drawdown = (peak - value) / peak * 100
            max_drawdown = max(max_drawdown, drawdown)

        return max_drawdown

    def _calculate_sharpe_ratio(self, returns: List[float], risk_free_rate: float = 2.0) -> float:
        """计算夏普比率 (年化)"""
        if not returns or len(returns) < 2:
            return 0.0

        excess_returns = [r - risk_free_rate/365 for r in returns]
        mean_excess = sum(excess_returns) / len(excess_returns)
        std_dev = self._calculate_volatility(returns)

        if std_dev == 0:
            return 0.0

        # 年化夏普比率
        return (mean_excess / std_dev) * (365 ** 0.5)

    def _calculate_volatility(self, returns: List[float]) -> float:
        """计算波动率 (年化)"""
        if not returns or len(returns) < 2:
            return 0.0

        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / (len(returns) - 1)
        daily_vol = variance ** 0.5

        # 年化波动率
        return daily_vol * (365 ** 0.5)

    def seed_sample_data(self):
        """播种示例数据（用于测试）"""
        import random
        from datetime import timedelta

        sample_stocks = ['000001', '000002', '600000', '600036', '000858']
        base_date = datetime.now() - timedelta(days=365)

        for stock in sample_stocks:
            for i in range(30):  # 每只股票30条记录
                rec_date = (base_date + timedelta(days=i*12)).strftime('%Y-%m-%d')
                score = round(random.uniform(0.6, 0.95), 2)

                rec_types = ['技术突破', '资金流入', '基本面改善', '市场情绪', '价格偏离']
                rec_type = random.choice(rec_types)
                confidence = round(random.uniform(0.6, 0.95), 2)

                # 模拟推荐时价格
                price = round(random.uniform(10, 100), 2)

                self.add_recommendation(
                    stock_code=stock,
                    recommendation_date=rec_date,
                    score=score,
                    recommendation_type=rec_type,
                    confidence=confidence,
                    price_at_recommendation=price,
                    reason=f"基于{rec_type}的推荐"
                )

        logger.info("示例数据播种完成")


# 全局数据库实例
_backtest_db = None


def get_backtest_db() -> BacktestDatabase:
    """获取回测数据库实例（单例）"""
    global _backtest_db
    if _backtest_db is None:
        _backtest_db = BacktestDatabase()
    return _backtest_db