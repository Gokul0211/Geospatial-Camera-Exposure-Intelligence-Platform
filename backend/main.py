from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import asyncio
import json
import random
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from database import init_db
from config import CORS_ORIGINS
from routes import devices, news, brief, heatmap, stats


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="SurveillanceWatch API",
    description="OSINT platform mapping surveillance infrastructure deployments",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(devices.router, prefix="/api")
app.include_router(news.router, prefix="/api")
app.include_router(brief.router, prefix="/api")
app.include_router(heatmap.router, prefix="/api")
app.include_router(stats.router, prefix="/api")


@app.get("/health")
async def health():
    return {"status": "ok"}

@app.websocket("/api/ws/alerts")
async def websocket_alerts(websocket: WebSocket):
    await websocket.accept()
    
    cities = ["Mumbai", "Delhi", "Bangalore"]
    alert_types = [
        "Unauthenticated facial recognition match detected",
        "Anomalous bulk metadata transfer to external IP",
        "New unpatched DVR/NVR device exposed on Port 554",
        "RTSP stream accessed from foreign IP block"
    ]
    
    try:
        while True:
            # Simulate real-time alerts coming in every 10-30 seconds
            await asyncio.sleep(random.randint(10, 30))
            
            alert = {
                "type": "LIVE_ALERT",
                "city": random.choice(cities),
                "severity": random.choice(["HIGH", "CRITICAL", "MEDIUM"]),
                "message": random.choice(alert_types),
                "timestamp": asyncio.get_event_loop().time()
            }
            await websocket.send_text(json.dumps(alert))
    except WebSocketDisconnect:
        print("WebSocket client disconnected")

