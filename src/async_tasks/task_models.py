"""
异步任务系统 - 数据模型
定义任务状态、数据模型和进度模型
"""
from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "PENDING"        # 待执行
    RUNNING = "RUNNING"        # 运行中
    PAUSED = "PAUSED"          # 暂停
    COMPLETED = "COMPLETED"    # 完成
    FAILED = "FAILED"          # 失败
    CANCELLED = "CANCELLED"    # 取消


class TaskType(str, Enum):
    """任务类型枚举"""
    ANALYSIS_DAILY = "analysis_daily"      # 股票分析
    BACKTEST_BATCH = "backtest_batch"      # 批量回测
    SCHEDULER_CACHE = "scheduler_cache"    # 缓存预加载
    SECTOR_ANALYZE = "sector_analyze"      # 板块分析


class TaskModel(BaseModel):
    """任务数据模型"""
    task_id: str = Field(..., description="任务唯一标识")
    task_type: TaskType = Field(..., description="任务类型")
    task_name: str = Field(..., description="任务名称")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="任务状态")

    # 参数信息
    params: Dict[str, Any] = Field(default_factory=dict, description="执行参数")

    # 进度信息
    total_items: int = Field(default=0, description="总项目数")
    completed_items: int = Field(default=0, description="已完成数")
    progress_percent: float = Field(default=0.0, description="进度百分比")
    current_item: Optional[str] = Field(default=None, description="当前处理项")

    # 断点数据
    checkpoint_data: Dict[str, Any] = Field(default_factory=dict, description="断点数据")

    # 结果信息
    result: Optional[Dict[str, Any]] = Field(default=None, description="任务结果")
    error_message: Optional[str] = Field(default=None, description="错误信息")

    # 时间戳
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    started_at: Optional[datetime] = Field(default=None, description="开始时间")
    completed_at: Optional[datetime] = Field(default=None, description="完成时间")

    # 重试信息
    retry_count: int = Field(default=0, description="重试次数")
    max_retries: int = Field(default=3, description="最大重试次数")

    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class TaskProgress(BaseModel):
    """任务进度模型"""
    task_id: str = Field(..., description="任务ID")
    progress_percent: float = Field(..., ge=0, le=100, description="进度百分比")
    current_item: Optional[str] = Field(default=None, description="当前处理项")
    message: Optional[str] = Field(default=None, description="进度消息")
    completed_items: int = Field(default=0, description="已完成数")
    total_items: int = Field(default=0, description="总项目数")
    status: Optional[TaskStatus] = Field(default=None, description="任务状态")
    timestamp: datetime = Field(default_factory=datetime.now, description="时间戳")

    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class TaskStatistics(BaseModel):
    """任务统计模型"""
    total_tasks: int = Field(default=0, description="总任务数")
    pending_tasks: int = Field(default=0, description="待执行任务数")
    running_tasks: int = Field(default=0, description="运行中任务数")
    completed_tasks: int = Field(default=0, description="已完成任务数")
    failed_tasks: int = Field(default=0, description="失败任务数")
    average_execution_time: float = Field(default=0.0, description="平均执行时间（秒）")
    success_rate: float = Field(default=0.0, description="成功率")


class CheckpointData(BaseModel):
    """断点数据模型"""
    completed_items: List[str] = Field(default_factory=list, description="已完成项目列表")
    failed_items: List[Dict[str, Any]] = Field(default_factory=list, description="失败项目列表")
    last_position: int = Field(default=0, description="最后位置")
    batch_progress: Dict[int, int] = Field(default_factory=dict, description="批次进度")
    intermediate_results: List[Dict[str, Any]] = Field(default_factory=list, description="中间结果")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")


class TaskFilter(BaseModel):
    """任务筛选模型"""
    status: Optional[TaskStatus] = Field(default=None, description="状态筛选")
    task_type: Optional[TaskType] = Field(default=None, description="类型筛选")
    date_from: Optional[datetime] = Field(default=None, description="起始日期")
    date_to: Optional[datetime] = Field(default=None, description="结束日期")
    limit: int = Field(default=100, ge=1, le=1000, description="返回数量限制")
    offset: int = Field(default=0, ge=0, description="偏移量")