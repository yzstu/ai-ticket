"""
多线程并行股票分析器
提供高效的多线程股票分析功能
"""
import os
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from threading import Lock
import psutil


@dataclass
class AnalysisConfig:
    """分析配置"""
    max_workers: int = 0  # 0表示自动检测CPU核心数
    thread_timeout: int = 30  # 单个任务超时时间（秒）
    batch_size: int = 100  # 批处理大小
    progress_interval: int = 10  # 进度更新间隔
    retry_count: int = 2  # 失败重试次数
    rate_limit: float = 0  # 速率限制（秒/请求），0表示无限制


@dataclass
class AnalysisResult:
    """分析结果"""
    code: str
    name: str
    success: bool
    data: Optional[Dict] = None
    error: Optional[str] = None
    duration: float = 0.0


class ParallelAnalyzer:
    """多线程并行股票分析器"""

    def __init__(self, config: Optional[AnalysisConfig] = None):
        """
        初始化并行分析器

        Args:
            config: 分析配置
        """
        self.config = config or AnalysisConfig()
        self.logger = logging.getLogger(__name__)

        # 计算最优线程数
        self.max_workers = self._calculate_optimal_workers()

        # 进度跟踪
        self._progress_lock = Lock()
        self._completed = 0
        self._failed = 0

        # 统计信息
        self.stats = {
            'total': 0,
            'completed': 0,
            'failed': 0,
            'start_time': 0,
            'end_time': 0,
            'duration': 0
        }

        self.logger.info(f"并行分析器初始化完成，线程数: {self.max_workers}")

    def _calculate_optimal_workers(self) -> int:
        """计算最优线程数"""
        if self.config.max_workers > 0:
            return self.config.max_workers

        # 自动检测CPU核心数
        cpu_count = os.cpu_count() or 4

        # I/O密集型任务建议使用更多线程
        optimal_workers = cpu_count * 2

        # 限制最大线程数
        max_threads = min(optimal_workers, 32)

        self.logger.info(f"CPU核心数: {cpu_count}, 自动设置线程数: {max_threads}")
        return max_threads

    def analyze_stocks_parallel(
        self,
        stocks: List[Dict],
        analysis_func: Callable,
        description: str = "股票分析"
    ) -> List[AnalysisResult]:
        """
        并行分析多只股票

        Args:
            stocks: 股票列表
            analysis_func: 分析函数，接受stock参数返回结果
            description: 任务描述

        Returns:
            分析结果列表
        """
        if not stocks:
            return []

        self.stats['total'] = len(stocks)
        self.stats['start_time'] = time.time()

        print(f"\n🚀 开始{description}，共 {len(stocks)} 只股票")
        print(f"   线程数: {self.max_workers}, 超时: {self.config.thread_timeout}秒")
        print(f"   重试次数: {self.config.retry_count}, 批处理: {self.config.batch_size}")

        results = []

        # 按批处理大小分组
        batches = [
            stocks[i:i + self.config.batch_size]
            for i in range(0, len(stocks), self.config.batch_size)
        ]

        for batch_idx, batch in enumerate(batches):
            batch_start = time.time()

            print(f"\n📦 处理批次 {batch_idx + 1}/{len(batches)} ({len(batch)} 只股票)")

            batch_results = self._process_batch(batch, analysis_func)
            results.extend(batch_results)

            batch_duration = time.time() - batch_start
            print(f"   批次用时: {batch_duration:.2f}秒")

        self._finalize_stats()

        return results

    def _process_batch(
        self,
        stocks: List[Dict],
        analysis_func: Callable
    ) -> List[AnalysisResult]:
        """处理一批股票"""
        results = []
        completed_lock = Lock()
        failed_lock = Lock()

        def analyze_with_retry(stock: Dict) -> AnalysisResult:
            """带重试的分析"""
            stock_code = stock['code']
            stock_name = stock['name']

            for attempt in range(self.config.retry_count + 1):
                try:
                    start_time = time.time()

                    # 执行分析
                    data = analysis_func(stock)

                    duration = time.time() - start_time

                    # 更新进度
                    with completed_lock:
                        self._completed += 1
                        self._print_progress()

                    return AnalysisResult(
                        code=stock_code,
                        name=stock_name,
                        success=True,
                        data=data,
                        duration=duration
                    )

                except Exception as e:
                    error_msg = str(e)

                    if attempt < self.config.retry_count:
                        self.logger.warning(f"分析 {stock_code} 失败，重试 {attempt + 1}/{self.config.retry_count}: {error_msg}")
                        time.sleep(0.5 * (attempt + 1))  # 指数退避
                    else:
                        with failed_lock:
                            self._failed += 1
                            self._print_progress()

                        self.logger.error(f"分析 {stock_code} 最终失败: {error_msg}")

                        return AnalysisResult(
                            code=stock_code,
                            name=stock_name,
                            success=False,
                            error=error_msg,
                            duration=time.time() - start_time
                        )

        # 使用线程池执行
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务
            future_to_stock = {
                executor.submit(analyze_with_retry, stock): stock
                for stock in stocks
            }

            # 收集结果
            for future in as_completed(future_to_stock):
                try:
                    # 设置超时
                    result = future.result(timeout=self.config.thread_timeout)
                    results.append(result)
                except TimeoutError:
                    stock = future_to_stock[future]
                    with failed_lock:
                        self._failed += 1
                        self._print_progress()

                    self.logger.error(f"分析 {stock['code']} 超时")

                    results.append(AnalysisResult(
                        code=stock['code'],
                        name=stock['name'],
                        success=False,
                        error="分析超时",
                        duration=self.config.thread_timeout
                    ))
                except Exception as e:
                    stock = future_to_stock[future]
                    with failed_lock:
                        self._failed += 1
                        self._print_progress()

                    self.logger.error(f"处理 {stock['code']} 时发生异常: {e}")

                    results.append(AnalysisResult(
                        code=stock['code'],
                        name=stock['name'],
                        success=False,
                        error=str(e),
                        duration=0
                    ))

        return results

    def _print_progress(self):
        """打印进度"""
        total = self._completed + self._failed
        if total > 0 and total % self.config.progress_interval == 0:
            elapsed = time.time() - self.stats['start_time']
            rate = total / elapsed if elapsed > 0 else 0

            # 估算剩余时间
            remaining = self.stats['total'] - total
            eta = remaining / rate if rate > 0 else 0

            print(f"   进度: {total}/{self.stats['total']} "
                  f"({total/self.stats['total']*100:.1f}%) - "
                  f"成功: {self._completed}, 失败: {self._failed}, "
                  f"速率: {rate:.1f}只/秒, ETA: {eta:.1f}秒")

    def _finalize_stats(self):
        """最终统计"""
        self.stats['end_time'] = time.time()
        self.stats['duration'] = self.stats['end_time'] - self.stats['start_time']
        self.stats['completed'] = self._completed
        self.stats['failed'] = self._failed

    def get_stats(self) -> Dict:
        """获取统计信息"""
        return self.stats.copy()

    def print_summary(self):
        """打印摘要"""
        print(f"\n{'='*70}")
        print(f"📊 {self.stats['total']} 只股票分析完成")
        print(f"{'='*70}")
        print(f"总用时: {self.stats['duration']:.2f} 秒")
        print(f"成功分析: {self.stats['completed']} 只")
        print(f"失败分析: {self.stats['failed']} 只")
        print(f"成功率: {self.stats['completed']/self.stats['total']*100:.2f}%")
        print(f"平均速度: {self.stats['total']/self.stats['duration']:.2f} 只/秒")
        print(f"{'='*70}")


class AnalysisFunctionFactory:
    """分析函数工厂"""

    @staticmethod
    def create_analysis_func(analyzer, fetcher, strategy_tools) -> Callable:
        """
        创建分析函数

        Args:
            analyzer: 本地分析器
            fetcher: 数据获取器
            strategy_tools: 策略工具

        Returns:
            分析函数
        """
        from src.tools import get_daily_stock_data, evaluate_strategy, apply_risk_filters

        def analyze_single_stock(stock: Dict) -> Dict:
            """分析单只股票"""
            code = stock['code']
            name = stock['name']

            try:
                # 获取股票数据
                stock_data = get_daily_stock_data.invoke({"stock_code": code})

                # 应用风险过滤
                risk_result = apply_risk_filters.invoke({"stock_data": stock_data})
                if not risk_result["pass_risk_filter"]:
                    raise Exception(f"未通过风险过滤: {risk_result['risk_issues']}")

                # 评估策略
                evaluation = evaluate_strategy.invoke({"stock_data": stock_data})

                # 综合分析
                try:
                    technical_indicators = {
                        "rsi": stock_data.get("rsi", 50),
                        "macd": stock_data.get("macd", 0),
                        "macd_histogram": stock_data.get("macd_histogram", 0),
                        "ma5": stock_data.get("ma5", 0),
                        "ma20": stock_data.get("ma20", 0)
                    }

                    capital_flow = {
                        "main_net_inflow": stock_data.get("main_net_inflow", 0),
                        "retail_net_inflow": stock_data.get("retail_net_inflow", 0),
                        "foreign_net_inflow": stock_data.get("foreign_net_inflow", 0)
                    }

                    sentiment = {
                        "sentiment_score": stock_data.get("sentiment_score", 50),
                        "positive_news": stock_data.get("positive_news", 0),
                        "negative_news": stock_data.get("negative_news", 0)
                    }

                    # 获取综合分析
                    analysis_result = analyzer.analyze_stock(
                        code,
                        {
                            "price": stock_data.get("close", 0),
                            "volume": stock_data.get("volume", 0),
                            "avg_volume": stock_data.get("avg_volume", 0),
                            "volatility": stock_data.get("volatility", 0.02),
                            "price_change_5d": stock_data.get("price_change_5d", 0),
                            "trend_strength": stock_data.get("trend_strength", 0.5)
                        },
                        technical_indicators,
                        capital_flow,
                        sentiment
                    )

                    final_score = analysis_result.get("final_score", evaluation.get("score", 0))

                    return {
                        "code": code,
                        "name": name,
                        "score": final_score,
                        "recommendation": analysis_result.get("recommendation", evaluation["recommendation"]),
                        "technical_score": evaluation["technical_score"],
                        "sentiment_score": evaluation["sentiment_score"],
                        "capital_score": evaluation["capital_score"],
                        "price": round(stock_data.get("close", 0), 2),
                        "volume_increase": round(stock_data.get("volume_increase", 0), 2),
                        "rsi": round(stock_data.get("rsi", 50), 2),
                        "explanation": f"综合评分: {final_score:.1f}, 建议: {analysis_result.get('recommendation', 'N/A')}"
                    }

                except Exception as e:
                    # 降级到基本评估
                    if evaluation["recommendation"] == "BUY" or evaluation["score"] > 50:
                        return {
                            "code": code,
                            "name": name,
                            "score": evaluation["score"],
                            "recommendation": evaluation["recommendation"],
                            "technical_score": evaluation["technical_score"],
                            "sentiment_score": evaluation["sentiment_score"],
                            "capital_score": evaluation["capital_score"],
                            "price": round(stock_data.get("close", 0), 2),
                            "volume_increase": round(stock_data.get("volume_increase", 0), 2),
                            "rsi": round(stock_data.get("rsi", 50), 2),
                            "explanation": "基于基本技术分析"
                        }
                    else:
                        raise e

            except Exception as e:
                raise Exception(f"分析失败: {str(e)}")

        return analyze_single_stock


def create_parallel_analyzer(
    max_workers: int = 0,
    thread_timeout: int = 30,
    batch_size: int = 100
) -> ParallelAnalyzer:
    """
    创建并行分析器

    Args:
        max_workers: 最大线程数（0表示自动）
        thread_timeout: 线程超时时间
        batch_size: 批处理大小

    Returns:
        ParallelAnalyzer实例
    """
    config = AnalysisConfig(
        max_workers=max_workers,
        thread_timeout=thread_timeout,
        batch_size=batch_size
    )
    return ParallelAnalyzer(config)