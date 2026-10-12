"""Nepal-specific entities, institutions, and topic tagging (lexicon-based)."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

from config import DATA_DIR

# Built-in lexicon — also loadable/extendable from data/nepal_entities.json
DEFAULT_ENTITIES = {
    "parties": [
        ("Nepali Congress", ["nepali congress", "कांग्रेस", "nepalee congress", "nc "]),
        ("CPN-UML", ["cpn-uml", "uml", "एमाले", "cpn uml"]),
        ("CPN (Maoist Centre)", ["maoist", "माओवादी", "cpn-mc", "cpn mc"]),
        ("Rashtriya Swatantra Party", ["rsp", "राष्ट्रिय स्वतन्त्र", "rabi lamichhane"]),
        ("RPP", ["rpp", "राप्रपा", "rastriya prajatantra"]),
        ("Janata Samajwadi Party", ["jsp", "जनता समाजवादी"]),
    ],
    "institutions": [
        ("Government of Nepal", ["government of nepal", "नेपाल सरकार", "cabinet", "मन्त्रिपरिषद्"]),
        ("Federal Parliament", ["parliament", "संसद", "house of representatives", "प्रतिनिधि सभा", "national assembly"]),
        ("Election Commission", ["election commission", "निर्वाचन आयोग"]),
        ("Supreme Court", ["supreme court", "सर्वोच्च अदालत"]),
        ("Nepal Rastra Bank", ["nepal rastra bank", "नेपाल राष्ट्र बैंक", "nrb"]),
        ("CIAA", ["ciaa", "अख्तियार"]),
    ],
    "places": [
        ("Kathmandu", ["kathmandu", "काठमाडौं", "काठमाण्डौ"]),
        ("Pokhara", ["pokhara", "पोखरा"]),
        ("Lalitpur", ["lalitpur", "ललितपुर", "patan"]),
        ("Bhaktapur", ["bhaktapur", "भक्तपुर"]),
        ("Biratnagar", ["biratnagar", "विराटनगर"]),
        ("Province 1 / Koshi", ["koshi", "कोशी", "province 1"]),
        ("Madhesh", ["madhesh", "मधेश", "province 2"]),
        ("Bagmati", ["bagmati", "बागमती"]),
        ("Gandaki", ["gandaki", "गण्डकी"]),
        ("Lumbini", ["lumbini", "लुम्बिनी"]),
        ("Karnali", ["karnali", "कर्णाली"]),
        ("Sudurpashchim", ["sudurpashchim", "सुदूरपश्चिम", "far-west"]),
    ],
    "people": [
        ("KP Sharma Oli", ["kp oli", "केपी शर्मा ओली", "oli"]),
        ("Sher Bahadur Deuba", ["deuba", "शेरबहादुर देउवा"]),
        ("Pushpa Kamal Dahal", ["dahal", "prachanda", "प्रचण्ड", "पुष्पकमल"]),
        ("Balen Shah", ["balen", "बालेन"]),
        ("Rabi Lamichhane", ["rabi lamichhane", "रवि लामिछाने"]),
    ],
}

TOPIC_RULES = [
    ("Politics", [
        r"parliament", r"cabinet", r"election", r"minister", r"prime minister",
        r"संसद", r"मन्त्री", r"प्रधानमन्त्री", r"चुनाव", r"निर्वाचन", r"सरकार",
        r"congress", r"uml", r"maoist", r"कांग्रेस", r"एमाले", r"माओवादी",
    ]),
    ("Business", [
        r"economy", r"bank", r"inflation", r"stock", r"tax", r"budget",
        r"अर्थतन्त्र", r"बैंक", r"बजेट", r"कर", r"महँगी", r"शेयर",
    ]),
    ("Disaster", [
        r"earthquake", r"flood", r"landslide", r"monsoon", r"relief",
        r"भूकम्प", r"बाढी", r"पहिरो", r"मनसुन", r"राहत",
    ]),
    ("Sports", [
        r"cricket", r"football", r"match", r"tournament", r"olympic",
        r"क्रिकेट", r"फुटबल", r"खेल", r"म्याच",
    ]),
    ("World", [
        r"india", r"china", r"usa", r"united nations", r"ukraine", r"gaza",
        r"भारत", r"चीन", r"अमेरिका", r"संयुक्त राष्ट्र",
    ]),
    ("Technology", [
        r"internet", r"ai\b", r"cyber", r"telecom", r"digital",
        r"इन्टरनेट", r"साइबर", r"डिजिटल",
    ]),
]


@lru_cache(maxsize=1)
def load_entities() -> dict:
    path = DATA_DIR / "nepal_entities.json"
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    return DEFAULT_ENTITIES


def extract_entities(text: str) -> list[dict]:
    if not text:
        return []
    lowered = text.casefold()
    found: list[dict] = []
    seen: set[str] = set()
    entities = load_entities()
    for kind, items in entities.items():
        for canonical, aliases in items:
            for alias in aliases:
                if alias.casefold() in lowered and canonical not in seen:
                    seen.add(canonical)
                    found.append({
                        "name": canonical,
                        "type": kind.rstrip("s") if kind.endswith("s") else kind,
                        "matched_alias": alias,
                    })
                    break
    return found


def classify_topics(text: str, default: str = "Nepal") -> list[str]:
    if not text:
        return [default]
    topics: list[str] = []
    for topic, patterns in TOPIC_RULES:
        for pattern in patterns:
            if re.search(pattern, text, flags=re.IGNORECASE):
                topics.append(topic)
                break
    if "Nepal" not in topics and re.search(r"nepal|नेपाल|kathmandu|काठमाडौं", text, re.I):
        topics.insert(0, "Nepal")
    if not topics:
        topics = [default]
    # Deduplicate preserving order
    out: list[str] = []
    for t in topics:
        if t not in out:
            out.append(t)
    return out[:5]


def ensure_entity_file() -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = DATA_DIR / "nepal_entities.json"
    if not path.exists():
        path.write_text(json.dumps(DEFAULT_ENTITIES, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
