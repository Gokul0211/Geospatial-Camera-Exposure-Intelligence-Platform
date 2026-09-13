"""
video_pipeline/tracker.py
==========================
ByteTrack-based object tracker wired onto detector.py's output.

What it does
------------
Wraps ultralytics' built-in ByteTrack support (which is included in
`ultralytics >= 8.x` — no separate package needed). Maintains a per-object
track history: for each unique `track_id`, records every frame's normalised
centre point and timestamp, which `rules.py` consumes to detect:
  - Loitering: same track_id in a zone for > threshold seconds
  - Perimeter breach: track centre crosses a defined line between frames

Track history schema
---------------------
  track_id (int) → {
    "class_id"   : int,
    "class_name" : str,
    "history"    : [
        {
          "frame_idx"   : int,
          "timestamp_s" : float,
          "cx_norm"     : float,   # normalised centre x (0-1)
          "cy_norm"     : float,   # normalised centre y (0-1)
          "bbox_norm"   : [x1n, y1n, x2n, y2n],
          "confidence"  : float,
        },
        ...
    ]
  }

Design note on tracker choice
-------------------------------
We use ultralytics' built-in `track()` method which bundles ByteTrack
(default) and BoT-SORT. This avoids an extra dependency for a separate
ByteTrack package. The tracker is stateful across frames within a single
`Tracker` instance — reset by creating a new instance.
"""

from __future__ import annotations

import logging
from collections import defaultdict

import cv2
import numpy as np

from config import (
    YOLO_MODEL,
    DETECT_CLASSES,
    CONFIDENCE_THRESHOLD,
    LOG_LEVEL,
)

logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO))
log = logging.getLogger(__name__)

# Max frames of history to keep per track (prevents unbounded memory growth
# in a long-running pipeline; 2 × fps × max_dwell_seconds is a safe ceiling)
MAX_HISTORY_FRAMES = 500


class Tracker:
    """
    Stateful object tracker using YOLOv8 + ByteTrack.

    Usage
    -----
    tracker = Tracker()
    for frame_data in detector.run_detections(source):
        tracker.update(frame_data)
        histories = tracker.get_histories()
        # pass histories to rules.py
    """

    def __init__(
        self,
        model_path: str = YOLO_MODEL,
        classes: list[int] | None = None,
        conf_threshold: float = CONFIDENCE_THRESHOLD,
    ) -> None:
        try:
            from ultralytics import YOLO
            log.info(f"[tracker] Loading YOLO model for tracking: {model_path}")
            self._model = YOLO(model_path)
        except ImportError:
            raise ImportError(
                "ultralytics is not installed. "
                "Run: pip install -r video_pipeline/requirements.txt"
            )

        self.classes = classes if classes is not None else DETECT_CLASSES
        self.conf_threshold = conf_threshold

        # track_id → {class_id, class_name, history: [...]}
        self._histories: dict[int, dict] = defaultdict(
            lambda: {"class_id": 0, "class_name": "unknown", "history": []}
        )
        # track_ids seen in the current run (for cleanup of lost tracks)
        self._active_ids: set[int] = set()

    def update(self, frame_data: dict) -> dict[int, dict]:
        """
        Run tracking on a single frame's raw BGR image.

        Parameters
        ----------
        frame_data : dict
            A frame dict as yielded by `Detector.run_detections()`.
            Must contain: "frame" (np.ndarray), "frame_idx", "timestamp_s".

        Returns
        -------
        dict mapping track_id → track history entry for THIS frame only.
        Use `get_histories()` for the full accumulated history.
        """
        frame: np.ndarray = frame_data["frame"]
        frame_idx: int = frame_data["frame_idx"]
        timestamp_s: float = frame_data["timestamp_s"]
        h, w = frame.shape[:2]

        current_ids: set[int] = set()
        frame_tracks: dict[int, dict] = {}

        results = self._model.track(
            frame,
            classes=self.classes,
            conf=self.conf_threshold,
            persist=True,   # required for ByteTrack state to persist across calls
            verbose=False,
        )

        if results and results[0].boxes is not None:
            boxes = results[0].boxes
            for i in range(len(boxes)):
                # track_id is None if ByteTrack couldn't assign an ID yet
                raw_tid = boxes.id
                if raw_tid is None:
                    continue
                track_id = int(raw_tid[i])

                x1, y1, x2, y2 = boxes.xyxy[i].tolist()
                conf = float(boxes.conf[i])
                cls_id = int(boxes.cls[i])
                cls_name = self._model.names.get(cls_id, str(cls_id))

                cx_norm = ((x1 + x2) / 2) / w
                cy_norm = ((y1 + y2) / 2) / h

                entry = {
                    "frame_idx": frame_idx,
                    "timestamp_s": timestamp_s,
                    "cx_norm": cx_norm,
                    "cy_norm": cy_norm,
                    "bbox_norm": [x1 / w, y1 / h, x2 / w, y2 / h],
                    "confidence": conf,
                }

                track = self._histories[track_id]
                track["class_id"] = cls_id
                track["class_name"] = cls_name
                track["history"].append(entry)

                # Trim history to avoid unbounded growth
                if len(track["history"]) > MAX_HISTORY_FRAMES:
                    track["history"] = track["history"][-MAX_HISTORY_FRAMES:]

                current_ids.add(track_id)
                frame_tracks[track_id] = entry

        self._active_ids = current_ids
        return frame_tracks

    def get_histories(self) -> dict[int, dict]:
        """Return the full accumulated track history for all known tracks."""
        return dict(self._histories)

    def get_active_histories(self) -> dict[int, dict]:
        """Return histories for tracks currently visible in the latest frame."""
        return {
            tid: data
            for tid, data in self._histories.items()
            if tid in self._active_ids
        }

    def reset(self) -> None:
        """Clear all track histories — call between video files."""
        self._histories.clear()
        self._active_ids.clear()
        log.debug("[tracker] Track histories reset.")
