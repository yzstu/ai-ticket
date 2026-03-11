"""
FastAPI项目 - WebSocket路由
提供实时任务进度推送功能
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Dict, List
import logging
import json
import asyncio

from src.async_tasks.task_models import TaskProgress
from src.async_tasks.task_manager import get_task_manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ws/tasks", tags=["websockets"])


class ConnectionManager:
    """WebSocket连接管理器"""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        """接受WebSocket连接"""
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"Client {client_id} connected")

    def disconnect(self, client_id: str):
        """断开WebSocket连接"""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            logger.info(f"Client {client_id} disconnected")

    async def send_personal_message(self, message: str, client_id: str):
        """发送个人消息"""
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_text(message)
            except Exception as e:
                logger.error(f"Failed to send message to {client_id}: {e}")
                self.disconnect(client_id)

    async def broadcast(self, message: str, client_id: str = None):
        """广播消息"""
        if client_id:
            # 只发送给特定客户端
            await self.send_personal_message(message, client_id)
        else:
            # 广播给所有客户端
            disconnected_clients = []
            for client_id, connection in self.active_connections.items():
                try:
                    await connection.send_text(message)
                except Exception as e:
                    logger.error(f"Failed to send message to {client_id}: {e}")
                    disconnected_clients.append(client_id)

            # 清理断开的连接
            for client_id in disconnected_clients:
                self.disconnect(client_id)

    def get_connected_clients(self) -> List[str]:
        """获取所有已连接的客户端ID"""
        return list(self.active_connections.keys())


manager = ConnectionManager()


@router.websocket("/{client_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    client_id: str
):
    """
    WebSocket端点，用于接收任务进度推送

    - **client_id**: 客户端唯一标识
    """
    await manager.connect(websocket, client_id)

    # 获取任务管理器实例
    task_manager = get_task_manager()

    try:
        while True:
            # 接收客户端消息（心跳等）
            data = await websocket.receive_text()
            message_data = json.loads(data)

            message_type = message_data.get("type")

            if message_type == "ping":
                # 回复心跳
                await manager.send_personal_message(
                    json.dumps({"type": "pong"}),
                    client_id
                )
            elif message_type == "subscribe":
                # 订阅特定任务的进度
                task_id = message_data.get("task_id")
                if task_id:
                    # 注册进度回调
                    task_manager.register_progress_callback(
                        task_id,
                        lambda progress: asyncio.create_task(
                            manager.send_personal_message(
                                json.dumps({
                                    "type": "task_progress",
                                    "data": progress.dict()
                                }),
                                client_id
                            )
                        )
                    )
                    await manager.send_personal_message(
                        json.dumps({
                            "type": "subscribed",
                            "task_id": task_id
                        }),
                        client_id
                    )

    except WebSocketDisconnect:
        manager.disconnect(client_id)


@router.post("/broadcast")
async def broadcast_message(message: dict):
    """
    广播消息给所有WebSocket客户端
    （用于调试或管理功能）
    """
    await manager.broadcast(json.dumps(message))
    return {"status": "broadcast sent", "client_count": len(manager.active_connections)}


@router.get("/connections")
async def get_active_connections():
    """获取所有活跃的WebSocket连接"""
    return {
        "connected_clients": manager.get_connected_clients(),
        "total_connections": len(manager.active_connections)
    }