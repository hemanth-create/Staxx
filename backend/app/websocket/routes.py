"""WebSocket endpoints."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from fastapi.security import HTTPBearer, HTTPAuthCredential
import logging

from backend.app.websocket.cost_feed import cost_feed_manager
from platform.auth.api_key_auth import validate_api_key

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["websocket"])


@router.websocket("/cost-feed")
async def websocket_cost_feed(
    websocket: WebSocket,
    api_key: str = Query(...),
):
    """
    WebSocket endpoint for live cost feed.

    Client must provide `api_key` query parameter.
    Receives real-time cost updates and alerts.

    Message types:
    - cost_update: New LLM call processed
    - alert: System alert (quality drift, cost spike, etc.)
    - recommendation: New model swap recommendation
    """
    # Validate API key
    try:
        org_id = await validate_api_key(api_key)
        if not org_id:
            await websocket.close(code=4001, reason="Invalid API key")
            return
    except Exception as e:
        logger.warning(f"WebSocket auth failed: {e}")
        await websocket.close(code=4001, reason="Unauthorized")
        return

    # Connect client
    await cost_feed_manager.connect(str(org_id), websocket)

    try:
        # Keep connection alive - listen for any client messages
        while True:
            # Receive message from client (for future use: heartbeat, commands)
            data = await websocket.receive_text()

            # Echo message type for debugging
            logger.debug(f"Received from {org_id}: {data}")

    except WebSocketDisconnect:
        await cost_feed_manager.disconnect(str(org_id), websocket)
        logger.info(f"WebSocket disconnected: {org_id}")

    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await cost_feed_manager.disconnect(str(org_id), websocket)
