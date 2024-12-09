import os

import redis.asyncio as redis
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, APIRouter
from fastapi.responses import HTMLResponse

redis_port = int(os.getenv("REDIS_PORT"))
redis_host = os.getenv("REDIS_HOST")
redis_db = os.getenv("REDIS_DB")

r = redis.Redis(host=redis_host, port=redis_port, db=redis_db)

socket_router = APIRouter()

@socket_router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await websocket.accept()
    pubsub = r.pubsub()
    await pubsub.subscribe(f"notifications:{user_id}")

    try:
        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True)
            if message:
                await websocket.send_text(message['data'].decode('utf-8'))
            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        await pubsub.unsubscribe(f"notifications:{user_id}")
        print(f"User {user_id} disconnected")

@socket_router.get("/")
async def get():
    html_content = """
    <html>
        <body>
            <h2>Real-Time Notifications with Redis and WebSocket</h2>
            <p>Enter your user ID:</p>
            <input type="text" id="user_id" />
            <button onclick="connect()">Connect</button>
            <div id="notifications"></div>
            <script>
                function connect() {
                    const user_id = document.getElementById("user_id").value;
                    const websocket = new WebSocket(`ws://localhost:8000/ws/${user_id}`);

                    websocket.onopen = function(event) {
                        console.log('WebSocket connection established');
                    };

                    websocket.onmessage = function(event) {
                        const notificationsDiv = document.getElementById("notifications");
                        notificationsDiv.innerHTML += `<p>${event.data}</p>`;
                    };

                    websocket.onclose = function(event) {
                        console.log('Disconnected');
                    };

                    websocket.onerror = function(event) {
                        console.error('WebSocket error:', event);
                    };
                }
            </script>
        </body>
    </html>
    """
    return HTMLResponse(content=html_content)
@socket_router.post("/send_notification")
async def send_notification(user_id: str, message: str):
    await r.publish(f"notifications:{user_id}", message)
    return {"message": f"Notification sent to {user_id}"}