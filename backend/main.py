"""
main.py — COBRA-WATCH API
==========================
Phase 2 changes
---------------
- The fake `random.choice()` WebSocket alert generator has been REMOVED.
- A real `ConnectionManager` pub/sub replaces it. The WebSocket endpoint now
  only manages connections. Actual messages are pushed by `POST /api/detection-event`
  (in routes/alerts.py) via `manager.broadcast()`.
- The new `alerts` router is registered under `/api`.
- `set_connection_manager(manager)` is called at startup so alerts.py can
  broadcast without a circular import.

WebSocket message shape sent to clients (for LiveAlerts.jsx in Phase 4):
  {
    "type": "ALERT",
    "id": "...",
    "camera_id": "...",
    "city": "...",
    "event_type": "...",
    "trust_score": 0,
    "action_tier": "low_trust",
    "contributing_factors": [...],
    "corroborated_by": [...],
    "detected_at": "..."
  }
"""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from typing import Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from config import CORS_ORIGINS
from database import init_db
from routes import devices, news, brief, heatmap, stats
from routes import alerts as alerts_router
from routes.alerts import set_connection_manager


# ---------------------------------------------------------------------------
# Real WebSocket connection manager (replaces random.choice() loop)
# ---------------------------------------------------------------------------

class ConnectionManager:
    """
    Manages a set of connected WebSocket clients and provides a broadcast
    helper. Thread-safety is not a concern here since FastAPI runs on a single
    async event loop per process.
    """

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.add(websocket)
        print(f"[ws] Client connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket) -> None:
        self.active_connections.discard(websocket)
        print(f"[ws] Client disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, payload: dict) -> None:
        """Send `payload` as JSON to every connected WebSocket client."""
        if not self.active_connections:
            return
        message = json.dumps(payload)
        dead: Set[WebSocket] = set()
        for ws in list(self.active_connections):
            try:
                await ws.send_text(message)
            except Exception:
                # Client disconnected mid-broadcast — mark for removal
                dead.add(ws)
        for ws in dead:
            self.active_connections.discard(ws)


manager = ConnectionManager()


# ---------------------------------------------------------------------------
# App lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    # Inject the manager into alerts.py so it can broadcast without importing app
    set_connection_manager(manager)
    yield


# ---------------------------------------------------------------------------
# App + middleware
# ---------------------------------------------------------------------------

app = FastAPI(
    title="COBRA-WATCH API",
    description="Geospatial Camera Exposure Intelligence Platform — OSINT surveillance mapping",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(devices.router, prefix="/api")
app.include_router(news.router, prefix="/api")
app.include_router(brief.router, prefix="/api")
app.include_router(heatmap.router, prefix="/api")
app.include_router(stats.router, prefix="/api")
app.include_router(alerts_router.router, prefix="/api")  # Phase 2


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "ws_clients": len(manager.active_connections),
    }


# ---------------------------------------------------------------------------
# WebSocket — real pub/sub (fake random.choice() loop REMOVED)
# ---------------------------------------------------------------------------

@app.websocket("/api/ws/alerts")
async def websocket_alerts(websocket: WebSocket):
    """
    Real-time alert feed. Messages are pushed here when a detection event
    is processed via POST /api/detection-event — not from a random timer.

    Frontend (LiveAlerts.jsx) connects to this endpoint unchanged;
    only the message shape has evolved from the old fake LIVE_ALERT to the
    real ALERT shape documented in this file's module docstring.
    """
    await manager.connect(websocket)
    try:
        # Keep the connection alive — we only receive here (no client→server messages)
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)
