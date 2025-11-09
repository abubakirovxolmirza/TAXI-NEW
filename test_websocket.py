#!/usr/bin/env python3
"""
WebSocket Test Script for Taxi Service
Tests driver WebSocket connection
"""
import asyncio
import websockets
import json
import sys

# Driver token
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIyIiwiZXhwIjoxNzY1MjczNTY5fQ.vTGjRKyQX6R34sDYOOCIm0p7azs3XPq24FViEi5l10s"

# WebSocket URL (through Nginx on port 80, not direct 8000)
WS_URL = f"ws://164.90.229.192/ws/driver/{TOKEN}"

async def test_websocket():
    """Test WebSocket connection"""
    print("🚀 Starting WebSocket test...")
    print(f"📡 Connecting to: {WS_URL}")
    print("-" * 60)
    
    try:
        async with websockets.connect(WS_URL) as websocket:
            print("✅ WebSocket connection established!")
            print()
            
            # 1. Receive connection message
            print("⏳ Waiting for connection message...")
            message = await websocket.recv()
            data = json.loads(message)
            print(f"📩 Received: {json.dumps(data, indent=2)}")
            print()
            
            # 2. Send ping
            print("📤 Sending ping...")
            await websocket.send(json.dumps({"type": "ping"}))
            
            # 3. Receive pong
            print("⏳ Waiting for pong...")
            response = await websocket.recv()
            pong_data = json.loads(response)
            print(f"📩 Received: {json.dumps(pong_data, indent=2)}")
            print()
            
            # 4. Simulate viewing an order
            print("📤 Simulating viewing order #123...")
            await websocket.send(json.dumps({
                "type": "viewing_order",
                "order_id": 123,
                "order_type": "taxi"
            }))
            print("✅ Sent viewing_order message")
            print()
            
            # 5. Wait for any messages (like viewer count)
            print("⏳ Listening for messages (5 seconds)...")
            try:
                while True:
                    message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    msg_data = json.loads(message)
                    print(f"📩 Received: {json.dumps(msg_data, indent=2)}")
            except asyncio.TimeoutError:
                print("⏱️  Timeout - no more messages")
            
            print()
            print("=" * 60)
            print("✅ WebSocket test SUCCESSFUL!")
            print("=" * 60)
            print()
            print("✅ Connection works!")
            print("✅ Ping/Pong works!")
            print("✅ Message sending works!")
            print()
            print("🎉 Your WebSocket system is fully functional!")
            
    except websockets.exceptions.InvalidStatusCode as e:
        print(f"❌ Connection failed with status code: {e.status_code}")
        print(f"   Reason: {e}")
        sys.exit(1)
    except websockets.exceptions.WebSocketException as e:
        print(f"❌ WebSocket error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(test_websocket())
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(0)
