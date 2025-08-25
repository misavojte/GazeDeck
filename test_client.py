#!/usr/bin/env python3
"""
Simple WebSocket client to test GazeDeck server
"""
import asyncio
import websockets
import json


async def test_client():
    uri = "ws://localhost:8765"
    
    try:
        print(f"Connecting to {uri}...")
        async with websockets.connect(uri) as websocket:
            print("✅ Connected successfully!")
            print("Listening for messages... (Press Ctrl+C to stop)")
            
            async for message in websocket:
                try:
                    data = json.loads(message)
                    if data['type'] == 'fixationStart':
                        print(f"🎯 Fixation START at ({data['data']['x']:.3f}, {data['data']['y']:.3f}) - {data['timestamp']}")
                    elif data['type'] == 'fixationEnd':
                        print(f"🔚 Fixation END - {data['timestamp']}")
                    else:
                        print(f"📨 Message: {message}")
                except json.JSONDecodeError:
                    print(f"📨 Raw message: {message}")
                    
    except ConnectionRefusedError:
        print("❌ Connection refused. Make sure the GazeDeck server is running!")
        print("   1. Start GazeDeck GUI: gazedeck")
        print("   2. Click 'Start Server' button")
        print("   3. Run this test again")
    except KeyboardInterrupt:
        print("\n👋 Disconnected by user")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    print("GazeDeck WebSocket Test Client")
    print("=" * 40)
    asyncio.run(test_client())
