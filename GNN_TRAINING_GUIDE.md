# GNN Collusion Detection — Training Guide

This upgrades §5.3 (graph-based Sybil/collusion defense) from a pure
cycle-counting heuristic to a genuinely trained Graph Neural Network, per
`research_work.md` §5.3's own suggestion ("a lightweight GNN... or even a
simpler graph-motif heuristic as a non-deep-learning fallback"). The
heuristic stays — it's a fast, dependency-free pre-filter — this adds the
real thing as a second, learned scoring layer alongside it.

**Nothing here trains automatically.** Training is a deliberate, one-time
step you run yourself. No API endpoint, test, or server startup will ever
train a model as a side effect — an untrained model returns a clear `503`
telling you to run the script below, instead of silently training on
whatever machine happens to receive a request.

## 1. Prerequisites

`torch` is already a dependency of this project (needed by
`video_pipeline`/ultralytics for YOLOv8), so there's nothing new to install.
No GPU needed — this trains on CPU in well under a minute, on purely
synthetic generated graph data (no external dataset, no network access).

## 2. Train the model

From the project root:

```powershell
python scripts/train_gnn_collusion_model.py
```

Optional flags:

```powershell
python scripts/train_gnn_collusion_model.py --num-graphs 400 --epochs 200 --lr 0.01
```

This will:
1. Generate ~240 synthetic graphs (half benign — trees/stars/sparse random
   graphs; half containing an injected 4–7-node collusion ring, sometimes
   embedded inside a larger organic graph so the model can't just learn
   "any edge = collusion").
2. Train a 2-layer Graph Convolutional Network (Kipf & Welling propagation
   rule, implemented directly in PyTorch tensor ops — no `torch_geometric`
   dependency) for node-level binary classification (colluding vs benign).
3. Evaluate on a held-out 20% test split and print precision/recall/F1.
4. Save weights to `backend/ml_weights/gnn_collusion.pt` (gitignored —
   every developer trains their own copy locally).

Expected output (numbers will vary slightly run to run since the synthetic
data generation and training are randomized):

```
Held-out test precision: ~93%
Held-out test recall:    ~96%
Held-out test F1:        ~0.95
```

If your numbers land meaningfully lower than that, something's likely off
in the environment (e.g. a stale/mismatched torch install) rather than the
model itself — the task is easy enough on synthetic data that F1 well above
0.90 is expected.

## 3. Verify it's live

Restart the backend, then:

```powershell
curl http://localhost:8000/api/audit/collusion/gnn
```

With no active corroboration data yet, you'll get `{"camera_scores": {}, "flagged_cameras": [], ...}`.
To see it actually catch something, fire the same collusion-ring attack the
Attack Mode panel uses:

```powershell
curl -X POST http://localhost:8000/api/simulate/collusion-ring
curl http://localhost:8000/api/audit/collusion/gnn
```

You should see the 4 ring cameras (`SIM_RING_A`–`D`) with high
`camera_scores` (close to 1.0) and present in `flagged_cameras`.

## 4. What's actually new here vs. the existing heuristic

| | Heuristic (`detect_collusion_clusters`) | GNN (`detect_collusion_gnn`) |
|---|---|---|
| Signal | `edges >= nodes` (binary: cycle exists or not) | Learned continuous P(colluding) per camera |
| Features used | Edge count only | Degree, local clustering coefficient, component size, edge weight (5 features/node) |
| Catches | Guaranteed cycles (4+ nodes, dense enough) | Also near-cycles and denser-than-innocent topologies the binary rule misses |
| Dependency | None (pure Python) | `torch` (already a project dependency) |
| Needs training | No | Yes — this guide |

Both are exposed via the API (`GET /api/audit/collusion` for the heuristic,
`GET /api/audit/collusion/gnn` for the GNN) and the GNN endpoint's response
includes the heuristic's result too (`heuristic_comparison`), so you can
compare them side by side — useful for a paper/viva ablation ("does the GNN
catch anything the heuristic misses?").

## 5. Files involved

- `backend/services/gnn_collusion_model.py` — model definition, feature
  extraction, synthetic data generation, training, inference.
- `backend/services/collusion_graph_service.py::detect_collusion_gnn()` —
  bridges the real corroboration graph into the model.
- `backend/routes/audit_router.py::get_collusion_gnn_scores()` — the
  `GET /api/audit/collusion/gnn` endpoint.
- `scripts/train_gnn_collusion_model.py` — the training entry point (this guide).
- `backend/tests/test_gnn_collusion_model.py` — tests for the pure math
  (feature extraction, graph normalization, synthetic data generation) and
  for the untrained-model 503 path. Deliberately does **not** test actual
  training — that stays a manual, explicit step.
