"""Central configuration for SajhaNews (local-first)."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

APP_NAME = "SajhaNews"
APP_VERSION = "2.0.0"

# Database
_raw_db = os.getenv("DATABASE_URL", "").strip()
if _raw_db.startswith("postgres://"):
    _raw_db = _raw_db.replace("postgres://", "postgresql://", 1)

if not _raw_db or _raw_db == "sqlite:///news_aggregator.db":
    DATABASE_URL = f"sqlite:///{(BASE_DIR / 'news_aggregator.db').as_posix()}"
elif _raw_db.startswith("sqlite:///") and not Path(_raw_db[10:]).is_absolute():
    DATABASE_URL = f"sqlite:///{(BASE_DIR / _raw_db[10:]).as_posix()}"
else:
    DATABASE_URL = _raw_db

# Security
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "dev-admin-key-change-me")
CORS_ORIGINS = [
    o.strip()
    for o in os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")
    if o.strip()
]

# Ingestion
ENABLE_CRAWL_SCHEDULER = os.getenv("ENABLE_CRAWL_SCHEDULER", "false").lower() == "true"
CRAWL_INTERVAL_SECONDS = int(os.getenv("CRAWL_INTERVAL_SECONDS", "900"))
CRAWL_ENTRIES_PER_FEED = int(os.getenv("CRAWL_ENTRIES_PER_FEED", "20"))
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "12"))
USER_AGENT = os.getenv(
    "USER_AGENT",
    "SajhaNewsBot/2.0 (+https://localhost; Nepal news aggregation; contact=local)",
)

# AI / models — never claim Nepal fine-tuning unless FINETUNED_MODEL_PATH is set
FRAMING_ENABLED = os.getenv("FRAMING_ENABLED", "true").lower() == "true"
EMBEDDING_ENABLED = os.getenv("EMBEDDING_ENABLED", "true").lower() == "true"
HF_FRAMING_MODEL = os.getenv("HF_FRAMING_MODEL", "MoritzLaurer/mDeBERTa-v3-base-mnli-xnli")
HF_EMBEDDING_MODEL = os.getenv(
    "HF_EMBEDDING_MODEL",
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
)
FINETUNED_MODEL_PATH = os.getenv("FINETUNED_MODEL_PATH", "").strip()
FRAMING_MIN_CHARS = int(os.getenv("FRAMING_MIN_CHARS", "40"))
# 0.55 balances EN–NE recall on data/story_pairs.jsonl; raise for stricter merges
CLUSTER_SIMILARITY_THRESHOLD = float(os.getenv("CLUSTER_SIMILARITY_THRESHOLD", "0.55"))
CLUSTER_TIME_WINDOW_HOURS = int(os.getenv("CLUSTER_TIME_WINDOW_HOURS", "72"))

DATA_DIR = BASE_DIR / "data"
ML_DIR = BASE_DIR / "ml"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
