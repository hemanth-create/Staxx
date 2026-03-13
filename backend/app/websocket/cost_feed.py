"""WebSocket handler for live cost feed updates."""

import json
import logging
from datetime import datetime
from typing import Set
from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class CostFeedManager:
    """Manages WebSocket connections for live cost feeds."""

    def __init__(self):
        """Initialize connection manager."""
        self.active_connections: dict[str, Set[WebSocket]] = {}

    async def connect(self, org_id: str, websocket: WebSocket):
        """Accept a new WebSocket connection for an org."""
        await websocket.accept()
        if org_id not in self.active_connections:
            self.active_connections[org_id] = set()
        self.active_connections[org_id].add(websocket)
        logger.info(f"WebSocket connected for org {org_id}")

    async def disconnect(self, org_id: str, websocket: WebSocket):
        """Remove a WebSocket connection."""
        if org_id in self.active_connections:
            self.active_connections[org_id].discard(websocket)
            if not self.active_connections[org_id]:
                del self.active_connections[org_id]
        logger.info(f"WebSocket disconnected for org {org_id}")

    async def broadcast_cost_update(
        self,
        org_id: str,
        model: str,
        task_type: str,
        cost_usd: float,
        input_tokens: int,
        output_tokens: int,
        latency_ms: float,
    ):
        """Broadcast a cost update to all connected clients for an org."""
        if org_id not in self.active_connections:
            return

        message = {
            "type": "cost_update",
            "timestamp": datetime.utcnow().isoformat(),
            "model": model,
            "task_type": task_type,
            "cost_usd": cost_usd,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "latency_ms": latency_ms,
        }

        disconnected = set()
        for websocket in self.active_connections[org_id]:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send WebSocket message: {e}")
                disconnected.add(websocket)

        # Remove disconnected clients
        for ws in disconnected:
            await self.disconnect(org_id, ws)

    async def broadcast_alert(
        self,
        org_id: str,
        alert_type: str,
        severity: str,
        title: str,
        description: str,
    ):
        """Broadcast an alert to all connected clients for an org."""
        if org_id not in self.active_connections:
            return

        message = {
            "type": "alert",
            "timestamp": datetime.utcnow().isoformat(),
            "alert_type": alert_type,
            "severity": severity,
            "title": title,
            "description": description,
        }

        disconnected = set()
        for websocket in self.active_connections[org_id]:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send alert: {e}")
                disconnected.add(websocket)

        # Remove disconnected clients
        for ws in disconnected:
            await self.disconnect(org_id, ws)

    async def broadcast_recommendation_update(
        self,
        org_id: str,
        task_type: str,
        current_model: str,
        recommended_model: str,
        monthly_savings: float,
        confidence: float,
    ):
        """Broadcast a new recommendation to all connected clients."""
        if org_id not in self.active_connections:
            return

        message = {
            "type": "recommendation",
            "timestamp": datetime.utcnow().isoformat(),
            "task_type": task_type,
            "current_model": current_model,
            "recommended_model": recommended_model,
            "monthly_savings": monthly_savings,
            "confidence": confidence,
        }

        disconnected = set()
        for websocket in self.active_connections[org_id]:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send recommendation: {e}")
                disconnected.add(websocket)

        # Remove disconnected clients
        for ws in disconnected:
            await self.disconnect(org_id, ws)


# Global instance
cost_feed_manager = CostFeedManager()
