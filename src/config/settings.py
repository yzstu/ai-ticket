"""
统一配置管理模块
使用 Pydantic Settings 进行配置管理，支持 .env 文件和类型验证
"""
import os
from functools import lru_cache
from typing import Optional

try:
    from pydantic import BaseSettings, Field
except ImportError:
    # 如果没有安装 pydantic，使用自定义实现
    from pydantic_core import from_attributes
    from typing import Any, Dict
    import typing

    class BaseSettings(BaseSettings):
        """Pydantic BaseSettings 的简化实现"""

        def __init__(self, **data: Any):
            super().__init__(**data)

        @classmethod
        def parse_env_var(cls, field_name: str, raw_val: str) -> Any:
            """解析环境变量"""
            return raw_val

        @classmethod
        def model_fields(cls) -> Dict[str, Any]:
            """获取字段定义"""
            fields = {}
            for key, value in cls.__annotations__.items():
                if hasattr(cls, key):
                    field_value = getattr(cls, key)
                    if isinstance(field_value, Field):
                        fields[key] = field_value
                    else:
                        fields[key] = Field(default=field_value)
            return fields

        class Config:
            env_file = ".env"
            case_sensitive = True


class APISettings(BaseSettings):
    """API 服务配置"""

    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    api_base_url: str = Field(default="http://localhost:8000", env="API_BASE_URL")


class OllamaSettings(BaseSettings):
    """Ollama 配置"""

    ollama_base_url: str = Field(default="http://localhost:11434", env="OLLAMA_URL")
    ollama_model: str = Field(default="qwen3-coder:480b-cloud", env="OLLAMA_MODEL")
    ollama_timeout: int = Field(default=120, env="OLLAMA_TIMEOUT")


class DataSourceSettings(BaseSettings):
    """数据源配置"""

    akshare_timeout: int = Field(default=30, env="AKSHARE_TIMEOUT")
    akshare_max_retries: int = Field(default=3, env="AKSHARE_MAX_RETRIES")
    yfinance_timeout: int = Field(default=30, env="YFINANCE_TIMEOUT")
    yfinance_max_retries: int = Field(default=3, env="YFINANCE_MAX_RETRIES")


class CacheSettings(BaseSettings):
    """缓存配置"""

    cache_dir: str = Field(default="./cache", env="CACHE_DIR")
    cache_ttl_hours: int = Field(default=24, env="CACHE_TTL_HOURS")
    cache_max_days: int = Field(default=30, env="CACHE_MAX_DAYS")


class ParallelSettings(BaseSettings):
    """并行处理配置"""

    max_workers: int = Field(default=0, env="MAX_WORKERS")  # 0 = 自动检测
    thread_timeout: int = Field(default=30, env="THREAD_TIMEOUT")
    batch_size: int = Field(default=100, env="BATCH_SIZE")


class AnalysisSettings(BaseSettings):
    """分析配置"""

    max_stocks_to_analyze: int = Field(default=0, env="MAX_STOCKS_TO_ANALYZE")  # 0 = 无限制
    temperature: float = Field(default=0.3, env="TEMPERATURE")


class LogSettings(BaseSettings):
    """日志配置"""

    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_file: Optional[str] = Field(default="server.log", env="LOG_FILE")


class Settings(BaseSettings):
    """统一应用配置"""

    # 子配置
    api: APISettings = Field(default_factory=APISettings)
    ollama: OllamaSettings = Field(default_factory=OllamaSettings)
    data_source: DataSourceSettings = Field(default_factory=DataSourceSettings)
    cache: CacheSettings = Field(default_factory=CacheSettings)
    parallel: ParallelSettings = Field(default_factory=ParallelSettings)
    analysis: AnalysisSettings = Field(default_factory=AnalysisSettings)
    log: LogSettings = Field(default_factory=LogSettings)

    # 全局配置
    model_dir: str = Field(default="./models", env="MODEL_DIR")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    def get_api_docs_url(self) -> str:
        """获取 API 文档 URL"""
        return f"{self.api.api_base_url}/docs"

    def get_api_redoc_url(self) -> str:
        """获取 ReDoc URL"""
        return f"{self.api.api_base_url}/redoc"

    def as_dict(self) -> dict:
        """转换为字典（用于调试）"""
        return {
            "api": {
                "host": self.api.api_host,
                "port": self.api.api_port,
                "base_url": self.api.api_base_url,
            },
            "ollama": {
                "base_url": self.ollama.ollama_base_url,
                "model": self.ollama.ollama_model,
                "timeout": self.ollama.ollama_timeout,
            },
            "cache": {
                "dir": self.cache.cache_dir,
                "ttl_hours": self.cache.cache_ttl_hours,
                "max_days": self.cache.cache_max_days,
            },
            "parallel": {
                "max_workers": self.parallel.max_workers,
                "thread_timeout": self.parallel.thread_timeout,
                "batch_size": self.parallel.batch_size,
            },
            "analysis": {
                "max_stocks": self.analysis.max_stocks_to_analyze,
                "temperature": self.analysis.temperature,
            },
            "log": {
                "level": self.log.log_level,
                "file": self.log.log_file,
            }
        }


# 单例访问
@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()


# 便捷访问
settings = Settings()