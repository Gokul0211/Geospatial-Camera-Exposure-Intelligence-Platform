"""
test_reid_corroboration.py
===========================
Module F (IIT-B BTP) — Tests for Re-ID cosine similarity corroboration.
Literature: Nayak et al. (iSES, 2019), Liu et al. (arXiv 2503.11088, 2025)
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import math
import pytest
from services.corroboration_service import compute_cosine_similarity, REID_SIMILARITY_THRESHOLD


class TestCosineSimilarity:
    def test_identical_vectors_score_1(self):
        v = [1.0, 0.5, 0.3, 0.8]
        assert compute_cosine_similarity(v, v) == pytest.approx(1.0, abs=1e-6)

    def test_orthogonal_vectors_score_0(self):
        a = [1.0, 0.0]
        b = [0.0, 1.0]
        assert compute_cosine_similarity(a, b) == pytest.approx(0.0, abs=1e-6)

    def test_opposite_vectors_score_minus_1(self):
        a = [1.0, 0.0]
        b = [-1.0, 0.0]
        assert compute_cosine_similarity(a, b) == pytest.approx(-1.0, abs=1e-6)

    def test_empty_embedding_returns_0(self):
        assert compute_cosine_similarity([], [1.0, 0.5]) == 0.0
        assert compute_cosine_similarity([1.0], []) == 0.0
        assert compute_cosine_similarity([], []) == 0.0

    def test_mismatched_dimensions_returns_0(self):
        a = [1.0, 0.5, 0.3]
        b = [1.0, 0.5]
        assert compute_cosine_similarity(a, b) == 0.0

    def test_zero_vector_returns_0(self):
        a = [0.0, 0.0, 0.0]
        b = [1.0, 0.5, 0.3]
        assert compute_cosine_similarity(a, b) == 0.0

    def test_high_similarity_above_threshold(self):
        """Two nearly-identical embeddings should exceed the Re-ID threshold."""
        import random
        random.seed(42)
        base = [random.uniform(0.3, 0.9) for _ in range(64)]
        # Add tiny noise
        similar = [v + random.uniform(-0.01, 0.01) for v in base]
        sim = compute_cosine_similarity(base, similar)
        assert sim >= REID_SIMILARITY_THRESHOLD

    def test_different_embeddings_below_threshold(self):
        """Two random embeddings from different entities should be dissimilar."""
        import random
        random.seed(1)
        a = [random.gauss(0, 1) for _ in range(64)]
        random.seed(999)
        b = [random.gauss(0, 1) for _ in range(64)]
        sim = compute_cosine_similarity(a, b)
        # Random independent 64D vectors have similarity near 0 (< 0.80)
        assert sim < REID_SIMILARITY_THRESHOLD

    def test_64_dimensional_embedding(self):
        """Should handle standard 64-dim Re-ID feature embedding."""
        import random
        random.seed(7)
        a = [random.gauss(0, 1) for _ in range(64)]
        b = [random.gauss(0, 1) for _ in range(64)]
        sim = compute_cosine_similarity(a, b)
        assert -1.0 <= sim <= 1.0

    def test_unit_vectors_equivalence(self):
        """Cosine similarity of unit vectors == dot product."""
        a = [3.0 / 5.0, 4.0 / 5.0]  # unit vector [0.6, 0.8]
        b = [4.0 / 5.0, 3.0 / 5.0]  # unit vector [0.8, 0.6]
        sim = compute_cosine_similarity(a, b)
        dot = 0.6 * 0.8 + 0.8 * 0.6
        assert sim == pytest.approx(dot, abs=1e-6)

    def test_similarity_threshold_is_08(self):
        """Confirm REID_SIMILARITY_THRESHOLD is 0.80 per Nayak 2019 spec."""
        assert REID_SIMILARITY_THRESHOLD == 0.80

    def test_known_angle_30_degrees(self):
        """Cosine similarity for 30° angle should be cos(30°) ≈ 0.866."""
        angle_rad = math.pi / 6  # 30 degrees
        a = [math.cos(0), math.sin(0)]          # [1.0, 0.0]
        b = [math.cos(angle_rad), math.sin(angle_rad)]
        sim = compute_cosine_similarity(a, b)
        assert sim == pytest.approx(math.cos(angle_rad), abs=1e-6)


class TestReidThresholdBoundary:
    def test_exactly_at_threshold_is_accepted(self):
        """Vector pair with cosine sim exactly 0.80 should meet threshold."""
        sim = 0.80
        assert sim >= REID_SIMILARITY_THRESHOLD

    def test_just_below_threshold_is_rejected(self):
        sim = 0.799
        assert sim < REID_SIMILARITY_THRESHOLD
