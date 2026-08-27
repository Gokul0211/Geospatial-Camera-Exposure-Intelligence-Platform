"""
video_pipeline/main.py
=======================
Orchestrator for the COBRA-WATCH video AI pipeline.

Flow
-----
1. For each registered footage entry in config.FOOTAGE_CAMERA_MAP:
   a. Verify the camera_id exists in the COBRA-WATCH backend (GET /api/devices/{id}/trust-score)
   b. Open video → run Tracker frame-by-frame
   c. After each frame, pass all active track histories to RuleEngine.evaluate()
   d. For each rule fire → POST /api/detection-event to the backend
2. Handles connection errors gracefully (retries with backoff) so a temporary
   backend unavailability doesn't crash the pipeline.

Run
----
  # From the project root:
  python video_pipeline/main.py

  # Or inside Docker (docker-compose.yml uncomments the video-pipeline service):
  docker-compose up video-pipeline

Environment variables (see config.py)
---------------------------------------
  BACKEND_URL=http://localhost:8000   (or http://backend:8000 in Docker)
  YOLO_MODEL=yolov8n.pt
  VIDEO_PIPELINE_LOG=INFO

HARD ETHICAL/LEGAL BOUNDARY
------------------------------
This process ONLY processes video files registered in config.FOOTAGE_CAMERA_MAP.
It NEVER connects to an RTSP stream from a device discovered via the OSINT pipeline.
That enforcement is in detector.py (_assert_source_is_authorized).
"""

from __future__ import annotations

import sys
import os
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

from config import (
    BACKEND_URL,
    FOOTAGE_CAMERA_MAP,
    CAMERA_RULES,
    DEFAULT_RULES,
    LOG_LEVEL,
)

# Phase 4: read the detection API key from env so the pipeline can authenticate
# its POST /api/detection-event requests. Empty = no auth (local dev default).
DETECTION_API_KEY: str = os.getenv("DETECTION_API_KEY", "")
from tracker import Tracker
from rules import RuleEngine

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
log = logging.getLogger("cobra.pipeline")


# ---------------------------------------------------------------------------
# Backend communication
# ---------------------------------------------------------------------------

def _check_backend_health(client: httpx.Client) -> bool:
    """Return True if the backend is reachable."""
    try:
        res = client.get(f"{BACKEND_URL}/health", timeout=5.0)
        return res.status_code == 200
    except Exception as e:
        log.error(f"[main] Backend health check failed: {e}")
        return False


def _verify_camera_id(client: httpx.Client, camera_id: str) -> bool:
    """
    Check the camera_id exists in the backend's devices table.
    Warns rather than crashes so the pipeline can continue with other cameras.
    """
    try:
        res = client.get(
            f"{BACKEND_URL}/api/devices/{camera_id}/trust-score", timeout=5.0
        )
        if res.status_code == 200:
            log.info(f"[main] Camera verified: {camera_id}")
            return True
        elif res.status_code == 404:
            log.warning(
                f"[main] Camera '{camera_id}' not found in backend DB. "
                "Run seed_demo_data.py to create it, then update FOOTAGE_CAMERA_MAP "
                "in config.py with the real device ID."
            )
            return False
        else:
            log.warning(f"[main] Unexpected status {res.status_code} checking camera {camera_id}")
            return False
    except Exception as e:
        log.error(f"[main] Failed to verify camera {camera_id}: {e}")
        return False


def _post_detection_event(
    client: httpx.Client,
    camera_id: str,
    event_type: str,
    confidence: float,
    metadata: dict,
    max_retries: int = 3,
) -> bool:
    """
    POST a detection event to /api/detection-event with retry logic.
    Includes X-API-Key header if DETECTION_API_KEY is set.
    Returns True if successfully posted.
    """
    payload = {
        "camera_id": camera_id,
        "event_type": event_type,
        "confidence": round(confidence, 4),
        "detected_at": datetime.now(timezone.utc).isoformat(),
        "metadata": metadata,
    }
    headers = {}
    if DETECTION_API_KEY:
        headers["X-API-Key"] = DETECTION_API_KEY

    for attempt in range(1, max_retries + 1):
        try:
            res = client.post(
                f"{BACKEND_URL}/api/detection-event",
                json=payload,
                headers=headers,
                timeout=10.0,
            )
            if res.status_code == 200:
                data = res.json()
                log.info(
                    f"[main] Detection event posted → alert_id={data.get('alert_id')} "
                    f"trust_score={data.get('trust_score')} "
                    f"tier={data.get('action_tier')}"
                )
                return True
            else:
                log.warning(
                    f"[main] POST /api/detection-event returned {res.status_code}: "
                    f"{res.text[:200]}"
                )
        except httpx.TimeoutException:
            log.warning(f"[main] POST timed out (attempt {attempt}/{max_retries})")
        except Exception as e:
            log.error(f"[main] POST error (attempt {attempt}/{max_retries}): {e}")

        if attempt < max_retries:
            time.sleep(2 ** attempt)  # exponential backoff: 2s, 4s

    return False


# ---------------------------------------------------------------------------
# Per-footage-entry pipeline
# ---------------------------------------------------------------------------

def _run_pipeline_for_entry(
    client: httpx.Client,
    entry: dict,
    skip_frames: int = 2,
) -> None:
    """
    Run the full detection→tracking→rules→event-post pipeline for one footage entry.

    Parameters
    ----------
    entry : dict
        One entry from config.FOOTAGE_CAMERA_MAP:
        {"path": ..., "camera_id": ..., "description": ...}
    skip_frames : int
        Process every (skip_frames+1)th frame for speed. 2 = every 3rd frame.
    """
    from detector import Detector  # imported here to keep import errors local to this function

    source = entry["path"]
    camera_id = entry["camera_id"]
    description = entry.get("description", source)
    rules_config = CAMERA_RULES.get(camera_id, DEFAULT_RULES)

    log.info(f"[main] === Starting pipeline for: {description} ===")
    log.info(f"[main]   source={source}  camera_id={camera_id}")

    # Verify camera exists in backend
    if not _verify_camera_id(client, camera_id):
        log.warning(f"[main] Skipping '{description}' — camera not found in DB.")
        return

    tracker = Tracker()
    rule_engine = RuleEngine(camera_id=camera_id, rules_config=rules_config)
    detector = Detector()

    total_frames = 0
    total_events = 0
    events_fired: set[str] = set()  # deduplicate within this run

    for frame_data in detector.run_detections(source, skip_frames=skip_frames):
        total_frames += 1
        ts = frame_data["timestamp_s"]

        # Track
        active_tracks = tracker.update(frame_data)
        histories = tracker.get_histories()

        # Evaluate rules
        fires = rule_engine.evaluate(histories, current_timestamp_s=ts)
        rule_engine.cleanup_lost_tracks(set(active_tracks.keys()))

        # Post any rule fires
        for fire in fires:
            # Dedup: don't post the exact same (track_id, event_type) twice in one run
            # (cooldown in rules.py handles real-time gaps; this handles reruns)
            dedup_key = f"{fire['track_id']}:{fire['event_type']}:{int(ts)}"
            if dedup_key in events_fired:
                continue
            events_fired.add(dedup_key)

            success = _post_detection_event(
                client=client,
                camera_id=camera_id,
                event_type=fire["event_type"],
                confidence=fire["confidence"],
                metadata=fire["metadata"],
            )
            if success:
                total_events += 1

    log.info(
        f"[main] Done: {description} — "
        f"{total_frames} frames processed, {total_events} events posted."
    )
    tracker.reset()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    if not FOOTAGE_CAMERA_MAP:
        log.error(
            "[main] FOOTAGE_CAMERA_MAP is empty in config.py. "
            "Add at least one footage entry to run the pipeline."
        )
        sys.exit(1)

    log.info(f"[main] COBRA-WATCH Video AI Pipeline starting.")
    log.info(f"[main] Backend: {BACKEND_URL}")
    log.info(f"[main] Footage entries: {len(FOOTAGE_CAMERA_MAP)}")

    with httpx.Client() as client:
        # Wait for backend to be ready (up to 30 seconds)
        for attempt in range(6):
            if _check_backend_health(client):
                log.info("[main] Backend is reachable.")
                break
            log.info(f"[main] Waiting for backend... ({attempt+1}/6)")
            time.sleep(5)
        else:
            log.error(
                f"[main] Backend at {BACKEND_URL} is not reachable after 30s. "
                "Start the backend first: uvicorn main:app --reload (from backend/)"
            )
            sys.exit(1)

        for entry in FOOTAGE_CAMERA_MAP:
            try:
                _run_pipeline_for_entry(client, entry)
            except FileNotFoundError as e:
                log.error(
                    f"[main] Video file not found: {e}. "
                    "Place sample footage in video_pipeline/sample_footage/."
                )
            except ValueError as e:
                log.error(f"[main] Authorization error: {e}")
            except Exception as e:
                log.exception(f"[main] Unexpected error processing {entry}: {e}")

    log.info("[main] Pipeline complete.")


if __name__ == "__main__":
    main()
