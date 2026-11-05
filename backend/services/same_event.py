"""Same-event check for headlines.

Hash embeddings treat unrelated Devanagari headlines as near duplicates because
they share script-level character patterns. Coverage grouping uses this check
instead: two headlines are the same event only when their distinctive words
agree. A number that appears on both sides must overlap when both sides cite
figures. Cross-lingual paraphrases with no shared words are not guessed.
"""

from __future__ import annotations

import re

_DEVANAGARI_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")

_SUFFIXES = (
    "हरूको",
    "हरुको",
    "हरूमा",
    "हरुमा",
    "हरूले",
    "हरुले",
    "लाई",
    "बाट",
    "देखि",
    "सम्म",
    "माथि",
    "पछि",
    "हरू",
    "हरु",
    "को",
    "का",
    "की",
    "ले",
    "मा",
    "मै",
)

_STOP = {
    "about",
    "after",
    "also",
    "amid",
    "and",
    "are",
    "been",
    "before",
    "being",
    "but",
    "for",
    "from",
    "had",
    "has",
    "have",
    "her",
    "his",
    "into",
    "its",
    "more",
    "new",
    "not",
    "our",
    "out",
    "over",
    "said",
    "says",
    "than",
    "that",
    "the",
    "their",
    "there",
    "they",
    "this",
    "was",
    "were",
    "what",
    "when",
    "where",
    "which",
    "who",
    "will",
    "with",
    "within",
    "the",
    "र",
    "छ",
    "छन्",
    "गरे",
    "भने",
    "भएको",
    "तथा",
    "पनि",
    "एक",
    "यो",
    "त्यो",
    "लागि",
    "अनुसार",
    "बारे",
    "गर्ने",
    "हुने",
    "लाई",
    "मात्र",
    "आज",
    "भन्दा",
    "सम्म",
    "देखि",
    "नेपाल",
    "नेपालमा",
    "नेपालको",
    "सरकार",
    "सरकारले",
    "मा",
    "को",
    "का",
    "की",
    "ले",
}


def _stem(token: str) -> str:
    if token.isdigit():
        return token
    changed = True
    while changed and len(token) > 4:
        changed = False
        for suffix in _SUFFIXES:
            if token.endswith(suffix) and len(token) - len(suffix) >= 3:
                token = token[: -len(suffix)]
                changed = True
                break
    if len(token) > 5 and token.endswith("s") and not token.endswith("ss"):
        token = token[:-1]
    return token


def stems(text: str) -> set[str]:
    """Distinctive stems. Digits are kept. Function words are dropped."""
    raw = (text or "").translate(_DEVANAGARI_DIGITS).casefold()
    found: set[str] = set()
    for token in re.findall(r"[0-9]+|[a-z]{3,}|[\u0900-\u097f]{2,}", raw):
        stem = _stem(token)
        if not stem or stem in _STOP:
            continue
        if stem.isdigit() or len(stem) >= 3:
            found.add(stem)
    return found


def event_score(left: str, right: str) -> float:
    """1 when the headlines are the same wording, else the share of the shorter stem set."""
    a = " ".join((left or "").split())
    b = " ".join((right or "").split())
    if a and a.casefold() == b.casefold() and len(a) > 8:
        return 1.0
    if not same_event(left, right):
        return 0.0
    ta, tb = stems(left), stems(right)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / min(len(ta), len(tb))


def same_event(left: str, right: str) -> bool:
    """True when two headlines are about the same reported event."""
    a = " ".join((left or "").split())
    b = " ".join((right or "").split())
    if not a or not b:
        return False
    if a.casefold() == b.casefold() and len(a) > 8:
        return True

    ta, tb = stems(a), stems(b)
    if not ta or not tb:
        return False
    shared = ta & tb
    numbers_a = {token for token in ta if token.isdigit()}
    numbers_b = {token for token in tb if token.isdigit()}
    content_shared = {token for token in shared if not token.isdigit()}
    if len(content_shared) < 2:
        return False
    if numbers_a and numbers_b and not (numbers_a & numbers_b) and len(content_shared) < 4:
        return False

    smaller = ta if len(ta) <= len(tb) else tb
    containment = len(shared) / len(smaller)
    jaccard = len(shared) / len(ta | tb)
    if containment >= 0.6:
        return True
    if jaccard >= 0.45:
        return True
    return len(content_shared) >= 4 and containment >= 0.45


def _component_map(headlines: list[str]) -> dict[int, list[int]]:
    parent = list(range(len(headlines)))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    for i in range(len(headlines)):
        for j in range(i + 1, len(headlines)):
            if same_event(headlines[i], headlines[j]):
                ri, rj = find(i), find(j)
                if ri != rj:
                    parent[rj] = ri

    groups: dict[int, list[int]] = {}
    for index in range(len(headlines)):
        groups.setdefault(find(index), []).append(index)
    return groups


def _matches(headline: str, preferred: str | None) -> bool:
    if not preferred:
        return False
    if headline.strip() == preferred.strip():
        return True
    return same_event(headline, preferred)


def focus_coverage(
    articles: list,
    preferred: str | None = None,
    cluster_method: str | None = None,
) -> tuple[list, dict]:
    """Keep the headlines that belong to one event.

    A lexical core of two or more headlines wins, and singletons that do not
    share that event are left out. A cluster with no lexical links is kept
    whole when it was seeded or matched on the title. Clusters whose only
    evidence is the hash embedding keep the headline that matches the story
    title, because that embedding matches script rather than the event.
    """
    headlines = [(getattr(article, "original_headline", None) or "") for article in articles]
    if not articles:
        return [], {
            "omitted": 0,
            "coverage_sufficient": False,
            "headline": preferred or "",
            "bias_note": "Not enough related coverage to show bias.",
            "source_count": 0,
        }

    groups = list(_component_map(headlines).values())
    largest = max(groups, key=lambda group: (len(group), -group[0]))
    if len(largest) >= 2:
        chosen = largest
        if preferred:
            for group in groups:
                if len(group) == len(largest) and any(
                    _matches(headlines[index], preferred) for index in group
                ):
                    chosen = group
                    break
    else:
        trusted = (cluster_method or "") not in {"embedding", "hybrid"}
        if trusted:
            chosen = list(range(len(articles)))
        else:
            chosen = [
                index
                for index, headline in enumerate(headlines)
                if _matches(headline, preferred)
            ]
            if not chosen:
                chosen = [0]

    kept = [articles[index] for index in chosen]
    if preferred and any(_matches(headlines[index], preferred) for index in chosen):
        display = preferred
    else:
        display = min(
            (headlines[index] for index in chosen if headlines[index].strip()),
            key=len,
            default=preferred or "",
        )
    source_ids = {
        getattr(article, "source_id", None)
        for article in kept
        if getattr(article, "source_id", None) is not None
    }
    sufficient = len(source_ids) >= 2
    return kept, {
        "omitted": len(articles) - len(kept),
        "coverage_sufficient": sufficient,
        "headline": display,
        "bias_note": None if sufficient else "Not enough related coverage to show bias.",
        "source_count": len(source_ids),
    }
