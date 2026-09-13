"""
train_gnn_collusion_model.py
==============================
Trains the §5.3 GNN collusion-detection model and saves weights to
backend/ml_weights/gnn_collusion.pt. Required once before the GNN-backed
endpoint (GET /api/audit/collusion/gnn) will work — see
GNN_TRAINING_GUIDE.md for the full walkthrough. Prints held-out test
precision/recall/F1 on completion — that IS the benchmark; no separate
eval script needed.

Runs entirely on CPU, on purely synthetic generated data (no external
dataset, no network access, no GPU needed). Takes well under a minute.

Usage:
    python scripts/train_gnn_collusion_model.py
    python scripts/train_gnn_collusion_model.py --num-graphs 400 --epochs 200
"""
import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from services.gnn_collusion_model import train_gnn_model, WEIGHTS_PATH


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--num-graphs", type=int, default=240, help="Synthetic training graphs to generate (default: 240)")
    parser.add_argument("--epochs", type=int, default=120, help="Training epochs (default: 120)")
    parser.add_argument("--lr", type=float, default=0.01, help="Learning rate (default: 0.01)")
    args = parser.parse_args()

    print(f"Training GNN collusion model: {args.num_graphs} synthetic graphs, {args.epochs} epochs...")
    result = train_gnn_model(num_graphs=args.num_graphs, epochs=args.epochs, lr=args.lr)

    print("\n" + "=" * 60)
    print("TRAINING COMPLETE")
    print("=" * 60)
    print(f"Train graphs: {result['train_graphs']}  |  Test graphs: {result['test_graphs']}")
    print(f"Held-out test precision: {result['test_precision']:.2%}")
    print(f"Held-out test recall:    {result['test_recall']:.2%}")
    print(f"Held-out test F1:        {result['test_f1']:.4f}")
    cm = result["confusion_matrix"]
    print(f"Confusion matrix: TP={cm['tp']} FP={cm['fp']} TN={cm['tn']} FN={cm['fn']}")
    print(f"\nWeights saved to: {result['weights_path']}")
    print("\nThe GNN-backed endpoints are now live:")
    print("  GET /api/audit/collusion/gnn")
    print("=" * 60)


if __name__ == "__main__":
    main()
