"""Core unit and API tests for SajhaNews."""

from __future__ import annotations

import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

# Isolate test DB before importing app modules
os.environ["DATABASE_URL"] = f"sqlite:///{(BACKEND / 'test_sajhanews.db').as_posix()}"
os.environ["ADMIN_AUTH_DISABLED"] = "true"
os.environ["ENABLE_CRAWL_SCHEDULER"] = "false"
os.environ["FRAMING_ENABLED"] = "false"
os.environ["EMBEDDING_ENABLED"] = "false"
os.environ["ANALYZE_ON_CRAWL"] = "false"

from fastapi.testclient import TestClient  # noqa: E402

import database  # noqa: E402
from database import Article, SessionLocal, Source, Story, init_db  # noqa: E402
from services.clustering import get_or_create_story  # noqa: E402
from services.language import detect_language  # noqa: E402
from services.nepal import classify_topics, extract_entities  # noqa: E402
from services.claims import extract_claims_from_text  # noqa: E402
from services.framing import analyze_government_framing  # noqa: E402


def setup_module():
    if (BACKEND / "test_sajhanews.db").exists():
        (BACKEND / "test_sajhanews.db").unlink()
    init_db()


def test_detect_nepali_devanagari():
    result = detect_language("काठमाडौंमा आज भारी वर्षा भयो र बाढीको जोखिम बढेको छ।")
    assert result["language"] == "ne"
    assert result["script"] == "devanagari"


def test_detect_english():
    result = detect_language("The cabinet met in Kathmandu to discuss the budget.")
    assert result["language"] in {"en", "ne-rom"}


def test_entity_extraction():
    entities = extract_entities("KP Sharma Oli met leaders of Nepali Congress and CPN-UML in Kathmandu.")
    names = {e["name"] for e in entities}
    assert "Kathmandu" in names
    assert "Nepali Congress" in names or "CPN-UML" in names


def test_topic_classification():
    topics = classify_topics("Parliament debated the election bill amid coalition talks.")
    assert "Politics" in topics


def test_claim_extraction():
    claims = extract_claims_from_text(
        "The minister said inflation fell to 4.2 percent this quarter. Markets remained calm."
    )
    assert claims
    assert any("said" in c.lower() or "percent" in c.lower() for c in claims)


def test_framing_lexical_fallback():
    result = analyze_government_framing(
        "Opposition leaders criticised the government for failing to control corruption and mismanagement in procurement.",
        lexical_only=True,
    )
    assert result["label"] == "government_critical"
    assert result["scores"]["critical"] > result["scores"]["supportive"]
    assert abs(sum(result["scores"].values()) - 1.0) < 0.02
    assert "evidence" in result


def test_framing_soft_not_all_neutral():
    a = analyze_government_framing("Cabinet praised for historic welfare achievement launch.", lexical_only=True)
    b = analyze_government_framing("Protest against government corruption scandal grows in Kathmandu.", lexical_only=True)
    assert a["scores"]["supportive"] > 0.15
    assert b["scores"]["critical"] > 0.15
    assert a["bias_left_pct"] if False else a["scores"]["supportive"] != b["scores"]["supportive"]


def test_clustering_groups_similar_headlines():
    db = SessionLocal()
    try:
        story1, meta1 = get_or_create_story(
            db,
            "Nepal Rastra Bank keeps policy rate unchanged",
            category="Business",
            content="The central bank held rates steady amid inflation concerns.",
            language="en",
        )
        story2, meta2 = get_or_create_story(
            db,
            "Nepal Rastra Bank keeps policy rate unchanged amid inflation",
            category="Business",
            content="NRB officials said the policy rate remains the same.",
            language="en",
        )
        assert story1.id == story2.id
        assert meta2.get("matched") is True
    finally:
        db.close()


def test_api_health_and_seed_shape():
    # Re-import main after env set
    import importlib
    import main as main_mod

    importlib.reload(database)
    importlib.reload(main_mod)
    client = TestClient(main_mod.app)

    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["ok"] is True

    root = client.get("/api")
    assert root.status_code == 200
    assert root.json()["version"]

    # Create source via admin-disabled auth
    res = client.post(
        "/api/sources",
        json={
            "name": "Test Portal",
            "domain": "test-portal.example",
            "rss_url": "https://example.com/feed",
            "language": "en",
            "category": "Nepal",
        },
    )
    assert res.status_code == 200
    source_id = res.json()["id"]

    db = SessionLocal()
    try:
        source = db.query(Source).filter(Source.id == source_id).first()
        story = Story(ai_headline="Demo story about Nepal politics", topic="Politics")
        db.add(story)
        db.flush()
        db.add(
            Article(
                source_id=source.id,
                story_id=story.id,
                original_headline="Demo story about Nepal politics",
                url="https://test-portal.example/demo-1",
                content_text="Parliament discussed reforms. The minister said growth will improve.",
                language="en",
                government_framing="government_neutral",
                framing_evidence="test",
            )
        )
        db.commit()
        story_id = story.id
    finally:
        db.close()

    stories = client.get("/api/stories")
    assert stories.status_code == 200
    body = stories.json()
    assert "items" in body
    assert body["total"] >= 1

    detail = client.get(f"/api/stories/{story_id}")
    assert detail.status_code == 200
    assert detail.json()["source_count"] == 1
    assert isinstance(detail.json()["bias_left_pct"], (float, int, type(None)))

    analytics = client.get("/api/analytics/overview")
    assert analytics.status_code == 200
    assert "framing" in analytics.json()


def test_same_event_rejects_unrelated_nepali_headlines():
    from services.same_event import focus_coverage, same_event

    water = "तीन महिनामा खानेपानीका ९२ आयोजनाको ठेक्का आह्वान"
    water_long = "तीन महिनामै खानेपानीका ९२ आयोजनाको ठेक्का आह्वान, १३ लाख नागरिक लाभान्वित हुने"
    texas = (
        "टेक्सासमा डेमोक्रेटहरूको अप्रत्याशित जितपछि इलोन मस्कको साम्राज्यमा धक्का, "
        "कम्पनीहरूको १२० अर्ब डलर स्वाहा"
    )
    women = "महिला, निरक्षर मानिस र ज्येष्ठ नागरिकसम्म कसरी पुग्छ पूर्वसूचना"
    assert same_event(water, water_long)
    assert not same_event(water, texas)
    assert not same_event(water_long, women)
    assert not same_event(texas, women)

    class Row:
        def __init__(self, headline: str, source_id: int):
            self.original_headline = headline
            self.source_id = source_id

    kept, meta = focus_coverage(
        [
            Row(water, 1),
            Row(texas, 2),
            Row(water_long, 3),
            Row(water, 4),
            Row(women, 5),
        ],
        water,
        "embedding",
    )
    assert [row.source_id for row in kept] == [1, 3, 4]
    assert meta["omitted"] == 2
    assert meta["coverage_sufficient"] is True


def test_seeded_paraphrases_stay_together_when_not_embedding_merged():
    from services.same_event import focus_coverage

    class Row:
        def __init__(self, headline: str, source_id: int):
            self.original_headline = headline
            self.source_id = source_id

    headlines = [
        "Nepal Rastra Bank keeps policy rate unchanged at 6.5 percent",
        "NRB holds rates steady as inflation stays within comfort zone",
        "नेपाल राष्ट्र बैंकले नीतिगत दर यथावत् ६.५ प्रतिशतमै राख्यो",
        "राष्ट्र बैंकले ब्याजदर नबढाउने निर्णय गर्‍यो",
    ]
    kept, meta = focus_coverage(
        [Row(headline, index + 1) for index, headline in enumerate(headlines)],
        headlines[0],
        "new_story",
    )
    assert len(kept) == 4
    assert meta["omitted"] == 0
    assert meta["coverage_sufficient"] is True


def test_clustering_does_not_merge_unrelated_events():
    db = SessionLocal()
    try:
        water, _ = get_or_create_story(
            db,
            "तीन महिनामा खानेपानीका ९२ आयोजनाको ठेक्का आह्वान",
            category="Nepal",
            language="ne",
        )
        texas, texas_meta = get_or_create_story(
            db,
            "टेक्सासमा डेमोक्रेटहरूको अप्रत्याशित जितपछि इलोन मस्कको साम्राज्यमा धक्का",
            category="Nepal",
            language="ne",
        )
        again, again_meta = get_or_create_story(
            db,
            "तीन महिनामै खानेपानीका ९२ आयोजनाको ठेक्का आह्वान, १३ लाख नागरिक लाभान्वित हुने",
            category="Nepal",
            language="ne",
        )
        assert texas.id != water.id
        assert texas_meta["matched"] is False
        assert again.id == water.id
        assert again_meta["matched"] is True
        assert again_meta["method"] == "same_event"
    finally:
        db.close()


def test_story_detail_drops_unrelated_coverage_and_passage_lookup():
    import importlib
    import main as main_mod

    importlib.reload(database)
    importlib.reload(main_mod)
    client = TestClient(main_mod.app)

    db = SessionLocal()
    try:
        outlets = []
        for name, domain in (
            ("Clickmandu", "clickmandu.example"),
            ("Nagarik News", "nagarik.example"),
            ("BBC Nepali", "bbc-nepali.example"),
            ("Setopati", "setopati.example"),
        ):
            source = Source(name=name, domain=domain, language="ne", is_active=True)
            db.add(source)
            db.flush()
            outlets.append(source)
        story = Story(
            ai_headline="तीन महिनामा खानेपानीका ९२ आयोजनाको ठेक्का आह्वान",
            topic="Nepal",
            cluster_method="embedding",
        )
        db.add(story)
        db.flush()
        rows = [
            (outlets[0], "तीन महिनामा खानेपानीका ९२ आयोजनाको ठेक्का आह्वान", "https://clickmandu.example/water"),
            (
                outlets[0],
                "टेक्सासमा डेमोक्रेटहरूको अप्रत्याशित जितपछि इलोन मस्कको साम्राज्यमा धक्का, कम्पनीहरूको १२० अर्ब डलर स्वाहा",
                "https://clickmandu.example/texas",
            ),
            (
                outlets[1],
                "तीन महिनामै खानेपानीका ९२ आयोजनाको ठेक्का आह्वान, १३ लाख नागरिक लाभान्वित हुने",
                "https://nagarik.example/water",
            ),
            (outlets[2], "तीन महिनामा खानेपानीका ९२ आयोजनाको ठेक्का आह्वान", "https://bbc-nepali.example/water"),
            (
                outlets[3],
                "महिला, निरक्षर मानिस र ज्येष्ठ नागरिकसम्म कसरी पुग्छ पूर्वसूचना",
                "https://setopati.example/women",
            ),
        ]
        for source, headline, url in rows:
            db.add(
                Article(
                    source_id=source.id,
                    story_id=story.id,
                    original_headline=headline,
                    url=url,
                    content_text=headline,
                    language="ne",
                    government_framing="government_neutral",
                    framing_scores_json='{"critical": 0.16, "neutral": 0.62, "supportive": 0.22}',
                )
            )
        db.commit()
        story_id = story.id
    finally:
        db.close()

    detail = client.get(f"/api/stories/{story_id}")
    assert detail.status_code == 200
    body = detail.json()
    headlines = [row["headline"] for row in body["headline_comparison"]]
    assert len(headlines) == 3
    assert all("खानेपानी" in headline for headline in headlines)
    assert body["omitted_unrelated"] == 2
    assert body["coverage_sufficient"] is True
    assert body["source_count"] == 3
    assert "Setopati" not in body["sources"]

    unrelated = client.post(
        "/api/framing/preview",
        json={"text": "टेक्सासमा डेमोक्रेटहरूको अप्रत्याशित जितपछि इलोन मस्कको साम्राज्यमा धक्का"},
    )
    assert unrelated.status_code == 200
    unrelated_body = unrelated.json()
    assert unrelated_body["coverage_sufficient"] is False
    assert unrelated_body["scores"] is None
    assert unrelated_body["story_id"] is None
    assert "Clickmandu" in unrelated_body["sources"]
    assert "BBC Nepali" not in unrelated_body["sources"]

    missing = client.post(
        "/api/framing/preview",
        json={"text": "A completely different city council vote in Oslo about tram fares."},
    )
    assert missing.status_code == 200
    assert missing.json()["found"] is False
    assert missing.json()["message"] == "The news coverage is not found. Please paste the news link."

    found = client.post(
        "/api/framing/preview",
        json={"text": "तीन महिनामा खानेपानीका ९२ आयोजनाको ठेक्का आह्वान"},
    )
    assert found.status_code == 200
    found_body = found.json()
    assert found_body["found"] is True
    assert found_body["story_id"] == story_id
    assert found_body["coverage_sufficient"] is True
    assert found_body["source_count"] == 3
    assert set(found_body["sources"]) == {"Clickmandu", "Nagarik News", "BBC Nepali"}
    assert found_body["scores"]["neutral"] > found_body["scores"]["critical"]

    by_link = client.post(
        "/api/framing/preview",
        json={"text": "Please rate https://nagarik.example/water"},
    )
    assert by_link.status_code == 200
    assert by_link.json()["found"] is True
    assert by_link.json()["story_id"] == story_id


def test_desk_classifier_splits_framing():
    from services.framing import DESK_MODEL_PATH, analyze_government_framing

    assert DESK_MODEL_PATH.exists(), "Train with python -m ml.train_framing"
    critical = analyze_government_framing(
        "Opposition leaders criticised the cabinet for failing to deliver flood relief and alleged mismanagement."
    )
    neutral = analyze_government_framing(
        "The statistics office released the quarterly employment table without additional comment."
    )
    supportive = analyze_government_framing(
        "प्रधानमन्त्रीले नयाँ सामुदायिक अस्पताल उद्घाटन गर्दै यसलाई दिगो सार्वजनिक सेवा भने।"
    )
    assert critical["label"] == "government_critical"
    assert neutral["label"] == "government_neutral"
    assert supportive["label"] == "government_supportive"
    assert critical["model"] == "framing-desk-v1"
    for result in (critical, neutral, supportive):
        scores = result["scores"]
        assert abs(sum(scores.values()) - 1) < 0.02
        assert set(scores) == {"critical", "neutral", "supportive"}
