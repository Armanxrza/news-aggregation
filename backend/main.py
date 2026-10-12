"""SajhaNews FastAPI application — Nepal news intelligence API."""

from __future__ import annotations

import asyncio
import datetime
import json
import logging
import os
import re
from threading import Lock
from typing import Any, Optional

from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

import config
import crawler
import database
from database import (
    AnalysisRun,
    Article,
    Claim,
    CrawlRun,
    Source,
    Story,
    StoryCorrection,
    _json_dumps,
    _json_loads,
)
from services.claims import analyze_article_claims
from services.clustering import recluster_all
from services.bias import analyze_political_bias
from services.framing import analyze_government_framing, framing_to_bias_pcts

logging.basicConfig(level=getattr(logging, config.LOG_LEVEL.upper(), logging.INFO))
logger = logging.getLogger("sajhanews")

database.init_db()

app = FastAPI(
    title="SajhaNews API",
    version=config.APP_VERSION,
    description="Nepal-focused news intelligence: aggregation, clustering, framing, claims.",
)

crawl_task = None
crawl_lock = Lock()

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS or ["http://localhost:3000"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()


def require_admin(x_admin_key: Optional[str] = Header(default=None)) -> None:
    expected = config.ADMIN_API_KEY
    # Allow unauthenticated only when explicitly disabled for local demos
    if os.getenv("ADMIN_AUTH_DISABLED", "false").lower() == "true":
        return
    if not x_admin_key or x_admin_key != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing X-Admin-Key")


def run_crawl_job():
    if not crawl_lock.acquire(blocking=False):
        logger.info("Crawl already running; skip")
        return
    try:
        crawler.crawl_rss()
    finally:
        crawl_lock.release()


async def crawl_scheduler():
    while True:
        await asyncio.to_thread(run_crawl_job)
        await asyncio.sleep(config.CRAWL_INTERVAL_SECONDS)


@app.on_event("startup")
async def start_crawl_scheduler():
    global crawl_task
    if config.ENABLE_CRAWL_SCHEDULER:
        crawl_task = asyncio.create_task(crawl_scheduler())
        logger.info("Crawl scheduler enabled (every %ss)", config.CRAWL_INTERVAL_SECONDS)


@app.on_event("shutdown")
async def stop_crawl_scheduler():
    if crawl_task:
        crawl_task.cancel()


# ── Schemas ──────────────────────────────────────────────────────────────────

class SourceCreate(BaseModel):
    name: str
    domain: str
    rss_url: Optional[str] = None
    language: Optional[str] = "en"
    category: Optional[str] = "Nepal"
    ownership_notes: Optional[str] = None
    transparency_notes: Optional[str] = None
    perspective_label: Optional[str] = "not_independently_rated"
    perspective_evidence: Optional[str] = None
    default_bias: Optional[float] = None  # legacy ignored for public ideology


class SourceUpdate(BaseModel):
    name: Optional[str] = None
    rss_url: Optional[str] = None
    language: Optional[str] = None
    is_active: Optional[bool] = None
    category: Optional[str] = None
    ownership_notes: Optional[str] = None
    transparency_notes: Optional[str] = None
    perspective_label: Optional[str] = None
    perspective_evidence: Optional[str] = None


class MergeStoriesBody(BaseModel):
    source_story_id: int
    target_story_id: int
    note: Optional[str] = None


class SplitStoryBody(BaseModel):
    story_id: int
    article_ids: list[int] = Field(min_length=1)
    note: Optional[str] = None


# ── Helpers ──────────────────────────────────────────────────────────────────

FRAMING_BUCKETS = (
    "government_critical",
    "government_neutral",
    "government_supportive",
    "insufficient_evidence",
    "analysis_unavailable",
    "unclassified",
)


def framing_counts_for_articles(articles: list[Any]) -> dict[str, int]:
    counts = {k: 0 for k in FRAMING_BUCKETS}
    for article in articles:
        label, _scores = _ensure_article_framing(article)
        if label in counts:
            counts[label] += 1
        else:
            counts["government_neutral"] += 1
    return counts


def _ensure_article_framing(article: Any, *, persist: bool = False) -> tuple[str, dict[str, float]]:
    """Return (label, soft scores). Always has critical/neutral/supportive mix."""
    stored = _json_loads(getattr(article, "framing_scores_json", None), None)
    label = getattr(article, "government_framing", None)
    if (
        isinstance(stored, dict)
        and {"critical", "neutral", "supportive"} <= set(stored.keys())
        and label in {"government_critical", "government_neutral", "government_supportive"}
    ):
        return label, {
            "critical": float(stored["critical"]),
            "neutral": float(stored["neutral"]),
            "supportive": float(stored["supportive"]),
        }

    text = f"{getattr(article, 'original_headline', '') or ''}\n{getattr(article, 'content_text', '') or ''}"
    result = analyze_government_framing(text, lexical_only=True)
    label = result["label"]
    scores = result.get("scores") or {"critical": 0.2, "neutral": 0.55, "supportive": 0.25}

    if persist and isinstance(article, Article):
        article.government_framing = label
        article.framing_confidence = result.get("confidence")
        article.framing_evidence = result.get("evidence")
        article.framing_model = result.get("model")
        article.framing_method = result.get("method")
        article.framing_scores_json = _json_dumps(scores)
    else:
        try:
            article.government_framing = label
            article.framing_scores_json = _json_dumps(scores)
        except Exception:  # noqa: BLE001
            pass
    return label, scores


def _ensure_article_bias(article: Any, *, persist: bool = False, lexical_only: bool = True) -> str:
    """Legacy L/C/R helper (kept for admin/analytics)."""
    label = getattr(article, "political_bias", None)
    if label in {"left", "center", "right"}:
        return label
    text = f"{getattr(article, 'original_headline', '') or ''}\n{getattr(article, 'content_text', '') or ''}"
    result = analyze_political_bias(text, lexical_only=lexical_only)
    label = result["label"]
    if persist and isinstance(article, Article):
        article.political_bias = label
        article.bias_confidence = result.get("confidence")
        article.bias_evidence = result.get("evidence")
        article.bias_model = result.get("model")
        article.ai_bias_score = result.get("score")
    elif not isinstance(article, Article):
        article.political_bias = label
    return label


def story_to_dto(story: Story, articles: list[Article] | None = None) -> dict[str, Any]:
    articles = articles if articles is not None else list(story.articles or [])
    sources = sorted({a.source.name for a in articles if a.source})
    languages = sorted({
        (a.language or a.detected_language or (a.source.language if a.source else None) or "unknown")
        for a in articles
    })
    thumbs = [a.thumbnail_url for a in articles if a.thumbnail_url]
    thumbs.sort(key=lambda u: (0 if "/240/" in (u or "") else 1, len(u or "")), reverse=True)
    latest = max((a.published_at for a in articles if a.published_at), default=story.created_at)

    # Soft government-POV mix averaged across outlets (variable per story)
    score_rows: list[dict[str, float]] = []
    source_bias = []
    seen_sources: set[str] = set()
    for a in articles:
        label, scores = _ensure_article_framing(a)
        score_rows.append(scores)
        name = a.source.name if getattr(a, "source", None) else None
        if name and name not in seen_sources:
            seen_sources.add(name)
            source_bias.append({
                "source": name,
                "pov": label.replace("government_", ""),
                "scores": {
                    "critical": round(100 * scores["critical"]),
                    "neutral": round(100 * scores["neutral"]),
                    "supportive": round(100 * scores["supportive"]),
                },
            })
    gov_pcts = framing_to_bias_pcts(score_rows)
    framing_counts = framing_counts_for_articles(articles)

    return {
        "id": story.id,
        "ai_headline": story.ai_headline,
        "ai_summary": story.ai_summary,
        "topic": story.topic,
        # Mapped: left=Critical of gov, center=Neutral, right=Supportive of gov
        "bias_left_pct": gov_pcts["bias_left_pct"],
        "bias_center_pct": gov_pcts["bias_center_pct"],
        "bias_right_pct": gov_pcts["bias_right_pct"],
        "bias_axis": "government_pov",
        "gov_counts": {
            "critical": gov_pcts["gov_critical"],
            "neutral": gov_pcts["gov_neutral"],
            "supportive": gov_pcts["gov_supportive"],
        },
        "source_bias": source_bias[:8],
        "created_at": (latest or story.created_at).isoformat() if (latest or story.created_at) else None,
        "source_count": len({a.source_id for a in articles}),
        "article_count": len(articles),
        "thumbnail_url": thumbs[0] if thumbs else None,
        "sources": sources,
        "languages": [l for l in languages if l],
        "framing_counts": framing_counts,
        "cluster_method": story.cluster_method,
        "cluster_confidence": story.cluster_confidence,
    }


def article_to_dto(article: Article) -> dict[str, Any]:
    snippet = (article.content_text or "")[:280]
    return {
        "id": article.id,
        "source_name": article.source.name if article.source else "Unknown",
        "source_domain": article.source.domain if article.source else "",
        "source_language": (
            article.language
            or article.detected_language
            or (article.source.language if article.source else None)
            or "en"
        ),
        "source_bias": None,
        "perspective_label": article.source.perspective_label if article.source else None,
        "original_headline": article.original_headline,
        "url": article.url,
        "thumbnail_url": article.thumbnail_url,
        "published_at": article.published_at.isoformat() if article.published_at else None,
        "snippet": snippet or None,
        "political_bias": _ensure_article_bias(article),
        "bias_confidence": article.bias_confidence,
        "bias_evidence": article.bias_evidence,
        "bias_model": article.bias_model,
        "government_framing": _ensure_article_framing(article, persist=True)[0],
        "framing_confidence": article.framing_confidence,
        "framing_model": article.framing_model,
        "framing_evidence": article.framing_evidence,
        "framing_method": article.framing_method,
        "framing_scores": _json_loads(article.framing_scores_json, None),
        "entities": _json_loads(article.entities_json, []),
        "topics": _json_loads(article.topics_json, []),
        "signals": _json_loads(article.signals_json, {}),
    }


def claim_to_dto(claim: Claim) -> dict[str, Any]:
    evidence = _json_loads(claim.evidence_json, {})
    return {
        "id": claim.id,
        "article_id": claim.article_id,
        "story_id": claim.story_id,
        "claim_text": claim.claim_text,
        "status": claim.status,
        "confidence": claim.confidence,
        "evidence": evidence,
        "model": claim.model,
        "created_at": claim.created_at.isoformat() if claim.created_at else None,
    }


def source_to_dto(source: Source, db: Session | None = None) -> dict[str, Any]:
    framing = None
    if db is not None:
        rows = (
            db.query(Article.government_framing, func.count(Article.id))
            .filter(Article.source_id == source.id)
            .group_by(Article.government_framing)
            .all()
        )
        framing = { (label or "unclassified"): count for label, count in rows }
    return {
        "id": source.id,
        "name": source.name,
        "domain": source.domain,
        "rss_url": source.rss_url,
        "default_bias": None,
        "language": source.language,
        "is_active": source.is_active,
        "category": source.category,
        "ownership_notes": source.ownership_notes,
        "transparency_notes": source.transparency_notes,
        "perspective_label": source.perspective_label or "not_independently_rated",
        "perspective_confidence": source.perspective_confidence,
        "perspective_evidence": source.perspective_evidence,
        "last_crawl_at": source.last_crawl_at.isoformat() if source.last_crawl_at else None,
        "last_crawl_status": source.last_crawl_status,
        "last_error": source.last_error,
        "article_count": source.article_count or 0,
        "framing_history": framing,
    }


# ── Routes ───────────────────────────────────────────────────────────────────

@app.get("/")
@app.get("/api")
@app.get("/api/")
def root():
    return {
        "status": "online",
        "service": "SajhaNews API",
        "version": config.APP_VERSION,
        "docs": "/docs",
        "features": [
            "rss_ingestion",
            "multilingual_clustering",
            "government_framing",
            "claim_assistance",
            "source_profiles",
            "analytics",
        ],
        "models": {
            "framing": config.FINETUNED_MODEL_PATH or config.HF_FRAMING_MODEL,
            "embedding": config.HF_EMBEDDING_MODEL,
            "nepal_finetuned": bool(config.FINETUNED_MODEL_PATH),
        },
    }


@app.get("/api/health")
@app.get("/health")
def health(db: Session = Depends(get_db)):
    try:
        stories = db.query(func.count(Story.id)).scalar() or 0
        articles = db.query(func.count(Article.id)).scalar() or 0
        return {
            "ok": True,
            "database": "up",
            "stories": stories,
            "articles": articles,
            "scheduler": config.ENABLE_CRAWL_SCHEDULER,
        }
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/api/sources")
@app.get("/sources")
def list_sources(db: Session = Depends(get_db)):
    sources = db.query(Source).order_by(Source.name.asc()).all()
    return [source_to_dto(s, db) for s in sources]


@app.get("/api/sources/{source_id}")
@app.get("/sources/{source_id}")
def get_source(source_id: int, db: Session = Depends(get_db)):
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise HTTPException(404, "Source not found")
    recent = (
        db.query(Article)
        .options(joinedload(Article.source))
        .filter(Article.source_id == source_id)
        .order_by(Article.published_at.desc().nullslast())
        .limit(20)
        .all()
    )
    dto = source_to_dto(source, db)
    dto["recent_articles"] = [article_to_dto(a) for a in recent]
    return dto


@app.post("/api/sources")
@app.post("/sources")
def create_source(
    payload: SourceCreate,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    if db.query(Source).filter(Source.domain == payload.domain).first():
        raise HTTPException(400, "Domain already exists")
    source = Source(
        name=payload.name,
        domain=payload.domain,
        rss_url=payload.rss_url,
        language=payload.language or "en",
        category=payload.category,
        ownership_notes=payload.ownership_notes,
        transparency_notes=payload.transparency_notes,
        perspective_label=payload.perspective_label,
        perspective_evidence=payload.perspective_evidence,
        is_active=True,
        default_bias=None,
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return source_to_dto(source, db)


@app.patch("/api/sources/{source_id}")
@app.patch("/sources/{source_id}")
def update_source(
    source_id: int,
    payload: SourceUpdate,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise HTTPException(404, "Source not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(source, field, value)
    db.commit()
    db.refresh(source)
    return source_to_dto(source, db)


@app.delete("/api/sources/{source_id}")
@app.delete("/sources/{source_id}")
def delete_source(
    source_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise HTTPException(404, "Source not found")
    article_count = db.query(Article).filter(Article.source_id == source_id).count()
    if article_count:
        source.is_active = False
        db.commit()
        return {"message": "Source deactivated (has articles)", "id": source_id}
    db.delete(source)
    db.commit()
    return {"message": "Source deleted", "id": source_id}


@app.get("/api/stats")
@app.get("/stats")
def stats(db: Session = Depends(get_db)):
    return {
        "total_stories": db.query(func.count(Story.id)).scalar() or 0,
        "total_articles": db.query(func.count(Article.id)).scalar() or 0,
        "total_sources": db.query(func.count(Source.id)).scalar() or 0,
        "active_sources": db.query(func.count(Source.id)).filter(Source.is_active.is_(True)).scalar() or 0,
        "nepali_sources": db.query(func.count(Source.id)).filter(Source.language == "ne").scalar() or 0,
        "claims": db.query(func.count(Claim.id)).scalar() or 0,
        "crawl_runs": db.query(func.count(CrawlRun.id)).scalar() or 0,
    }


@app.get("/api/topics")
@app.get("/topics")
def topics(db: Session = Depends(get_db)):
    rows = (
        db.query(Story.topic, func.count(Story.id))
        .filter(Story.topic.isnot(None))
        .group_by(Story.topic)
        .order_by(func.count(Story.id).desc())
        .all()
    )
    return [{"topic": topic, "count": count} for topic, count in rows if topic]


@app.get("/api/coverage-distribution")
@app.get("/coverage-distribution")
def coverage_distribution(db: Session = Depends(get_db)):
    articles = db.query(Article).all()
    counts = framing_counts_for_articles(articles)
    classified = (
        counts["government_critical"]
        + counts["government_neutral"]
        + counts["government_supportive"]
    )
    today = datetime.datetime.utcnow().date()
    today_articles = sum(
        1 for a in articles if a.published_at and a.published_at.date() == today
    )
    latest = max((a.published_at for a in articles if a.published_at), default=None)
    # Backward-compatible nested counts for older frontend
    legacy_counts = {
        "government_critical": counts["government_critical"],
        "government_neutral": counts["government_neutral"],
        "government_supportive": counts["government_supportive"],
        "unclassified": (
            counts["unclassified"]
            + counts["insufficient_evidence"]
            + counts["analysis_unavailable"]
        ),
        "insufficient_evidence": counts["insufficient_evidence"],
        "analysis_unavailable": counts["analysis_unavailable"],
    }
    bias_counts = {"left": 0, "center": 0, "right": 0}
    for a in articles:
        lab = _ensure_article_bias(a, persist=False, lexical_only=True)
        bias_counts[lab] = bias_counts.get(lab, 0) + 1

    return {
        "total_articles": len(articles),
        "classified_articles": classified,
        "today_articles": today_articles,
        "latest_published_at": latest.isoformat() if latest else None,
        "counts": legacy_counts,
        "bias_counts": bias_counts,
    }


@app.get("/api/stories")
@app.get("/stories")
def list_stories(
    topic: Optional[str] = None,
    lang: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    min_sources: int = Query(1, ge=1),
    db: Session = Depends(get_db),
):
    # Prefetch article aggregates to avoid N+1 and full ORM graph for every story
    article_rows = (
        db.query(
            Article.story_id,
            Article.source_id,
            Article.published_at,
            Article.thumbnail_url,
            Article.language,
            Article.detected_language,
            Article.government_framing,
            Article.political_bias,
            Article.original_headline,
            Article.content_text,
            Source.name.label("source_name"),
            Source.language.label("source_language"),
        )
        .join(Source, Source.id == Article.source_id)
        .filter(Article.story_id.isnot(None))
        .all()
    )
    by_story: dict[int, list[Any]] = {}
    for row in article_rows:
        by_story.setdefault(row.story_id, []).append(row)

    q = db.query(Story)
    if topic and topic.lower() != "all":
        q = q.filter(Story.topic.ilike(topic))
    if search and search.strip():
        q = q.filter(Story.ai_headline.ilike(f"%{search.strip()}%"))
    stories = q.all()

    results: list[dict[str, Any]] = []
    search_l = (search or "").strip().casefold()
    for story in stories:
        rows = by_story.get(story.id, [])
        if not rows:
            continue
        if lang and lang.lower() != "all":
            rows = [
                r for r in rows
                if (r.language or r.detected_language or r.source_language or "") == lang
            ]
            if not rows:
                continue
        if search_l:
            hay = " ".join(
                [story.ai_headline or ""]
                + [r.original_headline or "" for r in rows]
            ).casefold()
            if search_l not in hay:
                continue
        source_ids = {r.source_id for r in rows}
        if len(source_ids) < min_sources:
            continue

        # Build a lightweight article-like view for DTO helper
        class _A:
            pass

        articles_proxy = []
        for r in rows:
            a = _A()
            a.source_id = r.source_id
            a.published_at = r.published_at
            a.thumbnail_url = r.thumbnail_url
            a.language = r.language
            a.detected_language = r.detected_language
            a.government_framing = r.government_framing
            a.political_bias = r.political_bias
            a.original_headline = r.original_headline
            a.content_text = (r.content_text or "")[:500]
            src = _A()
            src.name = r.source_name
            src.language = r.source_language
            a.source = src
            articles_proxy.append(a)

        dto = story_to_dto(story, articles_proxy)
        results.append(dto)

    def _nepal_rank(s: dict[str, Any]) -> int:
        topic = (s.get("topic") or "").casefold()
        langs = s.get("languages") or []
        headline = s.get("ai_headline") or ""
        score = 0
        if topic == "nepal":
            score += 3
        elif topic in {"politics", "disaster", "business"}:
            score += 2
        elif topic == "world":
            score -= 2
        if "ne" in langs or "ne-rom" in langs:
            score += 1
        if re.search(r"nepal|नेपाल|काठमाडौं|kathmandu", headline, re.I):
            score += 1
        return score

    # Nepal bucket first, then multi-source, then newest
    results.sort(
        key=lambda s: (
            1 if _nepal_rank(s) > 0 else 0,
            s["source_count"],
            _nepal_rank(s),
            s.get("created_at") or "",
        ),
        reverse=True,
    )
    total = len(results)
    page = results[skip : skip + limit]
    return {
        "items": page,
        "total": total,
        "skip": skip,
        "limit": limit,
        "has_more": skip + limit < total,
    }


@app.get("/api/stories/{story_id}")
@app.get("/stories/{story_id}")
def get_story(story_id: int, db: Session = Depends(get_db)):
    story = (
        db.query(Story)
        .options(joinedload(Story.articles).joinedload(Article.source))
        .filter(Story.id == story_id)
        .first()
    )
    if not story:
        raise HTTPException(404, "Story not found")
    articles = sorted(
        story.articles or [],
        key=lambda a: a.published_at or datetime.datetime.min,
        reverse=True,
    )
    dto = story_to_dto(story, articles)
    dto["articles"] = [article_to_dto(a) for a in articles]

    # Headline comparison matrix
    comparison = []
    for a in articles:
        label, scores = _ensure_article_framing(a, persist=True)
        comparison.append({
            "source": a.source.name if a.source else "Unknown",
            "language": a.language or a.detected_language or (a.source.language if a.source else None),
            "headline": a.original_headline,
            "framing": label,
            "bias": label.replace("government_", ""),
            "scores": {
                "critical": round(100 * scores["critical"]),
                "neutral": round(100 * scores["neutral"]),
                "supportive": round(100 * scores["supportive"]),
            },
            "url": a.url,
        })
    dto["headline_comparison"] = comparison
    db.commit()

    claims = db.query(Claim).filter(Claim.story_id == story_id).all()
    dto["claims"] = [claim_to_dto(c) for c in claims]

    # Coverage gap: outlets in registry not covering this story
    covering = {a.source_id for a in articles}
    all_active = db.query(Source).filter(Source.is_active.is_(True)).all()
    dto["coverage_gap"] = [
        {"id": s.id, "name": s.name, "domain": s.domain, "language": s.language}
        for s in all_active
        if s.id not in covering
    ][:40]
    dto["methodology_note"] = (
        "Coverage gap lists active registered outlets without an article in this cluster. "
        "It is an observable registry gap, not a judgment that an outlet 'should' have covered the event."
    )
    return dto


@app.get("/api/search")
@app.get("/search")
def search(
    q: str = Query(..., min_length=1),
    lang: Optional[str] = None,
    limit: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
):
    term = f"%{q.strip()}%"
    article_q = (
        db.query(Article)
        .options(joinedload(Article.source), joinedload(Article.story))
        .filter(
            or_(
                Article.original_headline.ilike(term),
                Article.content_text.ilike(term),
            )
        )
    )
    if lang and lang.lower() != "all":
        article_q = article_q.filter(
            or_(Article.language == lang, Article.detected_language == lang)
        )
    articles = article_q.order_by(Article.published_at.desc().nullslast()).limit(limit).all()

    story_q = db.query(Story).filter(Story.ai_headline.ilike(term)).limit(limit).all()
    return {
        "query": q,
        "stories": [story_to_dto(s) for s in story_q],
        "articles": [article_to_dto(a) for a in articles],
    }


@app.get("/api/analytics/overview")
@app.get("/analytics/overview")
def analytics_overview(db: Session = Depends(get_db)):
    articles = db.query(Article).all()
    sources = db.query(Source).all()
    by_lang: dict[str, int] = {}
    by_topic: dict[str, int] = {}
    for a in articles:
        lang = a.language or a.detected_language or "unknown"
        by_lang[lang] = by_lang.get(lang, 0) + 1
        for topic in _json_loads(a.topics_json, []) or []:
            by_topic[topic] = by_topic.get(topic, 0) + 1

    framing = framing_counts_for_articles(articles)
    claim_rows = (
        db.query(Claim.status, func.count(Claim.id)).group_by(Claim.status).all()
    )
    last_crawl = db.query(CrawlRun).order_by(CrawlRun.started_at.desc()).first()
    return {
        "articles_by_language": by_lang,
        "articles_by_topic": dict(sorted(by_topic.items(), key=lambda x: -x[1])[:15]),
        "framing": framing,
        "claims_by_status": {status: count for status, count in claim_rows},
        "sources_active": sum(1 for s in sources if s.is_active),
        "sources_total": len(sources),
        "last_crawl": {
            "id": last_crawl.id,
            "started_at": last_crawl.started_at.isoformat() if last_crawl and last_crawl.started_at else None,
            "status": last_crawl.status if last_crawl else None,
            "articles_new": last_crawl.articles_new if last_crawl else None,
            "feeds_failed": last_crawl.feeds_failed if last_crawl else None,
        } if last_crawl else None,
    }


@app.get("/api/claims")
@app.get("/claims")
def list_claims(
    status: Optional[str] = None,
    story_id: Optional[int] = None,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    q = db.query(Claim).order_by(Claim.created_at.desc())
    if status:
        q = q.filter(Claim.status == status)
    if story_id:
        q = q.filter(Claim.story_id == story_id)
    return [claim_to_dto(c) for c in q.limit(limit).all()]


@app.post("/api/stories/{story_id}/analyze-claims")
@app.post("/stories/{story_id}/analyze-claims")
def analyze_story_claims(
    story_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    story = (
        db.query(Story)
        .options(joinedload(Story.articles))
        .filter(Story.id == story_id)
        .first()
    )
    if not story:
        raise HTTPException(404, "Story not found")
    run = AnalysisRun(kind="claims", status="running", model="embedding-crosscheck-v1")
    db.add(run)
    db.commit()
    total = 0
    for article in story.articles or []:
        analyze_article_claims(db, article, replace=True)
        total += 1
    run.status = "completed"
    run.finished_at = datetime.datetime.utcnow()
    run.items_processed = total
    db.commit()
    claims = db.query(Claim).filter(Claim.story_id == story_id).all()
    return {"processed_articles": total, "claims": [claim_to_dto(c) for c in claims]}


@app.post("/api/articles/{article_id}/analyze-framing")
@app.post("/articles/{article_id}/analyze-framing")
def analyze_article_framing(
    article_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(404, "Article not found")
    result = analyze_government_framing(
        f"{article.original_headline}\n{article.content_text or ''}"
    )
    article.government_framing = result["label"]
    article.framing_confidence = result.get("confidence")
    article.framing_model = result.get("model")
    article.framing_evidence = result.get("evidence")
    article.framing_method = result.get("method")
    db.commit()
    return article_to_dto(article)


@app.post("/api/stories/merge")
@app.post("/stories/merge")
def merge_stories(
    body: MergeStoriesBody,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    if body.source_story_id == body.target_story_id:
        raise HTTPException(400, "Stories must differ")
    source = db.query(Story).filter(Story.id == body.source_story_id).first()
    target = db.query(Story).filter(Story.id == body.target_story_id).first()
    if not source or not target:
        raise HTTPException(404, "Story not found")
    moved = (
        db.query(Article)
        .filter(Article.story_id == source.id)
        .update({Article.story_id: target.id})
    )
    db.add(
        StoryCorrection(
            action="merge",
            source_story_id=source.id,
            target_story_id=target.id,
            note=body.note,
        )
    )
    db.delete(source)
    db.commit()
    return {"moved_articles": moved, "target_story_id": target.id}


@app.post("/api/stories/split")
@app.post("/stories/split")
def split_story(
    body: SplitStoryBody,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    story = db.query(Story).filter(Story.id == body.story_id).first()
    if not story:
        raise HTTPException(404, "Story not found")
    articles = (
        db.query(Article)
        .filter(Article.id.in_(body.article_ids), Article.story_id == story.id)
        .all()
    )
    if not articles:
        raise HTTPException(400, "No matching articles in story")
    new_story = Story(
        ai_headline=articles[0].original_headline,
        topic=story.topic,
        cluster_method="admin_split",
        cluster_confidence=1.0,
    )
    db.add(new_story)
    db.flush()
    for article in articles:
        article.story_id = new_story.id
    db.add(
        StoryCorrection(
            action="split",
            source_story_id=story.id,
            target_story_id=new_story.id,
            article_ids_json=json.dumps(body.article_ids),
            note=body.note,
        )
    )
    db.commit()
    db.refresh(new_story)
    return {"new_story_id": new_story.id, "article_ids": body.article_ids}


@app.post("/api/recluster")
@app.post("/recluster")
def recluster(
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    result = recluster_all(db)
    return result


@app.get("/api/crawl-runs")
@app.get("/crawl-runs")
def crawl_runs(limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    rows = db.query(CrawlRun).order_by(CrawlRun.started_at.desc()).limit(limit).all()
    return [
        {
            "id": r.id,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "finished_at": r.finished_at.isoformat() if r.finished_at else None,
            "status": r.status,
            "feeds_attempted": r.feeds_attempted,
            "feeds_succeeded": r.feeds_succeeded,
            "feeds_failed": r.feeds_failed,
            "articles_new": r.articles_new,
            "errors": _json_loads(r.errors_json, []),
        }
        for r in rows
    ]


@app.post("/api/crawl")
@app.post("/crawl")
def trigger_crawl(
    background_tasks: BackgroundTasks,
    _: None = Depends(require_admin),
):
    background_tasks.add_task(run_crawl_job)
    return {"message": "Crawl started in background"}


# Backward-compatible list shape: some clients expect a bare array.
# Provide /api/stories/list/raw that always returns items array only — frontend will be updated.
@app.get("/api/stories/raw")
def list_stories_raw(
    topic: Optional[str] = None,
    lang: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    payload = list_stories(topic=topic, lang=lang, search=search, skip=skip, limit=limit, db=db)
    return payload["items"]
