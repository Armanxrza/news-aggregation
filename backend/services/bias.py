"""Left / centre / right political framing (evidence-backed, Nepal-aware)."""

from __future__ import annotations

import logging
import re
from functools import lru_cache
from typing import Any

from config import FINETUNED_MODEL_PATH, FRAMING_ENABLED, FRAMING_MIN_CHARS, HF_FRAMING_MODEL

logger = logging.getLogger(__name__)

BIAS_LABELS = [
    "left-leaning progressive or socialist political framing",
    "centrist neutral factual political framing",
    "right-leaning conservative or nationalist political framing",
]
BIAS_MAP = {
    BIAS_LABELS[0]: "left",
    BIAS_LABELS[1]: "center",
    BIAS_LABELS[2]: "right",
}

LEFT_PATTERNS = [
    r"\bsocialist\b", r"\bcommunist\b", r"\bmaoist\b", r"\bworkers?\b",
    r"\bunion\b", r"\binequality\b", r"\bprogressive\b", r"\blabor\b", r"\blabour\b",
    r"समाजवादी", r"कम्युनिस्ट", r"माओवादी", r"मजदुर", r"श्रमिक", r"वर्ग संघर्ष",
]
RIGHT_PATTERNS = [
    r"\bmonarchy\b", r"\bhindu (?:state|rashtra)\b", r"\bnationalist\b",
    r"\btraditional values\b", r"\banti-secular\b", r"\bking\b", r"\brpp\b",
    r"राजतन्त्र", r"हिन्दू राष्ट्र", r"राप्रपा", r"राष्ट्रवादी", r"संस्कार",
]
CENTER_PATTERNS = [
    r"\baccording to\b", r"\bofficials? said\b", r"\breported\b",
    r"अनुसार", r"जनाएको छ", r"प्रकाशित",
]


@lru_cache(maxsize=1)
def _classifier():
    if not FRAMING_ENABLED:
        return None
    try:
        from transformers import pipeline

        model = FINETUNED_MODEL_PATH or HF_FRAMING_MODEL
        return pipeline("zero-shot-classification", model=model)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Bias NLI unavailable: %s", exc)
        return None


def _hits(text: str, patterns: list[str]) -> list[str]:
    found = []
    for p in patterns:
        m = re.search(p, text or "", re.I)
        if m:
            found.append(m.group(0))
    return found[:6]


def analyze_political_bias(text: str, *, lexical_only: bool = False) -> dict[str, Any]:
    cleaned = (text or "").strip()
    if len(cleaned) < max(20, FRAMING_MIN_CHARS // 2):
        return {
            "label": "center",
            "confidence": 0.35,
            "model": "length-default-center",
            "method": "default",
            "evidence": "Short text; defaulted to centre (neutral) with low confidence.",
            "score": 0.0,
        }

    left_h = _hits(cleaned, LEFT_PATTERNS)
    right_h = _hits(cleaned, RIGHT_PATTERNS)
    center_h = _hits(cleaned, CENTER_PATTERNS)

    clf = None if lexical_only else _classifier()
    if clf is not None:
        try:
            result = clf(cleaned[:5000], BIAS_LABELS, multi_label=False)
            label = BIAS_MAP[result["labels"][0]]
            conf = round(float(result["scores"][0]), 4)
            # Soft lexical veto when NLI conflicts strongly with cues
            if label == "left" and len(right_h) >= 2 and len(left_h) == 0:
                label, conf = "center", min(conf, 0.45)
            elif label == "right" and len(left_h) >= 2 and len(right_h) == 0:
                label, conf = "center", min(conf, 0.45)
            spans = left_h[:2] + right_h[:2] + center_h[:1]
            evidence = f"NLI chose {label} ({conf})."
            if spans:
                evidence += " Cues: " + ", ".join(spans)
            score = {"left": -1.0, "center": 0.0, "right": 1.0}[label] * conf
            return {
                "label": label,
                "confidence": conf,
                "model": FINETUNED_MODEL_PATH or HF_FRAMING_MODEL,
                "method": "zero_shot_nli",
                "evidence": evidence,
                "score": round(score, 4),
            }
        except Exception as exc:  # noqa: BLE001
            logger.warning("Bias NLI failed: %s", exc)

    if len(left_h) > len(right_h) and left_h:
        label, conf = "left", min(0.7, 0.4 + 0.08 * len(left_h))
        cues = left_h
    elif len(right_h) > len(left_h) and right_h:
        label, conf = "right", min(0.7, 0.4 + 0.08 * len(right_h))
        cues = right_h
    else:
        label, conf = "center", 0.5 if center_h or (not left_h and not right_h) else 0.42
        cues = center_h or ["no strong ideological cues"]

    score = {"left": -1.0, "center": 0.0, "right": 1.0}[label] * conf
    return {
        "label": label,
        "confidence": round(conf, 4),
        "model": "nepal-lexical-bias-v1",
        "method": "lexical",
        "evidence": f"Lexical {label} cues: {', '.join(cues[:4])}",
        "score": round(score, 4),
    }


def aggregate_bias_pcts(labels: list[str]) -> dict[str, float | None]:
    counts = {"left": 0, "center": 0, "right": 0}
    for lab in labels:
        if lab in counts:
            counts[lab] += 1
    total = sum(counts.values())
    if total == 0:
        return {"bias_left_pct": None, "bias_center_pct": None, "bias_right_pct": None}
    return {
        "bias_left_pct": round(100 * counts["left"] / total, 1),
        "bias_center_pct": round(100 * counts["center"] / total, 1),
        "bias_right_pct": round(100 * counts["right"] / total, 1),
    }
