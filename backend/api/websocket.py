"""
WebSocket endpoint for real-time updates
Broadcasts position updates, trades, and reasoning to connected clients
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List, Dict, Any
import json
import asyncio
from datetime import datetime

from backend.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


class ConnectionManager:
    """
    Manages WebSocket connections and broadcasts messages
    """

    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        """Accept and register a new WebSocket connection"""
        await websocket.accept()
        async with self._lock:
            self.active_connections.append(websocket)
        logger.info(f"New WebSocket connection. Total connections: {len(self.active_connections)}")

    async def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection"""
        async with self._lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def disconnect_all(self):
        """Close all active connections"""
        logger.info(f"Closing {len(self.active_connections)} WebSocket connections...")
        for connection in self.active_connections:
            try:
                await connection.close()
            except Exception as e:
                logger.error(f"Error closing connection: {e}")
        self.active_connections.clear()

    async def broadcast(self, message: Dict[str, Any]):
        """
        Broadcast a message to all connected clients

        Args:
            message: Dictionary to send as JSON
        """
        if not self.active_connections:
            return

        # Add timestamp if not present
        if "timestamp" not in message:
            message["timestamp"] = datetime.utcnow().isoformat()

        # Convert to JSON
        json_message = json.dumps(message)

        # Send to all connections
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(json_message)
            except WebSocketDisconnect:
                disconnected.append(connection)
            except Exception as e:
                logger.error(f"Error broadcasting to connection: {e}")
                disconnected.append(connection)

        # Remove disconnected clients
        if disconnected:
            async with self._lock:
                for connection in disconnected:
                    if connection in self.active_connections:
                        self.active_connections.remove(connection)

    async def broadcast_position_update(
        self,
        model_id: int,
        symbol: str,
        current_price: float,
        unrealized_pl: float
    ):
        """Broadcast position value update"""
        await self.broadcast({
            "type": "position_update",
            "model_id": model_id,
            "symbol": symbol,
            "current_price": current_price,
            "unrealized_pl": unrealized_pl
        })

    async def broadcast_trade(
        self,
        model_id: int,
        trade_id: int,
        symbol: str,
        side: str,
        quantity: int,
        price: float,
        fee: float
    ):
        """Broadcast trade execution"""
        await self.broadcast({
            "type": "trade",
            "model_id": model_id,
            "trade_id": trade_id,
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "price": price,
            "fee": fee
        })

    async def broadcast_reasoning(
        self,
        model_id: int,
        reasoning_id: int,
        decision: str,
        confidence: str
    ):
        """Broadcast model reasoning update"""
        await self.broadcast({
            "type": "reasoning",
            "model_id": model_id,
            "reasoning_id": reasoning_id,
            "decision": decision,
            "confidence": confidence
        })

    async def broadcast_portfolio_update(
        self,
        model_id: int,
        current_balance: float,
        total_value: float,
        total_pl: float
    ):
        """Broadcast portfolio value change"""
        await self.broadcast({
            "type": "portfolio_update",
            "model_id": model_id,
            "current_balance": current_balance,
            "total_value": total_value,
            "total_pl": total_pl
        })

    async def broadcast_scheduler_event(self, event: str, details: Dict[str, Any]):
        """Broadcast scheduler event"""
        await self.broadcast({
            "type": "scheduler_event",
            "event": event,
            "details": details
        })


# Global connection manager instance
connection_manager = ConnectionManager()


@router.websocket("/ws/live")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time updates

    Clients connect to this endpoint to receive:
    - Position value updates
    - Trade executions
    - Model reasoning updates
    - Portfolio value changes
    - Scheduler events
    """
    await connection_manager.connect(websocket)

    try:
        # Send welcome message
        await websocket.send_json({
            "type": "connected",
            "message": "Connected to Sentiment Arena live updates",
            "timestamp": datetime.utcnow().isoformat()
        })

        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Receive message from client (ping/pong or subscription management)
                data = await websocket.receive_text()

                # Parse message
                try:
                    message = json.loads(data)
                    message_type = message.get("type")

                    if message_type == "ping":
                        # Respond to ping
                        await websocket.send_json({
                            "type": "pong",
                            "timestamp": datetime.utcnow().isoformat()
                        })
                    elif message_type == "subscribe":
                        # Handle subscription (future enhancement)
                        await websocket.send_json({
                            "type": "subscribed",
                            "topics": message.get("topics", []),
                            "timestamp": datetime.utcnow().isoformat()
                        })
                    else:
                        logger.warning(f"Unknown message type: {message_type}")

                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON received: {data}")

            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Error handling message: {e}")
                break

    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await connection_manager.disconnect(websocket)
