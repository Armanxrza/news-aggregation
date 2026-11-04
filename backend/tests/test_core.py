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
