"""
风险指标计算
提供各种风险和收益指标的计算方法
"""
import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class RiskMetricsCalculator:
    """风险指标计算器"""

    @staticmethod
    def calculate_all_metrics(returns: List[float]) -> Dict[str, float]:
        """计算所有主要风险指标"""
        if not returns or len(returns) < 2:
            return {
                'total_return': 0.0,
                'avg_return': 0.0,
                'volatility': 0.0,
                'max_drawdown': 0.0,
                'sharpe_ratio': 0.0,
                'sortino_ratio': 0.0,
                'calmar_ratio': 0.0,
                'win_rate': 0.0,
                'profit_loss_ratio': 0.0,
                'var_95': 0.0,
                'cvar_95': 0.0
            }

        returns_array = np.array(returns)

        # 基本指标
        total_return = np.sum(returns_array)
        avg_return = np.mean(returns_array)

        # 波动率
        volatility = RiskMetricsCalculator._calculate_volatility(returns_array)

        # 最大回撤
        max_drawdown = RiskMetricsCalculator._calculate_max_drawdown(returns_array)

        # 夏普比率
        sharpe_ratio = RiskMetricsCalculator._calculate_sharpe_ratio(returns_array)

        # 索提诺比率
        sortino_ratio = RiskMetricsCalculator._calculate_sortino_ratio(returns_array)

        # 卡尔玛比率
        calmar_ratio = RiskMetricsCalculator._calculate_calmar_ratio(returns_array, max_drawdown)

        # 胜率
        win_rate = RiskMetricsCalculator._calculate_win_rate(returns_array)

        # 盈亏比
        profit_loss_ratio = RiskMetricsCalculator._calculate_profit_loss_ratio(returns_array)

        # VaR和CVaR
        var_95 = RiskMetricsCalculator._calculate_var(returns_array, confidence=0.95)
        cvar_95 = RiskMetricsCalculator._calculate_cvar(returns_array, confidence=0.95)

        return {
            'total_return': total_return,
            'avg_return': avg_return,
            'volatility': volatility,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'sortino_ratio': sortino_ratio,
            'calmar_ratio': calmar_ratio,
            'win_rate': win_rate,
            'profit_loss_ratio': profit_loss_ratio,
            'var_95': var_95,
            'cvar_95': cvar_95
        }

    @staticmethod
    def _calculate_volatility(returns: np.ndarray) -> float:
        """计算年化波动率"""
        if len(returns) < 2:
            return 0.0

        std_dev = np.std(returns, ddof=1)
        # 年化波动率 (假设数据为日收益率)
        return std_dev * np.sqrt(252)

    @staticmethod
    def _calculate_max_drawdown(returns: np.ndarray) -> float:
        """计算最大回撤"""
        if len(returns) < 1:
            return 0.0

        # 计算累计收益
        cumulative = np.cumprod(1 + returns / 100)

        # 计算回撤序列
        peak = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - peak) / peak * 100

        # 返回最大回撤（绝对值）
        return abs(np.min(drawdown))

    @staticmethod
    def _calculate_sharpe_ratio(returns: np.ndarray, risk_free_rate: float = 2.0) -> float:
        """计算夏普比率"""
        if len(returns) < 2:
            return 0.0

        excess_returns = returns - risk_free_rate / 252  # 日化无风险利率
        mean_excess = np.mean(excess_returns)
        std_dev = np.std(returns, ddof=1)

        if std_dev == 0:
            return 0.0

        return (mean_excess / std_dev) * np.sqrt(252)

    @staticmethod
    def _calculate_sortino_ratio(returns: np.ndarray, risk_free_rate: float = 2.0) -> float:
        """计算索提诺比率（只考虑下行波动率）"""
        if len(returns) < 2:
            return 0.0

        excess_returns = returns - risk_free_rate / 252
        mean_excess = np.mean(excess_returns)

        # 只考虑负收益的下行波动率
        downside_returns = returns[returns < np.mean(returns)]
        if len(downside_returns) == 0:
            return float('inf') if mean_excess > 0 else 0.0

        downside_std = np.std(downside_returns, ddof=1)
        if downside_std == 0:
            return 0.0

        return (mean_excess / downside_std) * np.sqrt(252)

    @staticmethod
    def _calculate_calmar_ratio(returns: np.ndarray, max_drawdown: float) -> float:
        """计算卡尔玛比率"""
        if max_drawdown == 0:
            return float('inf') if np.mean(returns) > 0 else 0.0

        total_return = np.sum(returns)
        annualized_return = total_return * (252 / len(returns))

        return annualized_return / max_drawdown

    @staticmethod
    def _calculate_win_rate(returns: np.ndarray) -> float:
        """计算胜率"""
        if len(returns) == 0:
            return 0.0

        winning_trades = np.sum(returns > 0)
        return winning_trades / len(returns) * 100

    @staticmethod
    def _calculate_profit_loss_ratio(returns: np.ndarray) -> float:
        """计算盈亏比"""
        positive_returns = returns[returns > 0]
        negative_returns = returns[returns < 0]

        if len(positive_returns) == 0 or len(negative_returns) == 0:
            return 0.0

        avg_win = np.mean(positive_returns)
        avg_loss = abs(np.mean(negative_returns))

        return avg_win / avg_loss if avg_loss > 0 else 0.0

    @staticmethod
    def _calculate_var(returns: np.ndarray, confidence: float = 0.95) -> float:
        """计算风险价值 (VaR)"""
        if len(returns) == 0:
            return 0.0

        return np.percentile(returns, (1 - confidence) * 100)

    @staticmethod
    def _calculate_cvar(returns: np.ndarray, confidence: float = 0.95) -> float:
        """计算条件风险价值 (CVaR)"""
        if len(returns) == 0:
            return 0.0

        var = RiskMetricsCalculator._calculate_var(returns, confidence)
        tail_returns = returns[returns <= var]

        if len(tail_returns) == 0:
            return var

        return np.mean(tail_returns)

    @staticmethod
    def calculate_monthly_returns(returns: List[float], dates: List[str]) -> Dict[str, float]:
        """计算月度收益率"""
        if not returns or not dates:
            return {}

        try:
            df = pd.DataFrame({
                'date': pd.to_datetime(dates),
                'return': returns
            })

            df['year_month'] = df['date'].dt.to_period('M')
            monthly = df.groupby('year_month')['return'].sum()

            return {str(period): round(ret, 2) for period, ret in monthly.items()}
        except Exception as e:
            logger.error(f"计算月度收益率失败: {e}")
            return {}

    @staticmethod
    def generate_risk_summary(metrics: Dict[str, float]) -> Dict[str, Any]:
        """生成风险评估摘要"""
        score = 0
        risk_level = "低风险"
        recommendations = []

        # 根据夏普比率评分
        sharpe = metrics.get('sharpe_ratio', 0)
        if sharpe > 2.0:
            score += 30
            recommendations.append("优秀的风险调整后收益")
        elif sharpe > 1.0:
            score += 20
            recommendations.append("良好的风险调整后收益")
        elif sharpe > 0.5:
            score += 10
        else:
            recommendations.append("风险调整后收益偏低")

        # 根据最大回撤评分
        max_dd = metrics.get('max_drawdown', 0)
        if max_dd < 5:
            score += 30
        elif max_dd < 10:
            score += 20
        elif max_dd < 20:
            score += 10
        else:
            score -= 10
            recommendations.append("最大回撤较大，需要注意风险控制")

        # 根据胜率评分
        win_rate = metrics.get('win_rate', 0)
        if win_rate > 70:
            score += 20
        elif win_rate > 60:
            score += 15
        elif win_rate > 50:
            score += 10
        else:
            score -= 5
            recommendations.append("胜率偏低，建议优化选股策略")

        # 根据盈亏比评分
        pl_ratio = metrics.get('profit_loss_ratio', 0)
        if pl_ratio > 2.0:
            score += 20
        elif pl_ratio > 1.5:
            score += 15
        elif pl_ratio > 1.0:
            score += 10
        else:
            score -= 5
            recommendations.append("盈亏比偏低，建议设置止损位")

        # 确定风险等级
        if score >= 80:
            risk_level = "优秀"
        elif score >= 65:
            risk_level = "良好"
        elif score >= 50:
            risk_level = "中等"
        elif score >= 35:
            risk_level = "一般"
        else:
            risk_level = "较差"

        return {
            'score': max(0, min(100, score)),
            'risk_level': risk_level,
            'recommendations': recommendations
        }