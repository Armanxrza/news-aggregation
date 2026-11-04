"""Evaluate government framing classifier on framing_labels.jsonl."""

from __future__ import annotations

import json
import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from config import DATA_DIR, FINETUNED_MODEL_PATH
from services.framing import active_model_name, analyze_government_framing


def load_labels(path: Path) -> list[dict]:
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

    path = DATA_DIR / "framing_labels.jsonl"
    rows = load_labels(path)
    if not rows:
        print(f"No labels found at {path}")
        return

    using_finetuned = bool(FINETUNED_MODEL_PATH)
    print("SajhaNews framing evaluation")
    print(f"  Active model: {active_model_name()}")
    if using_finetuned:
        print(f"  Mode: Nepal-finetuned weights ({FINETUNED_MODEL_PATH})")
    elif active_model_name() == "framing-desk-v1":
        print("  Mode: desk classifier on curated EN/NE labels (not a claim of full-news understanding)")
    else:
        print("  Mode: multilingual pretrained NLI or lexical fallback")

    correct = 0
    skipped = 0
    by_label: dict[str, dict[str, int]] = {}

    for row in rows:
        gold = row.get("label")
        text = row.get("text") or ""
        if not gold or not text:
            skipped += 1
            continue
        pred = analyze_government_framing(text)
        label = pred.get("label")
        by_label.setdefault(gold, {"correct": 0, "total": 0})
        by_label[gold]["total"] += 1
        if label == gold:
            correct += 1
            by_label[gold]["correct"] += 1

    evaluated = sum(v["total"] for v in by_label.values())
    accuracy = correct / evaluated if evaluated else 0.0
    print(f"  Evaluated: {evaluated} (skipped {skipped})")
    print(f"  Accuracy:  {accuracy:.3f}")
    for gold, stats in sorted(by_label.items()):
        acc = stats["correct"] / stats["total"] if stats["total"] else 0.0
        print(f"    {gold}: {acc:.3f} ({stats['correct']}/{stats['total']})")


if __name__ == "__main__":
    main()
