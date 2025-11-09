# WebSocket Integration Guide

## Overview

The Taxi Service API now includes WebSocket support for real-time communication between drivers, users, and the server. This enables instant notifications, prevents double-booking of orders, and provides live updates on order status.

## Features

✅ **Real-time Order Notifications** - Drivers instantly receive new order alerts  
✅ **Duplicate Prevention** - Locking mechanism prevents multiple drivers from accepting the same order  
✅ **Live Order Updates** - Users get instant notifications when orders are accepted/completed  
✅ **Viewer Tracking** - See how many drivers are currently viewing an order  
✅ **Automatic Reconnection** - Handles connection drops gracefully  

---

## WebSocket Endpoints

### 1. Driver WebSocket Connection

**Endpoint:** `ws://your-domain.com/ws/driver/{access_token}`

Replace `{access_token}` with the driver's JWT token.

#### Connection Example (JavaScript):
```javascript
const token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...";
const ws = new WebSocket(`ws://164.90.229.192/ws/driver/${token}`);

ws.onopen = () => {
    console.log("✅ Connected to driver WebSocket");
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log("📨 Received:", data);
    
    switch(data.type) {
        case "connected":
            console.log(`Driver ${data.driver_id} connected`);
            break;
        case "new_order":
            // New order available
            showNewOrderNotification(data.order);
            break;
        case "order_accepted":
            // Order was accepted by another driver
            removeOrderFromList(data.order_id);
            break;
        case "viewer_count":
            // Update viewer count for an order
            updateViewerCount(data.order_id, data.count);
            break;
        case "lock_acquired":
            // You can now accept the order
            proceedWithAcceptance(data.order_id);
            break;
        case "lock_failed":
            // Another driver is accepting
            showMessage("Another driver is accepting this order");
            break;
    }
};

ws.onerror = (error) => {
    console.error("❌ WebSocket error:", error);
};

ws.onclose = () => {
    console.log("🔌 Disconnected");
    // Implement reconnection logic
    setTimeout(() => connectWebSocket(), 3000);
};
```

#### Events Driver Can Send:
```javascript
// 1. Keep-alive ping
ws.send(JSON.stringify({ type: "ping" }));

// 2. Notify when viewing an order
ws.send(JSON.stringify({
    type: "viewing_order",
    order_id: 123,
    order_type: "taxi"
}));

// 3. Stop viewing an order
ws.send(JSON.stringify({
    type: "stop_viewing_order",
    order_id: 123
}));

// 4. Request lock to accept order
ws.send(JSON.stringify({
    type: "request_lock",
    order_id: 123
}));
```

#### Events Driver Receives:

| Event Type | Description | Data |
|------------|-------------|------|
| `connected` | Connection confirmed | `{type, driver_id, message}` |
| `new_order` | New order available | `{type, order: {...}}` |
| `order_accepted` | Order accepted by someone | `{type, order_id, driver_id}` |
| `order_cancelled` | Order cancelled | `{type, order_id}` |
| `viewer_count` | Number of drivers viewing | `{type, order_id, count}` |
| `lock_acquired` | Can accept order | `{type, order_id, message}` |
| `lock_failed` | Someone else accepting | `{type, order_id, message}` |
| `pong` | Response to ping | `{type: "pong"}` |

---

### 2. User/Customer WebSocket Connection

**Endpoint:** `ws://your-domain.com/ws/user/{access_token}`

#### Connection Example:
```javascript
const token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...";
const ws = new WebSocket(`ws://164.90.229.192/ws/user/${token}`);

ws.onopen = () => {
    console.log("✅ Connected to user WebSocket");
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    switch(data.type) {
        case "connected":
            console.log(`User ${data.user_id} connected`);
            break;
        case "order_accepted":
            // Driver accepted your order
            showDriverInfo(data.driver);
            updateOrderStatus(data.order_id, "accepted");
            break;
        case "order_completed":
            // Order completed
            showRatingPrompt(data.order_id);
            break;
        case "driver_location":
            // Driver location update
            updateMapMarker(data.lat, data.lng);
            break;
    }
};
```

#### Events User Receives:

| Event Type | Description | Data |
|------------|-------------|------|
| `connected` | Connection confirmed | `{type, user_id, message}` |
| `order_accepted` | Driver accepted order | `{type, order_id, driver: {...}}` |
| `order_completed` | Order completed | `{type, order_id}` |
| `driver_location` | Driver's current location | `{type, order_id, lat, lng}` |

---

## Integration Flow

### Order Acceptance Flow (Prevents Double Booking)

```
1. User creates order → Broadcast to all drivers via WebSocket
2. Multiple drivers see the order
3. Driver A clicks "View Details"
   └─> Send: {type: "viewing_order", order_id: 123}
   └─> Receive: {type: "viewer_count", order_id: 123, count: 3}
4. Driver A clicks "Accept Order"
   └─> Send: {type: "request_lock", order_id: 123}
   └─> Receive: {type: "lock_acquired", order_id: 123}
5. Driver A calls HTTP API: POST /api/driver/orders/accept/taxi/123
6. Server broadcasts to all drivers:
   └─> {type: "order_accepted", order_id: 123, driver_id: A}
7. Other drivers automatically remove order from their list
8. User receives notification:
   └─> {type: "order_accepted", order_id: 123, driver: {...}}
```

### Lock Mechanism (5-second window)

- When driver clicks "Accept", they get a 5-second lock
- If another driver tries within 5 seconds, they get `lock_failed`
- Lock is released after order is accepted or 5 seconds expire
- This prevents race conditions and double-booking

---

## HTTP API Integration

WebSockets complement the existing HTTP API:

### Create Order (HTTP + WebSocket)
```javascript
// 1. HTTP POST to create order
const response = await fetch('/api/taxi-orders/', {
    method: 'POST',
    headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
    },
    body: JSON.stringify(orderData)
});

// 2. Server automatically broadcasts via WebSocket to all drivers
// 3. Server stores notification in database as backup
```

### Accept Order (HTTP + WebSocket)
```javascript
// 1. Request WebSocket lock first
ws.send(JSON.stringify({
    type: "request_lock",
    order_id: 123
}));

// 2. Wait for lock_acquired event
ws.onmessage = async (event) => {
    const data = JSON.parse(event.data);
    if (data.type === "lock_acquired") {
        // 3. Now call HTTP API to accept
        const response = await fetch('/api/driver/orders/accept/taxi/123', {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        
        // 4. Server broadcasts acceptance to all via WebSocket
    }
};
```

---

## Deployment Guide

### 1. Requirements

The WebSocket server is built into the FastAPI application. No additional services needed!

```bash
# Install FastAPI with WebSocket support (already in requirements.txt)
pip install fastapi[all]
pip install websockets
```

### 2. Running with Uvicorn (Development)

```bash
# Development mode with auto-reload
uvicorn main:app --host 0.0.0.0 --port 8000 --reload --ws-ping-interval 20 --ws-ping-timeout 20
```

### 3. Running with Gunicorn + Uvicorn Workers (Production)

**Option A: Using systemd service**

Edit `/etc/systemd/system/taxi-service.service`:

```ini
[Unit]
Description=Taxi Service API with WebSocket Support
After=network.target

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/var/www/taxi-service/TAXI-NEW
Environment="PATH=/var/www/taxi-service/TAXI-NEW/venv/bin"
ExecStart=/var/www/taxi-service/TAXI-NEW/venv/bin/gunicorn main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --timeout 120 \
    --keepalive 5 \
    --access-logfile /var/log/taxi-service/access.log \
    --error-logfile /var/log/taxi-service/error.log

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Important:** Use `uvicorn.workers.UvicornWorker` for WebSocket support!

```bash
sudo systemctl daemon-reload
sudo systemctl restart taxi-service
sudo systemctl status taxi-service
```

**Option B: Direct command**

```bash
gunicorn main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --timeout 120
```

### 4. Nginx Configuration

Update `/etc/nginx/sites-available/taxi-service`:

```nginx
upstream taxi_backend {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name 164.90.229.192 your-domain.com;

    client_max_body_size 10M;

    # HTTP API endpoints
    location /api/ {
        proxy_pass http://taxi_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket endpoints
    location /ws/ {
        proxy_pass http://taxi_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket specific timeouts
        proxy_read_timeout 86400;  # 24 hours
        proxy_send_timeout 86400;
        proxy_connect_timeout 60;
    }

    # Documentation
    location /docs {
        proxy_pass http://taxi_backend;
        proxy_set_header Host $host;
    }

    location /redoc {
        proxy_pass http://taxi_backend;
        proxy_set_header Host $host;
    }

    # Root
    location / {
        proxy_pass http://taxi_backend;
        proxy_set_header Host $host;
    }
}
```

Test and reload Nginx:
```bash
sudo nginx -t
sudo systemctl reload nginx
```

---

## Testing WebSockets

### Test with curl (basic handshake test):
```bash
curl -i -N -H "Connection: Upgrade" \
     -H "Upgrade: websocket" \
     -H "Sec-WebSocket-Version: 13" \
     -H "Sec-WebSocket-Key: SGVsbG8sIHdvcmxkIQ==" \
     http://164.90.229.192/ws/driver/YOUR_TOKEN
```

### Test with Python:
```python
import asyncio
import websockets
import json

async def test_driver_connection():
    token = "YOUR_JWT_TOKEN"
    uri = f"ws://164.90.229.192/ws/driver/{token}"
    
    async with websockets.connect(uri) as websocket:
        # Receive connection confirmation
        response = await websocket.recv()
        print(f"Connected: {response}")
        
        # Send ping
        await websocket.send(json.dumps({"type": "ping"}))
        response = await websocket.recv()
        print(f"Pong: {response}")
        
        # Keep listening for messages
        while True:
            message = await websocket.recv()
            print(f"Received: {message}")

asyncio.run(test_driver_connection())
```

### Test with JavaScript (Browser Console):
```javascript
const token = "YOUR_JWT_TOKEN";
const ws = new WebSocket(`ws://164.90.229.192/ws/driver/${token}`);
ws.onmessage = (e) => console.log(JSON.parse(e.data));
ws.onopen = () => ws.send(JSON.stringify({type: "ping"}));
```

---

## Monitoring

### Check Active Connections:
```bash
GET /ws/stats
```

Response:
```json
{
    "active_drivers": 12,
    "active_users": 5,
    "total_connections": 17
}
```

### Server Logs:
```bash
# Check WebSocket connections
sudo journalctl -u taxi-service -f | grep WebSocket

# Check Nginx WebSocket upgrades
sudo tail -f /var/log/nginx/access.log | grep "101"
```

---

## Troubleshooting

### Issue: WebSocket connection fails

**Solution:**
```bash
# 1. Check if service is running
sudo systemctl status taxi-service

# 2. Check if using correct worker class
ps aux | grep gunicorn
# Should see: uvicorn.workers.UvicornWorker

# 3. Check Nginx config
sudo nginx -t
sudo systemctl reload nginx

# 4. Check firewall
sudo ufw allow 8000
```

### Issue: Connections dropping

**Solution:**
- Implement ping/pong keep-alive (every 30 seconds)
- Increase Nginx timeouts
- Add reconnection logic in client

### Issue: Messages not reaching all drivers

**Solution:**
- Check if using `asyncio.create_task()` for broadcasts
- Verify drivers are properly connected
- Check `/ws/stats` endpoint

---

## Best Practices

1. **Always authenticate** - Validate JWT token on connection
2. **Implement reconnection** - Handle network drops gracefully
3. **Use ping/pong** - Keep connections alive
4. **Graceful shutdown** - Close connections properly
5. **Error handling** - Catch and log WebSocket errors
6. **Rate limiting** - Prevent spam from clients
7. **Monitor connections** - Track active users/drivers

---

## Summary

✅ **WebSocket Server** - Integrated into main FastAPI app  
✅ **Driver Endpoint** - `/ws/driver/{token}`  
✅ **User Endpoint** - `/ws/user/{token}`  
✅ **Real-time Notifications** - Instant order updates  
✅ **Duplicate Prevention** - Order locking mechanism  
✅ **Production Ready** - Nginx + Gunicorn + Uvicorn Workers  
✅ **Monitoring** - `/ws/stats` endpoint  

The WebSocket integration is complete and ready for deployment! 🚀
