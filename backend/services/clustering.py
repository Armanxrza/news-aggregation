"""Staged story clustering: URL/title heuristics then multilingual embeddings."""

from __future__ import annotations

import datetime
import logging
import re
from difflib import SequenceMatcher

from sqlalchemy.orm import Session

from config import CLUSTER_SIMILARITY_THRESHOLD, CLUSTER_TIME_WINDOW_HOURS
from database import Article, Story
from services.embedding import cosine, embed_text, model_id, storage_to_vector, vector_to_storage

logger = logging.getLogger(__name__)

STOP_WORDS = {
    "about", "after", "before", "could", "from", "have", "into", "more",
    "over", "that", "their", "there", "these", "they", "this", "what",
    "when", "where", "which", "with", "will", "नेपालमा", "बारे", "गर्ने",
    "the", "and", "for", "are", "was", "were", "has", "had",
}


def normalize_title(title: str) -> str:
    return re.sub(r"[^\w\u0900-\u097f]+", " ", (title or "").casefold()).strip()


def story_tokens(title: str) -> set[str]:
    return {
        token for token in normalize_title(title).split()
        if len(token) > 2 and token not in STOP_WORDS
    }


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
    headline_tokens = story_tokens(headline)
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
        # Time window using story created_at / updated_at
        ref = story.updated_at or story.created_at
        if ref and not (window_start <= ref <= window_end + datetime.timedelta(hours=CLUSTER_TIME_WINDOW_HOURS)):
            # also allow if any article in story is in window — approximate via story age
            age = published_at - (story.created_at or published_at)
            if age < datetime.timedelta(hours=-6) or age > datetime.timedelta(hours=CLUSTER_TIME_WINDOW_HOURS):
                continue

        # Prefer same topic when both set, but allow cross-topic for strong semantic match
        same_topic = (story.topic or "").lower() == (category or "").lower()

        story_toks = story_tokens(story.ai_headline)
        overlap = len(headline_tokens & story_toks)
        title_sim = SequenceMatcher(
            None, normalize_title(headline), normalize_title(story.ai_headline)
        ).ratio()

        emb_sim = 0.0
        story_vec = storage_to_vector(story.embedding)
        if story_vec:
            emb_sim = cosine(vector, story_vec)

        score = 0.0
        method = "none"
        if emb_sim >= CLUSTER_SIMILARITY_THRESHOLD:
            score = emb_sim
            method = "embedding"
        elif (overlap >= 2 and title_sim >= 0.45) or title_sim >= 0.82:
            score = max(title_sim, 0.5 + 0.05 * overlap)
            method = "title_overlap"
        elif emb_sim >= CLUSTER_SIMILARITY_THRESHOLD - 0.08 and title_sim >= 0.35:
            score = 0.55 * emb_sim + 0.45 * title_sim
            method = "hybrid"

        if method == "none":
            continue
        if not same_topic and score < CLUSTER_SIMILARITY_THRESHOLD + 0.05 and method != "embedding":
            continue
        if best is None or score > best[1]:
            best = (story, score, method)

    if best and best[1] >= 0.5:
        story, score, method = best
        # Refresh story embedding as running mean of headline vectors (lightweight)
        old = storage_to_vector(story.embedding)
        if old and len(old) == len(vector):
            mixed = [(a + b) / 2 for a, b in zip(old, vector)]
            story.embedding = vector_to_storage(mixed)
        else:
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
