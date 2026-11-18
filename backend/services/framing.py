"""Article-level editorial stance toward government actions (C/N/S)."""

from __future__ import annotations

import logging
import json
import re
from functools import lru_cache
from typing import Any

from config import EVENT_RERANKER_ENABLED, FINETUNED_MODEL_PATH, FRAMING_ENABLED, FRAMING_MIN_CHARS, HF_FRAMING_MODEL, ML_DIR

logger = logging.getLogger(__name__)

DESK_MODEL_PATH = ML_DIR / "artifacts" / "framing-desk" / "model.joblib"
DESK_METRICS_PATH = ML_DIR / "artifacts" / "framing-desk" / "metrics.json"
DESK_MODEL_NAME = "framing-desk-v1"

LABELS = [
    "the publication's own reporting endorses a positive evaluation of government action",
    "the publication's own reporting endorses a negative evaluation of government action",
    "the publication reports government-related facts without a discernible positive or negative editorial position",
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
    r"\u0938\u092b\u0932", r"\u092a\u094d\u0930\u0936\u0902\u0938\u093e", r"\u0909\u092a\u0932\u092c\u094d\u0927\u093f",
    r"\u0915\u0932\u094d\u092f\u093e\u0923", r"\u0938\u0941\u0927\u093e\u0930", r"\u092a\u094d\u0930\u0917\u0924\u093f",
    r"\u0909\u0932\u094d\u0932\u0947\u0916\u0928\u0940\u092f", r"\u0938\u092e\u092f\u092e\u0948",
]
CRITICAL_PATTERNS = [
    r"\bfail", r"\bcorrupt", r"\bmismanag", r"\bcritici", r"\bprotest",
    r"\balleg", r"\bscandal", r"\bcontrovers", r"\bblame", r"\bcondemn",
    r"\baccuse", r"\boutrage", r"\bnegligen", r"\bcrisis", r"\bchaos",
    r"\bdispute", r"\bopposition\b", r"\bstrike\b", r"\birregularit",
    r"\bhid\b", r"\bblocked\b", r"\bleft out\b", r"\bnever reached\b",
    r"\binflated\b", r"\bmissing\b", r"\bwhistleblow", r"\bmarched\b",
    r"\bfee hike\b", r"\bwatchdog\b", r"\bstill has no\b", r"\bmonths late\b",
    r"\u092d\u094d\u0930\u0937\u094d\u091f", r"\u0905\u0938\u092b\u0932", r"\u0906\u0932\u094b\u091a\u0928\u093e",
    r"\u0928\u093f\u0928\u094d\u0926\u093e", r"\u0935\u093f\u0930\u094b\u0927", r"\u092a\u094d\u0930\u0926\u0930\u094d\u0936\u0928",
    r"\u0906\u0930\u094b\u092a", r"\u092c\u0947\u0925\u093f\u0924\u093f", r"\u0932\u093e\u092a\u0930\u092c\u093e\u0939\u0940",
    r"\u0935\u093f\u0935\u093e\u0926", r"\u0938\u0902\u0915\u091f", r"\u0917\u0941\u0928\u093e\u0938\u094b",
]
GOV_ACTORS = [
    r"\bgovernment\b", r"\bcabinet\b", r"\bprime minister\b", r"\bpm\b",
    r"\bminister\b", r"\bparliament\b", r"\boli\b", r"\bdeuba\b",
    r"\bdahal\b", r"\bprachanda\b", r"\bstate\b", r"\bauthority\b",
    r"\u0938\u0930\u0915\u093e\u0930", r"\u092e\u0928\u094d\u0924\u094d\u0930\u093f\u092a\u0930\u093f\u0937\u0926\u094d",
    r"\u092a\u094d\u0930\u0927\u093e\u0928\u092e\u0928\u094d\u0924\u094d\u0930\u0940", r"\u092e\u0928\u094d\u0924\u094d\u0930\u0940",
    r"\u0938\u0902\u0938\u0926", r"\u0913\u0932\u0940", r"\u0926\u0947\u0909\u0935\u093e", r"\u092a\u094d\u0930\u091a\u0923\u094d\u0921",
    r"\u092a\u094d\u0930\u0936\u093e\u0938\u0928", r"\u0905\u0927\u093f\u0915\u093e\u0930\u0940",
]
POSITIVE_NEAR = [r"\bgood\b", r"\bpositive\b", r"\bwelcomed?\b", r"\bpraised?\b", r"\bappreciat", r"\bstrong\b", r"\u0930\u093e\u092e\u094d\u0930\u094b", r"\u0938\u0915\u093e\u0930\u093e\u0924\u094d\u092e\u0915", r"\u0938\u094d\u0935\u093e\u0917\u0924"]
NEGATIVE_NEAR = [r"\bbad\b", r"\bnegative\b", r"\bweak\b", r"\bpoor\b", r"\bangry\b", r"\bunhappy\b", r"\bdissatisf", r"\u0928\u0930\u093e\u092e\u094d\u0930\u094b", r"\u0928\u0915\u093e\u0930\u093e\u0924\u094d\u092e\u0915", r"\u0905\u0938\u0928\u094d\u0924\u0941\u0937\u094d\u091f"]

GOV_ACTOR_PATTERN = (
    r"\bgovernment\b|\bcabinet\b|\bprime minister\b|\bminister\b|\bparliament\b|"
    r"\bgovernment officials?\b|\bstate\b|\bauthorit(?:y|ies)\b|\bministry\b|"
    r"सरकार|मन्त्रिपरिषद्|प्रधानमन्त्री|मन्त्री|संसद|प्रशासन|अधिकारी"
)
DIRECT_CRITICISM = (
    r"\b(?:failed|failure|corrupt|mismanaged|negligent|ineffective|incompetent|"
    r"reckless|irresponsible|poorly handled|violated|breached|abused|repressive)\b|"
    r"भ्रष्ट|असफल|लापरबाही|अप्रभावकारी|दुरुपयोग|उल्लङ्घन|दमनकारी|कुशासन"
)
DIRECT_SUPPORT = (
    r"\b(?:effective|successful|well.?managed|responsible|accountable|improved|"
    r"fair|equitable|competent|effective policy|delivered on its promise)\b|"
    r"प्रभावकारी|सफल|जवाफदेही|सुधारिएको|न्यायोचित|कुशल"
)
ATTRIBUTED = re.compile(
    r"\b(?:said|says|according to|told|claimed|alleged|argued|criticized|criticised|"
    r"praised|accused|warned|urged|complained|called for|denied)\b|"
    r"(?:ले\s*(?:भने|बताए|बताइन्|आरोप लगाए|दाबी गरे|प्रशंसा गरे|आलोचना गरे))",
    re.IGNORECASE,
)
QUOTED = re.compile(r"[\"“](.+?)[\"”]|‘(.+?)’", re.DOTALL)
SENTENCE_SPLIT = re.compile(r"(?<=[.!?।])\s+")
EVENT_RELATION_LABELS = [
    "the same specific news event",
    "a later development in the same event",
    "related but separate events",
    "different events in the same broad topic",
    "unrelated news events",
]
EVENT_RELATION_MAP = {
    EVENT_RELATION_LABELS[0]: "SAME_EVENT",
    EVENT_RELATION_LABELS[1]: "EVENT_UPDATE",
    EVENT_RELATION_LABELS[2]: "DIRECTLY_RELATED_EVENT",
    EVENT_RELATION_LABELS[3]: "SAME_TOPIC_DIFFERENT_EVENT",
    EVENT_RELATION_LABELS[4]: "UNRELATED_EVENT",
}


def _count_hits(text: str, patterns: list[str]) -> int:
    return sum(1 for pattern in patterns if re.search(pattern, text or "", re.IGNORECASE))


@lru_cache(maxsize=1)
def _desk_classifier() -> Any | None:
    if not DESK_MODEL_PATH.exists():
        return None
    try:
        import joblib

        logger.info("Loading bilingual desk framing model %s", DESK_MODEL_PATH)
        return joblib.load(DESK_MODEL_PATH)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Desk framing model unavailable: %s", exc)
        return None


@lru_cache(maxsize=1)
def _classifier() -> Any | None:
    if not FRAMING_ENABLED:
        return None
    model_id = FINETUNED_MODEL_PATH or HF_FRAMING_MODEL
    try:
        from transformers import pipeline

        logger.info("Loading multilingual stance NLI model %s", model_id)
        return pipeline("zero-shot-classification", model=model_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Stance model unavailable: %s", exc)
        return None


def active_model_name() -> str:
    if _desk_classifier() is not None:
        return DESK_MODEL_NAME
    return f"nepal-finetuned:{FINETUNED_MODEL_PATH}" if FINETUNED_MODEL_PATH else HF_FRAMING_MODEL


def desk_metrics() -> dict[str, Any] | None:
    if not DESK_METRICS_PATH.exists():
        return None
    try:
        return json.loads(DESK_METRICS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def rerank_event_relationships(pairs: list[tuple[str, str]]) -> list[dict[str, Any] | None]:
    """Use the shared multilingual NLI cross-encoder on a small English candidate set.

    Nepali pairs stay on multilingual embeddings and explicit event evidence:
    this NLI checkpoint is not fine-tuned on Nepali and should not be used to
    overrule a Devanagari event frame.
    """
    results: list[dict[str, Any] | None] = [None] * len(pairs)
    if not pairs or not EVENT_RERANKER_ENABLED or not FRAMING_ENABLED:
        return results
    selected: list[int] = []
    premises: list[str] = []
    for index, (left, right) in enumerate(pairs):
        if re.search(r"[\u0900-\u097f]", f"{left}{right}"):
            continue
        left = re.sub(r"\s+", " ", left or "")[:700]
        right = re.sub(r"\s+", " ", right or "")[:700]
        if not left or not right:
            continue
        selected.append(index)
        premises.append(f"News report A: {left} News report B: {right}")
    if not premises:
        return results
    classifier = _classifier()
    if classifier is None:
        return results
    try:
        outputs = classifier(
            premises,
            EVENT_RELATION_LABELS,
            multi_label=False,
            hypothesis_template="The reports describe {}.",
        )
        if isinstance(outputs, dict):
            outputs = [outputs]
        for original_index, output in zip(selected, outputs):
            scores = list(zip(output.get("labels", []), output.get("scores", [])))
            scores.sort(key=lambda item: float(item[1]), reverse=True)
            if not scores:
                continue
            label, score = scores[0]
            margin = float(score) - (float(scores[1][1]) if len(scores) > 1 else 0.0)
            if float(score) < 0.46 or margin < 0.04:
                continue
            relation = EVENT_RELATION_MAP.get(label)
            if relation:
                results[original_index] = {
                    "relationship": relation,
                    "confidence": round(float(score), 4),
                    "model": active_model_name(),
                    "method": "english_nli_event_reranker",
                }
    except Exception as exc:  # noqa: BLE001
        logger.warning("Event NLI reranking failed; retaining event-frame decisions: %s", exc)
    return results


def _narrator_text(text: str) -> str:
    """Exclude direct quotations and clearly attributed opinions from fallback evidence."""
    no_quotes = QUOTED.sub(" ", text or "")
    kept: list[str] = []
    for sentence in SENTENCE_SPLIT.split(no_quotes):
        sentence = sentence.strip()
        if not sentence:
            continue
        # Attribution verbs often introduce an allegation or praise from a
        # source. Treat that sentence as source speech, not publication stance.
        if ATTRIBUTED.search(sentence):
            continue
        kept.append(sentence)
    return "\n".join(kept)


def _normalize(scores: dict[str, float]) -> dict[str, float]:
    values = {k: max(0.0, float(v)) for k, v in scores.items()}
    total = sum(values.values())
    if total <= 0:
        return {"critical": 0.0, "neutral": 1.0, "supportive": 0.0}
    return {k: round(v / total, 4) for k, v in values.items()}


def _rule_scores(text: str) -> tuple[dict[str, float], list[str], bool]:
    narrative = _narrator_text(text)
    gov_sentences = [s for s in SENTENCE_SPLIT.split(narrative) if re.search(GOV_ACTOR_PATTERN, s, re.I)]
    if not gov_sentences:
        return {"critical": 0.0, "neutral": 1.0, "supportive": 0.0}, [], False

    critical_evidence: list[str] = []
    supportive_evidence: list[str] = []
    for sentence in gov_sentences:
        if re.search(DIRECT_CRITICISM, sentence, re.I):
            critical_evidence.append(sentence.strip()[:240])
        if re.search(DIRECT_SUPPORT, sentence, re.I):
            supportive_evidence.append(sentence.strip()[:240])

    c = len(critical_evidence)
    s = len(supportive_evidence)
    if c == 0 and s == 0:
        return {"critical": 0.0, "neutral": 1.0, "supportive": 0.0}, [], True
    scores = _normalize({"critical": float(c), "neutral": 0.25, "supportive": float(s)})
    return scores, (critical_evidence + supportive_evidence)[:3], True


def _result(
    scores: dict[str, float],
    *,
    model: str,
    method: str,
    evidence: str,
    uncertainty: str,
) -> dict[str, Any]:
    scores = _normalize(scores)
    label_key = max(scores, key=scores.get)
    return {
        "label": f"government_{label_key}",
        "confidence": round(scores[label_key], 4),
        "scores": scores,
        "model": model,
        "method": method,
        "evidence": evidence,
        "uncertainty": uncertainty,
        "nepal_finetuned": bool(FINETUNED_MODEL_PATH),
    }


def analyze_government_framing(text: str, *, lexical_only: bool = False) -> dict[str, Any]:
    """Classify the publication's own stance, not event sentiment or quoted views."""
    cleaned = (text or "").strip()
    if len(cleaned) < 12:
        return _result(
            {"critical": 0.0, "neutral": 1.0, "supportive": 0.0},
            model="stance-insufficient-v4",
            method="stance-v4-insufficient",
            evidence="Too little article text to infer an editorial stance.",
            uncertainty="high",
        )

    rule_scores, rule_evidence, government_referenced = _rule_scores(cleaned)
    if not government_referenced:
        return _result(
            rule_scores,
            model="gov-stance-rule-v4",
            method="stance-v4-no-government-target",
            evidence="No clear government target appears in the article text.",
            uncertainty="high",
        )

    narrative = _narrator_text(cleaned)
    desk = None if lexical_only else _desk_classifier()
    if desk is not None and len(narrative) >= 12:
        try:
            probabilities = desk.predict_proba([narrative[:6000]])[0]
            model_scores = {"critical": 0.0, "neutral": 0.0, "supportive": 0.0}
            for class_name, score in zip(desk.classes_, probabilities):
                key = str(class_name).removeprefix("government_")
                if key in model_scores:
                    model_scores[key] = float(score)
            blended = _normalize({
                key: 0.75 * model_scores[key] + 0.25 * rule_scores[key]
                for key in model_scores
            })
            top = max(blended, key=blended.get)
            evidence = f"Bilingual desk classifier C:{blended['critical']:.0%} N:{blended['neutral']:.0%} S:{blended['supportive']:.0%}."
            if rule_evidence:
                evidence += " Evidence: " + " | ".join(rule_evidence[:2])
            return _result(
                blended,
                model=DESK_MODEL_NAME,
                method="desk_classifier",
                evidence=evidence,
                uncertainty="low" if blended[top] >= 0.65 else "medium",
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Desk framing failed; using validated fallback: %s", exc)

    # XNLI fine-tuning covers Hindi but not Nepali. Keep Nepali stance calls on
    # the conservative evidence rules until a Nepali stance checkpoint is validated.
    nepali_script = bool(re.search(r"[\u0900-\u097f]", cleaned))
    clf = None if lexical_only or nepali_script else _classifier()
    if clf is not None and len(narrative) >= max(20, FRAMING_MIN_CHARS // 2):
        try:
            output = clf(narrative[:6000], LABELS, multi_label=False)
            nli = {"critical": 0.0, "neutral": 0.0, "supportive": 0.0}
            for label, score in zip(output["labels"], output["scores"]):
                key = LABEL_MAP.get(label)
                if key:
                    nli[key] = float(score)
            nli = _normalize(nli)
            top = max(nli, key=nli.get)
            ordered = sorted(nli.values(), reverse=True)
            margin = ordered[0] - ordered[1]
            # If NLI finds no clear position, use the defined neutral category
            # with explicit uncertainty instead of amplifying a weak label.
            if top != "neutral" and (nli[top] < 0.52 or margin < 0.10):
                nli = {"critical": 0.0, "neutral": 1.0, "supportive": 0.0}
                top = "neutral"
            spans = rule_evidence or [s.strip()[:220] for s in SENTENCE_SPLIT.split(narrative) if s.strip()][:2]
            evidence = f"Multilingual NLI assessment of unquoted, non-attributed reporting."
            if spans:
                evidence += " Evidence: " + " | ".join(spans[:2])
            return _result(
                nli,
                model=active_model_name(),
                method="stance-v4-nli",
                evidence=evidence,
                uncertainty="low" if max(nli.values()) >= 0.68 and margin >= 0.18 else "medium",
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Stance NLI failed; using conservative rules: %s", exc)

    label = max(rule_scores, key=rule_scores.get)
    if rule_evidence:
        evidence = "Unquoted evaluative language in the publication's own reporting: " + " | ".join(rule_evidence[:2])
        uncertainty = "medium"
    else:
        evidence = "No unquoted evaluative stance toward government actions was detected; factual reporting remains neutral."
        uncertainty = "medium"
    return _result(
        rule_scores,
        model="gov-stance-rule-v4",
        method="stance-v4-rule-fallback",
        evidence=evidence,
        uncertainty=uncertainty,
    )


def framing_to_bias_pcts(score_rows: list[dict[str, float]]) -> dict[str, float]:
    """Average per-publication stance probabilities for legacy UI field names."""
    if not score_rows:
        return {
            "bias_left_pct": 0.0,
            "bias_center_pct": 100.0,
            "bias_right_pct": 0.0,
            "gov_critical": 0,
            "gov_neutral": 0,
            "gov_supportive": 0,
        }
    avg = {k: 0.0 for k in ("critical", "neutral", "supportive")}
    hard = {k: 0 for k in avg}
    for row in score_rows:
        for key in avg:
            avg[key] += float(row.get(key, 0.0))
        hard[max(row, key=row.get)] += 1
    n = len(score_rows)
    avg = _normalize({key: value / n for key, value in avg.items()})
    return {
        "bias_left_pct": round(100 * avg["critical"], 1),
        "bias_center_pct": round(100 * avg["neutral"], 1),
        "bias_right_pct": round(100 * avg["supportive"], 1),
        "gov_critical": hard["critical"],
        "gov_neutral": hard["neutral"],
        "gov_supportive": hard["supportive"],
    }


analyze = analyze_government_framing
