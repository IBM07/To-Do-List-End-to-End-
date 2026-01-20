# ===========================================
# AuraTask - WebSocket for Live Updates
# ===========================================
# Real-time dashboard updates without page refresh

import json
from typing import Dict, List, Set

from fastapi import WebSocket, WebSocketDisconnect, APIRouter

from app.schemas.task import TaskResponse


router = APIRouter()


class ConnectionManager:
    """
    Manages WebSocket connections for real-time updates.
    
    Tracks active connections per user for targeted broadcasts.
    """
    
    def __init__(self):
        # Map user_id -> set of active WebSocket connections
        self.active_connections: Dict[int, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: int):
        """
        Accept and register a new WebSocket connection.
        
        Args:
            websocket: The WebSocket connection
            user_id: ID of the connecting user
        """
        await websocket.accept()
        
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        
        self.active_connections[user_id].add(websocket)
    
    def disconnect(self, websocket: WebSocket, user_id: int):
        """
        Remove a WebSocket connection when client disconnects.
        
        Args:
            websocket: The WebSocket connection
            user_id: ID of the disconnecting user
        """
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            
            # Clean up empty sets
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
    
    async def send_personal_message(self, message: dict, user_id: int):
        """
        Send a message to all connections of a specific user.
        
        Args:
            message: JSON-serializable message dict
            user_id: Target user ID
        """
        if user_id in self.active_connections:
            disconnected = []
            
            for websocket in self.active_connections[user_id]:
                try:
                    await websocket.send_json(message)
                except Exception:
                    disconnected.append(websocket)
            
            # Clean up dead connections
            for ws in disconnected:
                self.active_connections[user_id].discard(ws)
    
    async def broadcast(self, message: dict):
        """
        Send a message to all connected users.
        
        Args:
            message: JSON-serializable message dict
        """
        for user_id in list(self.active_connections.keys()):
            await self.send_personal_message(message, user_id)
    
    def get_connection_count(self, user_id: int = None) -> int:
        """
        Get number of active connections.
        
        Args:
            user_id: Optional user ID to count for specific user
            
        Returns:
            Number of active connections
        """
        if user_id is not None:
            return len(self.active_connections.get(user_id, set()))
        
        return sum(len(conns) for conns in self.active_connections.values())


# Global connection manager instance
manager = ConnectionManager()


@router.websocket("/ws/tasks/{user_id}")
async def websocket_tasks_endpoint(websocket: WebSocket, user_id: int):
    """
    WebSocket endpoint for real-time task updates.
    
    The dashboard connects to this endpoint to receive instant
    updates when tasks are created, modified, or completed.
    
    Message format (server -> client):
    {
        "event": "task_created" | "task_updated" | "task_deleted" | "score_updated",
        "data": { ... task data ... }
    }
    """
    await manager.connect(websocket, user_id)
    
    try:
        # Send connection confirmation
        await websocket.send_json({
            "event": "connected",
            "data": {"user_id": user_id, "status": "online"}
        })
        
        # Keep connection alive and handle incoming messages
        while True:
            # Wait for any client message (ping/pong, actions, etc.)
            data = await websocket.receive_text()
            
            # Handle ping
            if data == "ping":
                await websocket.send_text("pong")
            
            # Handle other commands if needed
            try:
                message = json.loads(data)
                
                if message.get("action") == "ping":
                    await websocket.send_json({"event": "pong"})
                
                # Future: handle client-initiated actions
                
            except json.JSONDecodeError:
                pass  # Not JSON, ignore
    
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)


# ===========================================
# Broadcast Functions (Called by CRUD layer)
# ===========================================

async def broadcast_task_created(user_id: int, task: TaskResponse):
    """
    Broadcast new task creation to user's dashboard.
    
    Args:
        user_id: Owner's user ID
        task: Created task response
    """
    await manager.send_personal_message(
        {
            "event": "task_created",
            "data": task.model_dump(mode="json")
        },
        user_id
    )


async def broadcast_task_updated(user_id: int, task: TaskResponse):
    """
    Broadcast task update to user's dashboard.
    
    Args:
        user_id: Owner's user ID
        task: Updated task response
    """
    await manager.send_personal_message(
        {
            "event": "task_updated",
            "data": task.model_dump(mode="json")
        },
        user_id
    )


async def broadcast_task_deleted(user_id: int, task_id: int):
    """
    Broadcast task deletion to user's dashboard.
    
    Args:
        user_id: Owner's user ID
        task_id: Deleted task ID
    """
    await manager.send_personal_message(
        {
            "event": "task_deleted",
            "data": {"task_id": task_id}
        },
        user_id
    )


async def broadcast_urgency_update(user_id: int, task_id: int, new_score: float):
    """
    Broadcast urgency score update for live sorting.
    
    Args:
        user_id: Owner's user ID
        task_id: Task ID
        new_score: New urgency score
    """
    await manager.send_personal_message(
        {
            "event": "score_updated",
            "data": {"task_id": task_id, "urgency_score": new_score}
        },
        user_id
    )
