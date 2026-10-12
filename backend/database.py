"""SQLAlchemy models and engine for SajhaNews."""

from __future__ import annotations

import datetime
import json
from typing import Any, Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    create_engine,
    inspect,
    text,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

from config import DATABASE_URL

Base = declarative_base()


class Source(Base):
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    domain = Column(String(255), nullable=False, unique=True)
    rss_url = Column(String(2048), nullable=True)
    default_bias = Column(Float, nullable=True)  # legacy; not used for public ideology scores
    language = Column(String(10), default="en")
    is_active = Column(Boolean, default=True)
    category = Column(String(64), nullable=True)
    ownership_notes = Column(Text, nullable=True)
    transparency_notes = Column(Text, nullable=True)
    perspective_label = Column(String(64), nullable=True)  # curated only; never auto-invented
    perspective_confidence = Column(Float, nullable=True)
    perspective_evidence = Column(Text, nullable=True)
    last_crawl_at = Column(DateTime, nullable=True)
    last_crawl_status = Column(String(32), nullable=True)
    last_error = Column(Text, nullable=True)
    article_count = Column(Integer, default=0)

    articles = relationship("Article", back_populates="source")


class Story(Base):
    __tablename__ = "stories"

    id = Column(Integer, primary_key=True)
    ai_headline = Column(String(512), nullable=False)
    ai_summary = Column(Text, nullable=True)
    topic = Column(String(255), nullable=True)
    # Legacy fields kept nullable — never synthesize ideology percentages
    bias_left_pct = Column(Float, nullable=True)
    bias_center_pct = Column(Float, nullable=True)
    bias_right_pct = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    embedding = Column(Text, nullable=True)
    languages = Column(String(64), nullable=True)
    cluster_method = Column(String(64), nullable=True)
    cluster_confidence = Column(Float, nullable=True)

    articles = relationship("Article", back_populates="story")
    claims = relationship("Claim", back_populates="story")


class Article(Base):
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True)
    source_id = Column(Integer, ForeignKey("sources.id"))
    story_id = Column(Integer, ForeignKey("stories.id"), nullable=True)

    original_headline = Column(String(512), nullable=False)
    url = Column(String(2048), nullable=False, unique=True)
    thumbnail_url = Column(String(2048), nullable=True)
    content_text = Column(Text, nullable=False)

    published_at = Column(DateTime, nullable=True)
    crawled_at = Column(DateTime, default=datetime.datetime.utcnow)

    language = Column(String(10), nullable=True)
    detected_language = Column(String(10), nullable=True)
    topics_json = Column(Text, nullable=True)
    entities_json = Column(Text, nullable=True)
    signals_json = Column(Text, nullable=True)

    ai_bias_score = Column(Float, nullable=True)  # unused for public ideology
    embedding = Column(Text, nullable=True)
    government_framing = Column(String(32), nullable=True)
    framing_confidence = Column(Float, nullable=True)
    framing_model = Column(String(255), nullable=True)
    framing_evidence = Column(Text, nullable=True)
    framing_method = Column(String(64), nullable=True)
    political_bias = Column(String(16), nullable=True)  # left | center | right
    bias_confidence = Column(Float, nullable=True)
    bias_evidence = Column(Text, nullable=True)
    bias_model = Column(String(255), nullable=True)
    framing_scores_json = Column(Text, nullable=True)  # {"critical":0.2,"neutral":0.5,"supportive":0.3}

    source = relationship("Source", back_populates="articles")
    story = relationship("Story", back_populates="articles")
    claims = relationship("Claim", back_populates="article")


class Claim(Base):
    """Extracted claim with evidence-backed verification status."""

    __tablename__ = "claims"

    id = Column(Integer, primary_key=True)
    article_id = Column(Integer, ForeignKey("articles.id"), nullable=False)
    story_id = Column(Integer, ForeignKey("stories.id"), nullable=True)
    claim_text = Column(Text, nullable=False)
    status = Column(String(32), nullable=False, default="unverified")
    # supported | contradicted | disputed | unverified
    confidence = Column(Float, nullable=True)
    evidence_json = Column(Text, nullable=True)
    model = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    article = relationship("Article", back_populates="claims")
    story = relationship("Story", back_populates="claims")


class CrawlRun(Base):
    __tablename__ = "crawl_runs"

    id = Column(Integer, primary_key=True)
    started_at = Column(DateTime, default=datetime.datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
    status = Column(String(32), default="running")
    feeds_attempted = Column(Integer, default=0)
    feeds_succeeded = Column(Integer, default=0)
    feeds_failed = Column(Integer, default=0)
    articles_new = Column(Integer, default=0)
    errors_json = Column(Text, nullable=True)


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"

    id = Column(Integer, primary_key=True)
    kind = Column(String(64), nullable=False)
    started_at = Column(DateTime, default=datetime.datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
    status = Column(String(32), default="running")
    items_processed = Column(Integer, default=0)
    model = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)


class StoryCorrection(Base):
    """Admin merge/split corrections for clustering evaluation."""

    __tablename__ = "story_corrections"

    id = Column(Integer, primary_key=True)
    action = Column(String(32), nullable=False)  # merge | split
    source_story_id = Column(Integer, nullable=True)
    target_story_id = Column(Integer, nullable=True)
    article_ids_json = Column(Text, nullable=True)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class EvalPair(Base):
    """Labeled article/headline pairs for clustering evaluation."""

    __tablename__ = "eval_pairs"
    __table_args__ = (UniqueConstraint("left_text", "right_text", name="uq_eval_pair"),)

    id = Column(Integer, primary_key=True)
    left_text = Column(Text, nullable=False)
    right_text = Column(Text, nullable=False)
    same_event = Column(Boolean, nullable=False)
    language_pair = Column(String(16), nullable=True)
    notes = Column(Text, nullable=True)


connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _json_dumps(value: Any) -> Optional[str]:
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False)


def _json_loads(value: Optional[str], default: Any = None) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    _migrate_columns()


def _migrate_columns() -> None:
    """Additive SQLite/MySQL-safe column migrations for existing installs."""
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())

    article_cols = {
        c["name"] for c in inspector.get_columns("articles")
    } if "articles" in tables else set()
    source_cols = {
        c["name"] for c in inspector.get_columns("sources")
    } if "sources" in tables else set()
    story_cols = {
        c["name"] for c in inspector.get_columns("stories")
    } if "stories" in tables else set()

    article_additions = {
        "language": "VARCHAR(10)",
        "detected_language": "VARCHAR(10)",
        "topics_json": "TEXT",
        "entities_json": "TEXT",
        "signals_json": "TEXT",
        "government_framing": "VARCHAR(32)",
        "framing_confidence": "FLOAT",
        "framing_model": "VARCHAR(255)",
        "framing_evidence": "TEXT",
        "framing_method": "VARCHAR(64)",
        "embedding": "TEXT",
        "political_bias": "VARCHAR(16)",
        "bias_confidence": "FLOAT",
        "bias_evidence": "TEXT",
        "bias_model": "VARCHAR(255)",
        "framing_scores_json": "TEXT",
    }
    source_additions = {
        "category": "VARCHAR(64)",
        "ownership_notes": "TEXT",
        "transparency_notes": "TEXT",
        "perspective_label": "VARCHAR(64)",
        "perspective_confidence": "FLOAT",
        "perspective_evidence": "TEXT",
        "last_crawl_at": "DATETIME",
        "last_crawl_status": "VARCHAR(32)",
        "last_error": "TEXT",
        "article_count": "INTEGER DEFAULT 0",
    }
    story_additions = {
        "updated_at": "DATETIME",
        "embedding": "TEXT",
        "languages": "VARCHAR(64)",
        "cluster_method": "VARCHAR(64)",
        "cluster_confidence": "FLOAT",
    }

    with engine.begin() as connection:
        for name, column_type in article_additions.items():
            if name not in article_cols:
                connection.execute(text(f"ALTER TABLE articles ADD COLUMN {name} {column_type}"))
        for name, column_type in source_additions.items():
            if name not in source_cols:
                connection.execute(text(f"ALTER TABLE sources ADD COLUMN {name} {column_type}"))
        for name, column_type in story_additions.items():
            if name not in story_cols:
                connection.execute(text(f"ALTER TABLE stories ADD COLUMN {name} {column_type}"))
