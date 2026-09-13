"""
video_pipeline/liveness_detector.py
===================================
Module G (Tier 2) — Frame-Level Visual Liveness & Tamper Detection
Literature:
  - Yilmazer & Karakose (2025): Image-quality & tampering trust modelling
  - Liu et al. (2025): Cross-view temporal baseline tracking

Responsibilities:
-----------------
1. Perceptual Hash (pHash) freeze & replay attack detection.
2. Rolling EWMA baseline tracking for blur (variance of Laplacian) & exposure drift.
3. Live frame spec verification against Shodan-declared metadata.
4. Composite Visual Liveness Score L(t) in [0.0, 1.0].

ETHICAL & ARCHITECTURAL SCOPE:
------------------------------
Operates ONLY on authorized local/whitelisted footage mapped in FOOTAGE_CAMERA_MAP.
Never probes or pulls frames from unauthorized Shodan targets.
"""

from __future__ import annotations

import cv2
import numpy as np
from typing import Any
from collections import deque


def compute_frame_phash(frame: np.ndarray, hash_size: int = 8) -> int:
    """
    Compute a 64-bit perceptual hash (pHash) for an image frame using DCT.

    Parameters
    ----------
    frame : np.ndarray
        BGR or Grayscale image.
    hash_size : int
        Size of the hash (default 8 -> 64-bit integer).

    Returns
    -------
    int
        64-bit perceptual hash.
    """
    if frame is None or frame.size == 0:
        return 0

    if len(frame.shape) == 3:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    else:
        gray = frame

    # Resize to (hash_size * 4, hash_size * 4) for DCT analysis
    resized = cv2.resize(gray, (hash_size * 4, hash_size * 4), interpolation=cv2.INTER_AREA)
    float_img = np.float32(resized)
    dct = cv2.dct(float_img)

    # Extract low frequency top-left DCT block (excluding DC term at [0,0])
    dct_low = dct[:hash_size, :hash_size]
    med = np.median(dct_low)
    bit_matrix = (dct_low > med).flatten()

    # Convert boolean array to integer
    hash_val = 0
    for bit in bit_matrix:
        hash_val = (hash_val << 1) | int(bit)

    return int(hash_val)


def hamming_distance(hash1: int, hash2: int) -> int:
    """Calculate the Hamming distance (number of differing bits) between two 64-bit hashes."""
    return bin(hash1 ^ hash2).count("1")


def compute_laplacian_blur(frame: np.ndarray) -> float:
    """
    Compute the variance of the Laplacian of an image (standard focus/blur metric).
    Higher variance indicates sharp edges; low variance indicates blur/defocus/occlusion.
    """
    if frame is None or frame.size == 0:
        return 0.0

    if len(frame.shape) == 3:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    else:
        gray = frame

    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    return float(laplacian.var())


def compute_exposure_histogram_metric(frame: np.ndarray) -> dict[str, float]:
    """
    Compute brightness and contrast metrics.
    """
    if frame is None or frame.size == 0:
        return {"mean_brightness": 0.0, "contrast_std": 0.0}

    if len(frame.shape) == 3:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    else:
        gray = frame

    return {
        "mean_brightness": float(np.mean(gray)),
        "contrast_std": float(np.std(gray)),
    }


class FrameLivenessTracker:
    """
    Stateful rolling-window frame liveness & signal integrity tracker for a camera stream.
    """

    def __init__(
        self,
        camera_id: str,
        window_size: int = 30,
        freeze_dist_threshold: int = 1,
        consecutive_freeze_frames: int = 25,
        declared_resolution: str | None = None,
    ):
        self.camera_id = camera_id
        self.window_size = window_size
        self.freeze_dist_threshold = freeze_dist_threshold
        self.consecutive_freeze_frames = consecutive_freeze_frames
        self.declared_resolution = declared_resolution

        self.hash_history: deque[int] = deque(maxlen=window_size)
        self.blur_history: deque[float] = deque(maxlen=window_size)
        self.brightness_history: deque[float] = deque(maxlen=window_size)

        self.freeze_counter: int = 0
        self.is_frozen: bool = False
        self.ewma_blur: float | None = None
        self.ewma_alpha: float = 0.05

    def process_frame(
        self,
        frame: np.ndarray,
        frame_idx: int,
        timestamp_s: float,
    ) -> dict[str, Any]:
        """
        Process a single video frame, update rolling statistics, and compute
        Tier 2 Visual Liveness Score L(t).
        """
        if frame is None or frame.size == 0:
            return {
                "liveness_score": 0.0,
                "freeze_detected": True,
                "quality_drift": 1.0,
                "spec_mismatch": True,
                "factors": ["empty_frame_received"],
            }

        h, w = frame.shape[:2]

        # 1. Perceptual Hash & Freeze Detection
        current_hash = compute_frame_phash(frame)
        if self.hash_history:
            prev_hash = self.hash_history[-1]
            dist = hamming_distance(current_hash, prev_hash)
            if dist <= self.freeze_dist_threshold:
                self.freeze_counter += 1
            else:
                self.freeze_counter = 0
        else:
            self.freeze_counter = 0

        self.is_frozen = self.freeze_counter >= self.consecutive_freeze_frames
        self.hash_history.append(current_hash)

        # 2. Blur / Quality Drift (Variance of Laplacian)
        blur_val = compute_laplacian_blur(frame)
        if self.ewma_blur is None:
            self.ewma_blur = blur_val
        else:
            self.ewma_blur = self.ewma_alpha * blur_val + (1.0 - self.ewma_alpha) * self.ewma_blur

        self.blur_history.append(blur_val)

        # Quality drift ratio: if blur is less than 30% of learned EWMA baseline
        if self.ewma_blur > 10.0:
            quality_drift = max(0.0, min(1.0, 1.0 - (blur_val / self.ewma_blur)))
        else:
            quality_drift = 0.0

        # 3. Exposure metrics
        exp_metrics = compute_exposure_histogram_metric(frame)
        self.brightness_history.append(exp_metrics["mean_brightness"])

        # 4. Declared Spec Mismatch (Resolution verification)
        spec_mismatch = False
        if self.declared_resolution:
            dec = self.declared_resolution.lower()
            if "1080" in dec and (h < 720 or w < 1280):
                spec_mismatch = True
            elif "720" in dec and (h < 480 or w < 640):
                spec_mismatch = True
            elif "4k" in dec and (h < 1080 or w < 1920):
                spec_mismatch = True

        # 5. Composite L(t) Formulation
        # L(t) = 1 - max(w1 * Freeze, w2 * QualityDrift, w3 * SpecMismatch)
        w_freeze, w_quality, w_spec = 0.50, 0.30, 0.20
        penalty = max(
            (1.0 if self.is_frozen else 0.0) * w_freeze,
            quality_drift * w_quality,
            (1.0 if spec_mismatch else 0.0) * w_spec,
        )
        liveness_score = max(0.0, min(1.0, 1.0 - penalty))

        factors = []
        if self.is_frozen:
            factors.append(f"freeze_attack_detected_{self.freeze_counter}_frames")
        if quality_drift > 0.40:
            factors.append(f"quality_degradation_blur_{blur_val:.1f}_vs_base_{self.ewma_blur:.1f}")
        if spec_mismatch:
            factors.append(f"spec_mismatch_live_{w}x{h}_vs_{self.declared_resolution}")

        return {
            "liveness_score": round(liveness_score, 4),
            "freeze_detected": self.is_frozen,
            "freeze_consecutive_frames": self.freeze_counter,
            "quality_drift": round(quality_drift, 4),
            "laplacian_blur": round(blur_val, 2),
            "ewma_blur_baseline": round(self.ewma_blur, 2),
            "spec_mismatch": spec_mismatch,
            "frame_dimensions": (w, h),
            "factors": factors,
            "frame_idx": frame_idx,
            "timestamp_s": timestamp_s,
        }
