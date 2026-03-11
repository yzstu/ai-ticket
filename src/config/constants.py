"""
常量定义模块
统一管理项目中的魔法数字和配置常量
"""

# =============== 分析评分常量 ===============
class ScoreConstants:
    """评分相关常量"""
    # 基础分数
    BASE_SCORE = 50
    
    # 评分阈值
    STRONG_BUY_THRESHOLD = 75  # 强烈买入
    BUY_THRESHOLD = 60         # 买入
    HOLD_THRESHOLD = 40        # 持有
    WATCH_THRESHOLD = 30       # 观望
    SELL_THRESHOLD = 0         # 卖出
    
    # 推荐/评分权重
    TECHNICAL_WEIGHT = 0.30    # 技术面权重
    SENTIMENT_WEIGHT = 0.20    # 情绪面权重
    CAPITAL_WEIGHT = 0.25      # 资金面权重
    RISK_WEIGHT = 0.15         # 风险权重
    OPERATION_WEIGHT = 0.10    # 操作建议权重
    
    # LLM/ML/DL 权重
    LLM_WEIGHT = 0.40
    ML_WEIGHT = 0.35
    DL_WEIGHT = 0.25


# =============== RSI 指标常量 ===============
class RSIConstants:
    """RSI 指标常量"""
    OVERSOLD_THRESHOLD = 30     # 超卖
    OVERBOUGHT_THRESHOLD = 70   # 超买
    
    # 评分区间
    OVERSOLD_BUY_ZONE = 40      # 超卖买入区
    STRONG_ZONE = 60            # 强势区


# =============== 资金流向常量 ===============
class CapitalFlowConstants:
    """资金流向常量"""
    # 大额流出阈值（元）
    LARGE_OUTFLOW_THRESHOLD = 1_000_000  # 100万
    
    # 放量阈值（倍数）
    HIGH_VOLUME_MULTIPLIER = 1.5
    LOW_VOLUME_MULTIPLIER = 0.5


# =============== 缓存配置常量 ===============
class CacheConstants:
    """缓存相关常量"""
    DEFAULT_TTL_HOURS = 24      # 默认缓存时间
    MAX_CACHE_DAYS = 30         # 最大缓存天数
    CLEANUP_INTERVAL_HOURS = 6  # 清理间隔


# =============== 并行处理常量 ===============
class ParallelConstants:
    """并行处理常量"""
    DEFAULT_MAX_WORKERS = 0     # 0 = 自动检测
    DEFAULT_TIMEOUT = 30        # 默认超时（秒）
    DEFAULT_BATCH_SIZE = 100    # 默认批次大小
    DEFAULT_RETRY_COUNT = 2     # 默认重试次数
    PROGRESS_INTERVAL = 10      # 进度更新间隔


# =============== HTTP/API 常量 ===============
class APIConstants:
    """API 相关常量"""
    DEFAULT_TIMEOUT = 30        # 默认请求超时
    MAX_RETRIES = 3            # 最大重试次数
    RETRY_DELAY = 1.0          # 重试延迟（秒）
    
    # 分页
    DEFAULT_PAGE_SIZE = 100
    MAX_PAGE_SIZE = 1000


# =============== 市场环境常量 ===============
class MarketConstants:
    """市场环境常量"""
    BULL_MARKET = "bull"
    BEAR_MARKET = "bear"
    VOLATILE_MARKET = "volatile"
    
    # 不同市场环境的权重配置
    WEIGHT_CONFIGS = {
        BULL_MARKET: {
            "technical": 0.50,
            "sentiment": 0.30,
            "capital": 0.20
        },
        BEAR_MARKET: {
            "technical": 0.70,
            "sentiment": 0.10,
            "capital": 0.20
        },
        VOLATILE_MARKET: {
            "technical": 0.40,
            "sentiment": 0.20,
            "capital": 0.40
        }
    }


# =============== 日期/时间常量 ===============
class TimeConstants:
    """时间相关常量"""
    DATE_FORMAT = "%Y-%m-%d"
    DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
    
    # 缓存时间
    CACHE_TTL_SECONDS = 86400       # 24小时
    TASK_TIMEOUT_SECONDS = 3600     # 1小时
    HEARTBEAT_INTERVAL_SECONDS = 30  # 心跳间隔


# =============== 文件路径常量 ===============
class PathConstants:
    """文件路径常量"""
    DEFAULT_CACHE_DIR = "./cache"
    DEFAULT_MODEL_DIR = "./models"
    DEFAULT_LOG_FILE = "server.log"
    DEFAULT_DB_FILE = "recommendations.db"


# =============== 技术指标常量 ===============
class IndicatorConstants:
    """技术指标常量"""
    # ADX 趋势强度
    ADX_STRONG_TREND = 25
    ADX_MODERATE_TREND = 20
    
    # 相对强度
    RS_OUTPERFORM = 1.1   # 跑赢大盘
    RS_UNDERPERFORM = 0.9  # 弱于大盘
    
    # 布林带位置
    BOLL_OVERSOLD = 0.2   # 接近下轨
    BOLL_OVERBOUGHT = 0.8  # 接近上轨
    
    # 均线周期
    MA_SHORT = 5
    MA_MEDIUM = 20
    MA_LONG = 60