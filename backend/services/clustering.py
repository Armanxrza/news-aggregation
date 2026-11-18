"""Conservative event identity matching for incoming news articles."""

from __future__ import annotations

import datetime
import json
import logging
import re
from collections import Counter
from typing import Any

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from config import (
    CLUSTER_CANDIDATE_LIMIT,
    CLUSTER_SIMILARITY_THRESHOLD,
    CLUSTER_TIME_WINDOW_HOURS,
    CLUSTER_UPDATE_WINDOW_HOURS,
)
from database import Article, Story
from services.embedding import cosine, embed_text, model_id, storage_to_vector, vector_to_storage
from services.event_intelligence import classify_event_relationship, extract_event_frame
from services.framing import rerank_event_relationships

logger = logging.getLogger(__name__)
_FALLBACK_MODEL = "local-hash-tfidf-fallback-v2"


def _json(raw: str | None, default: Any) -> Any:
    try:
        return json.loads(raw) if raw else default
    except (json.JSONDecodeError, TypeError):
        return default


def _summary_sentence(text: str) -> str | None:
    """Choose a short source sentence for a cautious, attributed story summary."""
    clean = re.sub(r"<[^>]+>", " ", text or "")
    clean = re.sub(r"\s+", " ", clean).strip()
    if not clean:
        return None
    parts = re.split(r"(?<=[.!?।])\s+", clean)
    sentence = next((p.strip() for p in parts if len(p.strip()) >= 35), clean)
    return sentence[:420].rstrip()


def _event_title(frame: dict[str, Any], fallback: str) -> str:
    """Create a restrained event title only when extracted anchors support it."""
    action = frame.get("action_family")
    locations = frame.get("locations") or []
    actors = frame.get("actors") or []
    objects = frame.get("objects") or []
    markers = frame.get("event_markers") or []
    if not action or not (locations or actors or objects or markers):
        return fallback[:512]
    where = f" in {locations[0]}" if locations else ""
    when = f" during {markers[0].title()}" if markers else ""
    if action == "traffic_restriction":
        subject = "Tipper operations" if "tippers" in objects else "Road traffic"
        return f"{subject} restricted{where}{when}"[:512]
    if action == "election_schedule":
        return f"Local election schedule announced{where}"[:512]
    if action == "cabinet_change":
        return "Cabinet reshuffle and ministerial appointments"
    if action == "court_order":
        subject = next((x.replace("_", " ") for x in objects), None)
        return f"Court order{f' on {subject}' if subject else ''}{where}"[:512]
    if action == "political_negotiation":
        return f"Coalition seat-sharing talks{where}"[:512]
    if action == "diplomacy_meeting":
        participants = " and ".join(actors[:2])
        return f"Bilateral talks{f' involving {participants}' if participants else ''}{where}"[:512]
    if action == "landslide":
        return f"Landslide impacts{where}"[:512]
    if action == "flood":
        return f"Flooding impacts{where}"[:512]
    if action == "earthquake":
        return f"Earthquake reported{where}"[:512]
    if action == "road_accident":
        return f"Road accident reported{where}"[:512]
    if action == "sports_result":
        return f"Sports result involving {' and '.join(actors[:2])}"[:512]
    if action == "market_price" and objects:
        return f"{objects[0].title()} price movement{where}"[:512]
    if action == "monetary_policy":
        return f"Nepal Rastra Bank policy-rate decision{when}"[:512]
    if action == "legal_case":
        return f"Legal case involving {' and '.join(actors[:2])}"[:512]
    return fallback[:512]


def _story_frame(story: Story) -> dict[str, Any]:
    cached = _json(story.event_frame_json, None)
    if isinstance(cached, dict) and cached.get("version") == "event-frame-v1":
        return cached
    texts = [story.ai_headline or ""]
    texts.extend((a.original_headline or "") for a in (story.articles or [])[:6])
    frame = extract_event_frame("\n".join(texts))
    story.event_frame_json = json.dumps(frame, ensure_ascii=False)
    return frame


def _story_embedding(story: Story, active_model: str) -> list[float] | None:
    if story.embedding and story.embedding_model == active_model:
        return storage_to_vector(story.embedding)
    # Old installations stored vectors without a model id. Rebuild once rather
    # than comparing unrelated embedding spaces that happen to share a length.
    texts = [story.ai_headline or ""]
    texts.extend((a.original_headline or "") for a in (story.articles or [])[:6])
    text = "\n".join(t for t in texts if t)
    vector = embed_text(text, role="passage") if text else None
    if vector:
        story.embedding = vector_to_storage(vector)
        story.embedding_model = active_model
    return vector


def _candidate_stories(db: Session, published_at: datetime.datetime) -> list[Story]:
    update_hours = max(CLUSTER_UPDATE_WINDOW_HOURS, CLUSTER_TIME_WINDOW_HOURS)
    from_time = published_at - datetime.timedelta(hours=update_hours)
    to_time = published_at + datetime.timedelta(hours=6)
    story_ids = (
        select(Article.story_id)
        .where(
            Article.story_id.isnot(None),
            Article.published_at >= from_time,
            Article.published_at <= to_time,
        )
        .distinct()
        .limit(CLUSTER_CANDIDATE_LIMIT)
    )
    # Stories without attached articles are included for the API and test seed
    # flows. Production articles are retrieved primarily by publication time.
    return (
        db.query(Story)
        .filter(
            or_(
                Story.id.in_(story_ids),
                and_(Story.created_at >= from_time, Story.created_at <= to_time),
            )
        )
        .order_by(Story.updated_at.desc())
        .limit(CLUSTER_CANDIDATE_LIMIT)
        .all()
    )


def _merge_related_ids(story: Story, new_ids: set[int]) -> None:
    current = _json(story.related_stories_json, [])
    ids = {int(value) for value in current if str(value).isdigit()}
    ids.update(new_ids)
    ids.discard(story.id)
    story.related_stories_json = json.dumps(sorted(ids)) if ids else None


def get_or_create_story(
    db: Session,
    headline: str,
    category: str = "Nepal",
    published_at: datetime.datetime | None = None,
    content: str = "",
    language: str | None = None,
    entities: list[dict[str, Any]] | None = None,
    topics: list[str] | None = None,
    source_name: str | None = None,
) -> tuple[Story, dict[str, Any]]:
    """Match only SAME_EVENT/EVENT_UPDATE. Related events remain independent."""
    published_at = published_at or datetime.datetime.utcnow()
    story_text = f"{headline}\n{(content or '')[:1200]}".strip()
    active_model = model_id()
    semantic_available = active_model != _FALLBACK_MODEL
    vector = embed_text(story_text, role="query")
    frame = extract_event_frame(story_text, entities=entities, topics=topics or [category])
    candidates = _candidate_stories(db, published_at)

    best_story: Story | None = None
    best_match: dict[str, Any] | None = None
    best_rank = -1.0
    related_story_ids: set[int] = set()
    all_relations: list[dict[str, Any]] = []
    candidate_rows: list[dict[str, Any]] = []

    for story in candidates:
        if story.id is None:
            continue
        existing_articles = list(story.articles or [])
        dates = [a.published_at for a in existing_articles if a.published_at]
        reference_time = max(dates) if dates else (story.updated_at or story.created_at)
        gap = abs((published_at - reference_time).total_seconds()) / 3600 if reference_time else None
        if gap is not None and gap > CLUSTER_UPDATE_WINDOW_HOURS:
            continue

        old_vector = _story_embedding(story, active_model)
        semantic_similarity = cosine(vector, old_vector) if semantic_available and old_vector else None
        old_frame = _story_frame(story)
        relation = classify_event_relationship(
            frame,
            old_frame,
            semantic_similarity=semantic_similarity,
            semantic_model_available=semantic_available,
            left_time=published_at,
            right_time=reference_time,
            left_text=story_text,
            right_text="\n".join([story.ai_headline or ""] + [a.original_headline or "" for a in existing_articles[:4]]),
        )
        all_relations.append({"story_id": story.id, **relation})
        if relation["relationship"] == "DIRECTLY_RELATED_EVENT":
            related_story_ids.add(story.id)
        # A reranking score combines embedding relevance with event identity.
        # Hash/TF fallback vectors never participate in the merge decision.
        signals = relation.get("signals") or {}
        event_score = (
            0.28 * bool(signals.get("action_match"))
            + 0.24 * bool(signals.get("shared_locations"))
            + 0.22 * bool(signals.get("shared_event_objects"))
            + 0.16 * bool(signals.get("shared_actors"))
            + 0.10 * bool(signals.get("shared_time_markers"))
        )
        semantic_score = float(semantic_similarity or 0.0) if semantic_available else 0.0
        rank = 0.68 * float(relation.get("confidence") or 0) + 0.20 * event_score + 0.12 * semantic_score
        if relation["relationship"] in {"SAME_EVENT", "EVENT_UPDATE"}:
            if semantic_available and semantic_score < CLUSTER_SIMILARITY_THRESHOLD and event_score < 0.62:
                continue
            candidate_rows.append({
                "story": story,
                "relation": relation,
                "rank": rank,
                "event_score": event_score,
                "semantic_score": semantic_score,
                "hard_conflict": bool(signals.get("location_conflict") or signals.get("action_conflict")),
                "text": "\n".join([story.ai_headline or ""] + [a.original_headline or "" for a in existing_articles[:4]]),
            })
        elif (
            semantic_available
            and semantic_score >= 0.65
            and not signals.get("location_conflict")
            and not signals.get("action_conflict")
        ):
            # Semantic retrieval can surface paraphrases the event lexicon did
            # not fully parse. Only the top few ambiguous candidates reach NLI.
            candidate_rows.append({
                "story": story,
                "relation": relation,
                "rank": rank,
                "event_score": event_score,
                "semantic_score": semantic_score,
                "hard_conflict": False,
                "text": "\n".join([story.ai_headline or ""] + [a.original_headline or "" for a in existing_articles[:4]]),
            })

    candidate_rows.sort(key=lambda row: row["rank"], reverse=True)
    nli_rows = candidate_rows[:3] if semantic_available else []
    reranked = rerank_event_relationships([(story_text, row["text"]) for row in nli_rows])
    for row, nli_result in zip(nli_rows, reranked):
        if nli_result:
            if nli_result["relationship"] not in {"SAME_EVENT", "EVENT_UPDATE"} or row["hard_conflict"]:
                row["relation"] = {**row["relation"], **nli_result}
                row["rank"] = -1.0
                if nli_result["relationship"] == "DIRECTLY_RELATED_EVENT":
                    related_story_ids.add(row["story"].id)
                continue
            evidence = list(row["relation"].get("evidence") or [])
            evidence.append(f"English multilingual-NLI reranker selected {nli_result['relationship']} ({nli_result['confidence']:.2f}).")
            row["relation"] = {
                **row["relation"],
                **nli_result,
                "evidence": evidence,
                "signals": {**(row["relation"].get("signals") or {}), "nli_reranker": nli_result["model"]},
            }
            row["rank"] = 0.68 * float(nli_result["confidence"]) + 0.20 * row["event_score"] + 0.12 * row["semantic_score"]

    for row in candidate_rows:
        relation = row["relation"]
        if relation.get("relationship") not in {"SAME_EVENT", "EVENT_UPDATE"} or row["rank"] < 0:
            continue
        if row["rank"] > best_rank:
            best_story, best_match, best_rank = row["story"], relation, row["rank"]

    if best_story and best_match:
        old = storage_to_vector(best_story.embedding)
        article_count = len(best_story.articles or [])
        if old and len(old) == len(vector):
            denominator = max(1, article_count + 1)
            mixed = [((a * article_count) + b) / denominator for a, b in zip(old, vector)]
            best_story.embedding = vector_to_storage(mixed)
        else:
            best_story.embedding = vector_to_storage(vector)
        best_story.embedding_model = active_model
        merged_frame = dict(_story_frame(best_story))
        for key in ("actors", "locations", "objects", "event_markers", "years", "numbers", "topics"):
            merged_frame[key] = sorted(set(merged_frame.get(key) or []) | set(frame.get(key) or []))
        merged_frame["version"] = "event-frame-v1"
        merged_frame["signature"] = "|".join([
            merged_frame.get("action_family") or frame.get("action_family") or "",
            ",".join(merged_frame.get("locations") or []),
            ",".join(merged_frame.get("actors") or []),
            ",".join(merged_frame.get("objects") or []),
            ",".join(merged_frame.get("event_markers") or []),
            ",".join(merged_frame.get("years") or []),
        ])
        best_story.event_frame_json = json.dumps(merged_frame, ensure_ascii=False)
        if not best_story.title_is_corrected:
            best_story.ai_headline = _event_title(merged_frame, best_story.ai_headline)
        best_story.updated_at = datetime.datetime.utcnow()
        best_story.cluster_method = "event-frame+multilingual-embedding" if semantic_available else "event-frame-conservative"
        best_story.cluster_relationship = best_match["relationship"]
        best_story.cluster_confidence = round(float(best_match.get("confidence") or best_rank), 4)
        best_story.cluster_evidence_json = json.dumps(
            {"relationship": best_match["relationship"], "evidence": best_match.get("evidence", []), "signals": best_match.get("signals", {})},
            ensure_ascii=False,
        )
        sentence = _summary_sentence(content)
        if sentence and not best_story.summary_is_corrected:
            base_summary = best_story.ai_summary or ""
            if not base_summary:
                best_story.ai_summary = f"Initial report from {source_name or 'the source'}: {sentence}"
            elif published_at >= (max((a.published_at for a in (best_story.articles or []) if a.published_at), default=published_at)):
                base_summary = re.split(r"\s+Latest report from ", base_summary, maxsplit=1)[0]
                best_story.ai_summary = f"{base_summary} Latest report from {source_name or 'the source'}: {sentence}"
        if language:
            langs = set((best_story.languages or "").split(","))
            langs.discard("")
            langs.add(language)
            best_story.languages = ",".join(sorted(langs))
        if related_story_ids:
            _merge_related_ids(best_story, related_story_ids)
        db.flush()
        return best_story, {
            "matched": True,
            "relationship": best_match["relationship"],
            "method": best_story.cluster_method,
            "confidence": best_story.cluster_confidence,
            "embedding_model": active_model,
            "article_embedding": vector_to_storage(vector),
            "related_story_ids": sorted(related_story_ids - {best_story.id}),
        }

    story = Story(
        ai_headline=_event_title(frame, headline),
        topic=category,
        embedding=vector_to_storage(vector),
        embedding_model=active_model,
        event_frame_json=json.dumps(frame, ensure_ascii=False),
        languages=language or None,
        cluster_method="new_story_event_frame",
        cluster_relationship="NEW_EVENT",
        cluster_confidence=0.0 if not frame.get("action_family") and not frame.get("actors") else 1.0,
        cluster_evidence_json=json.dumps({"relationship": "NEW_EVENT", "evidence": ["No existing story met the event identity threshold."], "candidates": all_relations[:5]}, ensure_ascii=False),
        bias_left_pct=None,
        bias_center_pct=None,
        bias_right_pct=None,
    )
    sentence = _summary_sentence(content)
    if sentence:
        story.ai_summary = f"Initial report from {source_name or 'the source'}: {sentence}"
    if related_story_ids:
        story.related_stories_json = json.dumps(sorted(related_story_ids))
    db.add(story)
    db.flush()
    for other_id in related_story_ids:
        other = db.query(Story).filter(Story.id == other_id).first()
        if other:
            _merge_related_ids(other, {story.id})
    db.flush()
    return story, {
        "matched": False,
        "relationship": "NEW_EVENT",
        "method": story.cluster_method,
        "confidence": story.cluster_confidence,
        "embedding_model": active_model,
        "article_embedding": vector_to_storage(vector),
        "related_story_ids": sorted(related_story_ids),
    }


def rebuild_story_embedding(db: Session, story: Story) -> None:
    articles = list(story.articles or [])
    text = "\n".join([story.ai_headline or ""] + [a.original_headline or "" for a in articles[:20]])
    if not text.strip():
        return
    story.embedding = vector_to_storage(embed_text(text, role="passage"))
    story.embedding_model = model_id()
    story.event_frame_json = json.dumps(extract_event_frame(text), ensure_ascii=False)


def recluster_all(db: Session) -> dict[str, int]:
    """Rebuild event clusters from stored articles; admin-only and destructive."""
    articles = db.query(Article).order_by(Article.published_at.asc().nullsfirst(), Article.id.asc()).all()
    db.query(Story).delete()
    db.commit()

    assigned = 0
    for article in articles:
        topics = _json(article.topics_json, [])
        entities = _json(article.entities_json, [])
        story, _ = get_or_create_story(
            db,
            article.original_headline,
            category=topics[0] if topics else "Nepal",
            published_at=article.published_at,
            content=article.content_text or "",
            language=article.language or article.detected_language,
            entities=entities,
            topics=topics,
        )
        article.story_id = story.id
        assigned += 1
    db.commit()
    return {"articles_reassigned": assigned, "stories": db.query(Story).count()}
