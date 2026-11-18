"""RSS ingestion for SajhaNews — sources from data/nepal_sources.json."""

from __future__ import annotations

import datetime
import hashlib
import html
import ipaddress
import json
import os
import re
import sys
import time
from difflib import SequenceMatcher
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import feedparser
import requests
from sqlalchemy.orm import Session

import config
from database import (
    Article,
    CrawlRun,
    SessionLocal,
    Source,
    _json_dumps,
    init_db,
)
from framing import analyze_government_framing
from services.bias import analyze_political_bias
from services.bias_signals import extract_signals
from services.claims import analyze_article_claims
from services.clustering import get_or_create_story
from services.language import detect_language
from services.nepal import classify_topics, ensure_entity_file
from services.editorial import analyze_editorial_context
from services.event_intelligence import extract_event_frame, normalize_for_analysis
from services.embedding import model_id
from services.ner import extract_news_entities

ANALYSIS_VERSION = "event-intelligence-v1"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ANALYZE_ON_CRAWL = os.getenv("ANALYZE_ON_CRAWL", "true").lower() == "true"
ANALYZE_CLAIMS_ON_CRAWL = os.getenv("ANALYZE_CLAIMS_ON_CRAWL", "false").lower() == "true"

_FALLBACK_SOURCES: list[dict] = [
    {
        "name": "BBC News",
        "domain": "bbc.co.uk",
        "rss_url": "https://feeds.bbci.co.uk/news/world/rss.xml",
        "language": "en",
        "category": "World",
        "is_active": True,
    },
    {
        "name": "The Kathmandu Post",
        "domain": "kathmandupost.com",
        "rss_url": "https://kathmandupost.com/rss/",
        "language": "en",
        "category": "Nepal",
        "is_active": True,
    },
    {
        "name": "Online Khabar",
        "domain": "onlinekhabar.com",
        "rss_url": "https://www.onlinekhabar.com/feed",
        "language": "ne",
        "category": "Nepal",
        "is_active": True,
    },
]

HEADERS = {"User-Agent": config.USER_AGENT}


def load_source_catalog() -> list[dict]:
    path = config.DATA_DIR / "nepal_sources.json"
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, list) and data:
                return data
        except (OSError, json.JSONDecodeError) as exc:
            print(f"[!] Could not read {path}: {exc}; using fallback sources")
    return _FALLBACK_SOURCES


def sync_sources(db: Session, catalog: list[dict]) -> list[Source]:
    """Upsert sources from catalog; return active sources that have an RSS URL."""
    crawlable: list[Source] = []
    for row in catalog:
        domain = (row.get("domain") or "").strip()
        if not domain:
            continue
        source = db.query(Source).filter(Source.domain == domain).first()
        is_active = row.get("is_active", True)
        rss_url = row.get("rss_url")
        if rss_url is not None and isinstance(rss_url, str):
            rss_url = rss_url.strip() or None

        if not source:
            source = Source(
                name=row.get("name") or domain,
                domain=domain,
                rss_url=rss_url,
                default_bias=row.get("default_bias"),
                language=row.get("language") or "en",
                is_active=bool(is_active),
                category=row.get("category"),
                ownership_notes=row.get("ownership_notes"),
                transparency_notes=row.get("transparency_notes"),
                perspective_label=row.get("perspective_label"),
            )
            db.add(source)
        else:
            source.name = row.get("name") or source.name
            if rss_url:
                source.rss_url = rss_url
            source.language = row.get("language") or source.language
            source.is_active = bool(is_active)
            if row.get("category"):
                source.category = row["category"]
            if row.get("ownership_notes"):
                source.ownership_notes = row["ownership_notes"]
            if row.get("transparency_notes"):
                source.transparency_notes = row["transparency_notes"]
            if "perspective_label" in row:
                source.perspective_label = row.get("perspective_label")

        db.flush()
        if source.is_active and source.rss_url:
            crawlable.append(source)

    db.commit()
    for source in crawlable:
        db.refresh(source)
    return crawlable


def feed_fetch_url(rss_url: str) -> str:
    """Prefer HTTPS for BBC feeds."""
    if "bbci.co.uk" in rss_url or "bbc.co.uk" in rss_url:
        return re.sub(r"^http://", "https://", rss_url, count=1)
    return rss_url


def feed_url_is_safe(rss_url: str) -> bool:
    """Only fetch explicitly configured public HTTP(S) RSS endpoints."""
    try:
        parts = urlsplit(rss_url)
        if parts.scheme.lower() not in {"http", "https"} or not parts.hostname or parts.username or parts.password:
            return False
        host = parts.hostname.rstrip(".").casefold()
        if host in {"localhost", "localhost.localdomain"} or host.endswith((".local", ".internal")):
            return False
        try:
            if not ipaddress.ip_address(host).is_global:
                return False
        except ValueError:
            pass
        return True
    except ValueError:
        return False


def extract_thumbnail(entry) -> str | None:
    if hasattr(entry, "media_thumbnail") and entry.media_thumbnail:
        return entry.media_thumbnail[0].get("url")
    if hasattr(entry, "media_content") and entry.media_content:
        for mc in entry.media_content:
            url = mc.get("url")
            if url and any(ext in url.lower() for ext in (".jpg", ".jpeg", ".png", ".webp", ".gif")):
                return url
        url = entry.media_content[0].get("url")
        if url:
            return url
    if hasattr(entry, "enclosures") and entry.enclosures:
        url = entry.enclosures[0].get("url") or entry.enclosures[0].get("href")
        if url:
            return url
    summary = getattr(entry, "summary", "") or ""
    if 'src="' in summary:
        try:
            start = summary.index('src="') + 5
            end = summary.index('"', start)
            candidate = summary[start:end]
            if candidate.startswith("http"):
                return candidate
        except ValueError:
            pass
    return None


def normalize_url(url: str) -> str:
    parts = urlsplit(url.strip())
    query = [(key, value) for key, value in parse_qsl(parts.query) if not key.lower().startswith("utm_")]
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, urlencode(query), ""))


def normalize_title(title: str) -> str:
    return re.sub(r"[^\w\u0900-\u097f]+", " ", title.casefold()).strip()


def clean_rss_text(value: str | None) -> str:
    """Reduce untrusted RSS markup to inert plain text for analysis and storage."""
    raw = html.unescape(value or "")
    raw = re.sub(r"(?is)<(script|style|iframe|object)[^>]*>.*?</\1\s*>", " ", raw)
    raw = re.sub(r"(?i)<br\s*/?>|</(?:p|div|li|h[1-6])\s*>", " ", raw)
    raw = re.sub(r"<[^>]*>", " ", raw)
    return re.sub(r"\s+", " ", raw).strip()[:12000]


def content_fingerprint(title: str, content: str) -> str:
    normalized = normalize_for_analysis(f"{title}\n{content}")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _find_exact_duplicate(db: Session, article: Article, fingerprint: str) -> tuple[int | None, str | None]:
    prior = (
        db.query(Article.id)
        .filter(Article.id != article.id, Article.content_fingerprint == fingerprint)
        .order_by(Article.published_at.asc(), Article.id.asc())
        .first()
    )
    if prior:
        return prior[0], "exact_syndicated"
    if article.published_at:
        candidates = (
            db.query(Article.id, Article.original_headline, Article.content_text)
            .filter(
                Article.id != article.id,
                Article.published_at >= article.published_at - datetime.timedelta(days=7),
                Article.published_at <= article.published_at + datetime.timedelta(days=7),
            )
            .order_by(Article.published_at.desc())
            .limit(250)
            .all()
        )
        current_body = normalize_for_analysis(article.content_text or "")
        current_title = normalize_title(article.original_headline or "")
        if len(current_body) >= 100 and len(current_title) >= 20:
            for candidate in candidates:
                prior_body = normalize_for_analysis(candidate.content_text or "")
                prior_title = normalize_title(candidate.original_headline or "")
                if len(prior_body) < 100 or len(prior_title) < 20:
                    continue
                title_ratio = SequenceMatcher(None, current_title, prior_title, autojunk=False).ratio()
                if title_ratio < 0.94:
                    continue
                body_ratio = SequenceMatcher(None, current_body, prior_body, autojunk=False).ratio()
                if body_ratio >= 0.92:
                    return candidate.id, "near_syndicated"
    return None, None


def fetch_feed(rss_url: str) -> bytes:
    """Fetch a configured feed with bounded retry and exponential backoff."""
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            response = requests.get(rss_url, headers=HEADERS, timeout=config.REQUEST_TIMEOUT)
            if response.status_code in {429, 500, 502, 503, 504} and attempt < 2:
                retry_after = response.headers.get("Retry-After")
                delay = min(8.0, float(retry_after)) if retry_after and retry_after.isdigit() else 0.5 * (2 ** attempt)
                time.sleep(delay)
                continue
            response.raise_for_status()
            return response.content
        except requests.RequestException as exc:
            last_error = exc
            if attempt == 2:
                break
            time.sleep(0.5 * (2 ** attempt))
    if last_error:
        raise last_error
    raise RuntimeError("Feed request failed after retries")


def is_near_duplicate(title: str, existing_titles: list[str], threshold: float = 0.92) -> bool:
    normalized = normalize_title(title)
    return any(
        SequenceMatcher(None, normalized, existing).ratio() >= threshold
        for existing in existing_titles
    )


def _parse_published(entry) -> datetime.datetime:
    try:
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            return datetime.datetime(*entry.published_parsed[:6])
    except (TypeError, ValueError):
        pass
    return datetime.datetime.utcnow()


def _recent_titles_for_source(db: Session, source_id: int) -> list[str]:
    rows = (
        db.query(Article.original_headline)
        .filter(Article.source_id == source_id)
        .order_by(Article.id.desc())
        .limit(250)
        .all()
    )
    return [normalize_title(h[0]) for h in rows]


def _enrich_article(
    db: Session,
    article: Article,
    source: Source,
    title: str,
    content_text: str,
    category: str,
    published_at: datetime.datetime,
) -> None:
    combined = f"{title}\n{content_text}"
    lang = detect_language(combined, source_language=source.language)
    detected = lang["language"]
    if detected in {"ne-rom", "mixed", "unknown"}:
        article_lang = source.language or detected
    else:
        article_lang = detected

    topics = classify_topics(combined, default=category or "Nepal")
    entities, entity_model = extract_news_entities(combined)
    signals = extract_signals(combined, entities)
    signals["entity_model"] = entity_model

    article.language = source.language
    article.detected_language = article_lang
    article.topics_json = _json_dumps(topics)
    article.entities_json = _json_dumps(entities)
    article.entities_model = entity_model
    article.signals_json = _json_dumps(signals)
    article.event_frame_json = _json_dumps(
        extract_event_frame(combined, entities=entities, topics=topics)
    )
    article.editorial_json = _json_dumps(
        analyze_editorial_context(title, content_text, entities=entities, source_name=source.name)
    )
    article.content_fingerprint = content_fingerprint(title, content_text)

    story, _meta = get_or_create_story(
        db,
        title,
        category=topics[0] if topics else category,
        published_at=published_at,
        content=content_text,
        language=article_lang,
        entities=entities,
        topics=topics,
        source_name=source.name,
    )
    article.story_id = story.id
    article.embedding = _meta.get("article_embedding")
    article.embedding_model = _meta.get("embedding_model") or model_id()

    # Government POV framing — soft scores always (lexical if NLI off)
    if not article.framing_is_corrected:
        framing = analyze_government_framing(combined, lexical_only=not ANALYZE_ON_CRAWL)
        article.government_framing = framing.get("label")
        article.framing_confidence = framing.get("confidence")
        article.framing_model = framing.get("model")
        article.framing_evidence = framing.get("evidence")
        article.framing_method = framing.get("method")
        article.framing_scores_json = _json_dumps(framing.get("scores"))

    bias = analyze_political_bias(combined, lexical_only=True)
    article.political_bias = bias.get("label")
    article.bias_confidence = bias.get("confidence")
    article.bias_evidence = bias.get("evidence")
    article.bias_model = bias.get("model")
    article.ai_bias_score = bias.get("score")

    db.flush()

    if ANALYZE_CLAIMS_ON_CRAWL:
        analyze_article_claims(db, article, replace=True)
    article.analysis_version = ANALYSIS_VERSION
    article.analysis_status = "complete"
    article.analysis_error = None


def crawl_rss() -> dict:
    """Fetch active RSS feeds, persist new articles, record CrawlRun metrics."""
    init_db()
    ensure_entity_file()
    db = SessionLocal()

    catalog = load_source_catalog()
    sources = sync_sources(db, catalog)

    crawl_run = CrawlRun(status="running")
    db.add(crawl_run)
    db.commit()
    db.refresh(crawl_run)

    print("=" * 60)
    print("Starting SajhaNews RSS Crawl")
    print(f"Active feeds with RSS: {len(sources)}")
    print("=" * 60)

    new_articles = 0
    feeds_attempted = 0
    feeds_succeeded = 0
    feeds_failed = 0
    errors: list[dict] = []

    per_feed_limit = config.CRAWL_ENTRIES_PER_FEED

    for source in sources:
        rss_url = feed_fetch_url(source.rss_url or "")
        feeds_attempted += 1
        print(f"\n[*] Fetching {source.name} ({rss_url}) ...")

        try:
            if not feed_url_is_safe(rss_url):
                raise ValueError("RSS URL must use public HTTP(S) and cannot target a local host")
            feed = feedparser.parse(fetch_feed(rss_url))
        except Exception as exc:
            feeds_failed += 1
            msg = str(exc)
            errors.append({"source": source.name, "domain": source.domain, "error": msg})
            source.last_crawl_at = datetime.datetime.utcnow()
            source.last_crawl_status = "failed"
            source.last_error = msg[:2000]
            db.commit()
            print(f"  [!] Failed: {exc}")
            continue

        if not feed.entries:
            feeds_failed += 1
            source.last_crawl_at = datetime.datetime.utcnow()
            source.last_crawl_status = "empty"
            source.last_error = "No entries in feed"
            db.commit()
            print(f"  [?] No entries in feed")
            continue

        feeds_succeeded += 1
        category = source.category or "Nepal"
        count = 0

        for entry in feed.entries[:per_feed_limit]:
            url = getattr(entry, "link", None)
            title = clean_rss_text(getattr(entry, "title", None))
            if not url or not title:
                continue

            try:
                url = normalize_url(url)
            except ValueError:
                continue
            if not feed_url_is_safe(url):
                continue

            published_at = _parse_published(entry)
            content_text = clean_rss_text(
                getattr(entry, "content", [{}])[0].get("value")
                if getattr(entry, "content", None)
                else getattr(entry, "summary", "") or getattr(entry, "description", "")
            )
            thumbnail = extract_thumbnail(entry)
            fingerprint = content_fingerprint(title, content_text)
            article = db.query(Article).filter(Article.url == url).first()
            is_new = article is None
            if article and article.content_fingerprint == fingerprint and article.analysis_version == ANALYSIS_VERSION:
                continue
            if article is None:
                article = Article(source_id=source.id, url=url, original_headline=title, content_text=content_text)
                db.add(article)
            article.original_headline = title[:512]
            article.thumbnail_url = thumbnail or article.thumbnail_url
            article.content_text = content_text
            article.published_at = published_at
            article.crawled_at = datetime.datetime.utcnow()
            article.content_fingerprint = fingerprint
            article.analysis_status = "processing"
            article.analysis_error = None
            db.flush()
            duplicate_id, duplicate_kind = _find_exact_duplicate(db, article, fingerprint)
            article.duplicate_of_id = duplicate_id
            article.duplicate_kind = duplicate_kind

            try:
                _enrich_article(
                    db, article, source, title, content_text, category, published_at
                )
                db.commit()
            except Exception as exc:
                db.rollback()
                failed_article = db.query(Article).filter(Article.url == url).first()
                if failed_article:
                    failed_article.analysis_status = "failed"
                    failed_article.analysis_error = str(exc)[:2000]
                    db.commit()
                errors.append({
                    "source": source.name,
                    "url": url,
                    "error": f"enrich: {exc}",
                })
                print(f"  [!] Skipped article enrich ({url}): {exc}")
                continue

            if is_new:
                count += 1
                new_articles += 1
                source.article_count = (source.article_count or 0) + 1

        source.last_crawl_at = datetime.datetime.utcnow()
        source.last_crawl_status = "ok"
        source.last_error = None
        db.commit()
        print(f"  [+] {count} new articles from {source.name}")

    crawl_run.finished_at = datetime.datetime.utcnow()
    crawl_run.status = "completed" if feeds_failed == 0 else "completed_with_errors"
    crawl_run.feeds_attempted = feeds_attempted
    crawl_run.feeds_succeeded = feeds_succeeded
    crawl_run.feeds_failed = feeds_failed
    crawl_run.articles_new = new_articles
    crawl_run.errors_json = _json_dumps(errors) if errors else None
    db.commit()
    db.close()

    print("\n" + "=" * 60)
    print(f"Crawl complete — {new_articles} new articles")
    print(
        f"Feeds: {feeds_succeeded} ok, {feeds_failed} failed "
        f"(attempted {feeds_attempted})"
    )
    print("=" * 60)

    return {
        "articles_new": new_articles,
        "feeds_attempted": feeds_attempted,
        "feeds_succeeded": feeds_succeeded,
        "feeds_failed": feeds_failed,
        "errors": errors,
    }


if __name__ == "__main__":
    crawl_rss()
