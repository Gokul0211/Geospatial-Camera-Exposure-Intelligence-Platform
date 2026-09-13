"""
gnn_collusion_model.py
========================
Module §5.3 upgrade — a genuinely trained Graph Neural Network for
distributed-collusion detection, replacing the "honestly-labeled heuristic"
version of this module with real learned graph representations.

Why this exists: research_work.md §5.3 itself named GNN-based Sybil/fraud
detection as the mature technique this project's velocity-tracker + cycle-
counting heuristic was standing in for ("a lightweight GNN... or even a
simpler graph-motif heuristic as a non-deep-learning fallback"). The
heuristic (collusion_graph_service.py) stays as a fast, dependency-free
pre-filter; this module adds the real thing as a second, learned scoring
layer — the two are complementary, not a replacement of one by the other.

No torch_geometric dependency — implemented as a plain 2-layer Graph
Convolutional Network (Kipf & Welling, ICLR 2017) directly in PyTorch
tensor ops. torch itself is already a hard dependency of this project
(video_pipeline/ultralytics needs it), so this adds zero new install surface.

Node features (per camera, computed from the real corroboration graph):
  0. degree                          — normalized edge count
  1. mean neighbor edge weight       — normalized
  2. max neighbor edge weight        — normalized
  3. local clustering coefficient    — fraction of neighbor pairs that are
                                        themselves connected (triangle density)
  4. component size                  — normalized size of the connected
                                        component this node belongs to

Training data: purely synthetic, generated at train time (see
generate_synthetic_training_graphs) — benign graphs (trees, star topologies,
sparse random graphs — no cycles, or cycles too sparse to matter) labeled 0
for every node, and collusion graphs (one or more injected dense rings/
cliques among a subset of nodes, optionally embedded in a larger organic
graph) labeled 1 for ring/clique members and 0 for the rest.
"""

from __future__ import annotations

import os
import random
from dataclasses import dataclass

import torch
import torch.nn as nn
import torch.nn.functional as F

# NOTE: this is deliberately NOT backend/models/ (that package already holds
# Pydantic request/response schemas — brief.py, device.py, news.py — and reusing
# it for binary ML weight files would be a confusing naming collision).
MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ml_weights")
WEIGHTS_PATH = os.path.join(MODEL_DIR, "gnn_collusion.pt")

NUM_FEATURES = 5
HIDDEN_DIM = 16
SEED = 1337


# ---------------------------------------------------------------------------
# Model definition — plain 2-layer GCN, no torch_geometric
# ---------------------------------------------------------------------------

class CollusionGCN(nn.Module):
    """
    2-layer Graph Convolutional Network for binary node classification
    (colluding vs benign), following Kipf & Welling's propagation rule:
        H^(l+1) = sigma( D^-1/2 * A_hat * D^-1/2 * H^(l) * W^(l) )
    where A_hat = A + I (self-loops) and D is A_hat's degree matrix.
    """

    def __init__(self, in_dim: int = NUM_FEATURES, hidden_dim: int = HIDDEN_DIM):
        super().__init__()
        self.w0 = nn.Linear(in_dim, hidden_dim)
        self.w1 = nn.Linear(hidden_dim, 1)  # binary logit per node

    def forward(self, x: torch.Tensor, norm_adj: torch.Tensor) -> torch.Tensor:
        h = F.relu(self.w0(norm_adj @ x))
        h = F.dropout(h, p=0.3, training=self.training)
        logits = self.w1(norm_adj @ h).squeeze(-1)
        return logits


def _normalized_adjacency(adj: torch.Tensor) -> torch.Tensor:
    """A_hat = A + I, then D^-1/2 A_hat D^-1/2 (symmetric normalization)."""
    n = adj.shape[0]
    a_hat = adj + torch.eye(n)
    deg = a_hat.sum(dim=1)
    deg_inv_sqrt = torch.pow(deg, -0.5)
    deg_inv_sqrt[torch.isinf(deg_inv_sqrt)] = 0.0
    d_mat = torch.diag(deg_inv_sqrt)
    return d_mat @ a_hat @ d_mat


# ---------------------------------------------------------------------------
# Feature extraction — shared by training-graph generation and real inference
# ---------------------------------------------------------------------------

def compute_node_features(adj: torch.Tensor) -> torch.Tensor:
    n = adj.shape[0]
    degree = adj.sum(dim=1)
    max_degree = max(degree.max().item(), 1.0)

    features = torch.zeros((n, NUM_FEATURES))
    features[:, 0] = degree / max_degree

    for i in range(n):
        neighbors = (adj[i] > 0).nonzero(as_tuple=True)[0]
        if len(neighbors) == 0:
            continue
        neighbor_weights = adj[i][neighbors]
        features[i, 1] = (neighbor_weights.mean() / max(adj.max().item(), 1.0)).item()
        features[i, 2] = (neighbor_weights.max() / max(adj.max().item(), 1.0)).item()

        # Local clustering coefficient: fraction of neighbor-pairs that are connected
        if len(neighbors) >= 2:
            possible_pairs = len(neighbors) * (len(neighbors) - 1) / 2
            connected_pairs = 0
            for a_idx in range(len(neighbors)):
                for b_idx in range(a_idx + 1, len(neighbors)):
                    if adj[neighbors[a_idx], neighbors[b_idx]] > 0:
                        connected_pairs += 1
            features[i, 3] = connected_pairs / possible_pairs if possible_pairs > 0 else 0.0

    # Component size (BFS from each node) — normalized by graph size
    visited_global = torch.zeros(n, dtype=torch.bool)
    comp_size = torch.zeros(n)
    for start in range(n):
        if visited_global[start]:
            continue
        stack = [start]
        component = []
        local_visited = {start}
        while stack:
            node = stack.pop()
            component.append(node)
            for neighbor in (adj[node] > 0).nonzero(as_tuple=True)[0].tolist():
                if neighbor not in local_visited:
                    local_visited.add(neighbor)
                    stack.append(neighbor)
        for node in component:
            comp_size[node] = len(component) / n
            visited_global[node] = True

    features[:, 4] = comp_size
    return features


# ---------------------------------------------------------------------------
# Synthetic training data generation
# ---------------------------------------------------------------------------

@dataclass
class SyntheticGraph:
    adjacency: torch.Tensor
    labels: torch.Tensor
    node_ids: list[str]


def _make_ring(n: int, weight: float = 2.0) -> torch.Tensor:
    adj = torch.zeros((n, n))
    for i in range(n):
        j = (i + 1) % n
        adj[i, j] = weight
        adj[j, i] = weight
    return adj


def _make_random_sparse(n: int, edge_prob: float = 0.15) -> torch.Tensor:
    adj = torch.zeros((n, n))
    for i in range(n):
        for j in range(i + 1, n):
            if random.random() < edge_prob:
                w = random.uniform(0.5, 1.5)
                adj[i, j] = w
                adj[j, i] = w
    return adj


def _make_star(n: int) -> torch.Tensor:
    adj = torch.zeros((n, n))
    for i in range(1, n):
        w = random.uniform(0.5, 1.5)
        adj[0, i] = w
        adj[i, 0] = w
    return adj


def generate_synthetic_training_graphs(num_graphs: int = 240, seed: int = SEED) -> list[SyntheticGraph]:
    """
    Roughly half benign (trees/stars/sparse random — no meaningful cycles),
    half containing an injected collusion ring/clique of 4-7 nodes optionally
    embedded inside a larger organic graph, mirroring how a real attacker
    would seed fake adjacency among a subset of otherwise-normal cameras.
    """
    rng = random.Random(seed)
    random.seed(seed)
    graphs: list[SyntheticGraph] = []

    for i in range(num_graphs):
        is_collusive = i % 2 == 0
        total_n = rng.randint(6, 20)

        if not is_collusive:
            shape = rng.choice(["star", "sparse", "tree_like_sparse"])
            if shape == "star":
                adj = _make_star(total_n)
            else:
                adj = _make_random_sparse(total_n, edge_prob=rng.uniform(0.05, 0.12))
            labels = torch.zeros(total_n)
        else:
            ring_n = rng.randint(4, min(7, total_n))
            adj = torch.zeros((total_n, total_n))
            ring_adj = _make_ring(ring_n, weight=rng.uniform(1.5, 3.0))
            adj[:ring_n, :ring_n] = ring_adj
            # Embed the ring inside some organic background noise so the model
            # can't just learn "any edge = collusion" — most training graphs
            # have SOME edges that are perfectly innocent.
            if total_n > ring_n:
                background = _make_random_sparse(total_n - ring_n, edge_prob=0.08)
                adj[ring_n:, ring_n:] = background
                # A couple of organic edges connecting the ring to the rest,
                # like a colluding camera also legitimately neighboring a real one
                for _ in range(rng.randint(0, 2)):
                    a = rng.randint(0, ring_n - 1)
                    b = rng.randint(ring_n, total_n - 1)
                    w = rng.uniform(0.3, 0.8)
                    adj[a, b] = w
                    adj[b, a] = w
            labels = torch.zeros(total_n)
            labels[:ring_n] = 1.0

        node_ids = [f"g{i}_n{j}" for j in range(total_n)]
        graphs.append(SyntheticGraph(adjacency=adj, labels=labels, node_ids=node_ids))

    return graphs


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------

def train_gnn_model(num_graphs: int = 240, epochs: int = 120, lr: float = 0.01, seed: int = SEED) -> dict:
    torch.manual_seed(seed)
    graphs = generate_synthetic_training_graphs(num_graphs=num_graphs, seed=seed)

    split = int(len(graphs) * 0.8)
    train_graphs, test_graphs = graphs[:split], graphs[split:]

    # Precompute per-graph normalized adjacency + node features ONCE — neither
    # changes across epochs (only the model weights do). The original version
    # recomputed both inside the epoch loop, which meant compute_node_features'
    # O(n^2) Python-level clustering-coefficient loop ran num_graphs * epochs
    # times instead of num_graphs times — ~100x more work than necessary and
    # the reason a first training run took ~90s instead of ~1s.
    train_precomputed = [(g, _normalized_adjacency(g.adjacency), compute_node_features(g.adjacency)) for g in train_graphs]
    test_precomputed = [(g, _normalized_adjacency(g.adjacency), compute_node_features(g.adjacency)) for g in test_graphs]

    model = CollusionGCN()
    optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=1e-4)

    for epoch in range(epochs):
        model.train()
        total_loss = 0.0
        for g, norm_adj, x in train_precomputed:
            optimizer.zero_grad()
            logits = model(x, norm_adj)
            loss = F.binary_cross_entropy_with_logits(logits, g.labels)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()

    model.eval()
    tp = fp = tn = fn = 0
    with torch.no_grad():
        for g, norm_adj, x in test_precomputed:
            logits = model(x, norm_adj)
            preds = (torch.sigmoid(logits) >= 0.5).float()
            for pred, label in zip(preds.tolist(), g.labels.tolist()):
                if pred == 1 and label == 1:
                    tp += 1
                elif pred == 1 and label == 0:
                    fp += 1
                elif pred == 0 and label == 0:
                    tn += 1
                else:
                    fn += 1

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    os.makedirs(MODEL_DIR, exist_ok=True)
    torch.save(model.state_dict(), WEIGHTS_PATH)

    return {
        "train_graphs": len(train_graphs),
        "test_graphs": len(test_graphs),
        "test_precision": round(precision, 4),
        "test_recall": round(recall, 4),
        "test_f1": round(f1, 4),
        "confusion_matrix": {"tp": tp, "fp": fp, "tn": tn, "fn": fn},
        "weights_path": WEIGHTS_PATH,
    }


# ---------------------------------------------------------------------------
# Inference — used by collusion_graph_service.py
# ---------------------------------------------------------------------------

_model_cache: CollusionGCN | None = None


class ModelNotTrainedError(RuntimeError):
    pass


def _load_model() -> CollusionGCN:
    """
    Loads cached weights from disk. Deliberately does NOT auto-train on a
    missing weights file — training is a deliberate, explicit action
    (`python scripts/train_gnn_collusion_model.py`, see GNN_TRAINING_GUIDE.md),
    never something an incoming API request should silently trigger.
    """
    global _model_cache
    if _model_cache is not None:
        return _model_cache

    if not os.path.exists(WEIGHTS_PATH):
        raise ModelNotTrainedError(
            f"No trained GNN weights found at {WEIGHTS_PATH}. Run "
            "'python scripts/train_gnn_collusion_model.py' first (see "
            "GNN_TRAINING_GUIDE.md) — takes well under a minute on CPU."
        )

    model = CollusionGCN()
    model.load_state_dict(torch.load(WEIGHTS_PATH, weights_only=True))
    model.eval()
    _model_cache = model
    return model


def infer_collusion_scores(camera_ids: list[str], edge_counts: dict[frozenset, int]) -> dict[str, float]:
    """
    Run the trained GNN over the REAL current corroboration graph.

    Parameters
    ----------
    camera_ids : list[str]
        All camera IDs to score (nodes with zero edges get score 0.0 without
        running the model — an isolated node can't be part of a collusion ring).
    edge_counts : dict[frozenset, int]
        Same shape as corroboration_service.get_pair_edge_counts().

    Returns
    -------
    dict[str, float] : camera_id -> P(colluding) in [0, 1]
    """
    active_nodes = sorted({cam for pair in edge_counts for cam in pair} | set())
    if not active_nodes:
        return {cid: 0.0 for cid in camera_ids}

    idx = {cid: i for i, cid in enumerate(active_nodes)}
    n = len(active_nodes)
    adj = torch.zeros((n, n))
    for pair, count in edge_counts.items():
        a, b = tuple(pair)
        if a in idx and b in idx:
            adj[idx[a], idx[b]] = float(count)
            adj[idx[b], idx[a]] = float(count)

    model = _load_model()
    with torch.no_grad():
        norm_adj = _normalized_adjacency(adj)
        x = compute_node_features(adj)
        logits = model(x, norm_adj)
        probs = torch.sigmoid(logits).tolist()

    scores = {cid: round(probs[idx[cid]], 4) for cid in active_nodes}
    for cid in camera_ids:
        scores.setdefault(cid, 0.0)
    return scores
