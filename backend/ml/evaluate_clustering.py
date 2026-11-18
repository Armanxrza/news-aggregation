"""Evaluate event matching and cluster quality on curated bilingual fixtures."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from config import DATA_DIR
from services.embedding import cosine, embed_text, model_id
from services.event_intelligence import classify_event_relationship, extract_event_frame
from services.nepal import classify_topics, extract_entities

MERGE_RELATIONSHIPS = {"SAME_EVENT", "EVENT_UPDATE"}
FALLBACK_MODEL = "local-hash-tfidf-fallback-v2"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def compare(
    left_text: str,
    right_text: str,
    *,
    left_time: datetime | None = None,
    right_time: datetime | None = None,
) -> dict[str, Any]:
    active_model = model_id()
    model_available = active_model != FALLBACK_MODEL
    left_topics = classify_topics(left_text)
    right_topics = classify_topics(right_text)
    left_frame = extract_event_frame(left_text, entities=extract_entities(left_text), topics=left_topics)
    right_frame = extract_event_frame(right_text, entities=extract_entities(right_text), topics=right_topics)
    similarity = None
    if model_available:
        similarity = cosine(embed_text(left_text, role="query"), embed_text(right_text, role="passage"))
    return classify_event_relationship(
        left_frame,
        right_frame,
        semantic_similarity=similarity,
        semantic_model_available=model_available,
        left_time=left_time,
        right_time=right_time,
        left_text=left_text,
        right_text=right_text,
    )


def pair_metrics(rows: list[tuple[bool, bool]]) -> dict[str, float | int]:
    tp = sum(1 for gold, pred in rows if gold and pred)
    fp = sum(1 for gold, pred in rows if not gold and pred)
    tn = sum(1 for gold, pred in rows if not gold and not pred)
    fn = sum(1 for gold, pred in rows if gold and not pred)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "pairs": len(rows),
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "false_merge_rate": fp / (fp + tn) if fp + tn else 0.0,
        "false_split_rate": fn / (fn + tp) if fn + tp else 0.0,
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
    }


def _components(size: int, positive_edges: list[tuple[int, int]]) -> list[int]:
    parent = list(range(size))

    def find(value: int) -> int:
        while parent[value] != value:
            parent[value] = parent[parent[value]]
            value = parent[value]
        return value

    for left, right in positive_edges:
        a, b = find(left), find(right)
        if a != b:
            parent[b] = a
    root_to_label: dict[int, int] = {}
    labels: list[int] = []
    for index in range(size):
        root = find(index)
        if root not in root_to_label:
            root_to_label[root] = len(root_to_label)
        labels.append(root_to_label[root])
    return labels


def _b_cubed(gold: list[str], predicted: list[int]) -> dict[str, float]:
    precision_sum = recall_sum = 0.0
    for index in range(len(gold)):
        gold_members = {i for i, value in enumerate(gold) if value == gold[index]}
        predicted_members = {i for i, value in enumerate(predicted) if value == predicted[index]}
        overlap = len(gold_members & predicted_members)
        precision_sum += overlap / max(1, len(predicted_members))
        recall_sum += overlap / max(1, len(gold_members))
    count = max(1, len(gold))
    precision, recall = precision_sum / count, recall_sum / count
    return {"b_cubed_precision": precision, "b_cubed_recall": recall, "b_cubed_f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0}


def evaluate_clusters(cases: list[dict[str, Any]]) -> dict[str, Any]:
    texts: list[str] = []
    gold: list[str] = []
    times: list[datetime] = []
    base = datetime(2026, 10, 1)
    for cluster in cases:
        for article in cluster.get("articles", []):
            texts.append(article["text"])
            gold.append(cluster["event_id"])
            times.append(base + timedelta(hours=float(article.get("offset_hours", 0))))

    pair_rows: list[tuple[bool, bool]] = []
    edges: list[tuple[int, int]] = []
    relationships: dict[str, int] = {}
    for left in range(len(texts)):
        for right in range(left + 1, len(texts)):
            result = compare(texts[left], texts[right], left_time=times[left], right_time=times[right])
            relation = result["relationship"]
            relationships[relation] = relationships.get(relation, 0) + 1
            predicted_same = relation in MERGE_RELATIONSHIPS
            pair_rows.append((gold[left] == gold[right], predicted_same))
            if predicted_same:
                edges.append((left, right))

    predicted_labels = _components(len(texts), edges)
    quality: dict[str, Any] = {"pairwise": pair_metrics(pair_rows), "relationship_counts": relationships}
    quality.update(_b_cubed(gold, predicted_labels))
    try:
        from sklearn.metrics import adjusted_rand_score

        quality["adjusted_rand_index"] = float(adjusted_rand_score(gold, predicted_labels))
    except Exception:  # noqa: BLE001
        quality["adjusted_rand_index"] = None
    return quality


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    pairs_path = DATA_DIR / "story_pairs.jsonl"
    pairs = load_jsonl(pairs_path)
    observations: list[tuple[bool, bool]] = []
    mismatches: list[tuple[dict[str, Any], str]] = []
    for row in pairs:
        left = row.get("left") or row.get("left_text") or ""
        right = row.get("right") or row.get("right_text") or ""
        result = compare(left, right)
        predicted_same = result["relationship"] in MERGE_RELATIONSHIPS
        gold_same = bool(row.get("same_event"))
        observations.append((gold_same, predicted_same))
        expected_relation = row.get("relationship")
        if predicted_same != gold_same or (expected_relation and result["relationship"] != expected_relation):
            mismatches.append((row, result["relationship"]))

    print("Sajha event identity evaluation")
    print(f"  Embedding model: {model_id()}")
    print("  Pairwise metrics:", json.dumps(pair_metrics(observations), ensure_ascii=False))
    print(f"  Relationship expectation mismatches: {len(mismatches)} / {len(pairs)}")
    for row, actual in mismatches[:12]:
        print(f"  - expected={row.get('relationship', row.get('same_event'))}, actual={actual}: {row.get('left')}  ||  {row.get('right')}")

    clusters = load_jsonl(DATA_DIR / "event_clusters.jsonl")
    if clusters:
        print("  Cluster quality:", json.dumps(evaluate_clusters(clusters), ensure_ascii=False))


if __name__ == "__main__":
    main()
