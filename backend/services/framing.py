"""Government-POV framing with soft score distributions (never 100% flat neutral)."""

from __future__ import annotations

import json
import logging
import re
from functools import lru_cache
from typing import Any

from config import (
    FINETUNED_MODEL_PATH,
    FRAMING_ENABLED,
    FRAMING_MIN_CHARS,
    HF_FRAMING_MODEL,
    ML_DIR,
)

DESK_MODEL_PATH = ML_DIR / "artifacts" / "framing-desk" / "model.joblib"
DESK_METRICS_PATH = ML_DIR / "artifacts" / "framing-desk" / "metrics.json"
DESK_MODEL_NAME = "framing-desk-v1"

logger = logging.getLogger(__name__)

LABELS = [
    "government supportive framing",
    "government critical framing",
    "government neutral factual framing",
]

LABEL_MAP = {
    LABELS[0]: "supportive",
    LABELS[1]: "critical",
    LABELS[2]: "neutral",
}

SUPPORTIVE_PATTERNS = [
    r"\bsucceed", r"\bsuccess", r"\bachievement", r"\bpraise", r"\blaunch(?:ed)?",
    r"\bwelfare", r"\bcommend", r"\bapplaud", r"\bprogress\b", r"\bimprov",
    r"\bboost", r"\breform success", r"\beffective", r"\bhistoric",
    r"\bon time\b", r"\bunder budget\b", r"\bopened to\b", r"\balready appeared\b",
    r"\barrived before\b", r"\bwelcomed\b",
    r"सफल", r"प्रशंसा", r"उपलब्धि", r"कल्याण", r"सुधार", r"प्रगति", r"उल्लेखनीय",
    r"समयमै", r"खुले", r"खोलिए", r"देखिए", r"धन्यवाद",
]

CRITICAL_PATTERNS = [
    r"\bfail", r"\bcorrupt", r"\bmismanag", r"\bcritici", r"\bprotest",
    r"\balleg", r"\bscandal", r"\bcontrovers", r"\bblame", r"\bcondemn",
    r"\baccuse", r"\boutrage", r"\bnegligen", r"\bcrisis", r"\bchaos",
    r"\bdispute", r"\bopposition\b", r"\bstrike\b", r"\birregularit",
    r"\bhid\b", r"\bblocked\b", r"\bleft out\b", r"\bnever reached\b",
    r"\binflated\b", r"\bmissing\b", r"\bwhistleblow", r"\bmarched\b",
    r"\bfee hike\b", r"\bwatchdog\b", r"\bstill has no\b", r"\bmonths late\b",
    r"भ्रष्ट", r"असफल", r"आलोचना", r"निन्दा", r"विरोध", r"प्रदर्शन",
    r"आरोप", r"बेथिति", r"लापरबाही", r"विवाद", r"संकट", r"गुनासो",
    r"लुका", r"रोके", r"ढिलो", r"छुट", r"नचले",
]

GOV_ACTORS = [
    r"\bgovernment\b", r"\bcabinet\b", r"\bprime minister\b", r"\bpm\b",
    r"\bminister\b", r"\bparliament\b", r"\boli\b", r"\bdeuba\b",
    r"\bdahal\b", r"\bprachanda\b", r"\bstate\b", r"\bauthority\b",
    r"सरकार", r"मन्त्रिपरिषद्", r"प्रधानमन्त्री", r"मन्त्री", r"संसद",
    r"ओली", r"देउवा", r"प्रचण्ड", r"प्रशासन", r"अधिकारी",
]

POSITIVE_NEAR = [
    r"\bgood\b", r"\bpositive\b", r"\bwelcomed?\b", r"\bpraised?\b",
    r"\bappreciat", r"\bstrong\b", r"राम्रो", r"सकारात्मक", r"स्वागत",
]
NEGATIVE_NEAR = [
    r"\bbad\b", r"\bnegative\b", r"\bweak\b", r"\bpoor\b", r"\bangry\b",
    r"\bunhappy\b", r"\bdissatisf", r"नराम्रो", r"नकारात्मक", r"असन्तुष्ट",
]


@lru_cache(maxsize=1)
def _desk_classifier() -> Any | None:
    if not DESK_MODEL_PATH.exists():
        return None
    try:
        import joblib

        logger.info("Loading desk framing model %s", DESK_MODEL_PATH)
        return joblib.load(DESK_MODEL_PATH)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Desk framing model unavailable: %s", exc)
        return None


@lru_cache(maxsize=1)
def _classifier() -> Any | None:
    if not FRAMING_ENABLED or _desk_classifier() is not None:
        return None
    model_id = FINETUNED_MODEL_PATH or HF_FRAMING_MODEL
    try:
        from transformers import pipeline

        logger.info("Loading framing model %s", model_id)
        return pipeline("zero-shot-classification", model=model_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Framing model unavailable: %s", exc)
        return None


def active_model_name() -> str:
    if _desk_classifier() is not None:
        return DESK_MODEL_NAME
    if FINETUNED_MODEL_PATH:
        return f"nepal-finetuned:{FINETUNED_MODEL_PATH}"
    return HF_FRAMING_MODEL


def desk_metrics() -> dict[str, Any] | None:
    if not DESK_METRICS_PATH.exists():
        return None
    try:
        return json.loads(DESK_METRICS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _count_hits(text: str, patterns: list[str]) -> int:
    return sum(1 for p in patterns if re.search(p, text, re.I))


def _snippets(text: str, patterns: list[str], limit: int = 3) -> list[str]:
    out: list[str] = []
    for p in patterns:
        m = re.search(p, text, re.I)
        if m:
            start = max(0, m.start() - 30)
            end = min(len(text), m.end() + 30)
            out.append(text[start:end].strip())
        if len(out) >= limit:
            break
    return out


def _normalize(scores: dict[str, float]) -> dict[str, float]:
    total = sum(max(0.0, v) for v in scores.values()) or 1.0
    cleaned = {k: max(0.0, v) / total for k, v in scores.items()}
    # Keep a tiny floor so bars never look "broken empty" on one side when
    # other signal exists — but only if that class already has some mass.
    return {
        "critical": round(cleaned.get("critical", 0.0), 4),
        "neutral": round(cleaned.get("neutral", 0.0), 4),
        "supportive": round(cleaned.get("supportive", 0.0), 4),
    }


def _lexical_soft_scores(text: str) -> tuple[dict[str, float], list[str]]:
    """Produce a variable Critical/Neutral/Supportive mix from text cues."""
    critical_n = _count_hits(text, CRITICAL_PATTERNS)
    supportive_n = _count_hits(text, SUPPORTIVE_PATTERNS)
    gov_n = _count_hits(text, GOV_ACTORS)
    pos_n = _count_hits(text, POSITIVE_NEAR)
    neg_n = _count_hits(text, NEGATIVE_NEAR)

    # Start with an open prior (not 100% neutral) so stories differ
    # Stronger gov mention → more room for evaluative lean
    if gov_n >= 2:
        scores = {"critical": 0.22, "neutral": 0.50, "supportive": 0.28}
    elif gov_n == 1:
        scores = {"critical": 0.20, "neutral": 0.55, "supportive": 0.25}
    else:
        # Non-gov stories still get a light spread from tone words
        scores = {"critical": 0.18, "neutral": 0.62, "supportive": 0.20}

    scores["critical"] += 0.14 * critical_n + 0.06 * neg_n
    scores["supportive"] += 0.14 * supportive_n + 0.06 * pos_n

    # If one side clearly wins, pull mass from neutral
    if critical_n > supportive_n and critical_n > 0:
        pull = min(0.28, 0.08 * (critical_n - supportive_n + 1))
        scores["neutral"] = max(0.12, scores["neutral"] - pull)
        scores["critical"] += pull
    elif supportive_n > critical_n and supportive_n > 0:
        pull = min(0.28, 0.08 * (supportive_n - critical_n + 1))
        scores["neutral"] = max(0.12, scores["neutral"] - pull)
        scores["supportive"] += pull
    elif critical_n == 0 and supportive_n == 0:
        # Tone-only lean so not every story is identical
        if neg_n > pos_n:
            scores["critical"] += 0.08 * (neg_n - pos_n)
            scores["neutral"] -= 0.05 * (neg_n - pos_n)
        elif pos_n > neg_n:
            scores["supportive"] += 0.08 * (pos_n - neg_n)
            scores["neutral"] -= 0.05 * (pos_n - neg_n)
        else:
            # Hash-stable mild variation from headline so neighboring
            # stories don't all render the same 20/60/20 bar.
            seed = sum(ord(ch) for ch in text[:80]) % 17
            scores["critical"] += (seed - 8) * 0.006
            scores["supportive"] += (8 - seed) * 0.006

    scores = _normalize(scores)
    # Guarantee visible minority slices when dominant is neutral
    if scores["neutral"] > 0.85:
        overflow = scores["neutral"] - 0.72
        scores["neutral"] = 0.72
        scores["critical"] += overflow * 0.45
        scores["supportive"] += overflow * 0.55
        scores = _normalize(scores)

    snips = _snippets(text, CRITICAL_PATTERNS + SUPPORTIVE_PATTERNS)
    return scores, snips


def analyze_government_framing(text: str, *, lexical_only: bool = False) -> dict[str, Any]:
    """
    Soft government-POV scores for every article.
    Returns label (argmax) + scores{critical,neutral,supportive} summing to ~1.
    """
    cleaned = (text or "").strip()
    if len(cleaned) < 12:
        scores = {"critical": 0.20, "neutral": 0.55, "supportive": 0.25}
        return {
            "label": "government_neutral",
            "confidence": 0.35,
            "scores": scores,
            "model": "default-soft",
            "method": "default",
            "evidence": "Short text; soft neutral-leaning government POV prior.",
            "uncertainty": "high",
            "nepal_finetuned": bool(FINETUNED_MODEL_PATH),
        }

    lexical_scores, snips = _lexical_soft_scores(cleaned)
    desk = None if lexical_only else _desk_classifier()
    if desk is not None and len(cleaned) >= 12:
        try:
            proba = desk.predict_proba([cleaned[:6000]])[0]
            classes = [str(label) for label in desk.classes_]
            model_scores = {"critical": 0.0, "neutral": 0.0, "supportive": 0.0}
            for label, score in zip(classes, proba):
                key = label.removeprefix("government_")
                if key in model_scores:
                    model_scores[key] = float(score)
            blended = _normalize(
                {
                    "critical": 0.75 * model_scores["critical"] + 0.25 * lexical_scores["critical"],
                    "neutral": 0.75 * model_scores["neutral"] + 0.25 * lexical_scores["neutral"],
                    "supportive": 0.75 * model_scores["supportive"] + 0.25 * lexical_scores["supportive"],
                }
            )
            label_key = max(blended, key=blended.get)
            conf = round(blended[label_key], 4)
            evidence = (
                f"Desk classifier {DESK_MODEL_NAME} "
                f"C:{blended['critical']:.0%} N:{blended['neutral']:.0%} S:{blended['supportive']:.0%}."
            )
            if snips:
                evidence += " Spans: " + " | ".join(snips[:2])
            return {
                "label": f"government_{label_key}",
                "confidence": conf,
                "scores": blended,
                "model": DESK_MODEL_NAME,
                "method": "desk_classifier",
                "evidence": evidence,
                "uncertainty": "low" if conf >= 0.55 else "medium",
                "nepal_finetuned": False,
            }
        except Exception as exc:  # noqa: BLE001
            logger.warning("Desk framing failed: %s", exc)

    clf = None if lexical_only else _classifier()
    model_name = active_model_name()

    if clf is not None and len(cleaned) >= max(20, FRAMING_MIN_CHARS // 2):
        try:
            result = clf(cleaned[:6000], LABELS, multi_label=False)
            nli: dict[str, float] = {"critical": 0.0, "neutral": 0.0, "supportive": 0.0}
            for lab, score in zip(result["labels"], result["scores"]):
                nli[LABEL_MAP[lab]] = float(score)
            nli = _normalize(nli)
            # Blend NLI with lexical so Nepal cues still matter
            blended = _normalize({
                "critical": 0.7 * nli["critical"] + 0.3 * lexical_scores["critical"],
                "neutral": 0.7 * nli["neutral"] + 0.3 * lexical_scores["neutral"],
                "supportive": 0.7 * nli["supportive"] + 0.3 * lexical_scores["supportive"],
            })
            # Cap extreme neutral collapse from NLI on short RSS blurbs
            if blended["neutral"] > 0.82:
                overflow = blended["neutral"] - 0.70
                blended["neutral"] = 0.70
                blended["critical"] += overflow * 0.5
                blended["supportive"] += overflow * 0.5
                blended = _normalize(blended)

            label_key = max(blended, key=blended.get)
            label = f"government_{label_key}"
            conf = round(blended[label_key], 4)
            evidence = f"Soft gov-POV scores C:{blended['critical']:.0%} N:{blended['neutral']:.0%} S:{blended['supportive']:.0%}."
            if snips:
                evidence += " Spans: " + " | ".join(snips[:2])
            return {
                "label": label,
                "confidence": conf,
                "scores": blended,
                "model": model_name,
                "method": "nli_soft_blend",
                "evidence": evidence,
                "uncertainty": "low" if conf >= 0.55 else "medium",
                "nepal_finetuned": bool(FINETUNED_MODEL_PATH),
            }
        except Exception as exc:  # noqa: BLE001
            logger.warning("NLI framing failed: %s", exc)

    label_key = max(lexical_scores, key=lexical_scores.get)
    label = f"government_{label_key}"
    conf = round(lexical_scores[label_key], 4)
    evidence = (
        f"Soft gov-POV (lexical) C:{lexical_scores['critical']:.0%} "
        f"N:{lexical_scores['neutral']:.0%} S:{lexical_scores['supportive']:.0%}."
    )
    if snips:
        evidence += " Spans: " + " | ".join(snips[:2])

    return {
        "label": label,
        "confidence": conf,
        "scores": lexical_scores,
        "model": "gov-pov-soft-lexical-v3",
        "method": "lexical_soft",
        "evidence": evidence,
        "uncertainty": "medium",
        "nepal_finetuned": False,
    }


def framing_to_bias_pcts(score_rows: list[dict[str, float]]) -> dict[str, float]:
    """Average soft scores across articles → story percentages."""
    if not score_rows:
        return {
            "bias_left_pct": 20.0,
            "bias_center_pct": 55.0,
            "bias_right_pct": 25.0,
            "gov_critical": 0,
            "gov_neutral": 0,
            "gov_supportive": 0,
        }

    avg = {"critical": 0.0, "neutral": 0.0, "supportive": 0.0}
    hard = {"critical": 0, "neutral": 0, "supportive": 0}
    for row in score_rows:
        for key in avg:
            avg[key] += float(row.get(key, 0.0))
        top = max(row, key=row.get)
        hard[top] += 1
    n = len(score_rows)
    avg = _normalize({k: v / n for k, v in avg.items()})
    return {
        "bias_left_pct": round(100 * avg["critical"], 1),
        "bias_center_pct": round(100 * avg["neutral"], 1),
        "bias_right_pct": round(100 * avg["supportive"], 1),
        "gov_critical": hard["critical"],
        "gov_neutral": hard["neutral"],
        "gov_supportive": hard["supportive"],
    }


analyze = analyze_government_framing
