"""
collusion_graph_service.py
===========================
Module §5.3 (Secondary Contribution) — Graph-Based Collusion/Sybil Defense
over the Camera Corroboration Network.

Literature: GNN-based Sybil/fraud detection is mature technique in
social-network security (SybilLimit, SybilInfer, SybilDefender, modern GNN
variants — arXiv 2409.08631, ACM KDD fraud-detection literature). Porting it
to a camera-adjacency corroboration graph is a domain transfer, not a new
algorithm (research_work.md §5.3) — an honest secondary contribution.

Why the existing velocity tracker isn't enough
-----------------------------------------------
`corroboration_service._velocity_tracker` catches ONE attack shape: the same
two cameras (A, B) corroborating each other more than VELOCITY_THRESHOLD (5)
times in VELOCITY_WINDOW_MINUTES (60). It is structurally blind to a
*distributed* attack: a ring of four or more colluding/spoofed devices
(A -> B -> C -> D -> A) where each individual pairwise edge stays just under
the per-pair threshold, but the cluster as a whole is manufacturing
corroboration in a cycle that would never occur between genuinely independent
cameras.

Approach — lightweight graph-motif heuristic (no ML dependency)
-----------------------------------------------------------------
research_work.md §5.3 explicitly sanctions "a simpler graph-motif /
community-detection heuristic as a non-deep-learning fallback" in place of a
full GNN, given this is a low-node-count graph (tens of cameras, not millions
of social-graph accounts) where a full GNN would be architectural overkill.

1. Build an undirected graph: nodes = cameras, edges = camera pairs whose
   corroboration count in the rolling window is >= GRAPH_EDGE_MIN_COUNT (a
   threshold deliberately LOWER than the pairwise VELOCITY_THRESHOLD, so a
   ring where every edge is "just under" the pairwise cutoff still lights up
   here).
2. Find connected components (plain BFS — the graph is tiny).
3. A component of size >= MIN_SUSPICIOUS_CLUSTER_SIZE whose edge count is
   >= its node count is graph-theoretically guaranteed to contain a cycle
   (a tree on n nodes has exactly n-1 edges; >= n edges means at least one
   cycle exists). Independent, honestly-behaving cameras corroborating a
   genuinely busy real-world intersection do not organically form cycles at
   this density — a cycle here means the corroboration relationships loop
   back on themselves, the fingerprint of coordinated/fabricated adjacency.
"""

from __future__ import annotations

from collections import defaultdict

from services.corroboration_service import get_pair_edge_counts

# Lower than corroboration_service.VELOCITY_THRESHOLD (5) — this is the
# per-edge bar for inclusion in the collusion graph, not a suspicion verdict
# on its own. A pair crossing this alone is not flagged; only a cyclic
# cluster built from such edges is.
GRAPH_EDGE_MIN_COUNT = 2

# A "ring" needs at least this many distinct cameras to be a distributed
# collusion pattern rather than the already-handled single-pair case.
MIN_SUSPICIOUS_CLUSTER_SIZE = 4


def _build_adjacency(edge_counts: dict[frozenset, int]) -> dict[str, set[str]]:
    adjacency: dict[str, set[str]] = defaultdict(set)
    for pair, count in edge_counts.items():
        if count < GRAPH_EDGE_MIN_COUNT:
            continue
        cam_a, cam_b = tuple(pair)
        adjacency[cam_a].add(cam_b)
        adjacency[cam_b].add(cam_a)
    return adjacency


def _connected_components(adjacency: dict[str, set[str]]) -> list[set[str]]:
    seen: set[str] = set()
    components: list[set[str]] = []
    for start in adjacency:
        if start in seen:
            continue
        component: set[str] = set()
        stack = [start]
        while stack:
            node = stack.pop()
            if node in component:
                continue
            component.add(node)
            stack.extend(adjacency[node] - component)
        seen |= component
        components.append(component)
    return components


def detect_collusion_clusters(window_minutes: int | None = None) -> list[dict]:
    """
    Detect distributed collusion rings in the current corroboration graph.

    Returns a list of suspicious clusters, each:
        camera_ids   : list[str]
        node_count   : int
        edge_count   : int
        density      : float — edges / (n*(n-1)/2), in [0, 1]
        cycle_guaranteed : bool — True iff edge_count >= node_count
        risk         : human-readable explanation

    An empty list means no distributed collusion pattern is currently active
    (independent of the single-pair velocity tracker, which is checked
    separately via GET /api/audit/velocity).
    """
    kwargs = {} if window_minutes is None else {"window_minutes": window_minutes}
    edge_counts = get_pair_edge_counts(**kwargs)
    adjacency = _build_adjacency(edge_counts)
    components = _connected_components(adjacency)

    clusters: list[dict] = []
    for component in components:
        n = len(component)
        if n < MIN_SUSPICIOUS_CLUSTER_SIZE:
            continue

        edges_in_component = sum(
            1
            for pair, count in edge_counts.items()
            if count >= GRAPH_EDGE_MIN_COUNT and pair <= component
        )
        cycle_guaranteed = edges_in_component >= n
        if not cycle_guaranteed:
            continue

        max_possible_edges = n * (n - 1) / 2
        density = round(edges_in_component / max_possible_edges, 4) if max_possible_edges > 0 else 0.0

        clusters.append({
            "camera_ids": sorted(component),
            "node_count": n,
            "edge_count": edges_in_component,
            "density": density,
            "cycle_guaranteed": cycle_guaranteed,
            "risk": (
                f"{n} cameras form a corroboration cycle ({edges_in_component} edges) — "
                "each pairwise edge may be individually below the single-pair velocity "
                "threshold, but the cluster as a whole is structurally consistent with "
                "fabricated/collusive adjacency rather than independent corroboration."
            ),
        })

    return clusters


def detect_collusion_gnn(window_minutes: int | None = None) -> dict:
    """
    §5.3 upgrade — score every active camera in the current corroboration
    graph with the trained GNN (services/gnn_collusion_model.py) instead of
    (or alongside) the pure cycle-count heuristic above.

    The GNN sees the same graph the heuristic does, but learns a continuous
    per-camera P(colluding) from real graph structure (degree, local
    clustering, component size, edge weight) rather than a single hardcoded
    "edges >= nodes" cutoff — it can flag a camera as suspicious even in
    topologies the heuristic's binary rule doesn't cover (e.g. a near-cycle
    missing one edge, or a dense-but-technically-acyclic cluster).

    Raises `gnn_collusion_model.ModelNotTrainedError` if the model hasn't
    been trained yet (see GNN_TRAINING_GUIDE.md) — this is intentional: the
    API surfaces that as a clear 503 rather than silently training on an
    incoming request.
    """
    from services.gnn_collusion_model import infer_collusion_scores

    kwargs = {} if window_minutes is None else {"window_minutes": window_minutes}
    edge_counts = get_pair_edge_counts(**kwargs)
    active_cameras = sorted({cam for pair in edge_counts for cam in pair})

    if not active_cameras:
        return {"scores": {}, "flagged_cameras": [], "heuristic_clusters": []}

    scores = infer_collusion_scores(active_cameras, edge_counts)
    flagged = sorted([cam for cam, p in scores.items() if p >= 0.5], key=lambda c: -scores[c])

    return {
        "scores": scores,
        "flagged_cameras": flagged,
        # Included for comparison — same underlying graph, the heuristic's
        # binary "definitely a cycle" answer alongside the GNN's continuous score.
        "heuristic_clusters": detect_collusion_clusters(**kwargs),
    }
