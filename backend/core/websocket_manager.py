import asyncio
import json
import logging
import uuid
from typing import Dict, Optional, List, Any
from dataclasses import dataclass, field
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect

from .event_bus import EventBus

logger = logging.getLogger(__name__)


@dataclass
class WebSocketConnection:
    """Represents a WebSocket connection"""
    websocket: WebSocket
    client_id: str
    connected_at: datetime = field(default_factory=datetime.utcnow)
    last_ping: Optional[datetime] = None
    subscriptions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class WebSocketManager:
    """
    Manages WebSocket connections and integrates with the event bus
    """

    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.connections: Dict[str, WebSocketConnection] = {}
        self.heartbeat_task: Optional[asyncio.Task] = None
        self.heartbeat_interval = 30  # seconds

        # Register event handlers
        self._register_handlers()

    def _register_handlers(self):
        """Register event handlers for WebSocket functionality"""

        @self.event_bus.on("websocket.send")
        async def handle_websocket_send(data: Dict[str, Any]):
            """Send message to specific client"""
            client_id = data.get("client_id")
            message = data.get("message")

            if client_id and message:
                await self.send_to_client(client_id, message)

        @self.event_bus.on("websocket.broadcast")
        async def handle_websocket_broadcast(data: Dict[str, Any]):
            """Broadcast message to all or filtered clients"""
            message = data.get("message")
            filter_func = data.get("filter")  # Optional filtering function

            if message:
                await self.broadcast(message, filter_func)

        @self.event_bus.on("websocket.subscribe")
        async def handle_websocket_subscribe(data: Dict[str, Any]):
            """Subscribe client to event types"""
            client_id = data.get("client_id")
            event_types = data.get("event_types", [])

            if client_id and event_types:
                await self.subscribe_client(client_id, event_types)

        @self.event_bus.on("websocket.unsubscribe")
        async def handle_websocket_unsubscribe(data: Dict[str, Any]):
            """Unsubscribe client from event types"""
            client_id = data.get("client_id")
            event_types = data.get("event_types", [])

            if client_id:
                await self.unsubscribe_client(client_id, event_types)

    async def connect(self, websocket: WebSocket) -> str:
        """
        Accept a new WebSocket connection

        Returns:
            Client ID for the connection
        """
        await websocket.accept()

        client_id = str(uuid.uuid4())
        connection = WebSocketConnection(
            websocket=websocket,
            client_id=client_id
        )

        self.connections[client_id] = connection

        # Send welcome message
        await self.send_to_client(client_id, {
            "type": "connection.welcome",
            "payload": {
                "client_id": client_id,
                "server_time": datetime.utcnow().isoformat()
            }
        })

        # Start heartbeat if this is the first connection
        if len(self.connections) == 1:
            await self._start_heartbeat()

        # Emit connection event
        await self.event_bus.emit("websocket.connected", {
            "client_id": client_id,
            "total_connections": len(self.connections)
        })

        logger.info(f"WebSocket client {client_id} connected ({len(self.connections)} total)")
        return client_id

    async def disconnect(self, client_id: str):
        """Disconnect a WebSocket client"""
        if client_id in self.connections:
            connection = self.connections[client_id]

            try:
                await connection.websocket.close()
            except:
                pass  # Connection might already be closed

            del self.connections[client_id]

            # Stop heartbeat if no connections
            if not self.connections:
                await self._stop_heartbeat()

            # Emit disconnection event
            await self.event_bus.emit("websocket.disconnected", {
                "client_id": client_id,
                "total_connections": len(self.connections)
            })

            logger.info(f"WebSocket client {client_id} disconnected ({len(self.connections)} total)")

    async def send_to_client(self, client_id: str, message: Dict[str, Any]) -> bool:
        """
        Send message to a specific client

        Returns:
            True if message was sent successfully
        """
        if client_id not in self.connections:
            logger.warning(f"Attempted to send message to non-existent client {client_id}")
            return False

        connection = self.connections[client_id]

        try:
            await connection.websocket.send_text(json.dumps(message))
            return True
        except WebSocketDisconnect:
            logger.info(f"Client {client_id} disconnected during send")
            await self.disconnect(client_id)
            return False
        except Exception as e:
            logger.error(f"Error sending message to client {client_id}: {e}")
            await self.disconnect(client_id)
            return False

    async def broadcast(self, message: Dict[str, Any], filter_func: Optional[callable] = None) -> int:
        """
        Broadcast message to all connected clients

        Args:
            message: Message to broadcast
            filter_func: Optional function to filter clients (receives connection as argument)

        Returns:
            Number of clients that received the message
        """
        if not self.connections:
            return 0

        clients_to_send = []

        for client_id, connection in self.connections.items():
            if filter_func is None or filter_func(connection):
                clients_to_send.append(client_id)

        # Send to all filtered clients concurrently
        tasks = [self.send_to_client(client_id, message) for client_id in clients_to_send]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        successful_sends = sum(1 for result in results if result is True)

        logger.debug(f"Broadcast message to {successful_sends}/{len(clients_to_send)} clients")
        return successful_sends

    async def subscribe_client(self, client_id: str, event_types: List[str]):
        """Subscribe a client to specific event types"""
        if client_id not in self.connections:
            return

        connection = self.connections[client_id]

        for event_type in event_types:
            if event_type not in connection.subscriptions:
                connection.subscriptions.append(event_type)

                # Register a handler for this event type that sends to this client
                @self.event_bus.on(event_type)
                async def handle_subscribed_event(data: Dict[str, Any], client=client_id, event=event_type):
                    await self.send_to_client(client, {
                        "type": "event",
                        "payload": {
                            "event_type": event,
                            "data": data
                        }
                    })

        logger.debug(f"Client {client_id} subscribed to {event_types}")

    async def unsubscribe_client(self, client_id: str, event_types: List[str] = None):
        """Unsubscribe a client from event types"""
        if client_id not in self.connections:
            return

        connection = self.connections[client_id]

        if event_types is None:
            # Unsubscribe from all
            connection.subscriptions.clear()
        else:
            # Unsubscribe from specific event types
            for event_type in event_types:
                if event_type in connection.subscriptions:
                    connection.subscriptions.remove(event_type)

        logger.debug(f"Client {client_id} unsubscribed from {event_types or 'all events'}")

    async def _start_heartbeat(self):
        """Start heartbeat task"""
        if self.heartbeat_task is None:
            self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    async def _stop_heartbeat(self):
        """Stop heartbeat task"""
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass
            self.heartbeat_task = None

    async def _heartbeat_loop(self):
        """Heartbeat loop to keep connections alive"""
        try:
            while True:
                await asyncio.sleep(self.heartbeat_interval)

                if not self.connections:
                    break

                # Send ping to all clients
                ping_message = {
                    "type": "ping",
                    "payload": {
                        "timestamp": datetime.utcnow().isoformat()
                    }
                }

                await self.broadcast(ping_message)

        except asyncio.CancelledError:
            logger.info("Heartbeat loop cancelled")

    async def get_connection_info(self, client_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a connection"""
        if client_id not in self.connections:
            return None

        connection = self.connections[client_id]
        return {
            "client_id": client_id,
            "connected_at": connection.connected_at.isoformat(),
            "last_ping": connection.last_ping.isoformat() if connection.last_ping else None,
            "subscriptions": connection.subscriptions.copy(),
            "metadata": connection.metadata.copy()
        }

    async def update_client_metadata(self, client_id: str, metadata: Dict[str, Any]):
        """Update metadata for a client"""
        if client_id in self.connections:
            self.connections[client_id].metadata.update(metadata)

    @property
    def connection_count(self) -> int:
        """Get current connection count"""
        return len(self.connections)

    async def get_stats(self) -> Dict[str, Any]:
        """Get WebSocket manager statistics"""
        return {
            "total_connections": len(self.connections),
            "connections": [
                {
                    "client_id": conn.client_id,
                    "connected_at": conn.connected_at.isoformat(),
                    "subscriptions": len(conn.subscriptions),
                    "metadata": conn.metadata
                }
                for conn in self.connections.values()
            ],
            "heartbeat_active": self.heartbeat_task is not None
        }
