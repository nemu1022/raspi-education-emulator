import asyncio
from websockets.server import serve

async def handler(websocket):
    while True:
        await websocket.send("LED_ON")
        await asyncio.sleep(1)

        await websocket.send("LED_OFF")
        await asyncio.sleep(1)

async def main():
    async with serve(handler, "0.0.0.0", 8765):
        print("WebSocket Server Started")
        await asyncio.Future()

asyncio.run(main())