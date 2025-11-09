"""
WebSocket Connection Manager for Real-time Communication
Handles driver and user connections for live order updates
"""
from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List, Set
import json
from datetime import datetime
from decimal import Decimal


class ConnectionManager:
    """Manages WebSocket connections for drivers and users"""
    
    def __init__(self):
        # Active driver connections: {driver_id: [websocket1, websocket2, ...]}
        self.driver_connections: Dict[int, List[WebSocket]] = {}
        
        # Active user connections: {user_id: [websocket1, websocket2, ...]}
        self.user_connections: Dict[int, List[WebSocket]] = {}
        
        # Track which driver is viewing which order to prevent double acceptance
        self.order_viewers: Dict[int, Set[int]] = {}  # {order_id: {driver_id1, driver_id2, ...}}
        
        # Track order locks when driver clicks accept (temporary 5 second lock)
        self.order_locks: Dict[int, tuple] = {}  # {order_id: (driver_id, timestamp)}
    
    async def connect_driver(self, websocket: WebSocket, driver_id: int):
        """Connect a driver to WebSocket"""
        await websocket.accept()
        if driver_id not in self.driver_connections:
            self.driver_connections[driver_id] = []
        self.driver_connections[driver_id].append(websocket)
        print(f"✅ Driver {driver_id} connected. Total driver connections: {len(self.driver_connections)}")
    
    async def connect_user(self, websocket: WebSocket, user_id: int):
        """Connect a user to WebSocket"""
        await websocket.accept()
        if user_id not in self.user_connections:
            self.user_connections[user_id] = []
        self.user_connections[user_id].append(websocket)
        print(f"✅ User {user_id} connected. Total user connections: {len(self.user_connections)}")
    
    def disconnect_driver(self, websocket: WebSocket, driver_id: int):
        """Disconnect a driver from WebSocket"""
        if driver_id in self.driver_connections:
            if websocket in self.driver_connections[driver_id]:
                self.driver_connections[driver_id].remove(websocket)
            if not self.driver_connections[driver_id]:
                del self.driver_connections[driver_id]
        print(f"❌ Driver {driver_id} disconnected. Remaining drivers: {len(self.driver_connections)}")
    
    def disconnect_user(self, websocket: WebSocket, user_id: int):
        """Disconnect a user from WebSocket"""
        if user_id in self.user_connections:
            if websocket in self.user_connections[user_id]:
                self.user_connections[user_id].remove(websocket)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]
        print(f"❌ User {user_id} disconnected. Remaining users: {len(self.user_connections)}")
    
    async def send_to_driver(self, driver_id: int, message: dict):
        """Send message to a specific driver (all their connections)"""
        if driver_id in self.driver_connections:
            disconnected = []
            for connection in self.driver_connections[driver_id]:
                try:
                    await connection.send_json(message)
                except:
                    disconnected.append(connection)
            
            # Remove disconnected connections
            for conn in disconnected:
                self.disconnect_driver(conn, driver_id)
    
    async def send_to_user(self, user_id: int, message: dict):
        """Send message to a specific user (all their connections)"""
        if user_id in self.user_connections:
            disconnected = []
            for connection in self.user_connections[user_id]:
                try:
                    await connection.send_json(message)
                except:
                    disconnected.append(connection)
            
            # Remove disconnected connections
            for conn in disconnected:
                self.disconnect_user(conn, user_id)
    
    async def broadcast_to_all_drivers(self, message: dict):
        """Send message to all connected drivers"""
        for driver_id in list(self.driver_connections.keys()):
            await self.send_to_driver(driver_id, message)
    
    async def broadcast_to_all_users(self, message: dict):
        """Send message to all connected users"""
        for user_id in list(self.user_connections.keys()):
            await self.send_to_user(user_id, message)
    
    def add_order_viewer(self, order_id: int, driver_id: int):
        """Track that a driver is viewing an order"""
        if order_id not in self.order_viewers:
            self.order_viewers[order_id] = set()
        self.order_viewers[order_id].add(driver_id)
    
    def remove_order_viewer(self, order_id: int, driver_id: int):
        """Remove driver from order viewers"""
        if order_id in self.order_viewers:
            self.order_viewers[order_id].discard(driver_id)
            if not self.order_viewers[order_id]:
                del self.order_viewers[order_id]
    
    def get_order_viewer_count(self, order_id: int) -> int:
        """Get number of drivers currently viewing an order"""
        return len(self.order_viewers.get(order_id, set()))
    
    def try_lock_order(self, order_id: int, driver_id: int) -> bool:
        """
        Try to lock an order for acceptance (5 second temporary lock)
        Returns True if lock acquired, False if already locked by another driver
        """
        current_time = datetime.utcnow()
        
        if order_id in self.order_locks:
            locked_driver_id, lock_time = self.order_locks[order_id]
            # Check if lock expired (5 seconds)
            if (current_time - lock_time).total_seconds() < 5:
                return locked_driver_id == driver_id  # Only original driver can proceed
        
        # Acquire lock
        self.order_locks[order_id] = (driver_id, current_time)
        return True
    
    def release_order_lock(self, order_id: int):
        """Release order lock"""
        if order_id in self.order_locks:
            del self.order_locks[order_id]
    
    def get_active_driver_count(self) -> int:
        """Get count of active drivers"""
        return len(self.driver_connections)
    
    def get_active_user_count(self) -> int:
        """Get count of active users"""
        return len(self.user_connections)


# Global connection manager instance
manager = ConnectionManager()


def convert_decimal_to_float(obj):
    """Convert Decimal objects to float for JSON serialization"""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {key: convert_decimal_to_float(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_decimal_to_float(item) for item in obj]
    return obj
