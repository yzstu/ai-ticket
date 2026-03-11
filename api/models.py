"""
FastAPI项目 - Pydantic模型
定义请求和响应的数据模型
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


# 股票相关模型
class StockInfo(BaseModel):
    """股票信息"""
    code: str = Field(..., description="股票代码")
    name: str = Field(..., description="股票名称")


class StockSelectionConfig(BaseModel):
    """股票选择配置"""
    mode: str = Field(..., description="选择模式: top_n/custom/range/all")
    max_results: Optional[int] = Field(default=10, description="最大结果数量")
    custom_stocks: Optional[List[str]] = Field(default=None, description="自定义股票列表")
    code_range: Optional[tuple] = Field(default=None, description="代码范围")


# 数据相关模型
class DailyDataRequest(BaseModel):
    """日线数据请求"""
    stock_code: str = Field(..., description="股票代码")
    days: int = Field(default=30, description="数据天数")
    force_refresh: bool = Field(default=False, description="是否强制刷新")


class CapitalFlowRequest(BaseModel):
    """资金流向请求"""
    stock_code: str = Field(..., description="股票代码")
    force_refresh: bool = Field(default=False, description="是否强制刷新")


class MarketSentimentRequest(BaseModel):
    """市场情绪请求"""
    stock_code: str = Field(..., description="股票代码")
    force_refresh: bool = Field(default=False, description="是否强制刷新")


# 分析相关模型
class AnalysisRequest(BaseModel):
    """股票分析请求"""
    selection_mode: str = Field(default="top_n", description="股票选择模式")
    max_results: int = Field(default=10, description="最大分析股票数")
    custom_stocks: Optional[List[str]] = Field(default=None, description="自定义股票列表")
    code_range_start: Optional[str] = Field(default=None, description="代码范围起始")
    code_range_end: Optional[str] = Field(default=None, description="代码范围结束")
    use_parallel: bool = Field(default=True, description="是否使用并行分析")
    max_workers: int = Field(default=0, description="最大线程数(0=自动)")
    thread_timeout: int = Field(default=30, description="线程超时时间")
    batch_size: int = Field(default=100, description="批处理大小")
    use_cache: bool = Field(default=True, description="是否启用缓存")


class StockAnalysisResult(BaseModel):
    """单只股票分析结果"""
    code: str = Field(..., description="股票代码")
    name: str = Field(..., description="股票名称")
    score: float = Field(..., description="综合评分")
    recommendation: str = Field(..., description="建议(买入/持有/卖出)")
    technical_score: float = Field(..., description="技术面评分")
    sentiment_score: float = Field(..., description="情绪面评分")
    capital_score: float = Field(..., description="资金面评分")
    price: float = Field(..., description="当前价格")
    price_change: Optional[float] = Field(default=None, description="涨跌幅(%)")
    volume: Optional[int] = Field(default=None, description="成交量")
    avg_volume: Optional[int] = Field(default=None, description="平均成交量")
    volume_ratio: Optional[float] = Field(default=None, description="量比")
    volume_increase: float = Field(..., description="成交量增幅(%)")
    rsi: float = Field(..., description="RSI指标")
    explanation: str = Field(..., description="分析解释")


class AnalysisResponse(BaseModel):
    """分析响应"""
    date: str = Field(..., description="分析日期")
    recommended_stocks: List[StockAnalysisResult] = Field(..., description="推荐股票列表")
    total_analyzed: int = Field(..., description="分析股票总数")
    total_recommended: int = Field(..., description="推荐股票数量")
    selection_config: Dict[str, Any] = Field(..., description="选择配置")
    analysis_type: str = Field(..., description="分析类型(parallel/serial)")
    cache_enabled: bool = Field(..., description="是否启用缓存")
    cache_stats: Optional[Dict[str, Any]] = Field(default=None, description="缓存统计")


# 缓存相关模型
class CacheStatsResponse(BaseModel):
    """缓存统计响应"""
    total_requests: int = Field(..., description="总请求数")
    cache_hits: int = Field(..., description="缓存命中数")
    cache_misses: int = Field(..., description="缓存未命中数")
    cache_hit_rate: float = Field(..., description="缓存命中率(%)")
    api_requests: int = Field(..., description="API请求数")
    cache_writes: int = Field(..., description="缓存写入数")
    daily_data_count: int = Field(..., description="日线数据记录数")
    capital_flow_count: int = Field(..., description="资金流向记录数")
    sentiment_count: int = Field(..., description="市场情绪记录数")
    db_size_mb: float = Field(..., description="数据库大小(MB)")


class CacheCleanupRequest(BaseModel):
    """缓存清理请求"""
    dry_run: bool = Field(default=False, description="是否仅预览不执行")


class CacheCleanupResponse(BaseModel):
    """缓存清理响应"""
    deleted_count: int = Field(..., description="删除的记录数")
    message: str = Field(..., description="结果消息")


class CacheExportRequest(BaseModel):
    """缓存导出请求"""
    output_path: str = Field(..., description="输出文件路径")
    days: int = Field(default=7, description="导出最近几天的数据")


class CacheExportResponse(BaseModel):
    """缓存导出响应"""
    success: bool = Field(..., description="是否成功")
    output_path: str = Field(..., description="输出文件路径")
    message: str = Field(..., description="结果消息")


# 定时任务相关模型
class SchedulerConfig(BaseModel):
    """调度器配置"""
    cache_time: str = Field(default="16:30", description="缓存时间(HH:MM)")
    cleanup_time: str = Field(default="02:00", description="清理时间(HH:MM)")
    batch_size: int = Field(default=100, description="批处理大小")
    max_workers: int = Field(default=4, description="最大工作线程数")


class StartSchedulerRequest(BaseModel):
    """启动调度器请求"""
    config: SchedulerConfig = Field(..., description="调度器配置")


class SchedulerStats(BaseModel):
    """调度器统计"""
    total_cache_tasks: int = Field(..., description="总缓存任务数")
    successful_cache_tasks: int = Field(..., description="成功任务数")
    failed_cache_tasks: int = Field(..., description="失败任务数")
    total_cache_records: int = Field(..., description="总缓存记录数")
    start_time: Optional[datetime] = Field(default=None, description="启动时间")
    last_cache_time: Optional[datetime] = Field(default=None, description="最后缓存时间")
    runtime_hours: Optional[float] = Field(default=None, description="运行时间(小时)")


class ManualCacheRequest(BaseModel):
    """手动缓存请求"""
    stock_codes: Optional[List[str]] = Field(default=None, description="指定股票代码列表")
    batch_size: int = Field(default=50, description="批处理大小")
    max_workers: int = Field(default=4, description="最大工作线程数")


class ManualCacheResponse(BaseModel):
    """手动缓存响应"""
    total_stocks: int = Field(..., description="总股票数")
    cached_stocks: int = Field(..., description="成功缓存数")
    failed_stocks: int = Field(..., description="失败数")
    start_time: datetime = Field(..., description="开始时间")


# 系统相关模型
class HealthCheck(BaseModel):
    """健康检查"""
    status: str = Field(..., description="状态")
    timestamp: datetime = Field(..., description="时间戳")
    version: str = Field(..., description="版本")
    services: Dict[str, str] = Field(..., description="服务状态")


class SystemInfo(BaseModel):
    """系统信息"""
    cache_enabled: bool = Field(..., description="缓存是否启用")
    cache_dir: str = Field(..., description="缓存目录")
    parallel_enabled: bool = Field(..., description="并行分析是否启用")
    scheduler_running: bool = Field(..., description="调度器是否运行")


class ErrorResponse(BaseModel):
    """错误响应"""
    error: str = Field(..., description="错误信息")
    detail: Optional[str] = Field(default=None, description="错误详情")
    timestamp: datetime = Field(default_factory=datetime.now, description="时间戳")


# 批量数据模型
class BatchDailyDataRequest(BaseModel):
    """批量日线数据请求"""
    stock_codes: List[str] = Field(..., description="股票代码列表")
    days: int = Field(default=30, description="数据天数")
    use_cache_first: bool = Field(default=True, description="优先使用缓存")
    max_workers: int = Field(default=4, description="最大工作线程数")


class BatchDailyDataResponse(BaseModel):
    """批量日线数据响应"""
    results: Dict[str, Optional[Dict[str, Any]]] = Field(..., description="结果字典")
    total_requested: int = Field(..., description="请求总数")
    successful: int = Field(..., description="成功数")
    cache_hits: int = Field(..., description="缓存命中数")
    api_requests: int = Field(..., description="API请求数")


# 回测相关模型
class BacktestRequest(BaseModel):
    """回测请求"""
    stock_code: Optional[str] = Field(default=None, description="股票代码")
    stock_codes: Optional[List[str]] = Field(default=None, description="股票代码列表")
    days_forward: int = Field(default=5, description="向前跟踪天数")
    min_recommendation_score: float = Field(default=0.7, description="最小推荐评分")
    start_date: Optional[str] = Field(default=None, description="回测开始日期")
    end_date: Optional[str] = Field(default=None, description="回测结束日期")


class BacktestResultItem(BaseModel):
    """单次回测结果"""
    recommendation_date: str = Field(..., description="推荐日期")
    recommendation_score: float = Field(..., description="推荐评分")
    price_changes: List[float] = Field(..., description="每日涨跌幅(%)")
    total_return: float = Field(..., description="总收益率(%)")
    is_profitable: bool = Field(..., description="是否盈利")
    max_return: float = Field(..., description="最大收益率(%)")
    min_return: float = Field(..., description="最小收益率(%)")


class BacktestResult(BaseModel):
    """回测结果"""
    stock_code: str = Field(..., description="股票代码")
    days_forward: int = Field(..., description="向前跟踪天数")
    total_recommendations: int = Field(..., description="总推荐次数")
    success_rate: float = Field(..., description="成功率(%)")
    avg_return: float = Field(..., description="平均收益率(%)")
    results: List[BacktestResultItem] = Field(..., description="详细结果")
    backtest_period: Dict[str, str] = Field(..., description="回测期间")


class StockBacktestSummary(BaseModel):
    """股票回测汇总"""
    stock_code: str = Field(..., description="股票代码")
    total_recommendations: int = Field(..., description="总推荐次数")
    success_rate: float = Field(..., description="成功率(%)")
    avg_return: float = Field(..., description="平均收益率(%)")
    error: Optional[str] = Field(default=None, description="错误信息")


class BacktestSummary(BaseModel):
    """批量回测汇总"""
    total_stocks: int = Field(..., description="总股票数")
    total_recommendations: int = Field(..., description="总推荐次数")
    overall_success_rate: float = Field(..., description="整体成功率(%)")
    overall_avg_return: float = Field(..., description="整体平均收益率(%)")
    stock_summaries: List[StockBacktestSummary] = Field(..., description="股票汇总列表")
    backtest_period: str = Field(..., description="回测期间")
    days_forward: int = Field(..., description="向前跟踪天数")


class SuccessRateBucket(BaseModel):
    """成功率分档"""
    min_score: float = Field(..., description="最小评分")
    success_rate: float = Field(..., description="成功率(%)")
    count: int = Field(..., description="样本数")


class DailySuccessRate(BaseModel):
    """每日成功率"""
    date: str = Field(..., description="日期")
    success_rate: float = Field(..., description="成功率(%)")


class TimeWindowSuccess(BaseModel):
    """不同时间窗口成功率"""
    days: int = Field(..., description="时间窗口(天)")
    success_rate: float = Field(..., description="成功率(%)")


class BacktestSuccessRate(BaseModel):
    """回测成功率统计"""
    score_buckets: List[SuccessRateBucket] = Field(..., description="评分分档统计")
    daily_success_rates: List[DailySuccessRate] = Field(..., description="每日成功率")
    time_windows: List[TimeWindowSuccess] = Field(..., description="时间窗口统计")
    total_recommendations: int = Field(..., description="总推荐数")
    overall_success_rate: float = Field(..., description="整体成功率(%)")
    last_updated: str = Field(..., description="最后更新时间")


class RecommendationHistory(BaseModel):
    """推荐历史"""
    date: str = Field(..., description="推荐日期")
    score: float = Field(..., description="评分")
    recommendation_type: str = Field(..., description="推荐类型")
    confidence: float = Field(..., description="置信度")
    price_at_recommendation: float = Field(..., description="推荐时价格")
    reason: str = Field(..., description="推荐理由")


class RecommendationHistoryResponse(BaseModel):
    """推荐历史响应"""
    stock_code: str = Field(..., description="股票代码")
    total_recommendations: int = Field(..., description="总推荐数")
    history: List[RecommendationHistory] = Field(..., description="历史记录")
    avg_score: float = Field(..., description="平均评分")
    high_confidence_count: int = Field(..., description="高置信度推荐数")