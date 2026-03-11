"""
统一验证工具模块
提供输入验证、日期处理、批量限制等功能
"""
import re
from datetime import datetime, date
from typing import Optional, List, Any
from fastapi import HTTPException


class ValidationError(Exception):
    """验证错误"""
    pass


class DateValidator:
    """日期验证器"""
    
    DATE_FORMAT = "%Y-%m-%d"
    DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
    
    @classmethod
    def validate_date(cls, date_str: str, field_name: str = "date") -> str:
        """
        验证日期格式
        
        Args:
            date_str: 日期字符串
            field_name: 字段名（用于错误信息）
            
        Returns:
            验证后的日期字符串
            
        Raises:
            ValidationError: 日期格式无效
        """
        if not date_str:
            raise ValidationError(f"{field_name} 不能为空")
        
        try:
            datetime.strptime(date_str, cls.DATE_FORMAT)
            return date_str
        except ValueError:
            raise ValidationError(f"{field_name} 格式无效，应为 YYYY-MM-DD")
    
    @classmethod
    def validate_date_range(
        cls, 
        start_date: str, 
        end_date: str,
        max_days: int = 365
    ) -> tuple:
        """
        验证日期范围
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            max_days: 最大天数限制
            
        Returns:
            (start_date, end_date) 元组
            
        Raises:
            ValidationError: 日期范围无效
        """
        cls.validate_date(start_date, "开始日期")
        cls.validate_date(end_date, "结束日期")
        
        start = datetime.strptime(start_date, cls.DATE_FORMAT)
        end = datetime.strptime(end_date, cls.DATE_FORMAT)
        
        if start > end:
            raise ValidationError("开始日期不能晚于结束日期")
        
        days = (end - start).days
        if days > max_days:
            raise ValidationError(f"日期范围不能超过 {max_days} 天")
        
        return start_date, end_date
    
    @classmethod
    def to_date(cls, date_str: str) -> date:
        """转换字符串为 date 对象"""
        return datetime.strptime(date_str, cls.DATE_FORMAT).date()
    
    @classmethod
    def today(cls) -> str:
        """获取今天的日期字符串"""
        return datetime.now().strftime(cls.DATE_FORMAT)


class StockValidator:
    """股票代码验证器"""
    
    # A股股票代码正则：6位数字，000/002/300/600/601/603/688 开头
    STOCK_CODE_PATTERN = re.compile(r'^(000|001|002|003|300|600|601|603|605|688|689)\d{3}$')
    
    @classmethod
    def validate_code(cls, code: str) -> str:
        """
        验证单个股票代码
        
        Args:
            code: 股票代码
            
        Returns:
            验证后的股票代码
            
        Raises:
            ValidationError: 股票代码无效
        """
        if not code or len(code) != 6:
            raise ValidationError(f"股票代码格式无效: {code}，应为6位数字")
        
        if not code.isdigit():
            raise ValidationError(f"股票代码格式无效: {code}，应只包含数字")
        
        if not cls.STOCK_CODE_PATTERN.match(code):
            raise ValidationError(f"不支持的股票代码: {code}")
        
        return code
    
    @classmethod
    def validate_codes(cls, codes: List[str], max_count: int = 100) -> List[str]:
        """
        验证股票代码列表
        
        Args:
            codes: 股票代码列表
            max_count: 最大数量限制
            
        Returns:
            验证后的股票代码列表
            
        Raises:
            ValidationError: 验证失败
        """
        if not codes:
            raise ValidationError("股票代码列表不能为空")
        
        if len(codes) > max_count:
            raise ValidationError(f"股票代码数量超过限制（最多 {max_count} 只）")
        
        validated = []
        seen = set()
        
        for code in codes:
            code = code.strip()
            if code in seen:
                continue  # 去重
            seen.add(code)
            validated.append(cls.validate_code(code))
        
        return validated


class BatchLimitValidator:
    """批量请求限制验证器"""
    
    # 各类型请求的默认限制
    DEFAULT_LIMITS = {
        "analysis": 100,      # 分析请求
        "backtest": 50,       # 回测请求
        "cache": 500,         # 缓存请求
        "sector": 200,        # 板块分析
        "list": 1000,         # 列表请求
    }
    
    @classmethod
    def validate_count(
        cls, 
        count: int, 
        limit_type: str = "list",
        max_override: int = None
    ) -> int:
        """
        验证批量请求数量
        
        Args:
            count: 请求数量
            limit_type: 限制类型
            max_override: 自定义最大值
            
        Returns:
            验证后的数量
            
        Raises:
            ValidationError: 数量超限
        """
        if count < 1:
            raise ValidationError("数量必须大于0")
        
        max_count = max_override or cls.DEFAULT_LIMITS.get(limit_type, 1000)
        
        if count > max_count:
            raise ValidationError(f"数量超过限制（最多 {max_count}）")
        
        return count
    
    @classmethod
    def validate_batch_size(
        cls, 
        batch_size: int,
        min_size: int = 1,
        max_size: int = 500
    ) -> int:
        """
        验证批处理大小
        
        Args:
            batch_size: 批处理大小
            min_size: 最小值
            max_size: 最大值
            
        Returns:
            验证后的批处理大小
        """
        if batch_size < min_size:
            raise ValidationError(f"批处理大小不能小于 {min_size}")
        
        if batch_size > max_size:
            raise ValidationError(f"批处理大小不能超过 {max_size}")
        
        return batch_size


def raise_validation_error(message: str, status_code: int = 400):
    """抛出验证错误"""
    raise HTTPException(
        status_code=status_code,
        detail={
            "error": "Validation Error",
            "message": message
        }
    )