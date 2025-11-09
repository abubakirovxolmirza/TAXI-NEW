"""
WebSocket Connection Manager with Redis PubSub for Real-time Communication
Handles driver and user connections with multi-server support
"""
from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List, Set, Optional
import json
import asyncio
from datetime import datetime, timezone
from decimal import Decimal
import redis.asyncio as redis
from app.config import settings


class ConnectionManager:
    """Manages WebSocket connections with Redis PubSub for scalability"""
    
    def __init__(self):
        # Active driver connections: {driver_id: [websocket1, websocket2, ...]}
        self.driver_connections: Dict[int, List[WebSocket]] = {}
        
        # Active user connections: {user_id: [websocket1, websocket2, ...]}
        self.user_connections: Dict[int, List[WebSocket]] = {}
        
        # Track which driver is viewing which order to prevent double acceptance
        self.order_viewers: Dict[int, Set[int]] = {}  # {order_id: {driver_id1, driver_id2, ...}}
        
        # Track order locks when driver clicks accept (temporary 5 second lock)
        self.order_locks: Dict[int, tuple] = {}  # {order_id: (driver_id, timestamp)}
        
        # Redis connection pool
        self.redis_pool: Optional[redis.Redis] = None
        self.pubsub: Optional[redis.client.PubSub] = None
        self._redis_listener_task: Optional[asyncio.Task] = None
    
    async def init_redis(self):
        """Initialize Redis connection pool"""
        try:
            self.redis_pool = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                max_connections=10
            )
            # Test connection
            await self.redis_pool.ping()
            print("✅ Redis connected successfully")
            
            # Start Redis PubSub listener
            self._redis_listener_task = asyncio.create_task(self._redis_listener())
        except Exception as e:
            print(f"⚠️ Redis connection failed: {e}. Running in standalone mode.")
            self.redis_pool = None
    
    async def _redis_listener(self):
        """Listen to Redis PubSub channels and broadcast to local WebSocket connections"""
        if not self.redis_pool:
            return
        
        try:
            self.pubsub = self.redis_pool.pubsub()
            await self.pubsub.subscribe(
                "drivers_channel",  # All drivers
                "users_channel"      # All users
            )
            
            print("✅ Redis PubSub listener started")
            
            async for message in self.pubsub.listen():
                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        channel = message["channel"]
                        
                        if channel == "drivers_channel":
                            # Broadcast to all local driver connections
                            await self._broadcast_local_drivers(data)
                        elif channel == "users_channel":
                            # Check if message is for specific user or all users
                            if "user_id" in data:
                                await self._send_local_user(data["user_id"], data["message"])
                            else:
                                await self._broadcast_local_users(data)
                    except Exception as e:
                        print(f"Error processing Redis message: {e}")
        except Exception as e:
            print(f"Redis listener error: {e}")
    
    async def _broadcast_local_drivers(self, message: dict):
        """Broadcast to local driver connections only"""
        for driver_id in list(self.driver_connections.keys()):
            await self._send_to_local_driver(driver_id, message)
    
    async def _broadcast_local_users(self, message: dict):
        """Broadcast to local user connections only"""
        for user_id in list(self.user_connections.keys()):
            await self._send_to_local_user(user_id, message)
    
    async def _send_to_local_driver(self, driver_id: int, message: dict):
        """Send message to local driver connections"""
        if driver_id in self.driver_connections:
            disconnected = []
            for connection in self.driver_connections[driver_id]:
                try:
                    await connection.send_json(message)
                except:
                    disconnected.append(connection)
            
            for conn in disconnected:
                self.disconnect_driver(conn, driver_id)
    
    async def _send_to_local_user(self, user_id: int, message: dict):
        """Send message to local user connections"""
        if user_id in self.user_connections:
            disconnected = []
            for connection in self.user_connections[user_id]:
                try:
                    await connection.send_json(message)
                except:
                    disconnected.append(connection)
            
            for conn in disconnected:
                self.disconnect_user(conn, user_id)
    
    async def connect_driver(self, websocket: WebSocket, driver_id: int):
        """Connect a driver to WebSocket"""
        await websocket.accept()
        if driver_id not in self.driver_connections:
            self.driver_connections[driver_id] = []
        self.driver_connections[driver_id].append(websocket)
        print(f"✅ Driver {driver_id} connected. Total driver connections: {len(self.driver_connections)}")
        
        # Store in Redis for tracking across servers
        if self.redis_pool:
            try:
                await self.redis_pool.sadd("active_drivers", str(driver_id))
            except:
                pass
    
    async def connect_user(self, websocket: WebSocket, user_id: int):
        """Connect a user to WebSocket"""
        await websocket.accept()
        if user_id not in self.user_connections:
            self.user_connections[user_id] = []
        self.user_connections[user_id].append(websocket)
        print(f"✅ User {user_id} connected. Total user connections: {len(self.user_connections)}")
        
        # Store in Redis for tracking across servers
        if self.redis_pool:
            try:
                await self.redis_pool.sadd("active_users", str(user_id))
            except:
                pass
    
    def disconnect_driver(self, websocket: WebSocket, driver_id: int):
        """Disconnect a driver from WebSocket"""
        if driver_id in self.driver_connections:
            if websocket in self.driver_connections[driver_id]:
                self.driver_connections[driver_id].remove(websocket)
            if not self.driver_connections[driver_id]:
                del self.driver_connections[driver_id]
                # Remove from Redis
                if self.redis_pool:
                    asyncio.create_task(self.redis_pool.srem("active_drivers", str(driver_id)))
        print(f"❌ Driver {driver_id} disconnected. Remaining drivers: {len(self.driver_connections)}")
    
    def disconnect_user(self, websocket: WebSocket, user_id: int):
        """Disconnect a user from WebSocket"""
        if user_id in self.user_connections:
            if websocket in self.user_connections[user_id]:
                self.user_connections[user_id].remove(websocket)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]
                # Remove from Redis
                if self.redis_pool:
                    asyncio.create_task(self.redis_pool.srem("active_users", str(user_id)))
        print(f"❌ User {user_id} disconnected. Remaining users: {len(self.user_connections)}")
    
    async def send_to_driver(self, driver_id: int, message: dict):
        """Send message to a specific driver (all their connections across all servers)"""
        if self.redis_pool:
            # Use Redis PubSub to reach driver on any server
            try:
                await self.redis_pool.publish(
                    "drivers_channel",
                    json.dumps({"driver_id": driver_id, "message": message})
                )
            except Exception as e:
                print(f"Redis publish error: {e}")
                # Fallback to local
                await self._send_to_local_driver(driver_id, message)
        else:
            # No Redis, send locally only
            await self._send_to_local_driver(driver_id, message)
    
    async def send_to_user(self, user_id: int, message: dict):
        """Send message to a specific user (all their connections across all servers)"""
        if self.redis_pool:
            # Use Redis PubSub to reach user on any server
            try:
                await self.redis_pool.publish(
                    "users_channel",
                    json.dumps({"user_id": user_id, "message": message})
                )
            except Exception as e:
                print(f"Redis publish error: {e}")
                # Fallback to local
                await self._send_to_local_user(user_id, message)
        else:
            # No Redis, send locally only
            await self._send_to_local_user(user_id, message)
    
    async def broadcast_to_all_drivers(self, message: dict):
        """Send message to all connected drivers across all servers"""
        if self.redis_pool:
            try:
                await self.redis_pool.publish("drivers_channel", json.dumps(message))
            except Exception as e:
                print(f"Redis broadcast error: {e}")
                await self._broadcast_local_drivers(message)
        else:
            await self._broadcast_local_drivers(message)
    
    async def broadcast_to_all_users(self, message: dict):
        """Send message to all connected users across all servers"""
        if self.redis_pool:
            try:
                await self.redis_pool.publish("users_channel", json.dumps(message))
            except Exception as e:
                print(f"Redis broadcast error: {e}")
                await self._broadcast_local_users(message)
        else:
            await self._broadcast_local_users(message)
    
    def add_order_viewer(self, order_id: int, driver_id: int):
        """Track that a driver is viewing an order"""
        if order_id not in self.order_viewers:
            self.order_viewers[order_id] = set()
        self.order_viewers[order_id].add(driver_id)
        
        # Store in Redis with expiration
        if self.redis_pool:
            asyncio.create_task(
                self.redis_pool.sadd(f"order_viewers:{order_id}", str(driver_id))
            )
            asyncio.create_task(
                self.redis_pool.expire(f"order_viewers:{order_id}", 300)  # 5 minutes
            )
    
    def remove_order_viewer(self, order_id: int, driver_id: int):
        """Remove driver from order viewers"""
        if order_id in self.order_viewers:
            self.order_viewers[order_id].discard(driver_id)
            if not self.order_viewers[order_id]:
                del self.order_viewers[order_id]
        
        if self.redis_pool:
            asyncio.create_task(
                self.redis_pool.srem(f"order_viewers:{order_id}", str(driver_id))
            )
    
    async def get_order_viewer_count(self, order_id: int) -> int:
        """Get number of drivers currently viewing an order (across all servers)"""
        if self.redis_pool:
            try:
                count = await self.redis_pool.scard(f"order_viewers:{order_id}")
                return count
            except:
                pass
        return len(self.order_viewers.get(order_id, set()))
    
    async def try_lock_order(self, order_id: int, driver_id: int) -> bool:
        """
        Try to lock an order for acceptance (5 second temporary lock)
        Uses Redis for distributed locking across servers
        Returns True if lock acquired, False if already locked by another driver
        """
        if self.redis_pool:
            try:
                # Try to set lock in Redis with 5 second expiration
                lock_key = f"order_lock:{order_id}"
                success = await self.redis_pool.set(
                    lock_key,
                    str(driver_id),
                    nx=True,  # Only set if not exists
                    ex=5      # Expire after 5 seconds
                )
                return bool(success)
            except Exception as e:
                print(f"Redis lock error: {e}")
                # Fallback to local locking
                pass
        
        # Local locking (for standalone mode)
        current_time = datetime.now(timezone.utc)
        if order_id in self.order_locks:
            locked_driver_id, lock_time = self.order_locks[order_id]
            if (current_time - lock_time).total_seconds() < 5:
                return locked_driver_id == driver_id
        
        self.order_locks[order_id] = (driver_id, current_time)
        return True
    
    async def release_order_lock(self, order_id: int):
        """Release order lock"""
        if self.redis_pool:
            try:
                await self.redis_pool.delete(f"order_lock:{order_id}")
            except:
                pass
        
        if order_id in self.order_locks:
            del self.order_locks[order_id]
    
    async def get_active_driver_count(self) -> int:
        """Get count of active drivers across all servers"""
        if self.redis_pool:
            try:
                count = await self.redis_pool.scard("active_drivers")
                return count
            except:
                pass
        return len(self.driver_connections)
    
    async def get_active_user_count(self) -> int:
        """Get count of active users across all servers"""
        if self.redis_pool:
            try:
                count = await self.redis_pool.scard("active_users")
                return count
            except:
                pass
        return len(self.user_connections)
    
    async def cleanup(self):
        """Cleanup Redis connections on shutdown"""
        if self._redis_listener_task:
            self._redis_listener_task.cancel()
        if self.pubsub:
            await self.pubsub.unsubscribe()
            await self.pubsub.close()
        if self.redis_pool:
            await self.redis_pool.close()


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
