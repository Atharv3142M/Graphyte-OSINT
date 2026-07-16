"""WebSocket routes for real-time updates."""
import json
from typing import Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.logging_config import logger

router = APIRouter()

# Active WebSocket connections
active_connections: Set[WebSocket] = set()


@router.websocket("/ws/investigations/{investigation_id}")
async def websocket_investigation_updates(websocket: WebSocket, investigation_id: str):
    """WebSocket endpoint for investigation real-time updates."""
    await websocket.accept()
    active_connections.add(websocket)
    logger.info(f"WebSocket connected for investigation: {investigation_id}")
    
    try:
        while True:
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                logger.debug(f"WebSocket message from {investigation_id}: {message}")
                
                # Echo back for now (TODO: implement actual message handling)
                await websocket.send_text(json.dumps({
                    "type": "ack",
                    "message_id": message.get("id"),
                }))
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "detail": "Invalid JSON",
                }))
    
    except WebSocketDisconnect:
        active_connections.discard(websocket)
        logger.info(f"WebSocket disconnected for investigation: {investigation_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        active_connections.discard(websocket)


@router.websocket("/ws/playbook/{playbook_id}")
async def websocket_playbook_stream(websocket: WebSocket, playbook_id: str):
    """WebSocket endpoint for playbook execution streaming."""
    await websocket.accept()
    active_connections.add(websocket)
    logger.info(f"WebSocket connected for playbook: {playbook_id}")
    
    try:
        while True:
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                
                # Handle different message types
                if message.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
                elif message.get("type") == "subscribe":
                    await websocket.send_text(json.dumps({
                        "type": "subscribed",
                        "playbook_id": playbook_id,
                    }))
            except json.JSONDecodeError:
                pass
    
    except WebSocketDisconnect:
        active_connections.discard(websocket)
        logger.info(f"WebSocket disconnected for playbook: {playbook_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        active_connections.discard(websocket)


async def broadcast_update(message: dict):
    """Broadcast update to all active WebSocket connections."""
    disconnected = set()
    
    for connection in active_connections:
        try:
            await connection.send_text(json.dumps(message))
        except Exception as e:
            logger.error(f"Failed to send WebSocket message: {e}")
            disconnected.add(connection)
    
    # Clean up disconnected connections
    for connection in disconnected:
        active_connections.discard(connection)
