"""Event-frame extraction and conservative multilingual relationship decisions.

The frame keeps original article text elsewhere. It is a compact, explainable
representation for candidate matching, not a claim that rules understand every
Nepali event. Semantic embeddings help rank candidates; only strong event
evidence can authorize an automatic story merge.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime
from typing import Any

from services.nepal import extract_entities

RELATIONSHIPS = {
    "SAME_EVENT",
    "EVENT_UPDATE",
    "DIRECTLY_RELATED_EVENT",
    "SAME_TOPIC_DIFFERENT_EVENT",
    "UNRELATED_EVENT",
    "INSUFFICIENT_EVIDENCE",
}

LOCATION_ALIASES = {
    "Kavre": (r"\bkavre(?:ma|ko|ka)?\b", r"\bkabh?re(?:ma|ko|ka)?\b", r"\bkavrepalanchok\b", r"\bkabhrepalanchok\b", "काभ्रे", "काभ्रेपलाञ्चोक"),
    "Sindhupalchok": (r"\bsindhupalch(?:ok|owk)\b", "सिन्धुपाल्चोक"),
    "Kathmandu": (r"\bkathmandu\b", "काठमाडौँ", "काठमाडौं"),
    "Lalitpur": (r"\blalitpur\b", "ललितपुर"),
    "Bhaktapur": (r"\bbhaktapur\b", "भक्तपुर"),
    "Pokhara": (r"\bpokhara\b", "पोखरा"),
    "Chitwan": (r"\bchitwan\b", "चितवन"),
    "Kaski": (r"\bkaski\b", "कास्की"),
    "Rupandehi": (r"\brupandehi\b", "रुपन्देही", "रुपन्देही"),
    "Morang": (r"\bmorang\b", "मोरङ"),
    "Koshi": (r"\bkoshi\b", "कोशी"),
    "Madhesh": (r"\bmadhesh\b", "मधेश"),
    "Bagmati": (r"\bbagmati\b", "बागमती"),
    "Gandaki": (r"\bgandaki\b", "गण्डकी"),
    "Lumbini": (r"\blumbini\b", "लुम्बिनी"),
    "Karnali": (r"\bkarnali\b", "कर्णाली"),
    "Sudurpashchim": (r"\bsudurpashchim\b", "सुदूरपश्चिम"),
}

ACTION_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("legislative_address", (r"\b(?:address(?:es|ed)?|speak(?:s|spoke)? to)\b.{0,80}\b(?:parliament|assembly)\b|\b(?:parliament|assembly)\b.{0,80}\baddress(?:es|ed)?\b", "\u0938\u092e\u094d\u092c\u094b\u0927\u0928")),
    ("diplomacy_meeting", (r"\bbilateral talks\b", r"(?=.*\u0926\u094d\u0935\u093f\u092a\u0915\u094d\u0937\u0940\u092f \u0935\u093e\u0930\u094d\u0924\u093e)")),
    ("legal_case", (r"\bfiles? (?:a )?(?:corruption )?case\b|\b(?:open|opens|opened) (?:a )?(?:corruption )?case\b",)),
    ("procurement_tender", (r"\b(?:call(?:s|ed)? for bids?|bid(?:s)? invited|tenders? (?:issued|invited|announced)|bid invitation)\b", r"(?=.*\u0920\u0947\u0915\u094d\u0915\u093e)(?=.*\u0906\u0939\u094d\u0935\u093e\u0928)")),
    ("traffic_restriction", (r"\b(?:ban|bar(?:red)?|prohibit(?:ed)?|restrict(?:ed|ion)?|suspend(?:ed)?|curb|halt|rok(?:ka)?|pratibandh)\b", "प्रतिबन्ध", "रोक", "बन्द")),
    ("cabinet_change", (r"\b(?:cabinet reshuffle|minister(?:s)? sworn|appoint(?:ed|ment)?|resign(?:ed|ation)?)\b", "मन्त्रिपरिषद् पुनर्गठन", "नियुक्त", "शपथ", "राजीनामा")),
    ("court_order", (r"\b(?:court|judg(?:e|ment)|verdict|interim order|ruling)\b", "अदालत", "सर्वोच्च", "अन्तरिम आदेश", "फैसला")),
    ("election_schedule", (r"\b(?:election|polls?)\b.{0,50}\b(?:schedule|date|timetable)\b|\b(?:schedule|date|timetable)\b.{0,50}\b(?:election|polls?)\b", "निर्वाचन", "चुनाव", "तालिका", "मतदान")),
    ("political_negotiation", (r"\b(?:seat.?sharing|sharing election seats|coalition talks|alliance talks|negotiat(?:e|ion|ions))\b", "सिट बाँडफाँड", "गठबन्धन वार्ता", "वार्ता")),
    ("diplomacy_meeting", (r"\b(?:bilateral talks|hold talks|held talks|meeting|meet with|visit(?:ed)?)\b", "द्विपक्षीय वार्ता", "भेटवार्ता", "बैठक", "भेटे")),
    ("protest_or_strike", (r"\b(?:protest(?:s|ed)?|rally|demonstrat(?:ion|ors?)|strike|walkout)\b", "प्रदर्शन", "आन्दोलन", "हडताल", "धर्ना")),
    ("landslide", (r"\blandslide(?:s)?\b", "पहिरो")),
    ("flood", (r"\bflood(?:s|ing)?\b", "बाढी")),
    ("earthquake", (r"\bearthquake\b", "भूकम्प")),
    ("fire", (r"\b(?:fire|blaze)\b", "आगलागी")),
    ("road_accident", (r"\b(?:crash|collision|overturn(?:s|ed)?|road accident|bus accident)\b", "दुर्घटना", "ठक्कर")),
    ("monetary_policy", (r"\b(?:policy rate|interest rate|central bank rate)\b", "नीतिगत दर", "ब्याजदर")),
    ("fuel_price", (r"\b(?:fuel|petrol|diesel) prices?\b|\bprice(?:s)? (?:revised|increased|cut|reduced)\b", "इन्धन मूल्य", "पेट्रोलियम पदार्थको मूल्य", "मूल्य समायोजन")),
    ("market_price", (r"\b(?:gold|silver|vegetable|food) prices?\b|\bprices? (?:surge|rise|fall|drop)\b", "सुनको मूल्य", "मूल्य बढ", "मूल्य घट")),
    ("tourism_trend", (r"\b(?:tourist arrivals|tourism arrivals|visitor numbers)\b", "पर्यटक आगमन")),
    ("sports_result", (r"\b(?:beat|defeat|won|lost to|draw against)\b", "पराजित", "हरायो", "जित्यो", "विजयी")),
    ("legal_case", (r"\b(?:files? (?:a )?case|charged|indicted|arrested|fraud case)\b", "मुद्दा दायर", "मुद्दा चलायो", "पक्राउ", "आरोपपत्र")),
    ("official_decision", (r"\b(?:approv(?:e|es|ed|al)|reject(?:s|ed|ion)?|pass(?:es|ed)?|decid(?:e|es|ed|ion)|announc(?:e|es|ed|ement))\b", "निर्णय", "स्वीकृत", "अस्वीकृत", "घोषणा", "पारित")),
)

OBJECT_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("economic_reform_bill", (r"\beconomic reform bill\b", r"\u0906\u0930\u094d\u0925\u093f\u0915 \u0938\u0941\u0927\u093e\u0930 \u0935\u093f\u0927\u0947\u092f\u0915")),
    ("seat_sharing", (r"\bsharing election seats\b",)),
    ("water_project_tender", (r"(?=.*\bwater[ -]supply\b)(?=.*\bprojects?\b)", r"(?=.*\u0916\u093e\u0928\u0947\u092a\u093e\u0928\u0940)(?=.*\u0906\u092f\u094b\u091c\u0928\u093e)")),
    ("rain_triggered_landslide", (r"(?=.*\blandslides?\b)(?=.*\b(?:heavy )?rain(?:fall)?\b)", r"(?=.*\u092a\u0939\u093f\u0930\u094b)(?=.*\u0935\u0930\u094d\u0937\u093e)")),
    ("nepal_oman_cricket", (r"(?=.*\bnepal\b)(?=.*\boman\b)(?=.*\b(?:cricket|game|match)\b)", r"(?=.*\u0928\u0947\u092a\u093e\u0932)(?=.*\u0913\u092e\u093e\u0928)(?=.*\u0916\u0947\u0932)")),
    ("india_nepal_bilateral_talks", (r"(?=.*\bindia\b)(?=.*\bnepal\b)(?=.*\b(?:bilateral|talks|meeting)\b)", r"(?=.*\u092d\u093e\u0930\u0924)(?=.*\u0928\u0947\u092a\u093e\u0932)(?=.*\u0926\u094d\u0935\u093f\u092a\u0915\u094d\u0937\u0940\u092f \u0935\u093e\u0930\u094d\u0924\u093e)")),
    ("tribhuvan_university_fees", (r"(?=.*\btribhuvan university\b)(?=.*\b(?:fee|fees|tuition)\b)", r"(?=.*\u0924\u094d\u0930\u093f\u092d\u0941\u0935\u0928 \u0935\u093f\u0936\u094d\u0935\u0935\u093f\u0926\u094d\u092f\u093e\u0932\u092f)(?=.*\u0936\u0941\u0932\u094d\u0915)")),
    ("tippers", (r"\b(?:tippers?|dump trucks?)\b", "टिपर")),
    ("trucks", (r"\b(?:trucks?|lorries?)\b", "ट्रक", "ट्रकहरू")),
    ("policy_rate", (r"\bpolicy rate\b", "नीतिगत दर")),
    ("citizenship", (r"\bcitizenship\b", "नागरिकता")),
    ("local_elections", (r"\blocal (?:elections?|polls?)\b", "स्थानीय तहको चुनाव", "स्थानीय निर्वाचन")),
    ("seat_sharing", (r"\bseat.?sharing\b", "सिट बाँडफाँड")),
    ("gold", (r"\bgold\b", "सुन")),
    ("fuel", (r"\b(?:fuel|petrol|diesel)\b", "इन्धन", "पेट्रोल", "डिजेल")),
    ("university_fees", (r"\b(?:tuition|university) fees?\b", "विश्वविद्यालय शुल्क", "शुल्क वृद्धि")),
)

EVENT_MARKERS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("tihar", (r"\btihar(?:\s*(?:bhar|ma|ko))?\b", "तिहार")),
    ("dashain", (r"\bdashain\b", "दशैँ", "दशैं")),
    ("dashain_season", (r"\bdashain season\b", "दशैँको समयमा")),
)

RELATED_CUES = re.compile(
    r"\b(?:in response|following|aftermath|reaction to|as a result|rescue teams sent)\b|"
    r"प्रतिक्रिया|लगत्तै|जवाफमा|परिणामस्वरूप",
    re.IGNORECASE,
)


def normalize_for_analysis(text: str) -> str:
    value = unicodedata.normalize("NFKC", text or "").casefold()
    return value.translate(str.maketrans("०१२३४५६७८९", "0123456789"))


def _matches(text: str, aliases: tuple[str, ...]) -> bool:
    for alias in aliases:
        if alias.startswith((r"\b", "(?=")):
            if re.search(alias, text, re.IGNORECASE):
                return True
        elif alias and alias in text:
            return True
    return False


def extract_event_frame(
    text: str,
    *,
    entities: list[dict[str, Any]] | None = None,
    topics: list[str] | None = None,
) -> dict[str, Any]:
    normalized = normalize_for_analysis(text)
    extracted = entities if entities is not None else extract_entities(text or "")
    locations = {
        canonical for canonical, aliases in LOCATION_ALIASES.items()
        if _matches(normalized, aliases)
    }
    for entity in extracted:
        if entity.get("type") == "place" and entity.get("name"):
            locations.add(str(entity["name"]))

    actors = sorted({
        str(entity.get("name")) for entity in extracted
        if entity.get("name") and entity.get("type") in {"person", "party", "institution", "organization"}
    })
    action_family = next(
        (name for name, aliases in ACTION_RULES if _matches(normalized, aliases)),
        None,
    )
    objects = sorted(name for name, aliases in OBJECT_RULES if _matches(normalized, aliases))
    markers = sorted(name for name, aliases in EVENT_MARKERS if _matches(normalized, aliases))
    years = sorted(set(re.findall(r"\b(?:19|20)\d{2}\b", normalized)))
    numbers = sorted(set(re.findall(r"(?<!\w)\d{1,6}(?:\.\d+)?%?(?!\w)", normalized)))
    event_topics = sorted({str(t) for t in (topics or []) if t})
    if not event_topics:
        event_topics = sorted({
            str(entity.get("type")) for entity in extracted
            if entity.get("type") in {"party", "institution", "organization"}
        })

    signature_parts = [
        action_family or "",
        ",".join(sorted(locations)),
        ",".join(actors),
        ",".join(objects),
        ",".join(markers),
        ",".join(years),
    ]
    return {
        "version": "event-frame-v1",
        "action_family": action_family,
        "actors": actors[:12],
        "locations": sorted(locations),
        "objects": objects,
        "event_markers": markers,
        "years": years,
        "numbers": numbers[:8],
        "topics": event_topics[:5],
        "signature": "|".join(signature_parts),
    }


def _set_overlap(left: dict[str, Any], right: dict[str, Any], key: str) -> set[str]:
    return set(left.get(key) or []) & set(right.get(key) or [])


def _hours_between(left: datetime | None, right: datetime | None) -> float | None:
    if not left or not right:
        return None
    if left.tzinfo and not right.tzinfo:
        right = right.replace(tzinfo=left.tzinfo)
    elif right.tzinfo and not left.tzinfo:
        left = left.replace(tzinfo=right.tzinfo)
    return abs((left - right).total_seconds()) / 3600


def classify_event_relationship(
    left: dict[str, Any],
    right: dict[str, Any],
    *,
    semantic_similarity: float | None = None,
    semantic_model_available: bool = False,
    left_time: datetime | None = None,
    right_time: datetime | None = None,
    left_text: str = "",
    right_text: str = "",
) -> dict[str, Any]:
    """Return a typed relationship, confidence, and human-readable evidence."""
    if not left or not right or (not left.get("action_family") and not left.get("actors") and not left.get("locations")):
        return {"relationship": "INSUFFICIENT_EVIDENCE", "confidence": 0.0, "evidence": ["Event details are too sparse to compare."], "signals": {}}

    actor_overlap = _set_overlap(left, right, "actors")
    location_overlap = _set_overlap(left, right, "locations")
    object_overlap = _set_overlap(left, right, "objects")
    marker_overlap = _set_overlap(left, right, "event_markers")
    year_overlap = _set_overlap(left, right, "years")
    left_locations = set(left.get("locations") or [])
    right_locations = set(right.get("locations") or [])
    location_conflict = bool(left_locations and right_locations and not location_overlap)
    left_action = left.get("action_family")
    right_action = right.get("action_family")
    action_match = bool(left_action and right_action and left_action == right_action)
    action_conflict = bool(left_action and right_action and left_action != right_action)
    topics_match = bool(set(left.get("topics") or []) & set(right.get("topics") or []))
    time_gap = _hours_between(left_time, right_time)
    sem = semantic_similarity if semantic_similarity is not None else 0.0
    shared_anchor = bool(actor_overlap or object_overlap or marker_overlap)
    cue_text = normalize_for_analysis(f"{left_text} {right_text}")
    related_cue = bool(RELATED_CUES.search(cue_text))
    signals = {
        "semantic_similarity": round(sem, 4) if semantic_model_available else None,
        "shared_actors": sorted(actor_overlap),
        "shared_locations": sorted(location_overlap),
        "shared_event_objects": sorted(object_overlap),
        "shared_time_markers": sorted(marker_overlap),
        "action_match": action_match,
        "action_conflict": action_conflict,
        "location_conflict": location_conflict,
        "hours_between_publications": round(time_gap, 1) if time_gap is not None else None,
    }
    evidence: list[str] = []
    if actor_overlap:
        evidence.append("Shared named participants or institutions: " + ", ".join(sorted(actor_overlap)))
    if location_overlap:
        evidence.append("Shared location: " + ", ".join(sorted(location_overlap)))
    if object_overlap:
        evidence.append("Shared event subject: " + ", ".join(sorted(object_overlap)))
    if marker_overlap:
        evidence.append("Shared event marker: " + ", ".join(sorted(marker_overlap)))
    if action_match:
        evidence.append(f"Both report a {left_action.replace('_', ' ')} development.")
    if location_conflict:
        evidence.append("The articles identify different specific locations.")
    if semantic_model_available:
        evidence.append(f"Multilingual embedding similarity: {sem:.2f}.")

    if left.get("years") and right.get("years") and not year_overlap:
        return {"relationship": "SAME_TOPIC_DIFFERENT_EVENT" if topics_match else "UNRELATED_EVENT", "confidence": 0.92, "evidence": evidence + ["The articles refer to different years."], "signals": signals}

    if location_conflict and not actor_overlap:
        rel = "SAME_TOPIC_DIFFERENT_EVENT" if topics_match or action_match else "UNRELATED_EVENT"
        return {"relationship": rel, "confidence": 0.92, "evidence": evidence, "signals": signals}

    if related_cue and location_overlap and not (actor_overlap or object_overlap or marker_overlap):
        return {"relationship": "DIRECTLY_RELATED_EVENT", "confidence": 0.70, "evidence": evidence + ["The report signals a response or follow-up at the same location, without matching event-specific anchors."], "signals": signals}

    if action_conflict:
        if (actor_overlap or location_overlap) and related_cue and (time_gap is None or time_gap <= 240):
            return {"relationship": "DIRECTLY_RELATED_EVENT", "confidence": 0.72, "evidence": evidence + ["The report uses a response, aftermath, or follow-up cue."], "signals": signals}
        rel = "SAME_TOPIC_DIFFERENT_EVENT" if topics_match or actor_overlap else "UNRELATED_EVENT"
        return {"relationship": rel, "confidence": 0.86, "evidence": evidence + [f"Event actions differ ({left_action} vs {right_action})."], "signals": signals}

    if action_match and shared_anchor and not location_conflict:
        if time_gap is None or time_gap <= 96:
            conf = 0.94 if (location_overlap and (object_overlap or marker_overlap or actor_overlap)) else 0.86
            return {"relationship": "SAME_EVENT", "confidence": conf, "evidence": evidence, "signals": signals}
        if time_gap <= 168 and (location_overlap or not left_locations or not right_locations):
            if object_overlap or marker_overlap or actor_overlap:
                return {"relationship": "EVENT_UPDATE", "confidence": 0.82, "evidence": evidence + ["Coverage arrived within the developing-story window."], "signals": signals}

    if (
        semantic_model_available
        and sem >= 0.82
        and not location_conflict
        and not action_conflict
        and (actor_overlap or location_overlap or object_overlap or marker_overlap)
        and (time_gap is None or time_gap <= 96)
    ):
        return {"relationship": "SAME_EVENT", "confidence": min(0.92, sem), "evidence": evidence, "signals": signals}

    if actor_overlap and related_cue and (time_gap is None or time_gap <= 240):
        return {"relationship": "DIRECTLY_RELATED_EVENT", "confidence": 0.68, "evidence": evidence + ["The report uses a response, aftermath, or follow-up cue."], "signals": signals}
    if topics_match or actor_overlap or location_overlap:
        return {"relationship": "SAME_TOPIC_DIFFERENT_EVENT", "confidence": 0.72, "evidence": evidence + ["Shared topic or entity evidence is not enough to establish one event."], "signals": signals}
    if not shared_anchor and not left_action and not right_action:
        return {"relationship": "INSUFFICIENT_EVIDENCE", "confidence": 0.0, "evidence": evidence or ["No reliable event identity anchors were found."], "signals": signals}
    return {"relationship": "UNRELATED_EVENT", "confidence": 0.78, "evidence": evidence or ["No shared event identity evidence was found."], "signals": signals}
