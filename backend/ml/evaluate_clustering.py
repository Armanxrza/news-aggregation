"""Evaluate headline-pair clustering against story_pairs.jsonl."""

from __future__ import annotations

import json
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from config import CLUSTER_SIMILARITY_THRESHOLD, DATA_DIR
from services.embedding import cosine, embed_text


def load_pairs(path: Path) -> list[dict]:
    rows: list[dict] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    path = DATA_DIR / "story_pairs.jsonl"
    pairs = load_pairs(path)
    if not pairs:
        print(f"No pairs found at {path}")
        return

    threshold = CLUSTER_SIMILARITY_THRESHOLD
    tp = fp = tn = fn = 0

    print("SajhaNews clustering evaluation")
    print(f"  Pairs: {len(pairs)}")
    print(f"  Similarity threshold: {threshold}")

    for row in pairs:
        left = row.get("left") or row.get("left_text") or ""
        right = row.get("right") or row.get("right_text") or ""
        gold = bool(row.get("same_event"))
        sim = cosine(embed_text(left), embed_text(right))
        pred = sim >= threshold
        if pred and gold:
            tp += 1
        elif pred and not gold:
            fp += 1
        elif not pred and gold:
            fn += 1
        else:
            tn += 1

    total = tp + fp + tn + fn
    accuracy = (tp + tn) / total if total else 0.0
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0

    print(f"  Accuracy:  {accuracy:.3f}")
    print(f"  Precision: {precision:.3f}")
    print(f"  Recall:    {recall:.3f}")
    print(f"  F1:        {f1:.3f}")
    print(f"  Confusion: TP={tp} FP={fp} TN={tn} FN={fn}")


if __name__ == "__main__":
    main()
