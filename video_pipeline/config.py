"""
video_pipeline/config.py
=========================
All configuration for the video AI pipeline.

Environment variables
----------------------
BACKEND_URL       : URL of the COBRA-WATCH FastAPI backend.
                    Default: http://localhost:8000 for local dev.
                    Use http://backend:8000 inside Docker Compose.
YOLO_MODEL        : Path to YOLOv8 model weights file.
                    Default: yolov8n.pt (nano — downloads automatically on first run).
VIDEO_PIPELINE_LOG: Log level. Default: INFO.

Footage mapping (FOOTAGE_CAMERA_MAP)
--------------------------------------
Maps local video file paths → demo camera_ids (from the devices table).
This is the ONLY place that connects a video file to a camera_id.
detector.py refuses to accept a camera_id that is NOT registered here,
which enforces the hard legal/ethical boundary: you cannot accidentally
point the pipeline at a live device discovered via Shodan.

Zone/threshold configuration (CAMERA_RULES)
---------------------------------------------
Per-camera rule parameters. Keys must match camera_ids in FOOTAGE_CAMERA_MAP.
  loitering_threshold_seconds : dwell time (in seconds) before a loitering event fires
  loitering_zone              : list of [x, y] polygon vertices (normalized 0.0–1.0)
  perimeter_lines             : list of line segments [[x1,y1],[x2,y2]] (normalized)
  event_cooldown_seconds      : min time between two events of the same type from same track
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Backend connection
# ---------------------------------------------------------------------------
BACKEND_URL: str = os.getenv("BACKEND_URL", "http://localhost:8000")

# ---------------------------------------------------------------------------
# YOLOv8 model weights
# If the path doesn't exist, ultralytics auto-downloads it on first run.
# For CPU-only Docker: yolov8n.pt (nano) is fastest.
# For GPU Docker: yolov8s.pt or yolov8m.pt gives better accuracy.
# ---------------------------------------------------------------------------
YOLO_MODEL: str = os.getenv("YOLO_MODEL", "yolov8n.pt")

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_LEVEL: str = os.getenv("VIDEO_PIPELINE_LOG", "INFO")

# ---------------------------------------------------------------------------
# FOOTAGE → CAMERA_ID mapping
#
# This is the enforcement point for the hard ethical/legal boundary:
# detector.py ONLY accepts video sources whose camera_id is listed here.
# It will NEVER accept an IP address or RTSP URL from the devices DB.
#
# To add a new demo clip:
#   1. Put the video file in video_pipeline/sample_footage/
#   2. Add an entry here: {"path": "sample_footage/clip.mp4", "camera_id": "<seeded_id>"}
#   3. Run scripts/seed_demo_data.py (from root) to make sure that camera_id exists in DB.
#
# camera_ids below are placeholders — replace with real IDs from your seeded DB.
# Run: sqlite3 backend/data/surveillancewatch.db "SELECT id, city, manufacturer FROM devices LIMIT 5;"
# ---------------------------------------------------------------------------
FOOTAGE_CAMERA_MAP: list[dict] = [
    {
        "path": "sample_footage/demo_loitering.mp4",
        "camera_id": "DEMO_CAM_001",   # replace with real device id from DB
        "description": "Mumbai Dharavi cluster — loitering demo",
    },
    {
        "path": "sample_footage/demo_perimeter.mp4",
        "camera_id": "DEMO_CAM_002",   # replace with real device id from DB
        "description": "Delhi Connaught Place cluster — perimeter breach demo",
    },
]

# ---------------------------------------------------------------------------
# Per-camera rule configuration
#
# All coordinates are NORMALIZED (0.0–1.0 relative to frame width/height)
# so they work regardless of the input video resolution.
#
# loitering_zone: polygon vertices in [x, y] format.
#   A bounding-box centre point is "in zone" if it falls inside this polygon.
#
# perimeter_lines: list of line segments. Each segment is [[x1,y1],[x2,y2]].
#   A track "crosses" a line if its centre point transitions from one side
#   to the other between consecutive frames.
#
# event_cooldown_seconds: prevents the same track from firing the same rule
#   repeatedly. After one fire, that rule is suppressed for this duration.
# ---------------------------------------------------------------------------
CAMERA_RULES: dict[str, dict] = {
    "DEMO_CAM_001": {
        "loitering_threshold_seconds": 5.0,   # 5s dwell = loitering in demo
        "loitering_zone": [                    # centre-frame zone (normalized)
            [0.25, 0.25],
            [0.75, 0.25],
            [0.75, 0.75],
            [0.25, 0.75],
        ],
        "perimeter_lines": [],                 # no perimeter rule for this camera
        "event_cooldown_seconds": 10.0,
    },
    "DEMO_CAM_002": {
        "loitering_threshold_seconds": 8.0,
        "loitering_zone": [
            [0.1, 0.1],
            [0.9, 0.1],
            [0.9, 0.9],
            [0.1, 0.9],
        ],
        "perimeter_lines": [
            [[0.0, 0.5], [1.0, 0.5]],         # horizontal mid-frame line
        ],
        "event_cooldown_seconds": 15.0,
    },
}

# Fallback rule config for camera_ids not explicitly listed above
DEFAULT_RULES: dict = {
    "loitering_threshold_seconds": 10.0,
    "loitering_zone": [
        [0.2, 0.2],
        [0.8, 0.2],
        [0.8, 0.8],
        [0.2, 0.8],
    ],
    "perimeter_lines": [],
    "event_cooldown_seconds": 30.0,
}

# ---------------------------------------------------------------------------
# YOLOv8 class filtering — only detect these COCO classes
# 0 = person, 2 = car, 7 = truck (add more as needed)
# ---------------------------------------------------------------------------
DETECT_CLASSES: list[int] = [0]   # person only; add 2, 7 for vehicles
CONFIDENCE_THRESHOLD: float = 0.40  # min detection confidence to track
