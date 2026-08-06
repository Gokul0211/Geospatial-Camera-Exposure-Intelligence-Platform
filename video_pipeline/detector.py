"""
video_pipeline/detector.py
===========================
YOLOv8 inference wrapper.

Responsibilities
-----------------
- Load a YOLOv8 model (CPU or GPU, auto-detected).
- Accept a local video file path (or an explicitly whitelisted test feed URL).
- Yield per-frame detection results as structured dicts.

HARD LEGAL/ETHICAL BOUNDARY (enforced by construction)
--------------------------------------------------------
`run_detections()` only accepts sources that are registered in
`config.FOOTAGE_CAMERA_MAP`. It explicitly rejects:
  - Any string containing a device IP from the devices DB
  - Any RTSP:// URL not pre-whitelisted in config

The pipeline NEVER pulls frames from a discovered device's live stream.
Sample/public/self-recorded footage only.

Detection output schema (per frame)
--------------------------------------
Each yielded dict:
  {
    "frame_idx"   : int,
    "frame"       : np.ndarray (H×W×3, BGR),
    "timestamp_s" : float,       # seconds from video start
    "detections"  : [
        {
          "bbox_xyxy"  : [x1, y1, x2, y2],   # pixel coords
          "bbox_norm"  : [x1n, y1n, x2n, y2n], # normalized 0-1
          "confidence" : float,
          "class_id"   : int,
          "class_name" : str,
        }, ...
    ]
  }
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Generator

import cv2
import numpy as np

from config import (
    YOLO_MODEL,
    FOOTAGE_CAMERA_MAP,
    DETECT_CLASSES,
    CONFIDENCE_THRESHOLD,
    LOG_LEVEL,
)

logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO))
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Allowed source registry — built once at import time
# ---------------------------------------------------------------------------
_ALLOWED_PATHS: set[str] = {
    entry["path"] for entry in FOOTAGE_CAMERA_MAP
}


def _assert_source_is_authorized(source: str) -> None:
    """
    Enforce the hard legal/ethical boundary.

    Raises ValueError if the source path/URL is not in FOOTAGE_CAMERA_MAP.
    This makes it impossible to accidentally point the pipeline at a
    Shodan-discovered device's live RTSP stream.
    """
    # Reject any rtsp:// URLs not explicitly whitelisted
    if source.lower().startswith("rtsp://"):
        if source not in _ALLOWED_PATHS:
            raise ValueError(
                f"RTSP source '{source}' is NOT whitelisted in config.FOOTAGE_CAMERA_MAP. "
                "This pipeline may only process authorized test feeds. "
                "Do NOT point it at discovered device IPs — that is unauthorized access."
            )

    # Reject local paths not in the allowed set
    # (normalise to just filename for flexibility)
    source_norm = source.replace("\\", "/")
    allowed_norms = {p.replace("\\", "/") for p in _ALLOWED_PATHS}
    if source_norm not in allowed_norms:
        # Also accept absolute paths whose suffix matches a registered relative path
        source_path = Path(source_norm)
        if not any(source_path.name == Path(p).name for p in allowed_norms):
            raise ValueError(
                f"Video source '{source}' is not registered in config.FOOTAGE_CAMERA_MAP. "
                "Register it there (with a mapped camera_id) before processing. "
                "This check exists to prevent accidentally pulling live streams from "
                "third-party devices discovered via the OSINT pipeline."
            )


class Detector:
    """
    YOLOv8 inference wrapper.

    Parameters
    ----------
    model_path : str
        Path to YOLOv8 weights (.pt file). If the file doesn't exist,
        ultralytics auto-downloads it.
    classes : list[int]
        COCO class IDs to detect. Default: [0] (person only).
    conf_threshold : float
        Minimum confidence to include a detection.
    """

    def __init__(
        self,
        model_path: str = YOLO_MODEL,
        classes: list[int] | None = None,
        conf_threshold: float = CONFIDENCE_THRESHOLD,
    ) -> None:
        # Lazy import so the module can be imported without ultralytics installed
        # (e.g. in rule-only test environments)
        try:
            from ultralytics import YOLO
            log.info(f"[detector] Loading YOLO model: {model_path}")
            self.model = YOLO(model_path)
            log.info("[detector] Model loaded.")
        except ImportError:
            raise ImportError(
                "ultralytics is not installed. "
                "Run: pip install -r video_pipeline/requirements.txt"
            )

        self.classes = classes if classes is not None else DETECT_CLASSES
        self.conf_threshold = conf_threshold

    def run_detections(
        self,
        source: str,
        skip_frames: int = 0,
    ) -> Generator[dict, None, None]:
        """
        Yield per-frame detection results from a video source.

        Parameters
        ----------
        source : str
            Local video file path registered in config.FOOTAGE_CAMERA_MAP.
        skip_frames : int
            Process every (skip_frames + 1)th frame for speed.
            0 = process every frame.

        Yields
        ------
        dict — see module docstring for schema.

        Raises
        ------
        ValueError  — if source is not in FOOTAGE_CAMERA_MAP (boundary enforcement)
        FileNotFoundError — if local file path doesn't exist
        """
        _assert_source_is_authorized(source)

        if not source.lower().startswith("rtsp://"):
            p = Path(source)
            if not p.exists():
                raise FileNotFoundError(
                    f"Video file '{source}' not found. "
                    "Place sample footage in video_pipeline/sample_footage/."
                )

        cap = cv2.VideoCapture(source)
        if not cap.isOpened():
            raise RuntimeError(f"Could not open video source: {source}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        frame_idx = 0
        processed = 0

        log.info(f"[detector] Starting detection on '{source}' @ {fps:.1f} fps")

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                frame_idx += 1
                if skip_frames > 0 and (frame_idx % (skip_frames + 1)) != 0:
                    continue

                timestamp_s = (frame_idx - 1) / fps
                h, w = frame.shape[:2]

                results = self.model(
                    frame,
                    classes=self.classes,
                    conf=self.conf_threshold,
                    verbose=False,
                )

                detections = []
                if results and results[0].boxes is not None:
                    boxes = results[0].boxes
                    for i in range(len(boxes)):
                        x1, y1, x2, y2 = boxes.xyxy[i].tolist()
                        conf = float(boxes.conf[i])
                        cls_id = int(boxes.cls[i])
                        cls_name = self.model.names.get(cls_id, str(cls_id))
                        detections.append({
                            "bbox_xyxy": [x1, y1, x2, y2],
                            "bbox_norm": [x1 / w, y1 / h, x2 / w, y2 / h],
                            "confidence": conf,
                            "class_id": cls_id,
                            "class_name": cls_name,
                        })

                processed += 1
                yield {
                    "frame_idx": frame_idx,
                    "frame": frame,
                    "timestamp_s": timestamp_s,
                    "detections": detections,
                }

        finally:
            cap.release()
            log.info(
                f"[detector] Done. Processed {processed} frames "
                f"({frame_idx} total read, {skip_frames} skip_frames)."
            )
