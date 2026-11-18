"""Story relevance score using freshness, impact, locality, and source diversity."""

from __future__ import annotations

import datetime
import math
from typing import Any

HIGH_IMPACT = {
    "court_order", "cabinet_change", "election_schedule", "traffic_restriction",
    "landslide", "flood", "earthquake", "legal_case", "monetary_policy",
}


def story_importance(
    articles: list[Any],
    *,
    latest: datetime.datetime | None,
    frame: dict[str, Any],
    topic: str | None,
) -> float:
    now = datetime.datetime.utcnow()
    if latest and latest.tzinfo:
        now = now.replace(tzinfo=latest.tzinfo)
    age_hours = max(0.0, (now - latest).total_seconds() / 3600) if latest else 168.0
    recency = math.exp(-age_hours / 72.0)

    independent = [a for a in articles if not getattr(a, "duplicate_of_id", None)]
    source_ids = {getattr(a, "source_id", None) for a in independent}
    source_ids.discard(None)
    diversity = min(1.0, math.log1p(len(source_ids)) / math.log(6))

    action = frame.get("action_family")
    significance = 1.0 if action in HIGH_IMPACT else 0.70 if action else 0.45
    topic_l = (topic or "").casefold()
    if topic_l in {"politics", "disaster", "business"}:
        significance = min(1.0, significance + 0.12)

    languages = {
        (getattr(a, "language", None) or getattr(a, "detected_language", None) or "").casefold()
        for a in articles
    }
    local = 1.0 if frame.get("locations") or "ne" in languages or "ne-rom" in languages else 0.65 if topic_l == "nepal" else 0.35

    recent_cutoff = now - datetime.timedelta(hours=24)
    recent_sources: set[int | None] = set()
    for article in independent:
        published = getattr(article, "published_at", None)
        if not published:
            continue
        if now.tzinfo and not published.tzinfo:
            published = published.replace(tzinfo=now.tzinfo)
        elif published.tzinfo and not now.tzinfo:
            published = published.replace(tzinfo=None)
        if published >= recent_cutoff:
            recent_sources.add(getattr(article, "source_id", None))
    novelty = min(1.0, len(recent_sources) / 3.0) if recent_sources else 0.15

    score = 100 * (
        0.32 * recency
        + 0.24 * diversity
        + 0.22 * significance
        + 0.14 * local
        + 0.08 * novelty
    )
    return round(score, 1)
