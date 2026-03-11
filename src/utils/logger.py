"""
统一日志管理模块
提供标准化的日志记录功能，支持多种输出格式和级别
"""
import logging
import sys
from typing import Optional
from datetime import datetime


class ColoredFormatter(logging.Formatter):
    """彩色日志格式化器"""

    # 颜色代码
    COLORS = {
        'DEBUG': '\033[36m',    # 青色
        'INFO': '\033[32m',     # 绿色
        'WARNING': '\033[33m',  # 黄色
        'ERROR': '\033[31m',    # 红色
        'CRITICAL': '\033[35m', # 紫色
        'RESET': '\033[0m'      # 重置
    }

    def format(self, record):
        # 添加颜色
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        record.levelname = f"{color}{record.levelname}{self.COLORS['RESET']}"

        # 调用父类格式化
        return super().format(record)


class StructuredFormatter(logging.Formatter):
    """结构化日志格式化器"""

    def format(self, record):
        # 获取基础信息
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
        }

        # 添加文件信息（如果是错误）
        if record.levelno >= logging.ERROR:
            log_entry['file'] = f"{record.filename}:{record.lineno}"
            log_entry['function'] = record.funcName

        # 添加异常信息
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)

        return str(log_entry)


def get_logger(
    name: str,
    level: str = "INFO",
    log_file: Optional[str] = None,
    use_colors: bool = True,
    structured: bool = False
) -> logging.Logger:
    """
    获取配置好的日志记录器

    Args:
        name: 日志记录器名称
        level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: 日志文件路径（可选）
        use_colors: 是否使用彩色输出
        structured: 是否使用结构化输出

    Returns:
        配置好的日志记录器
    """
    logger = logging.getLogger(name)

    # 避免重复添加处理器
    if logger.handlers:
        return logger

    # 设置日志级别
    logger.setLevel(getattr(logging, level.upper()))

    # 创建格式化器
    if structured:
        formatter = StructuredFormatter()
    else:
        format_template = (
            '%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s'
        )
        formatter = ColoredFormatter(format_template) if use_colors else logging.Formatter(format_template)

    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 文件处理器（如果指定了日志文件）
    if log_file:
        try:
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            # 文件处理器不使用颜色
            file_formatter = StructuredFormatter() if structured else logging.Formatter(
                '%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s'
            )
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            logger.warning(f"无法创建日志文件 {log_file}: {e}")

    return logger


# 便捷函数
def get_app_logger(name: str) -> logging.Logger:
    """获取应用日志记录器"""
    return get_logger(name, level="INFO", use_colors=True)


def get_debug_logger(name: str) -> logging.Logger:
    """获取调试日志记录器"""
    return get_logger(name, level="DEBUG", use_colors=True)


def get_error_logger(name: str, log_file: str = "error.log") -> logging.Logger:
    """获取错误日志记录器"""
    return get_logger(name, level="ERROR", log_file=log_file, use_colors=False)


# 全局默认日志记录器
default_logger = get_app_logger("app")


# 示例使用
if __name__ == "__main__":
    logger = get_app_logger(__name__)
    logger.info("日志系统初始化完成")
    logger.debug("这是一条调试信息")
    logger.warning("这是一条警告信息")
    logger.error("这是一条错误信息")