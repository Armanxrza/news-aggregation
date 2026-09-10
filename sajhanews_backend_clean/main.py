from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional

import database
import crawler

# Initialize DB
database.init_db()

app = FastAPI(title="SajhaNews Backend")

# Enable CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
@app.get("/api")
@app.get("/api/")
def root():
    return {
        "status": "online",
        "service": "SajhaNews API",
        "docs": "/docs",
        "version": "1.0.0"
    }

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ─────────────────────────────────────────────
# Sources
# ─────────────────────────────────────────────

class SourceCreate(BaseModel):
    name: str
    domain: str
    rss_url: Optional[str] = None
    default_bias: Optional[float] = 0.0
    language: Optional[str] = "en"

class SourceResponse(BaseModel):
    id: int
    name: str
    domain: str
    rss_url: Optional[str]
    default_bias: Optional[float]
    language: Optional[str]
    is_active: bool

    class Config:
        from_attributes = True

@app.post("/sources", response_model=SourceResponse)
@app.post("/api/sources", response_model=SourceResponse)
def create_source(source: SourceCreate, db: Session = Depends(get_db)):
    existing = db.query(database.Source).filter(database.Source.domain == source.domain).first()
    if existing:
        raise HTTPException(status_code=400, detail="Domain already exists")
    db_source = database.Source(**source.model_dump())
    db.add(db_source)
    db.commit()
    db.refresh(db_source)
    return db_source

@app.get("/sources", response_model=List[SourceResponse])
@app.get("/api/sources", response_model=List[SourceResponse])
def get_sources(db: Session = Depends(get_db)):
    return db.query(database.Source).all()

@app.delete("/sources/{source_id}")
@app.delete("/api/sources/{source_id}")
def delete_source(source_id: int, db: Session = Depends(get_db)):
    source = db.query(database.Source).filter(database.Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    db.delete(source)
    db.commit()
    return {"message": f"Source {source_id} deleted"}

# ─────────────────────────────────────────────
# Stats
# ─────────────────────────────────────────────

class StatsResponse(BaseModel):
    total_stories: int
    total_articles: int
    total_sources: int
    active_sources: int
    nepali_sources: int

@app.get("/stats", response_model=StatsResponse)
@app.get("/api/stats", response_model=StatsResponse)
def get_stats(db: Session = Depends(get_db)):
    return {
        "total_stories": db.query(database.Story).count(),
        "total_articles": db.query(database.Article).count(),
        "total_sources": db.query(database.Source).count(),
        "active_sources": db.query(database.Source).filter(database.Source.is_active == True).count(),
        "nepali_sources": db.query(database.Source).filter(database.Source.language == "ne").count(),
    }

# ─────────────────────────────────────────────
# Stories
# ─────────────────────────────────────────────

class ArticleInStory(BaseModel):
    """A single article/source perspective on a story."""
    id: int
    source_name: str
    source_domain: str
    source_language: str
    source_bias: Optional[float]
    original_headline: str
    url: str
    thumbnail_url: Optional[str]
    published_at: Optional[str]
    snippet: Optional[str]  # first ~240 chars of content_text

class StoryResponse(BaseModel):
    id: int
    ai_headline: str
    ai_summary: Optional[str]
    topic: Optional[str]
    bias_left_pct: float
    bias_center_pct: float
    bias_right_pct: float
    created_at: str
    source_count: int
    thumbnail_url: Optional[str]
    sources: List[str]
    languages: List[str]

    class Config:
        from_attributes = True

class StoryDetailResponse(StoryResponse):
    articles: List[ArticleInStory]

def _build_story_base(s, articles, db) -> dict:
    """Build the shared story response dict from a story + its articles."""
    source_count = len(articles)
    thumbnail_url = next((a.thumbnail_url for a in articles if a.thumbnail_url), None)
    seen: set = set()
    source_names: List[str] = []
    langs: List[str] = []
    for a in articles:
        src = db.query(database.Source).filter(database.Source.id == a.source_id).first()
        if src and src.name not in seen:
            seen.add(src.name)
            source_names.append(src.name)
            lang = src.language or "en"
            if lang not in langs:
                langs.append(lang)
    return {
        "id": s.id,
        "ai_headline": s.ai_headline,
        "ai_summary": s.ai_summary,
        "topic": s.topic or "World",
        "bias_left_pct": s.bias_left_pct,
        "bias_center_pct": s.bias_center_pct,
        "bias_right_pct": s.bias_right_pct,
        "created_at": s.created_at.isoformat(),
        "source_count": source_count,
        "thumbnail_url": thumbnail_url,
        "sources": source_names,
        "languages": langs,
    }

@app.get("/topics")
@app.get("/api/topics")
def get_topics(db: Session = Depends(get_db)):
    from sqlalchemy import func
    topics = (
        db.query(database.Story.topic, func.count(database.Story.id))
        .filter(database.Story.topic.isnot(None))
        .group_by(database.Story.topic)
        .all()
    )
    return [{"topic": t, "count": cnt} for t, cnt in topics if t]

@app.get("/stories", response_model=List[StoryResponse])
@app.get("/api/stories", response_model=List[StoryResponse])
def get_stories(
    topic: Optional[str] = None,
    lang: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    # Compatibility if invoked positionally with Session
    if isinstance(topic, Session):
        db = topic
        topic = None

    query = db.query(database.Story)

    if topic and topic.strip() and topic.lower() != "all":
        query = query.filter(database.Story.topic.ilike(f"%{topic.strip()}%"))

    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.filter(database.Story.ai_headline.ilike(term))

    if lang and lang.strip() and lang.lower() != "all":
        query = (
            query.join(database.Article, database.Story.id == database.Article.story_id)
            .join(database.Source, database.Article.source_id == database.Source.id)
            .filter(database.Source.language == lang.strip())
            .distinct()
        )

    stories = (
        query.order_by(database.Story.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    sources_by_id = {src.id: src for src in db.query(database.Source).all()}
    story_ids = [s.id for s in stories]
    articles = (
        db.query(database.Article).filter(database.Article.story_id.in_(story_ids)).all()
        if story_ids
        else []
    )
    articles_by_story: dict = {}
    for a in articles:
        articles_by_story.setdefault(a.story_id, []).append(a)

    result = []
    for s in stories:
        s_articles = articles_by_story.get(s.id, [])
        source_count = len(s_articles)
        thumbnail_url = next((a.thumbnail_url for a in s_articles if a.thumbnail_url), None)
        seen: set = set()
        source_names: List[str] = []
        langs: List[str] = []
        for a in s_articles:
            src = sources_by_id.get(a.source_id)
            if src and src.name not in seen:
                seen.add(src.name)
                source_names.append(src.name)
                s_lang = src.language or "en"
                if s_lang not in langs:
                    langs.append(s_lang)
        result.append({
            "id": s.id,
            "ai_headline": s.ai_headline,
            "ai_summary": s.ai_summary,
            "topic": s.topic or "World",
            "bias_left_pct": s.bias_left_pct,
            "bias_center_pct": s.bias_center_pct,
            "bias_right_pct": s.bias_right_pct,
            "created_at": s.created_at.isoformat(),
            "source_count": source_count,
            "thumbnail_url": thumbnail_url,
            "sources": source_names,
            "languages": langs,
        })
    return result

@app.get("/stories/{story_id}", response_model=StoryDetailResponse)
@app.get("/api/stories/{story_id}", response_model=StoryDetailResponse)
def get_story_detail(story_id: int, db: Session = Depends(get_db)):
    s = db.query(database.Story).filter(database.Story.id == story_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Story not found")

    articles = (
        db.query(database.Article)
        .filter(database.Article.story_id == story_id)
        .order_by(database.Article.published_at.desc())
        .all()
    )
    sources_by_id = {src.id: src for src in db.query(database.Source).all()}

    base = _build_story_base(s, articles, db)

    article_list: List[dict] = []
    for a in articles:
        src = sources_by_id.get(a.source_id)
        article_list.append({
            "id": a.id,
            "source_name": src.name if src else "Unknown",
            "source_domain": src.domain if src else "",
            "source_language": src.language if src else "en",
            "source_bias": src.default_bias if src else None,
            "original_headline": a.original_headline,
            "url": a.url,
            "thumbnail_url": a.thumbnail_url,
            "published_at": a.published_at.isoformat() if a.published_at else None,
            "snippet": (a.content_text or "")[:240].strip() or None,
        })

    return {**base, "articles": article_list}

# ─────────────────────────────────────────────
# Crawl trigger
# ─────────────────────────────────────────────

@app.post("/crawl")
@app.post("/api/crawl")
def trigger_crawl(background_tasks: BackgroundTasks):
    """Trigger the RSS crawler to fetch the latest headlines from all configured sources."""
    background_tasks.add_task(crawler.crawl_rss)
    return {"message": "Crawler pipeline triggered successfully in background."}
