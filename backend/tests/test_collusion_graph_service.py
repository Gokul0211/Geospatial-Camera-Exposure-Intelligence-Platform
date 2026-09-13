"""
test_collusion_graph_service.py
=================================
Tests for §5.3 — Graph-Based Collusion/Sybil Defense over the corroboration
network. Verifies that a distributed 4-camera collusion ring is detected even
when every individual pairwise edge stays below the single-pair velocity
threshold (the exact blind spot research_work.md §5.3 calls out).
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.corroboration_service import (
    _record_corroboration_pair,
    reset_velocity_tracker,
    VELOCITY_THRESHOLD,
)
from services.collusion_graph_service import (
    detect_collusion_clusters,
    GRAPH_EDGE_MIN_COUNT,
    MIN_SUSPICIOUS_CLUSTER_SIZE,
)


class TestCollusionGraphDetection:
    def setup_method(self):
        reset_velocity_tracker()

    def teardown_method(self):
        reset_velocity_tracker()

    def test_no_edges_no_clusters(self):
        assert detect_collusion_clusters() == []

    def test_single_hot_pair_below_ring_size_not_flagged(self):
        """Two cameras alone can never form a 4-node ring — not this detector's job."""
        for _ in range(GRAPH_EDGE_MIN_COUNT + 1):
            _record_corroboration_pair("CAM_A", "CAM_B")
        assert detect_collusion_clusters() == []

    def test_four_camera_ring_below_pairwise_threshold_is_detected(self):
        """
        Core thesis of §5.3: A -> B -> C -> D -> A, each edge corroborating
        just GRAPH_EDGE_MIN_COUNT times (well under the single-pair
        VELOCITY_THRESHOLD), forms a cycle the pairwise tracker would never
        flag on its own, but the graph detector should catch as a cluster.
        """
        ring_edges = [("R1", "R2"), ("R2", "R3"), ("R3", "R4"), ("R4", "R1")]
        for cam_a, cam_b in ring_edges:
            for _ in range(GRAPH_EDGE_MIN_COUNT):
                flag = _record_corroboration_pair(cam_a, cam_b)
                # None of these individual edges should trip the pairwise flag
                assert flag.flagged is False
                assert flag.count_in_window < VELOCITY_THRESHOLD

        clusters = detect_collusion_clusters()
        assert len(clusters) == 1
        cluster = clusters[0]
        assert cluster["node_count"] == 4
        assert cluster["edge_count"] >= cluster["node_count"]
        assert cluster["cycle_guaranteed"] is True
        assert set(cluster["camera_ids"]) == {"R1", "R2", "R3", "R4"}

    def test_tree_shaped_cluster_not_flagged(self):
        """
        A star/tree topology (n nodes, n-1 edges) has NO cycle — this is what
        genuinely independent cameras corroborating a shared busy hub would
        look like, and must NOT be flagged (false-positive guard).
        """
        # Star: HUB corroborates with 4 spokes, no edges between spokes — 4 edges, 5 nodes, no cycle
        for spoke in ["S1", "S2", "S3", "S4"]:
            for _ in range(GRAPH_EDGE_MIN_COUNT):
                _record_corroboration_pair("HUB", spoke)

        clusters = detect_collusion_clusters()
        assert clusters == [], "A tree (no cycle) must not be flagged as collusion"

    def test_below_min_cluster_size_not_flagged(self):
        """A 3-node triangle is a cycle but smaller than MIN_SUSPICIOUS_CLUSTER_SIZE."""
        assert MIN_SUSPICIOUS_CLUSTER_SIZE == 4
        triangle_edges = [("T1", "T2"), ("T2", "T3"), ("T3", "T1")]
        for cam_a, cam_b in triangle_edges:
            for _ in range(GRAPH_EDGE_MIN_COUNT):
                _record_corroboration_pair(cam_a, cam_b)
        assert detect_collusion_clusters() == []

    def test_low_count_edges_below_graph_threshold_ignored(self):
        """Edges with count < GRAPH_EDGE_MIN_COUNT don't even enter the graph."""
        ring_edges = [("Z1", "Z2"), ("Z2", "Z3"), ("Z3", "Z4"), ("Z4", "Z1")]
        for cam_a, cam_b in ring_edges:
            _record_corroboration_pair(cam_a, cam_b)  # only once each — below GRAPH_EDGE_MIN_COUNT=2
        assert detect_collusion_clusters() == []
