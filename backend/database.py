from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
import datetime

Base = declarative_base()

class Source(Base):
    __tablename__ = 'sources'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    domain = Column(String(255), nullable=False, unique=True)
    rss_url = Column(String(2048), nullable=True)  # If null, use custom scraper
    default_bias = Column(Float, nullable=True)  # Admin can set a known bias manually
    language = Column(String(10), default='en')  # ISO 639-1 language code (e.g. 'en', 'ne')
    is_active = Column(Boolean, default=True)
    
    articles = relationship("Article", back_populates="source")

class Story(Base):
    """
    A clustered event that groups multiple articles together.
    """
    __tablename__ = 'stories'
    
    id = Column(Integer, primary_key=True)
    ai_headline = Column(String(512), nullable=False)
    ai_summary = Column(Text, nullable=True)
    topic = Column(String(255), nullable=True)
    
    # Aggregated bias metrics
    bias_left_pct = Column(Float, default=0.0)
    bias_center_pct = Column(Float, default=0.0)
    bias_right_pct = Column(Float, default=0.0)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    articles = relationship("Article", back_populates="story")

class Article(Base):
    """
    A raw article crawled from a specific portal.
    """
    __tablename__ = 'articles'
    
    id = Column(Integer, primary_key=True)
    source_id = Column(Integer, ForeignKey('sources.id'))
    story_id = Column(Integer, ForeignKey('stories.id'), nullable=True) # Null until AI clusters it
    
    original_headline = Column(String(512), nullable=False)
    url = Column(String(2048), nullable=False, unique=True)
    thumbnail_url = Column(String(2048), nullable=True)
    content_text = Column(Text, nullable=False)
    
    published_at = Column(DateTime, nullable=True)
    crawled_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # NLP / AI Metadata
    ai_bias_score = Column(Float, nullable=True) # Evaluated by AI per article
    embedding = Column(Text, nullable=True) # Store vector as JSON/string for MVP if pgvector unavailable
    
    source = relationship("Source", back_populates="articles")
    story = relationship("Story", back_populates="articles")

import os
from dotenv import load_dotenv

load_dotenv()

# Database Setup
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
raw_db_url = os.getenv("DATABASE_URL", "").strip()

if not raw_db_url or raw_db_url == "sqlite:///news_aggregator.db":
    DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, 'news_aggregator.db')}"
elif raw_db_url.startswith("sqlite:///") and not os.path.isabs(raw_db_url[10:]):
    # Relative path like sqlite:///news_aggregator.db
    rel_path = raw_db_url[10:]
    DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, rel_path)}"
else:
    DATABASE_URL = raw_db_url

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)
