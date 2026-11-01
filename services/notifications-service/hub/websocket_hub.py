"""
services/notifications-service/hub/websocket_hub.py
---------------------------------------------------
Gestor de conexiones WebSocket concurrentes para notificaciones en tiempo real (Push / SSE).
"""

from typing import List, Dict, Any
from fastapi import WebSocket
import logging
import json

logger = logging.getLogger("websocket_hub")

class WebSocketHub:
    def __init__(self):
        # Mapeo de client_id o role a lista de conexiones activas
        self.active_connections: List[WebSocket] = []
        self.user_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: str = "anonymous"):
        await websocket.accept()
        self.active_connections.append(websocket)
        if user_id not in self.user_connections:
            self.user_connections[user_id] = []
        self.user_connections[user_id].append(websocket)
        logger.info(f"Cliente {user_id} conectado a WebSocket. Conexiones activas: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket, user_id: str = "anonymous"):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if user_id in self.user_connections and websocket in self.user_connections[user_id]:
            self.user_connections[user_id].remove(websocket)
        logger.info(f"Cliente {user_id} desconectado de WebSocket.")

    async def broadcast(self, message: Dict[str, Any]):
        """Envía notificación a todos los usuarios conectados."""
        data_text = json.dumps(message)
        for connection in list(self.active_connections):
            try:
                await connection.send_text(data_text)
            except Exception as e:
                logger.warning(f"Error enviando broadcast WS: {e}")
                if connection in self.active_connections:
                    self.active_connections.remove(connection)

    async def send_to_user(self, user_id: str, message: Dict[str, Any]):
        """Envía notificación dirigida a un usuario específico."""
        if user_id in self.user_connections:
            data_text = json.dumps(message)
            for connection in list(self.user_connections[user_id]):
                try:
                    await connection.send_text(data_text)
                except Exception as e:
                    logger.warning(f"Error enviando WS a usuario {user_id}: {e}")

ws_hub = WebSocketHub()
