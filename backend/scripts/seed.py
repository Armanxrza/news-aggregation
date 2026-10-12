"""Seed database from data files and offline demo coverage."""

from __future__ import annotations

import datetime
import json
import sys
from pathlib import Path

# Allow `python -m scripts.seed` from backend/
_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

import config
from database import (
    Article,
    Claim,
    EvalPair,
    SessionLocal,
    Source,
    Story,
    _json_dumps,
    init_db,
)
from services.bias_signals import extract_signals
from services.clustering import get_or_create_story
from services.nepal import classify_topics, ensure_entity_file, extract_entities

DEMO_STORY_SLUG = "nrb-policy-rate-unchanged-2026"


def _load_json_list(path: Path) -> list:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def seed_sources(db) -> tuple[int, int]:
    catalog = _load_json_list(config.DATA_DIR / "nepal_sources.json")
    created = updated = 0
    for row in catalog:
        domain = (row.get("domain") or "").strip()
        if not domain:
            continue
        source = db.query(Source).filter(Source.domain == domain).first()
        rss_url = row.get("rss_url")
        if isinstance(rss_url, str):
            rss_url = rss_url.strip() or None
        if not source:
            source = Source(
                name=row.get("name") or domain,
                domain=domain,
                rss_url=rss_url,
                language=row.get("language") or "en",
                is_active=row.get("is_active", True),
                category=row.get("category"),
                ownership_notes=row.get("ownership_notes"),
                transparency_notes=row.get("transparency_notes"),
                perspective_label=row.get("perspective_label"),
            )
            db.add(source)
            created += 1
        else:
            source.name = row.get("name") or source.name
            if rss_url:
                source.rss_url = rss_url
            source.language = row.get("language") or source.language
            source.is_active = bool(row.get("is_active", source.is_active))
            if row.get("category"):
                source.category = row["category"]
            updated += 1
    db.commit()
    return created, updated


def seed_eval_pairs(db) -> tuple[int, int]:
    path = config.DATA_DIR / "story_pairs.jsonl"
    if not path.exists():
        return 0, 0
    added = skipped = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        left = row.get("left") or row.get("left_text")
        right = row.get("right") or row.get("right_text")
        if not left or not right:
            continue
        exists = (
            db.query(EvalPair.id)
            .filter(EvalPair.left_text == left, EvalPair.right_text == right)
            .first()
        )
        if exists:
            skipped += 1
            continue
        db.add(
            EvalPair(
                left_text=left,
                right_text=right,
                same_event=bool(row.get("same_event")),
                language_pair=row.get("language_pair"),
                notes=row.get("notes"),
            )
        )
        added += 1
    db.commit()
    return added, skipped


def _get_or_create_source(db, domain: str, **kwargs) -> Source:
    source = db.query(Source).filter(Source.domain == domain).first()
    if source:
        return source
    kwargs.setdefault("name", domain)
    source = Source(domain=domain, **kwargs)
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


def seed_demo_story(db) -> int:
    """Multi-outlet demo cluster (EN + NE) for offline UI testing."""
    published = datetime.datetime(2026, 3, 15, 10, 30, 0)
    demo_articles = [
        {
            "domain": "kathmandupost.com",
            "name": "The Kathmandu Post",
            "language": "en",
            "url": f"https://seed.sajhanews.local/{DEMO_STORY_SLUG}/kathmandu-post",
            "headline": "Nepal Rastra Bank keeps policy rate unchanged at 6.5 percent",
            "content": (
                "The Nepal Rastra Bank left its policy rate unchanged at 6.5 percent on Friday, "
                "citing stable inflation near the target band. Officials said credit growth to "
                "productive sectors remained a priority while monitoring liquidity in the banking system."
            ),
            "framing": {
                "label": "government_neutral",
                "confidence": 0.71,
                "model": "seed-demo-v1",
                "method": "curated",
                "evidence": "Factual reporting on NRB monetary decision without evaluative government language.",
            },
            "claims": [
                {
                    "text": "The Nepal Rastra Bank left its policy rate unchanged at 6.5 percent.",
                    "status": "supported",
                    "confidence": 0.88,
                },
            ],
        },
        {
            "domain": "nepalitimes.com",
            "name": "Nepali Times",
            "language": "en",
            "url": f"https://seed.sajhanews.local/{DEMO_STORY_SLUG}/nepali-times",
            "headline": "NRB holds rates steady as inflation stays within comfort zone",
            "content": (
                "Nepal Rastra Bank's board decided to maintain the policy rate, according to a "
                "statement released after the monetary policy review. Economists said the move was "
                "widely expected given moderating food prices in Kathmandu Valley markets."
            ),
            "framing": {
                "label": "government_neutral",
                "confidence": 0.68,
                "model": "seed-demo-v1",
                "method": "curated",
                "evidence": "Neutral descriptive coverage anchored on official statement.",
            },
            "claims": [
                {
                    "text": "Nepal Rastra Bank's board decided to maintain the policy rate.",
                    "status": "supported",
                    "confidence": 0.85,
                },
            ],
        },
        {
            "domain": "onlinekhabar.com",
            "name": "Online Khabar",
            "language": "ne",
            "url": f"https://seed.sajhanews.local/{DEMO_STORY_SLUG}/online-khabar",
            "headline": "नेपाल राष्ट्र बैंकले नीतिगत दर यथावत् ६.५ प्रतिशतमै राख्यो",
            "content": (
                "नेपाल राष्ट्र बैंकले शुक्रबार मौद्रिक नीति समीक्षापछि नीतिगत दर ६.५ प्रतिशतमै "
                "यथावत् राखेको छ। बैंकले महँगी लक्ष्य सीमा भित्र रहेको जनाएको छ। "
                "तर आलोचकहरूले सरकारले महँगी नियन्त्रणमा पर्याप्त कदम नचालेको आरोप लगाएका छन्।"
            ),
            "framing": {
                "label": "government_critical",
                "confidence": 0.62,
                "model": "seed-demo-v1",
                "method": "curated",
                "evidence": "Includes critic allegation that government has not done enough on inflation.",
            },
            "claims": [
                {
                    "text": "नेपाल राष्ट्र बैंकले नीतिगत दर ६.५ प्रतिशतमै यथावत् राखेको छ।",
                    "status": "supported",
                    "confidence": 0.9,
                },
            ],
        },
        {
            "domain": "bbc.com/nepali",
            "name": "BBC Nepali",
            "language": "ne",
            "url": f"https://seed.sajhanews.local/{DEMO_STORY_SLUG}/bbc-nepali",
            "headline": "राष्ट्र बैंकले ब्याजदर नबढाउने निर्णय गर्‍यो",
            "content": (
                "नेपाल राष्ट्र बैंकले मौद्रिक नीतिको नीतिगत दर परिवर्तन नगर्ने निर्णय गरेको छ। "
                "बैंकका अनुसार मूल्य वृद्धि लक्ष्य सीमाभित्र रहेकाले दर यथावत् राखिएको हो।"
            ),
            "framing": {
                "label": "government_neutral",
                "confidence": 0.74,
                "model": "seed-demo-v1",
                "method": "curated",
                "evidence": "Attribution to central bank; no supportive or critical evaluative framing.",
            },
            "claims": [
                {
                    "text": "नेपाल राष्ट्र बैंकले मौद्रिक नीतिको नीतिगत दर परिवर्तन नगर्ने निर्णय गरेको छ।",
                    "status": "supported",
                    "confidence": 0.87,
                },
            ],
        },
    ]

    inserted = 0
    story: Story | None = None
    existing = (
        db.query(Article)
        .filter(Article.url.like(f"https://seed.sajhanews.local/{DEMO_STORY_SLUG}/%"))
        .first()
    )
    if existing and existing.story_id:
        story = db.query(Story).filter(Story.id == existing.story_id).first()

    for spec in demo_articles:
        if db.query(Article.id).filter(Article.url == spec["url"]).first():
            continue

        source = _get_or_create_source(
            db,
            spec["domain"],
            name=spec["name"],
            rss_url=None,
            language=spec["language"],
            category="Business",
            is_active=True,
        )

        combined = f"{spec['headline']}\n{spec['content']}"
        topics = classify_topics(combined, default="Business")
        entities = extract_entities(combined)
        signals = extract_signals(combined, entities)

        if story is None:
            story, _ = get_or_create_story(
                db,
                spec["headline"],
                category=topics[0],
                published_at=published,
                content=spec["content"],
                language=spec["language"],
            )
            story.ai_summary = (
                "Nepal Rastra Bank maintained its policy rate at 6.5% amid stable inflation, "
                "with English and Nepali outlets reporting the decision across Kathmandu."
            )
            db.commit()

        article = Article(
            source_id=source.id,
            story_id=story.id,
            original_headline=spec["headline"],
            url=spec["url"],
            content_text=spec["content"],
            published_at=published,
            language=spec["language"],
            detected_language=spec["language"],
            topics_json=_json_dumps(topics),
            entities_json=_json_dumps(entities),
            signals_json=_json_dumps(signals),
            government_framing=spec["framing"]["label"],
            framing_confidence=spec["framing"]["confidence"],
            framing_model=spec["framing"]["model"],
            framing_evidence=spec["framing"]["evidence"],
            framing_method=spec["framing"]["method"],
        )
        db.add(article)
        db.flush()

        for claim_spec in spec["claims"]:
            db.add(
                Claim(
                    article_id=article.id,
                    story_id=story.id if story else None,
                    claim_text=claim_spec["text"],
                    status=claim_spec["status"],
                    confidence=claim_spec["confidence"],
                    evidence_json=_json_dumps(
                        {
                            "citations": [],
                            "note": "Seeded demo claim for offline cross-outlet view.",
                        }
                    ),
                    model="seed-demo-v1",
                )
            )

        source.article_count = (source.article_count or 0) + 1
        inserted += 1

    if story:
        story.languages = "en,ne"
        db.commit()
    else:
        db.commit()

    return inserted


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    init_db()
    ensure_entity_file()
    db = SessionLocal()

    print("SajhaNews seed")
    src_created, src_updated = seed_sources(db)
    print(f"  Sources: {src_created} created, {src_updated} touched")

    pairs_added, pairs_skipped = seed_eval_pairs(db)
    print(f"  Eval pairs: {pairs_added} added, {pairs_skipped} skipped")

    demo_n = seed_demo_story(db)
    print(f"  Demo articles: {demo_n} inserted")

    db.close()
    print("Done.")


if __name__ == "__main__":
    main()
