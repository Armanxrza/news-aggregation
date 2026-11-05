"""Story clustering by same-event headlines.

The local hash embedding is not a semantic model. Its character patterns make
unrelated Nepali headlines look alike, so it is stored for later use and is
not allowed to merge stories.
"""

from __future__ import annotations

import datetime

from sqlalchemy.orm import Session

from config import CLUSTER_TIME_WINDOW_HOURS
from database import Article, Story
from services.embedding import embed_text, model_id, vector_to_storage
from services.same_event import event_score

def _in_window(story: Story, published_at: datetime.datetime, window_start: datetime.datetime, window_end: datetime.datetime) -> bool:
    ref = story.updated_at or story.created_at
    if ref and window_start <= ref <= window_end + datetime.timedelta(hours=CLUSTER_TIME_WINDOW_HOURS):
        return True
    age = published_at - (story.created_at or published_at)
    return datetime.timedelta(hours=-6) <= age <= datetime.timedelta(hours=CLUSTER_TIME_WINDOW_HOURS)


def _best_event_score(headline: str, story: Story) -> float:
    titles = [story.ai_headline or ""]
    for article in list(story.articles or [])[:12]:
        if article.original_headline:
            titles.append(article.original_headline)
    scores = [event_score(headline, title) for title in titles if title]
    return max(scores, default=0.0)


def get_or_create_story(
    db: Session,
    headline: str,
    category: str = "Nepal",
    published_at: datetime.datetime | None = None,
    content: str = "",
    language: str | None = None,
) -> tuple[Story, dict]:
    """
    Assign article to an existing story or create a new one.
    Returns (story, match_meta).
    """
    published_at = published_at or datetime.datetime.utcnow()
    text_for_embed = f"{headline}\n{(content or '')[:800]}"
    vector = embed_text(text_for_embed)
    window_start = published_at - datetime.timedelta(hours=CLUSTER_TIME_WINDOW_HOURS)
    window_end = published_at + datetime.timedelta(hours=6)

    candidates = (
        db.query(Story)
        .order_by(Story.created_at.desc())
        .limit(400)
        .all()
    )

    best: tuple[Story, float, str] | None = None

    for story in candidates:
        if not _in_window(story, published_at, window_start, window_end):
            continue
        score = _best_event_score(headline, story)
        if score <= 0:
            continue
        if best is None or score > best[1]:
            best = (story, score, "same_event")

    if best:
        story, score, method = best
        if not story.embedding:
            story.embedding = vector_to_storage(vector)
        story.updated_at = datetime.datetime.utcnow()
        story.cluster_method = method
        story.cluster_confidence = round(score, 4)
        if language:
            langs = set((story.languages or "").split(",")) if story.languages else set()
            langs.discard("")
            langs.add(language)
            story.languages = ",".join(sorted(langs))
        db.commit()
        db.refresh(story)
        return story, {
            "matched": True,
            "method": method,
            "confidence": round(score, 4),
            "embedding_model": model_id(),
        }

    new_story = Story(
        ai_headline=headline,
        topic=category,
        embedding=vector_to_storage(vector),
        languages=language or None,
        cluster_method="new_story",
        cluster_confidence=1.0,
        bias_left_pct=None,
        bias_center_pct=None,
        bias_right_pct=None,
    )
    db.add(new_story)
    db.commit()
    db.refresh(new_story)
    return new_story, {
        "matched": False,
        "method": "new_story",
        "confidence": 1.0,
        "embedding_model": model_id(),
    }


def recluster_all(db: Session) -> dict:
    """Rebuild stories from all articles (destructive)."""
    articles = db.query(Article).order_by(Article.published_at.asc().nullslast(), Article.id.asc()).all()
    db.query(Story).delete()
    db.commit()

    created = 0
    for article in articles:
        source_lang = article.language or article.detected_language
        category = "Nepal"
        if article.topics_json:
            import json

            try:
                topics = json.loads(article.topics_json)
                if topics:
                    category = topics[0]
            except json.JSONDecodeError:
                pass
        story, _meta = get_or_create_story(
            db,
            article.original_headline,
            category=category,
            published_at=article.published_at,
            content=article.content_text or "",
            language=source_lang,
        )
        article.story_id = story.id
        created += 1
        if created % 25 == 0:
            db.commit()
    db.commit()
    return {"articles_reassigned": created, "stories": db.query(Story).count()}
