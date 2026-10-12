"""Language detection for Nepali (Devanagari), English, and Romanized Nepali."""

from __future__ import annotations

import re

DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")
# Common Romanized Nepali cues (not exhaustive; used as weak evidence only)
ROMANIZED_CUES = {
    "nepal", "kathmandu", "pokhara", "lalitpur", "bhaktapur",
    "sarkar", "pradhanmantri", "mantri", "sanghiya", "pradesh",
    "chunab", "samsad", "adhikari", "dai", "bahini", "hoina",
    "chha", "chhan", "garne", "bhayo", "bhayeko", "lagayat",
    "rajya", "loktantra", "rajniti", "arthatantra",
}


def detect_language(text: str, source_language: str | None = None) -> dict:
    """
    Detect script/language of text.
    Returns label: ne | en | ne-rom | mixed | unknown
    """
    if not text or not text.strip():
        return {
            "language": source_language or "unknown",
            "script": "unknown",
            "confidence": 0.0,
            "method": "empty",
        }

    sample = text[:4000]
    letters = [c for c in sample if c.isalpha() or DEVANAGARI_RE.match(c)]
    if not letters:
        return {
            "language": source_language or "unknown",
            "script": "unknown",
            "confidence": 0.2,
            "method": "no_letters",
        }

    deavanagari = sum(1 for c in letters if DEVANAGARI_RE.match(c))
    latin = len(letters) - deavanagari
    ratio = deavanagari / len(letters)

    if ratio >= 0.55:
        return {
            "language": "ne",
            "script": "devanagari",
            "confidence": round(min(0.99, 0.55 + ratio / 2), 3),
            "method": "script_ratio",
        }

    lowered = sample.casefold()
    tokens = set(re.findall(r"[a-z]+", lowered))
    hits = tokens & ROMANIZED_CUES
    if hits and ratio < 0.15 and len(hits) >= 2:
        return {
            "language": "ne-rom",
            "script": "latin",
            "confidence": round(min(0.85, 0.4 + 0.1 * len(hits)), 3),
            "method": "romanized_cues",
            "evidence": sorted(hits)[:8],
        }

    if ratio > 0.15:
        return {
            "language": "mixed",
            "script": "mixed",
            "confidence": round(0.5 + ratio / 2, 3),
            "method": "script_ratio",
        }

    if source_language in {"ne", "en"}:
        return {
            "language": source_language,
            "script": "latin" if source_language == "en" else "unknown",
            "confidence": 0.55,
            "method": "source_default",
        }

    return {
        "language": "en",
        "script": "latin",
        "confidence": 0.7,
        "method": "latin_default",
    }
