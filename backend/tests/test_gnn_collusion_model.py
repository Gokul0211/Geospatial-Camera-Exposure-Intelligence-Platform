"""
test_gnn_collusion_model.py
=============================
Tests for the §5.3 GNN collusion model — deliberately scoped to pure math
and data-generation functions only. Actually TRAINING a model (even the
~20-second synthetic-data training run) is treated as an explicit, opt-in
action a developer runs on their own machine (`python
scripts/train_gnn_collusion_model.py`, see GNN_TRAINING_GUIDE.md) — not
something the automated test suite should ever trigger. These tests confirm
the untrained state fails loudly and correctly instead.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
import torch

from services.gnn_collusion_model import (
    CollusionGCN,
    compute_node_features,
    _normalized_adjacency,
    generate_synthetic_training_graphs,
    _make_ring,
    _make_star,
    NUM_FEATURES,
)


class TestNodeFeatures:
    def test_ring_nodes_have_uniform_degree(self):
        adj = _make_ring(5)
        features = compute_node_features(adj)
        assert features.shape == (5, NUM_FEATURES)
        # Every node in a ring has exactly 2 neighbors -> identical normalized degree
        assert torch.allclose(features[:, 0], features[0, 0] * torch.ones(5))

    def test_star_hub_has_highest_degree(self):
        adj = _make_star(6)
        features = compute_node_features(adj)
        # Node 0 is the hub, connected to all 5 others -> max degree
        assert features[0, 0] == 1.0
        assert (features[1:, 0] < features[0, 0]).all()

    def test_isolated_node_has_zero_features_except_component_size(self):
        adj = torch.zeros((3, 3))
        features = compute_node_features(adj)
        # No edges anywhere -> degree/weight/clustering all zero, but each node
        # is its own component of size 1 (normalized 1/3)
        assert torch.allclose(features[:, 0], torch.zeros(3))
        assert torch.allclose(features[:, 1], torch.zeros(3))
        assert torch.allclose(features[:, 4], torch.full((3,), 1 / 3))

    def test_ring_has_zero_clustering_coefficient(self):
        """A ring has no triangles — clustering coefficient must be 0 for every node."""
        adj = _make_ring(6)
        features = compute_node_features(adj)
        assert torch.allclose(features[:, 3], torch.zeros(6))

    def test_triangle_has_full_clustering_coefficient(self):
        """3 mutually-connected nodes: every neighbor pair IS connected -> coefficient 1.0."""
        adj = torch.tensor([[0., 1., 1.], [1., 0., 1.], [1., 1., 0.]])
        features = compute_node_features(adj)
        assert torch.allclose(features[:, 3], torch.ones(3))


class TestNormalizedAdjacency:
    def test_output_is_symmetric(self):
        adj = _make_ring(5)
        norm = _normalized_adjacency(adj)
        assert torch.allclose(norm, norm.T, atol=1e-6)

    def test_self_loops_included(self):
        """A_hat = A + I -- every node should have nonzero self-weight after normalization."""
        adj = _make_ring(4)
        norm = _normalized_adjacency(adj)
        assert (norm.diagonal() > 0).all()

    def test_isolated_node_self_loop_only(self):
        adj = torch.zeros((2, 2))
        norm = _normalized_adjacency(adj)
        # No edges: each node only has its self-loop, normalized weight = 1/sqrt(1)*1*1/sqrt(1) = 1
        assert torch.allclose(norm, torch.eye(2))


class TestSyntheticGraphGeneration:
    def test_returns_requested_count(self):
        graphs = generate_synthetic_training_graphs(num_graphs=10, seed=1)
        assert len(graphs) == 10

    def test_half_are_labeled_collusive(self):
        graphs = generate_synthetic_training_graphs(num_graphs=20, seed=1)
        collusive = [g for g in graphs if g.labels.sum() > 0]
        # Every even-indexed graph injects a ring (labels.sum() > 0); odd-indexed are benign (all zeros)
        assert len(collusive) == 10

    def test_benign_graphs_have_no_positive_labels(self):
        graphs = generate_synthetic_training_graphs(num_graphs=20, seed=1)
        benign = [g for g in graphs if g.labels.sum() == 0]
        for g in benign:
            assert (g.labels == 0).all()

    def test_collusive_graphs_ring_labels_match_ring_size(self):
        graphs = generate_synthetic_training_graphs(num_graphs=20, seed=1)
        collusive = [g for g in graphs if g.labels.sum() > 0]
        for g in collusive:
            # Labels are 1.0 for a contiguous prefix (the injected ring), 0.0 after
            ring_size = int(g.labels.sum().item())
            assert (g.labels[:ring_size] == 1.0).all()
            assert (g.labels[ring_size:] == 0.0).all()

    def test_deterministic_with_fixed_seed(self):
        g1 = generate_synthetic_training_graphs(num_graphs=5, seed=42)
        g2 = generate_synthetic_training_graphs(num_graphs=5, seed=42)
        for a, b in zip(g1, g2):
            assert torch.equal(a.adjacency, b.adjacency)
            assert torch.equal(a.labels, b.labels)


class TestModelForwardPass:
    """Forward pass on a freshly-initialized (untrained) model — just verifies
    the architecture is wired correctly (shapes, no NaNs), not prediction quality."""

    def test_forward_pass_produces_correct_shape(self):
        model = CollusionGCN()
        adj = _make_ring(6)
        norm_adj = _normalized_adjacency(adj)
        x = compute_node_features(adj)
        model.eval()
        with torch.no_grad():
            logits = model(x, norm_adj)
        assert logits.shape == (6,)
        assert not torch.isnan(logits).any()

    def test_forward_pass_handles_isolated_nodes(self):
        model = CollusionGCN()
        adj = torch.zeros((4, 4))
        norm_adj = _normalized_adjacency(adj)
        x = compute_node_features(adj)
        model.eval()
        with torch.no_grad():
            logits = model(x, norm_adj)
        assert logits.shape == (4,)
        assert not torch.isnan(logits).any()


class TestUntrainedModelFailsLoudly:
    """The core safety property this session's design change guarantees: an
    untrained model NEVER silently auto-trains — it raises a clear, actionable
    error instead. No training happens as a side effect of running this test."""

    def test_load_model_raises_when_weights_missing(self, tmp_path, monkeypatch):
        import services.gnn_collusion_model as gnn_mod

        fake_weights_path = str(tmp_path / "nonexistent_weights.pt")
        monkeypatch.setattr(gnn_mod, "WEIGHTS_PATH", fake_weights_path)
        monkeypatch.setattr(gnn_mod, "_model_cache", None)

        with pytest.raises(gnn_mod.ModelNotTrainedError) as exc_info:
            gnn_mod._load_model()

        assert "train_gnn_collusion_model.py" in str(exc_info.value)


class TestGnnEndpointUntrainedState:
    """Confirms GET /api/audit/collusion/gnn returns a clean 503 (not a 500
    crash, and definitely not a silent training run) when no weights exist."""

    @pytest.mark.asyncio
    async def test_endpoint_returns_503_when_untrained(self):
        import services.gnn_collusion_model as gnn_mod

        # Guard: this test only means what it says if weights genuinely don't
        # exist yet on this machine — skip rather than false-fail if a
        # developer already ran the training script locally.
        if os.path.exists(gnn_mod.WEIGHTS_PATH):
            pytest.skip("GNN weights already trained on this machine — untrained-state test not applicable")

        # detect_collusion_gnn() short-circuits to an empty (never touches the
        # model) result when there's no active corroboration data at all —
        # seed one pair so the code path actually reaches infer_collusion_scores().
        from services.corroboration_service import _record_corroboration_pair, reset_velocity_tracker
        reset_velocity_tracker()
        _record_corroboration_pair("GNN_TEST_CAM_A", "GNN_TEST_CAM_B")

        from fastapi import FastAPI
        from httpx import AsyncClient, ASGITransport
        from routes import audit_router

        app = FastAPI()
        app.include_router(audit_router.router, prefix="/api")

        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                res = await client.get("/api/audit/collusion/gnn")

            assert res.status_code == 503
            assert "train_gnn_collusion_model.py" in res.json()["detail"]
        finally:
            reset_velocity_tracker()
