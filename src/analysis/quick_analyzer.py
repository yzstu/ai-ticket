"""
快速股票分析模块
提供简化的快速分析功能，解决分析慢和没有推荐的问题
"""
import logging
import time
from typing import Dict, List, Any
import pandas as pd

logger = logging.getLogger(__name__)


def safe_float(value, default=0.0):
    """安全转换为浮点数，避免NaN和inf"""
    try:
        if value is None or value == '' or (isinstance(value, float) and (value != value or value == float('inf') or value == float('-inf'))):
            return default
        return float(value)
    except:
        return default


def quick_stock_analysis(stock_code: str, stock_name: str, stock_data: Dict) -> Dict:
    """
    快速分析单只股票

    Args:
        stock_code: 股票代码
        stock_name: 股票名称
        stock_data: 股票数据

    Returns:
        分析结果
    """
    try:
        # 提取关键数据
        close_price = safe_float(stock_data.get('close', 0), 0.0)
        volume = int(safe_float(stock_data.get('volume', 0), 0))
        price_change = safe_float(stock_data.get('price_change', 0), 0.0)
        rsi = safe_float(stock_data.get('rsi', 50), 50.0)

        # 基础评分
        score = 50  # 基础分

        # 价格分析 (30分)
        if close_price > 0:
            if price_change > 5:
                score += 15
            elif price_change > 0:
                score += 10
            elif price_change > -3:
                score += 5

        # RSI分析 (20分)
        if 30 <= rsi <= 70:
            score += 15
            if 30 <= rsi <= 45 or 55 <= rsi <= 70:
                score += 5
        elif rsi < 30:
            score += 10  # 超卖反弹
        elif rsi > 70:
            score -= 5   # 超买谨慎

        # 成交量分析 (20分)
        if volume > 0:
            avg_volume = safe_float(stock_data.get('avg_volume', 0), 0.0)
            if avg_volume > 0:
                volume_ratio = volume / avg_volume
                if volume_ratio > 1.5:
                    score += 15
                elif volume_ratio > 1.0:
                    score += 10
                elif volume_ratio > 0.5:
                    score += 5

        # 技术指标分析 (20分)
        macd = safe_float(stock_data.get('macd', 0), 0.0)
        macd_histogram = safe_float(stock_data.get('macd_histogram', 0), 0.0)

        if macd > 0 and macd_histogram > 0:
            score += 10  # MACD金叉
        if macd_histogram > 0:
            score += 5   # MACD向上
        elif macd_histogram < 0:
            score -= 5   # MACD向下

        # MA5, MA20分析
        ma5 = safe_float(stock_data.get('ma5', 0), 0.0)
        ma20 = safe_float(stock_data.get('ma20', 0), 0.0)

        if ma5 > ma20 and close_price > ma5:
            score += 5   # 多头排列

        # 资金流向分析 (10分)
        try:
            main_net_inflow = safe_float(stock_data.get('main_net_inflow', 0), 0.0)
            if main_net_inflow > 0:
                score += 10
            elif main_net_inflow < -1000000:  # 主力大量流出
                score -= 10
        except:
            pass

        # 确定推荐
        if score >= 75:
            recommendation = "BUY"
        elif score >= 60:
            recommendation = "HOLD"
        else:
            recommendation = "SELL"

        # 生成推荐理由
        reasons = []
        if price_change > 5:
            reasons.append("涨幅较好")
        if 30 <= rsi <= 45:
            reasons.append("RSI处于低位，可能反弹")
        if volume > float(stock_data.get('avg_volume', 0)) * 1.5:
            reasons.append("成交量放大")
        if macd_histogram > 0:
            reasons.append("MACD向上")

        if not reasons:
            reasons = ["技术面稳定"]

        # 确保所有数值都是安全的
        score = safe_float(score, 50.0)
        close_price = safe_float(close_price, 0.0)
        # price_change如果无法计算，使用0.0
        price_change = safe_float(price_change, 0.0) if price_change is not None else 0.0
        rsi = safe_float(rsi, 50.0)

        # 计算量比，如果无法计算则使用1.0（当日成交量等于平均成交量）
        avg_volume = safe_float(stock_data.get('avg_volume', 0), 0.0)
        if avg_volume > 0:
            volume_ratio = round(volume / avg_volume, 2)
        elif volume > 0:
            volume_ratio = 1.0  # 估算值
        else:
            volume_ratio = 0.0

        return {
            "code": stock_code,
            "name": stock_name,
            "score": round(score, 1),
            "recommendation": recommendation,
            "price": round(close_price, 2),
            "price_change": round(price_change, 2),
            "volume": volume,
            "avg_volume": int(avg_volume),
            "volume_ratio": volume_ratio,
            "volume_increase": round(safe_float(stock_data.get('volume_increase', 0), 0), 2),
            "rsi": round(rsi, 1),
            "technical_score": round(safe_float(score, 50.0), 1),
            "sentiment_score": 50.0,  # 简化处理
            "capital_score": 50.0,    # 简化处理
            "explanation": f"评分{score:.1f}分，建议{recommendation}。理由：{', '.join(reasons[:3])}",
            "success": True
        }

    except Exception as e:
        logger.error(f"分析 {stock_code} 失败: {e}")
        return {
            "code": stock_code,
            "name": stock_name,
            "score": 0,
            "recommendation": "UNKNOWN",
            "explanation": f"分析失败: {str(e)}",
            "success": False,
            "error": str(e)
        }


def fast_analyze_stocks(stocks: List[Dict], data_fetcher) -> List[Dict]:
    """
    快速分析多只股票

    Args:
        stocks: 股票列表
        data_fetcher: 数据获取器

    Returns:
        分析结果列表
    """
    print(f"\n🚀 启动快速分析模式...")
    print(f"   分析股票数: {len(stocks)}")

    results = []
    success_count = 0
    error_count = 0

    for i, stock in enumerate(stocks):
        try:
            stock_code = stock['code']
            stock_name = stock['name']

            if (i + 1) % 100 == 0:
                print(f"   进度: {i+1}/{len(stocks)} ({((i+1)/len(stocks)*100):.1f}%)")

            # 获取日线数据
            daily_data = data_fetcher.get_daily_data(stock_code, days=10, force_refresh=False)
            if daily_data is None or daily_data.empty:
                # 缓存未命中，尝试从API获取
                daily_data = data_fetcher.get_daily_data(stock_code, days=10, force_refresh=True)

            if daily_data is None or daily_data.empty:
                logger.warning(f"无法获取 {stock_code} 的数据")
                error_count += 1
                continue

            # 转换数据格式
            stock_data = daily_data.iloc[-1].to_dict() if not daily_data.empty else {}

            # 添加衍生数据
            if not daily_data.empty:
                stock_data['ma5'] = daily_data['close'].rolling(5).mean().iloc[-1] if len(daily_data) >= 5 else daily_data['close'].mean()
                stock_data['ma20'] = daily_data['close'].rolling(20).mean().iloc[-1] if len(daily_data) >= 20 else stock_data['ma5']
                stock_data['avg_volume'] = daily_data['volume'].rolling(10).mean().iloc[-1] if len(daily_data) >= 10 else daily_data['volume'].mean()

                # 计算日涨跌幅（当日收盘价相比前一日收盘价）
                if len(daily_data) >= 2:
                    current_close = daily_data['close'].iloc[-1]
                    previous_close = daily_data['close'].iloc[-2]
                    stock_data['price_change'] = ((current_close - previous_close) / previous_close * 100) if previous_close > 0 else 0
                elif len(daily_data) == 1:
                    # 如果只有一天数据，使用当日涨跌幅（如果有的话）
                    stock_data['price_change'] = daily_data.get('pct_change', daily_data.get('change_percent', 0)).iloc[-1] if 'pct_change' in daily_data.columns or 'change_percent' in daily_data.columns else 0
                else:
                    stock_data['price_change'] = 0
            else:
                stock_data['ma5'] = stock_data.get('ma5', stock_data.get('close', 0))
                stock_data['ma20'] = stock_data.get('ma20', stock_data.get('ma5', stock_data.get('close', 0)))
                stock_data['avg_volume'] = stock_data.get('avg_volume', stock_data.get('volume', 0))
                stock_data['price_change'] = stock_data.get('price_change', 0)

            # 确保所有字段都有值
            stock_data['price_change'] = safe_float(stock_data.get('price_change', 0), 0.0)

            # 快速分析
            result = quick_stock_analysis(stock_code, stock_name, stock_data)

            if result['success']:
                results.append(result)
                success_count += 1
            else:
                error_count += 1

        except Exception as e:
            logger.error(f"分析 {stock['code']} 时出错: {e}")
            error_count += 1

    # 排序并返回前N个结果
    results.sort(key=lambda x: x['score'], reverse=True)

    print(f"\n✅ 快速分析完成:")
    print(f"   成功分析: {success_count} 只")
    print(f"   分析失败: {error_count} 只")
    print(f"   返回结果: {len(results)} 只")

    return results


def create_quick_analysis_result(results: List[Dict], analyzed_count: int, config: Dict) -> Dict:
    """
    创建快速分析结果

    Args:
        results: 分析结果列表
        analyzed_count: 实际分析股票数
        config: 分析配置

    Returns:
        标准格式的分析结果
    """
    # 根据推荐等级分类
    buy_results = [r for r in results if r.get('recommendation') == 'BUY']
    hold_results = [r for r in results if r.get('recommendation') == 'HOLD']
    sell_results = [r for r in results if r.get('recommendation') == 'SELL']

    print(f"\n📊 推荐结果统计:")
    print(f"   强烈推荐 (BUY): {len(buy_results)} 只")
    print(f"   持有建议 (HOLD): {len(hold_results)} 只")
    print(f"   建议卖出 (SELL): {len(sell_results)} 只")

    # 返回推荐结果
    recommended_stocks = buy_results[:50] if len(buy_results) > 0 else hold_results[:30]

    return {
        "date": pd.Timestamp.now().strftime("%Y-%m-%d"),
        "recommended_stocks": recommended_stocks,
        "all_results": results,
        "total_analyzed": analyzed_count,
        "total_recommended": len(recommended_stocks),
        "analysis_type": "quick",
        "selection_config": config,
        "cache_enabled": True,
        "statistics": {
            "total_analyzed": analyzed_count,
            "total_recommended": len(recommended_stocks),
            "buy_count": len(buy_results),
            "hold_count": len(hold_results),
            "sell_count": len(sell_results),
            "success_rate": len(results) / analyzed_count * 100 if analyzed_count > 0 else 0
        },
        "summary": f"快速分析完成，从{analyzed_count}只股票中筛选出{len(recommended_stocks)}只推荐股票"
    }