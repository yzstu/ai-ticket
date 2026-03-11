"""
板块数据获取模块
使用AKShare获取板块实时数据
"""
import akshare as ak
import pandas as pd
from typing import List, Dict, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class SectorFetcher:
    """板块数据获取器"""

    def get_sector_list(self) -> List[Dict]:
        """
        获取所有板块列表及实时行情

        Returns:
            板块列表，每个板块包含：
            - code: 板块代码
            - name: 板块名称
            - price: 当前点位
            - change: 涨跌幅(%)
            - amount: 成交额（从总市值和换手率估算）
            - lead_stock: 领涨股
            - lead_stock_change: 领涨股涨幅
        """
        try:
            # 获取板块实时行情
            df = ak.stock_board_industry_name_em()

            sectors = []
            for _, row in df.iterrows():
                # 从总市值和换手率估算成交额
                total_market_cap = float(row.get('总市值', 0))
                turnover_rate = float(row.get('换手率', 0))
                # 成交额 = 总市值 * 换手率
                estimated_amount = total_market_cap * turnover_rate / 100 if total_market_cap > 0 else 0

                # 领涨股票涨跌幅列名是 "领涨股票-涨跌幅"（带连字符）
                lead_change_raw = row.get('领涨股票-涨跌幅', 0)
                lead_change = float(lead_change_raw) if lead_change_raw else 0

                sectors.append({
                    'code': row.get('板块代码', ''),
                    'name': row.get('板块名称', ''),
                    'price': float(row.get('最新价', 0)),
                    'change': float(row.get('涨跌幅', 0)),
                    'amount': estimated_amount,  # 估算的成交额
                    'turnover_rate': turnover_rate,
                    'total_market_cap': total_market_cap,
                    'lead_stock': row.get('领涨股票', ''),
                    'lead_stock_change': lead_change,
                    'up_count': int(row.get('上涨家数', 0)),
                    'down_count': int(row.get('下跌家数', 0)),
                })

            logger.info(f"获取到 {len(sectors)} 个板块数据")
            return sectors

        except Exception as e:
            logger.error(f"获取板块列表失败: {e}")
            return []

    def get_sector_stocks(self, sector_code: str) -> List[str]:
        """
        获取板块内股票代码列表

        Args:
            sector_code: 板块代码

        Returns:
            股票代码列表
        """
        try:
            df = ak.stock_board_industry_cons_em(symbol=sector_code)
            return df['代码'].tolist() if not df.empty else []
        except Exception as e:
            logger.error(f"获取板块 {sector_code} 股票列表失败: {e}")
            return []

    def calculate_sector_heat(self, sector: Dict) -> float:
        """
        计算板块热度评分 (0-100)

        综合考虑：
        - 涨跌幅权重 40%
        - 成交额权重 30%
        - 领涨股涨幅权重 20%
        - 上涨家数比例权重 10%

        Args:
            sector: 板块数据

        Returns:
            热度评分 (0-100)
        """
        score = 50.0  # 基础分

        # 涨跌幅 (40%)
        change = sector.get('change', 0)
        if change > 5:
            score += 20
        elif change > 3:
            score += 15
        elif change > 1:
            score += 10
        elif change > 0:
            score += 5
        elif change < -3:
            score -= 15
        elif change < -1:
            score -= 10
        elif change < 0:
            score -= 5

        # 成交额 (30%) - 使用估算的成交额
        amount = sector.get('amount', 0)
        if amount > 100e8:  # 100亿
            score += 15
        elif amount > 50e8:  # 50亿
            score += 10
        elif amount > 20e8:  # 20亿
            score += 5

        # 领涨股涨幅 (20%)
        lead_change = sector.get('lead_stock_change', 0)
        if lead_change > 9:
            score += 10
        elif lead_change > 5:
            score += 7
        elif lead_change > 3:
            score += 5
        elif lead_change < -5:
            score -= 10
        elif lead_change < -3:
            score -= 5

        # 上涨家数比例 (10%)
        up_count = sector.get('up_count', 0)
        down_count = sector.get('down_count', 0)
        total_count = up_count + down_count
        if total_count > 0:
            up_ratio = up_count / total_count
            if up_ratio > 0.8:
                score += 5
            elif up_ratio > 0.6:
                score += 3
            elif up_ratio < 0.3:
                score -= 5

        return max(0, min(100, score))

    def get_hot_sectors(self, limit: int = 20) -> List[Dict]:
        """
        获取热门板块（按热度排序）

        Args:
            limit: 返回数量

        Returns:
            热门板块列表，包含热度评分和颜色等级
        """
        sectors = self.get_sector_list()

        # 计算热度
        for sector in sectors:
            sector['heat'] = self.calculate_sector_heat(sector)
            sector['heat_level'] = self._get_heat_level(sector['heat'])
            sector['heat_color'] = self._get_heat_color(sector['heat'])

        # 按热度排序
        sectors.sort(key=lambda x: x['heat'], reverse=True)

        return sectors[:limit]

    def _get_heat_level(self, heat: float) -> str:
        """获取热度等级"""
        if heat >= 80:
            return '超热'
        elif heat >= 60:
            return '活跃'
        elif heat >= 40:
            return '中性'
        elif heat >= 20:
            return '冷门'
        else:
            return '冰点'

    def _get_heat_color(self, heat: float) -> str:
        """获取热度颜色 (CSS颜色值)"""
        if heat >= 80:
            return '#D32F2F'  # 深红
        elif heat >= 60:
            return '#FF5722'  # 橙红
        elif heat >= 40:
            return '#FFC107'  # 黄色
        elif heat >= 20:
            return '#64B5F6'  # 浅蓝
        else:
            return '#1565C0'  # 深蓝


# 单例
_sector_fetcher = None

def get_sector_fetcher() -> SectorFetcher:
    """获取板块数据获取器单例"""
    global _sector_fetcher
    if _sector_fetcher is None:
        _sector_fetcher = SectorFetcher()
    return _sector_fetcher