"""
异步任务系统 - SQLite存储层
基于SQLite的任务持久化管理
"""
import sqlite3
import json
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from pathlib import Path

from .task_models import (
    TaskModel, TaskStatus, TaskType, TaskFilter, TaskStatistics
)

logger = logging.getLogger(__name__)


class TaskStore:
    """任务存储管理器"""

    def __init__(self, db_path: str = "./cache/tasks.db"):
        """
        初始化任务存储

        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self._ensure_db_dir()
        self._init_db()

    def _ensure_db_dir(self):
        """确保数据库目录存在"""
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)

    def _init_db(self):
        """初始化数据库表结构"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    task_type TEXT NOT NULL,
                    task_name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    params TEXT,
                    total_items INTEGER DEFAULT 0,
                    completed_items INTEGER DEFAULT 0,
                    progress_percent REAL DEFAULT 0.0,
                    current_item TEXT,
                    checkpoint_data TEXT,
                    result TEXT,
                    error_message TEXT,
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT,
                    retry_count INTEGER DEFAULT 0,
                    max_retries INTEGER DEFAULT 3
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_status ON tasks(status)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_task_type ON tasks(task_type)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_created_at ON tasks(created_at)
            """)
            conn.commit()

    def create_task(self, task: TaskModel) -> bool:
        """
        创建新任务

        Args:
            task: 任务模型

        Returns:
            是否创建成功
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO tasks (
                        task_id, task_type, task_name, status, params,
                        total_items, completed_items, progress_percent,
                        current_item, checkpoint_data, result, error_message,
                        created_at, started_at, completed_at,
                        retry_count, max_retries
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    task.task_id,
                    task.task_type.value if hasattr(task.task_type, 'value') else task.task_type,
                    task.task_name,
                    task.status.value if hasattr(task.status, 'value') else task.status,
                    json.dumps(task.params) if task.params else None,
                    task.total_items,
                    task.completed_items,
                    task.progress_percent,
                    task.current_item,
                    json.dumps(task.checkpoint_data) if task.checkpoint_data else None,
                    json.dumps(task.result) if task.result else None,
                    task.error_message,
                    task.created_at.isoformat(),
                    task.started_at.isoformat() if task.started_at else None,
                    task.completed_at.isoformat() if task.completed_at else None,
                    task.retry_count,
                    task.max_retries
                ))
                conn.commit()
            logger.info(f"Task created: {task.task_id}")
            return True
        except sqlite3.IntegrityError:
            logger.error(f"Task already exists: {task.task_id}")
            return False
        except Exception as e:
            logger.error(f"Failed to create task: {e}", exc_info=True)
            return False

    def get_task(self, task_id: str) -> Optional[TaskModel]:
        """
        获取任务详情

        Args:
            task_id: 任务ID

        Returns:
            任务模型或None
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    "SELECT * FROM tasks WHERE task_id = ?",
                    (task_id,)
                )
                row = cursor.fetchone()

                if row:
                    return self._row_to_task_model(row)
                return None
        except Exception as e:
            logger.error(f"Failed to get task {task_id}: {e}", exc_info=True)
            return None

    def update_task(self, task: TaskModel) -> bool:
        """
        更新任务信息

        Args:
            task: 任务模型

        Returns:
            是否更新成功
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE tasks SET
                        task_type = ?,
                        task_name = ?,
                        status = ?,
                        params = ?,
                        total_items = ?,
                        completed_items = ?,
                        progress_percent = ?,
                        current_item = ?,
                        checkpoint_data = ?,
                        result = ?,
                        error_message = ?,
                        started_at = ?,
                        completed_at = ?,
                        retry_count = ?,
                        max_retries = ?
                    WHERE task_id = ?
                """, (
                    task.task_type.value if hasattr(task.task_type, 'value') else task.task_type,
                    task.task_name,
                    task.status.value if hasattr(task.status, 'value') else task.status,
                    json.dumps(task.params) if task.params else None,
                    task.total_items,
                    task.completed_items,
                    task.progress_percent,
                    task.current_item,
                    json.dumps(task.checkpoint_data) if task.checkpoint_data else None,
                    json.dumps(task.result) if task.result else None,
                    task.error_message,
                    task.started_at.isoformat() if task.started_at else None,
                    task.completed_at.isoformat() if task.completed_at else None,
                    task.retry_count,
                    task.max_retries,
                    task.task_id
                ))
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to update task {task.task_id}: {e}", exc_info=True)
            return False

    def delete_task(self, task_id: str) -> bool:
        """
        删除任务

        Args:
            task_id: 任务ID

        Returns:
            是否删除成功
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "DELETE FROM tasks WHERE task_id = ?",
                    (task_id,)
                )
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Failed to delete task {task_id}: {e}", exc_info=True)
            return False

    def list_tasks(self, filter_obj: Optional[TaskFilter] = None) -> List[TaskModel]:
        """
        列出任务

        Args:
            filter_obj: 筛选条件

        Returns:
            任务列表
        """
        try:
            filters = []
            params = []

            if filter_obj:
                if filter_obj.status:
                    filters.append("status = ?")
                    params.append(filter_obj.status.value)

                if filter_obj.task_type:
                    filters.append("task_type = ?")
                    params.append(filter_obj.task_type.value)

                if filter_obj.date_from:
                    filters.append("created_at >= ?")
                    params.append(filter_obj.date_from.isoformat())

                if filter_obj.date_to:
                    filters.append("created_at <= ?")
                    params.append(filter_obj.date_to.isoformat())

            where_clause = " AND ".join(filters) if filters else "1=1"

            query = f"""
                SELECT * FROM tasks
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """
            params.extend([filter_obj.limit if filter_obj else 100,
                          filter_obj.offset if filter_obj else 0])

            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(query, params)
                return [self._row_to_task_model(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to list tasks: {e}", exc_info=True)
            return []

    def get_running_tasks(self) -> List[TaskModel]:
        """
        获取运行中的任务

        Returns:
            运行中的任务列表
        """
        return self.list_tasks(TaskFilter(status=TaskStatus.RUNNING))

    def update_task_status(self, task_id: str, status: TaskStatus) -> bool:
        """
        更新任务状态

        Args:
            task_id: 任务ID
            status: 新状态

        Returns:
            是否更新成功
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                now = datetime.now().isoformat()
                conn.execute("""
                    UPDATE tasks
                    SET status = ?, started_at = CASE WHEN ? = 'RUNNING' THEN ? ELSE started_at END,
                        completed_at = CASE WHEN ? IN ('COMPLETED', 'FAILED', 'CANCELLED') THEN ? ELSE completed_at END
                    WHERE task_id = ?
                """, (
                    status.value,
                    status.value, now,
                    status.value, now,
                    task_id
                ))
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to update task status {task_id}: {e}", exc_info=True)
            return False

    def get_statistics(self) -> TaskStatistics:
        """
        获取任务统计信息

        Returns:
            统计信息
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row

                # 获取各状态任务数
                cursor = conn.execute("""
                    SELECT status, COUNT(*) as count
                    FROM tasks
                    GROUP BY status
                """)
                status_counts = {row['status']: row['count'] for row in cursor.fetchall()}

                # 获取平均执行时间
                cursor = conn.execute("""
                    SELECT AVG(
                        CAST((julianday(coalesce(completed_at, datetime('now'))) - julianday(started_at)) * 24 * 60 * 60 AS INTEGER)
                    ) as avg_time
                    FROM tasks
                    WHERE status = 'COMPLETED' AND started_at IS NOT NULL
                """)
                avg_time_row = cursor.fetchone()
                avg_execution_time = avg_time_row['avg_time'] if avg_time_row and avg_time_row['avg_time'] else 0.0

                # 计算成功率
                total = sum(status_counts.values())
                completed = status_counts.get('COMPLETED', 0)
                success_rate = (completed / total * 100) if total > 0 else 0.0

                return TaskStatistics(
                    total_tasks=total,
                    pending_tasks=status_counts.get('PENDING', 0),
                    running_tasks=status_counts.get('RUNNING', 0),
                    completed_tasks=status_counts.get('COMPLETED', 0),
                    failed_tasks=status_counts.get('FAILED', 0),
                    average_execution_time=avg_execution_time,
                    success_rate=success_rate
                )
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}", exc_info=True)
            return TaskStatistics()

    def cleanup_old_tasks(self, days: int = 7) -> int:
        """
        清理旧任务

        Args:
            days: 保留天数

        Returns:
            清理的任务数量
        """
        try:
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    DELETE FROM tasks
                    WHERE status IN ('COMPLETED', 'FAILED', 'CANCELLED')
                    AND completed_at < ?
                """, (cutoff_date,))
                conn.commit()
                return cursor.rowcount
        except Exception as e:
            logger.error(f"Failed to cleanup old tasks: {e}", exc_info=True)
            return 0

    def _row_to_task_model(self, row: sqlite3.Row) -> TaskModel:
        """将数据库行转换为任务模型"""
        # 处理task_type
        task_type_str = row['task_type']
        task_type = TaskType(task_type_str) if task_type_str in [t.value for t in TaskType] else task_type_str

        # 处理status
        status_str = row['status']
        status = TaskStatus(status_str) if status_str in [s.value for s in TaskStatus] else status_str

        return TaskModel(
            task_id=row['task_id'],
            task_type=task_type,
            task_name=row['task_name'],
            status=status,
            params=json.loads(row['params']) if row['params'] else {},
            total_items=row['total_items'],
            completed_items=row['completed_items'],
            progress_percent=row['progress_percent'],
            current_item=row['current_item'],
            checkpoint_data=json.loads(row['checkpoint_data']) if row['checkpoint_data'] else {},
            result=json.loads(row['result']) if row['result'] else None,
            error_message=row['error_message'],
            created_at=datetime.fromisoformat(row['created_at']),
            started_at=datetime.fromisoformat(row['started_at']) if row['started_at'] else None,
            completed_at=datetime.fromisoformat(row['completed_at']) if row['completed_at'] else None,
            retry_count=row['retry_count'],
            max_retries=row['max_retries']
        )


# 全局任务存储实例
_task_store: Optional[TaskStore] = None


def get_task_store(db_path: str = "./cache/tasks.db") -> TaskStore:
    """
    获取任务存储实例（单例模式）

    Args:
        db_path: 数据库路径

    Returns:
        任务存储实例
    """
    global _task_store
    if _task_store is None:
        _task_store = TaskStore(db_path)
    return _task_store