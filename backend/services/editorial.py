"""Evidence-linked emotion and headline framing signals, separate from stance."""

from __future__ import annotations

import re
import unicodedata
from typing import Any

EMOTION_PATTERNS: dict[str, tuple[str, ...]] = {
    "anger": (r"\b(?:angry|anger|furious|outraged|rage|resentment)\b", "आक्रोश", "रिस", "आक्रोशित"),
    "fear": (r"\b(?:fear|afraid|terror|panic|dread|threatened)\b", "डर", "भय", "त्रास"),
    "sadness": (r"\b(?:sad|grief|mourning|sorrow|heartbroken|tragic)\b", "दुःख", "शोक", "पीडा"),
    "hope": (r"\b(?:hope|hopeful|aspire|aspiration|looking forward)\b", "आशा", "आशावादी", "अपेक्षा"),
    "joy": (r"\b(?:joy|joyful|delighted|celebrat(?:e|ion)|happy)\b", "खुसी", "आनन्द", "उत्सव"),
    "concern": (r"\b(?:concern|concerned|worry|worried|anxious|alarm)\b", "चिन्ता", "चिन्तित", "सरोकार"),
    "urgency": (r"\b(?:urgent|urgency|immediate|emergency|critical deadline)\b", "तत्काल", "आपत्कालीन", "जरुरी"),
    "optimism": (r"\b(?:optimistic|optimism|promising|confidence|confident)\b", "सकारात्मक", "विश्वस्त", "उत्साहजनक"),
}

SENSATIONAL_WORDS = (
    r"\b(?:shocking|stunning|explosive|unbelievable|bombshell|horrific|devastating|jaw.?dropping)\b",
    "सनसनीपूर्ण", "चम्काउने", "अविश्वसनीय",
)
ATTRIBUTION = re.compile(
    r"\b(?:said|says|according to|told|wrote|claimed|warned|urged|complained|called)\b|"
    r"(?:ले\s*(?:भने|बताए|बताइन्|चेतावनी दिए|आरोप लगाए))",
    re.IGNORECASE,
)
DIRECT_QUOTE = re.compile(r"[\"“](.+?)[\"”]|‘(.+?)’", re.DOTALL)


def _normalize(text: str) -> str:
    return unicodedata.normalize("NFKC", text or "").casefold()


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?।])\s+", text or "") if s.strip()]


def analyze_editorial_context(
    headline: str,
    content: str,
    *,
    entities: list[dict[str, Any]] | None = None,
    source_name: str | None = None,
) -> dict[str, Any]:
    """Extract quoted/source emotion cues and cautious editorial tone indicators.

    This is a transparent multilingual signal pass. It never feeds the C/N/S
    stance classifier or story identity matcher.
    """
    headline = headline or ""
    body = content or ""
    text = f"{headline}. {body}"
    entity_names = [str(e.get("name")) for e in (entities or []) if e.get("name")]
    emotions: list[dict[str, Any]] = []
    for sentence in _sentences(text):
        normalized = _normalize(sentence)
        quote_ranges = [m.span() for m in DIRECT_QUOTE.finditer(sentence)]
        for emotion, patterns in EMOTION_PATTERNS.items():
            match = next((re.search(p, normalized, re.IGNORECASE) for p in patterns if re.search(p, normalized, re.IGNORECASE)), None)
            if not match:
                continue
            is_quoted = any(start <= match.start() < end for start, end in quote_ranges)
            attributed = bool(ATTRIBUTION.search(sentence)) or is_quoted
            speaker = "journalist narration"
            if attributed:
                if source_name and source_name.casefold() in sentence.casefold():
                    speaker = source_name
                else:
                    named = next((name for name in entity_names if name.casefold() in sentence.casefold()), None)
                    speaker = named or "attributed source (not identified)"
            target_match = re.search(
                r"\b(?:at|toward|against|about|over)\s+([^,.;:!?]{2,70})",
                sentence,
                re.IGNORECASE,
            )
            target = target_match.group(1).strip() if target_match else None
            emotions.append({
                "emotion": emotion,
                "speaker": speaker,
                "target": target,
                "evidence": sentence[:240],
                "attributed": attributed,
                "confidence": "low" if attributed else "medium",
            })

    headline_norm = _normalize(headline)
    sensational = [p for p in SENSATIONAL_WORDS if re.search(p, headline_norm, re.IGNORECASE)]
    punctuation = headline.count("!") + headline.count("?")
    sensationalism = "possible" if sensational or punctuation >= 2 else "not_detected"
    emotion_names = {row["emotion"] for row in emotions}
    if not emotion_names:
        tone = "no_clear_emotion_cue"
    elif len(emotion_names) > 1:
        tone = "mixed_emotion_cues"
    else:
        tone = f"{next(iter(emotion_names))}_cue"
    return {
        "version": "editorial-signals-v1",
        "emotions": emotions[:12],
        "overall_tone": tone,
        "sensationalism_signal": sensationalism,
        "sensational_words": sensational,
        "method": "attributed_multilingual_lexical_signals",
        "notice": "Signals identify wording and attribution cues; they are not verified psychological states or editorial intent.",
    }
