"""Observable framing / loaded-language signals — not ideology scores."""

from __future__ import annotations

import re
from typing import Any

LOADED_POSITIVE = [
    r"\bhero(?:ic)?\b", r"\btriumph\b", r"\blandmark\b", r"\bvisionary\b",
    r"ऐतिहासिक", r"सफल", r"उल्लेखनीय",
]
LOADED_NEGATIVE = [
    r"\bscandal\b", r"\bdisaster\b", r"\bchaos\b", r"\bfiasco\b", r"\bshameful\b",
    r"भ्रष्ट", r"नैराश्यजनक", r"विफल", r"काण्ड",
]
ATTRIBUTION = [
    r"\baccording to\b", r"\bsaid\b", r"\bclaimed\b", r"\bstated\b",
    r"अनुसार", r"भने", r"दाबी",
]


def extract_signals(text: str, entities: list[dict] | None = None) -> dict[str, Any]:
    entities = entities or []
    pos = [m.group(0) for p in LOADED_POSITIVE if (m := re.search(p, text or "", re.I))]
    neg = [m.group(0) for p in LOADED_NEGATIVE if (m := re.search(p, text or "", re.I))]
    attrs = [m.group(0) for p in ATTRIBUTION if (m := re.search(p, text or "", re.I))]

    political_actors = [e for e in entities if e.get("type") in {"party", "people", "institution"}]
    return {
        "loaded_positive": pos[:8],
        "loaded_negative": neg[:8],
        "attribution_markers": attrs[:8],
        "political_actors_mentioned": [e["name"] for e in political_actors[:12]],
        "tone_hint": (
            "critical_lexicon"
            if len(neg) > len(pos)
            else "supportive_lexicon"
            if len(pos) > len(neg)
            else "balanced_or_unclear"
        ),
        "disclaimer": (
            "These are observable lexical signals, not political affiliation or factuality scores."
        ),
    }
