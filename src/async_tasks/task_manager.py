"""
异步任务系统 - 任务管理器
管理任务的创建、执行、暂停、恢复和取消
"""
import asyncio
import logging
import threading
from typing import Callable, Optional, Dict, Any, List
from datetime import datetime
import uuid

from .task_models import TaskModel, TaskStatus, TaskType, TaskProgress
from .task_store import get_task_store

logger = logging.getLogger(__name__)


class TaskManager:
    """任务管理器"""

    def __init__(self, max_concurrent_tasks: int = 4):
        """
        初始化任务管理器

        Args:
            max_concurrent_tasks: 最大并发任务数
        """
        self.max_concurrent_tasks = max_concurrent_tasks
        self.store = get_task_store()
        self.task_handlers: Dict[TaskType, Callable] = {}
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self.task_locks: Dict[str, asyncio.Lock] = {}
        self.progress_callbacks: Dict[str, List[Callable]] = {}

        # 自动注册任务执行器
        self._setup_default_handlers()

    def _setup_default_handlers(self):
        """设置默认的任务处理器"""
        from .task_executor import setup_task_executor
        executor = setup_task_executor(self)

    def register_handler(self, task_type: TaskType, handler: Callable):
        """
        注册任务处理器

        Args:
            task_type: 任务类型
            handler: 处理器函数
        """
        self.task_handlers[task_type] = handler
        logger.info(f"Registered handler for {task_type}")

    async def create_task(
        self,
        task_type: TaskType,
        task_name: str,
        params: Dict[str, Any],
        total_items: int = 0,
        max_retries: int = 3
    ) -> str:
        """
        创建新任务

        Args:
            task_type: 任务类型
            task_name: 任务名称
            params: 执行参数
            total_items: 总项目数
            max_retries: 最大重试次数

        Returns:
            任务ID
        """
        task_id = str(uuid.uuid4())

        task = TaskModel(
            task_id=task_id,
            task_type=task_type,
            task_name=task_name,
            status=TaskStatus.PENDING,
            params=params,
            total_items=total_items,
            max_retries=max_retries
        )

        if self.store.create_task(task):
            logger.info(f"Task created: {task_id}")
            return task_id
        else:
            raise ValueError(f"Failed to create task: {task_id}")

    async def start_task(self, task_id: str) -> bool:
        """
        启动任务

        Args:
            task_id: 任务ID

        Returns:
            是否启动成功
        """
        task = self.store.get_task(task_id)
        if not task:
            logger.error(f"Task not found: {task_id}")
            return False

        if task.status != TaskStatus.PENDING:
            logger.warning(f"Task {task_id} is not pending (status: {task.status})")
            return False

        # 检查并发限制
        running_count = len([t for t in self.store.list_tasks()
                            if t.status == TaskStatus.RUNNING])
        if running_count >= self.max_concurrent_tasks:
            logger.warning(f"Max concurrent tasks reached: {self.max_concurrent_tasks}")
            return False

        # 获取处理器
        handler = self.task_handlers.get(task.task_type)
        if not handler:
            logger.error(f"No handler registered for task type: {task.task_type}")
            await self._update_task_status(task_id, TaskStatus.FAILED, "No handler registered")
            return False

        # 创建任务锁和回调列表
        self.task_locks[task_id] = asyncio.Lock()
        self.progress_callbacks[task_id] = []

        # 创建异步任务
        self.running_tasks[task_id] = asyncio.create_task(
            self._execute_task(task_id, handler)
        )

        logger.info(f"Task started: {task_id}")
        return True

    async def pause_task(self, task_id: str) -> bool:
        """
        暂停任务

        Args:
            task_id: 任务ID

        Returns:
            是否暂停成功
        """
        task = self.store.get_task(task_id)
        if not task or task.status != TaskStatus.RUNNING:
            return False

        # 设置暂停标志
        self.store.update_task_status(task_id, TaskStatus.PAUSED)

        # 取消运行中的任务
        if task_id in self.running_tasks:
            self.running_tasks[task_id].cancel()
            try:
                await self.running_tasks[task_id]
            except asyncio.CancelledError:
                pass
            del self.running_tasks[task_id]

        logger.info(f"Task paused: {task_id}")
        return True

    async def resume_task(self, task_id: str) -> bool:
        """
        恢复任务

        Args:
            task_id: 任务ID

        Returns:
            是否恢复成功
        """
        task = self.store.get_task(task_id)
        if not task or task.status != TaskStatus.PAUSED:
            logger.warning(f"Task {task_id} not found or not paused")
            return False

        # 获取处理器
        handler = self.task_handlers.get(task.task_type)
        if not handler:
            logger.error(f"No handler registered for task type: {task.task_type}")
            await self._update_task_status(task_id, TaskStatus.FAILED, "No handler registered")
            return False

        # 更新状态为运行中
        await self._update_task_status(task_id, TaskStatus.RUNNING)

        # 创建任务锁和回调列表
        self.task_locks[task_id] = asyncio.Lock()
        self.progress_callbacks[task_id] = []

        # 创建异步任务直接恢复执行
        self.running_tasks[task_id] = asyncio.create_task(
            self._execute_task(task_id, handler)
        )

        logger.info(f"Task resumed: {task_id}")
        return True

    async def cancel_task(self, task_id: str) -> bool:
        """
        取消任务

        Args:
            task_id: 任务ID

        Returns:
            是否取消成功
        """
        task = self.store.get_task(task_id)
        if not task or task.status not in [TaskStatus.PENDING, TaskStatus.RUNNING]:
            return False

        # 更新状态为取消
        await self._update_task_status(task_id, TaskStatus.CANCELLED)

        # 取消运行中的任务
        if task_id in self.running_tasks:
            self.running_tasks[task_id].cancel()
            try:
                await self.running_tasks[task_id]
            except asyncio.CancelledError:
                pass
            del self.running_tasks[task_id]

        # 清理资源
        if task_id in self.task_locks:
            del self.task_locks[task_id]
        if task_id in self.progress_callbacks:
            del self.progress_callbacks[task_id]

        logger.info(f"Task cancelled: {task_id}")
        return True

    async def retry_task(self, task_id: str) -> bool:
        """
        重试任务

        Args:
            task_id: 任务ID

        Returns:
            是否重试成功
        """
        task = self.store.get_task(task_id)
        if not task or task.status != TaskStatus.FAILED:
            return False

        if task.retry_count >= task.max_retries:
            logger.warning(f"Task {task_id} exceeded max retries")
            return False

        # 更新重试次数和状态
        task.retry_count += 1
        await self._update_task_status(task_id, TaskStatus.PENDING)

        # 重新启动
        return await self.start_task(task_id)

    def get_task(self, task_id: str) -> Optional[TaskModel]:
        """
        获取任务详情

        Args:
            task_id: 任务ID

        Returns:
            任务模型或None
        """
        return self.store.get_task(task_id)

    def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        task_type: Optional[TaskType] = None,
        limit: int = 100
    ) -> List[TaskModel]:
        """
        列出任务

        Args:
            status: 状态筛选
            task_type: 类型筛选
            limit: 返回数量限制

        Returns:
            任务列表
        """
        from .task_models import TaskFilter
        filter_obj = TaskFilter(
            status=status,
            task_type=task_type,
            limit=limit
        )
        return self.store.list_tasks(filter_obj)

    def get_running_tasks(self) -> List[TaskModel]:
        """
        获取运行中的任务

        Returns:
            运行中的任务列表
        """
        return self.store.get_running_tasks()

    def get_statistics(self):
        """
        获取统计信息

        Returns:
            统计信息
        """
        return self.store.get_statistics()

    def register_progress_callback(self, task_id: str, callback: Callable):
        """
        注册进度回调函数

        Args:
            task_id: 任务ID
            callback: 回调函数
        """
        if task_id not in self.progress_callbacks:
            self.progress_callbacks[task_id] = []
        self.progress_callbacks[task_id].append(callback)

    async def _execute_task(self, task_id: str, handler: Callable):
        """
        执行任务

        Args:
            task_id: 任务ID
            handler: 处理器函数
        """
        try:
            # 更新状态为运行中
            await self._update_task_status(task_id, TaskStatus.RUNNING)

            task = self.store.get_task(task_id)

            # 执行进度回调函数
            async def progress_callback(progress: TaskProgress):
                # 更新任务进度
                task.completed_items = progress.completed_items
                task.progress_percent = progress.progress_percent
                task.current_item = progress.current_item
                self.store.update_task(task)

                # 调用注册的回调（带详细错误处理）
                failed_callbacks = []
                for i, callback in enumerate(self.progress_callbacks.get(task_id, [])):
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(progress)
                        else:
                            callback(progress)
                    except Exception as e:
                        logger.error(
                            f"Progress callback {i} failed for task {task_id}: {e}",
                            exc_info=True
                        )
                        failed_callbacks.append(i)
                
                # 移除失败的回调（防止重复失败）
                if failed_callbacks:
                    for i in reversed(failed_callbacks):  # 从后往前删除
                        try:
                            self.progress_callbacks[task_id].pop(i)
                            logger.warning(f"Removed failed callback {i} for task {task_id}")
                        except IndexError:
                            pass

            # 获取任务锁
            lock = self.task_locks.get(task_id, asyncio.Lock())

            # 执行处理器
            async with lock:
                result = await handler(task, progress_callback)
                task.result = result

            # 更新为完成状态
            await self._update_task_status(task_id, TaskStatus.COMPLETED)

            logger.info(f"Task completed: {task_id}")

        except asyncio.CancelledError:
            # 任务被取消
            logger.info(f"Task cancelled: {task_id}")
            await self._update_task_status(task_id, TaskStatus.CANCELLED)
        except Exception as e:
            # 任务执行失败
            logger.error(f"Task failed: {task_id}, error: {e}", exc_info=True)
            task.error_message = str(e)
            await self._update_task_status(task_id, TaskStatus.FAILED)
        finally:
            # 清理资源
            if task_id in self.running_tasks:
                del self.running_tasks[task_id]
            if task_id in self.task_locks:
                del self.task_locks[task_id]
            if task_id in self.progress_callbacks:
                del self.progress_callbacks[task_id]

    async def _update_task_status(self, task_id: str, status: TaskStatus, error_message: str = None):
        """
        更新任务状态

        Args:
            task_id: 任务ID
            status: 新状态
            error_message: 错误信息（可选）
        """
        task = self.store.get_task(task_id)
        if task:
            task.status = status
            if error_message:
                task.error_message = error_message
            self.store.update_task(task)


# 全局任务管理器实例
_task_manager: Optional[TaskManager] = None
_manager_lock = threading.Lock()


def get_task_manager(max_concurrent_tasks: int = 4) -> TaskManager:
    """
    获取任务管理器实例（单例模式，线程安全）

    Args:
        max_concurrent_tasks: 最大并发任务数

    Returns:
        任务管理器实例
    """
    global _task_manager
    if _task_manager is None:
        with _manager_lock:
            # 双重检查锁定
            if _task_manager is None:
                _task_manager = TaskManager(max_concurrent_tasks)
    return _task_manager