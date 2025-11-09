"""
WebSocket Router for Real-time Communication
Handles WebSocket connections and real-time events
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.websocket import manager, convert_decimal_to_float
from app.models import User, Driver
from app.auth import get_user_from_token
import json

router = APIRouter(prefix="/ws", tags=["WebSocket"])


@router.websocket("/driver/{token}")
async def websocket_driver_endpoint(
    websocket: WebSocket,
    token: str
):
    """
    WebSocket endpoint for drivers
    
    Connection: ws://your-domain.com/ws/driver/{access_token}
    
    Events received from driver:
    - {"type": "ping"} - Keep alive
    - {"type": "viewing_order", "order_id": 123, "order_type": "taxi"} - Driver viewing order
    - {"type": "stop_viewing_order", "order_id": 123} - Driver stopped viewing
    - {"type": "request_lock", "order_id": 123} - Driver requesting to accept order
    
    Events sent to driver:
    - {"type": "new_order", "order": {...}} - New order available
    - {"type": "order_accepted", "order_id": 123, "driver_id": 456} - Order accepted by someone
    - {"type": "order_cancelled", "order_id": 123} - Order cancelled
    - {"type": "order_completed", "order_id": 123} - Order completed
    - {"type": "viewer_count", "order_id": 123, "count": 5} - Number of drivers viewing order
    - {"type": "lock_acquired", "order_id": 123} - Lock acquired, can accept
    - {"type": "lock_failed", "order_id": 123} - Lock failed, someone else accepting
    """
    # Verify driver token
    try:
        user = get_user_from_token(token)
        if not user or not user.driver_profile:
            await websocket.close(code=1008, reason="Invalid driver token")
            return
        
        driver_id = user.driver_profile.id
        await manager.connect_driver(websocket, driver_id)
        
        # Send connection confirmation
        await websocket.send_json({
            "type": "connected",
            "driver_id": driver_id,
            "message": "WebSocket connected successfully"
        })
        
        try:
            while True:
                # Receive messages from driver
                data = await websocket.receive_json()
                message_type = data.get("type")
                
                if message_type == "ping":
                    await websocket.send_json({"type": "pong"})
                
                elif message_type == "viewing_order":
                    order_id = data.get("order_id")
                    if order_id:
                        manager.add_order_viewer(order_id, driver_id)
                        # Notify all viewers about viewer count
                        viewer_count = manager.get_order_viewer_count(order_id)
                        await manager.broadcast_to_all_drivers({
                            "type": "viewer_count",
                            "order_id": order_id,
                            "count": viewer_count
                        })
                
                elif message_type == "stop_viewing_order":
                    order_id = data.get("order_id")
                    if order_id:
                        manager.remove_order_viewer(order_id, driver_id)
                        viewer_count = manager.get_order_viewer_count(order_id)
                        await manager.broadcast_to_all_drivers({
                            "type": "viewer_count",
                            "order_id": order_id,
                            "count": viewer_count
                        })
                
                elif message_type == "request_lock":
                    order_id = data.get("order_id")
                    if order_id:
                        # Try to acquire lock
                        if manager.try_lock_order(order_id, driver_id):
                            await websocket.send_json({
                                "type": "lock_acquired",
                                "order_id": order_id,
                                "message": "You can now accept this order"
                            })
                        else:
                            await websocket.send_json({
                                "type": "lock_failed",
                                "order_id": order_id,
                                "message": "Another driver is accepting this order"
                            })
        
        except WebSocketDisconnect:
            manager.disconnect_driver(websocket, driver_id)
    
    except Exception as e:
        print(f"WebSocket error: {e}")
        try:
            await websocket.close(code=1011, reason=str(e))
        except:
            pass


@router.websocket("/user/{token}")
async def websocket_user_endpoint(
    websocket: WebSocket,
    token: str
):
    """
    WebSocket endpoint for users/customers
    
    Connection: ws://your-domain.com/ws/user/{access_token}
    
    Events sent to user:
    - {"type": "order_accepted", "order_id": 123, "driver": {...}} - Order accepted by driver
    - {"type": "order_completed", "order_id": 123} - Order completed
    - {"type": "driver_location", "order_id": 123, "lat": 41.123, "lng": 69.456} - Driver location update
    """
    # Verify user token
    try:
        user = get_user_from_token(token)
        if not user:
            await websocket.close(code=1008, reason="Invalid user token")
            return
        
        user_id = user.id
        await manager.connect_user(websocket, user_id)
        
        # Send connection confirmation
        await websocket.send_json({
            "type": "connected",
            "user_id": user_id,
            "message": "WebSocket connected successfully"
        })
        
        try:
            while True:
                # Receive messages from user (mostly ping to keep alive)
                data = await websocket.receive_json()
                message_type = data.get("type")
                
                if message_type == "ping":
                    await websocket.send_json({"type": "pong"})
        
        except WebSocketDisconnect:
            manager.disconnect_user(websocket, user_id)
    
    except Exception as e:
        print(f"WebSocket error: {e}")
        try:
            await websocket.close(code=1011, reason=str(e))
        except:
            pass


@router.get("/stats")
async def get_websocket_stats():
    """Get WebSocket connection statistics"""
    return {
        "active_drivers": manager.get_active_driver_count(),
        "active_users": manager.get_active_user_count(),
        "total_connections": manager.get_active_driver_count() + manager.get_active_user_count()
    }
