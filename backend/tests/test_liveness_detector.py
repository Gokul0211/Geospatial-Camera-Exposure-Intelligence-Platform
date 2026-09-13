"""
test_liveness_detector.py
=========================
Unit tests for video_pipeline/liveness_detector.py.
Verifies:
  1. pHash calculation and hamming distance between identical and perturbed frames.
  2. FrameLivenessTracker freeze detection across consecutive identical frames.
  3. Variance of Laplacian blur tracking and quality degradation flags.
  4. Declared spec mismatch detection.
"""

import numpy as np
import pytest
from video_pipeline.liveness_detector import (
    compute_frame_phash,
    hamming_distance,
    compute_laplacian_blur,
    compute_exposure_histogram_metric,
    FrameLivenessTracker,
)


def test_phash_and_hamming_distance():
    """Verify pHash distance is 0 for identical frames and > 0 for different frames."""
    # Frame 1: gradient pattern
    f1 = np.zeros((240, 320, 3), dtype=np.uint8)
    for y in range(240):
        f1[y, :, 0] = y % 256
        f1[y, :, 1] = (y * 2) % 256

    # Frame 2: identical to Frame 1
    f2 = np.copy(f1)

    # Frame 3: completely different random noise
    np.random.seed(42)
    f3 = np.random.randint(0, 256, (240, 320, 3), dtype=np.uint8)

    h1 = compute_frame_phash(f1)
    h2 = compute_frame_phash(f2)
    h3 = compute_frame_phash(f3)

    assert hamming_distance(h1, h2) == 0
    assert hamming_distance(h1, h3) > 5


def test_frame_liveness_tracker_freeze_detection():
    """Verify tracker identifies a frozen/looped feed after consecutive frozen frames."""
    tracker = FrameLivenessTracker(
        camera_id="CAM_TEST_01",
        window_size=30,
        freeze_dist_threshold=1,
        consecutive_freeze_frames=10,
        declared_resolution="1080p",
    )

    static_frame = np.ones((1080, 1920, 3), dtype=np.uint8) * 128
    # Draw some features for nonzero laplacian
    static_frame[100:300, 100:300] = 255
    static_frame[500:800, 500:800] = 0

    # Feed 15 identical frames
    for i in range(15):
        res = tracker.process_frame(static_frame, frame_idx=i, timestamp_s=i * 0.1)

    # By frame 15 (> 10 consecutive), freeze must be detected
    assert res["freeze_detected"] is True
    assert res["liveness_score"] <= 0.50
    assert any("freeze_attack_detected" in f for f in res["factors"])


def test_frame_liveness_tracker_quality_drift():
    """Verify tracker detects blur degradation."""
    tracker = FrameLivenessTracker(
        camera_id="CAM_TEST_02",
        window_size=30,
        consecutive_freeze_frames=20,
    )

    # Sharp frames with high frequency texture
    np.random.seed(123)
    sharp_frame = np.random.randint(0, 256, (480, 640, 3), dtype=np.uint8)

    # Establish baseline
    for i in range(10):
        tracker.process_frame(sharp_frame, frame_idx=i, timestamp_s=i * 0.1)

    # Now introduce heavily blurred frame (defocus attack or lens occlusion)
    import cv2
    blurred_frame = cv2.GaussianBlur(sharp_frame, (51, 51), 0)
    res_blurred = tracker.process_frame(blurred_frame, frame_idx=11, timestamp_s=1.1)

    assert res_blurred["quality_drift"] > 0.50
    assert res_blurred["liveness_score"] < 1.0


def test_frame_liveness_tracker_spec_mismatch():
    """Verify tracker catches live 480p feed when camera declared 4K/1080p."""
    tracker = FrameLivenessTracker(
        camera_id="CAM_TEST_03",
        declared_resolution="1080p",
    )

    low_res_frame = np.ones((480, 640, 3), dtype=np.uint8) * 100
    res = tracker.process_frame(low_res_frame, frame_idx=0, timestamp_s=0.0)

    assert res["spec_mismatch"] is True
    assert any("spec_mismatch" in f for f in res["factors"])
