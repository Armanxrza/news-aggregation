import sys
import feedparser
import requests
import datetime
from sqlalchemy.orm import Session
from database import SessionLocal, Source, Article, Story, init_db

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ---------------------------------------------------------------------------
# Comprehensive list of Nepali & international news RSS feeds
# ---------------------------------------------------------------------------
RSS_FEEDS = [
    # ── International (English) ──────────────────────────────────────────────
    {
        "name": "BBC News",
        "domain": "bbc.co.uk",
        "rss_url": "http://feeds.bbci.co.uk/news/world/rss.xml",
        "default_bias": 0.0,
        "language": "en",
        "category": "World",
    },
    {
        "name": "Al Jazeera",
        "domain": "aljazeera.com",
        "rss_url": "https://www.aljazeera.com/xml/rss/all.xml",
        "default_bias": -0.2,
        "language": "en",
        "category": "World",
    },
    # ── Nepal English ────────────────────────────────────────────────────────
    {
        "name": "The Kathmandu Post",
        "domain": "kathmandupost.com",
        "rss_url": "https://kathmandupost.com/rss/",
        "default_bias": 0.0,
        "language": "en",
        "category": "Nepal",
    },
    {
        "name": "Nepali Times",
        "domain": "nepalitimes.com",
        "rss_url": "https://www.nepalitimes.com/feed",
        "default_bias": 0.0,
        "language": "en",
        "category": "Nepal",
    },
    {
        "name": "The Himalayan Times",
        "domain": "thehimalayantimes.com",
        "rss_url": None,          # No public RSS found
        "default_bias": 0.1,
        "language": "en",
        "category": "Nepal",
    },
    {
        "name": "Capital Nepal",
        "domain": "capitalnepal.com",
        "rss_url": "https://capitalnepal.com/feed",
        "default_bias": 0.0,
        "language": "en",
        "category": "Business",
    },
    {
        "name": "Clickmandu",
        "domain": "clickmandu.com",
        "rss_url": "https://clickmandu.com/feed",
        "default_bias": 0.0,
        "language": "en",
        "category": "Nepal",
    },
    {
        "name": "Goal Nepal",
        "domain": "goalnepal.com",
        "rss_url": None,          # 404
        "default_bias": 0.0,
        "language": "en",
        "category": "Sports",
    },
    {
        "name": "Hamro Khelkud",
        "domain": "hamrokhelkud.com",
        "rss_url": "https://hamrokhelkud.com/feed",
        "default_bias": 0.0,
        "language": "en",
        "category": "Sports",
    },
    {
        "name": "Avenues TV",
        "domain": "avenues.tv",
        "rss_url": None,
        "default_bias": 0.0,
        "language": "en",
        "category": "Nepal",
    },
    # ── Nepal Nepali-language ────────────────────────────────────────────────
    {
        "name": "Online Khabar",
        "domain": "onlinekhabar.com",
        "rss_url": "https://www.onlinekhabar.com/feed",
        "default_bias": 0.0,
        "language": "ne",
        "category": "Nepal",
    },
    {
        "name": "Setopati",
        "domain": "setopati.com",
        "rss_url": "https://www.setopati.com/feed",
        "default_bias": 0.0,
        "language": "ne",
        "category": "Nepal",
    },
    {
        "name": "Ratopati",
        "domain": "ratopati.com",
        "rss_url": "https://www.ratopati.com/feed",
        "default_bias": 0.0,
        "language": "ne",
        "category": "Nepal",
    },
    {
        "name": "Annapurna Post",
        "domain": "annapurnapost.com",
        "rss_url": None,          # 404
        "default_bias": 0.0,
        "language": "ne",
        "category": "Nepal",
    },
    {
        "name": "Ekantipur",
        "domain": "ekantipur.com",
        "rss_url": None,          # 404
        "default_bias": 0.0,
        "language": "ne",
        "category": "Nepal",
    },
    {
        "name": "Nagarik News",
        "domain": "nagariknews.nagariknetwork.com",
        "rss_url": "https://nagariknews.nagariknetwork.com/feed",
        "default_bias": 0.0,
        "language": "ne",
        "category": "Nepal",
    },
    {
        "name": "Naya Patrika",
        "domain": "nayapatrikadaily.com",
        "rss_url": None,          # 403
        "default_bias": 0.0,
        "language": "ne",
        "category": "Nepal",
    },
    {
        "name": "Himal Khabar",
        "domain": "himalkhabar.com",
        "rss_url": "https://himalkhabar.com/feed",
        "default_bias": -0.1,
        "language": "ne",
        "category": "Nepal",
    },
    {
        "name": "Rajdhani Daily",
        "domain": "rajdhanidaily.com",
        "rss_url": "https://www.rajdhanidaily.com/feed",
        "default_bias": 0.0,
        "language": "ne",
        "category": "Nepal",
    },
    {
        "name": "Rajdhani News",
        "domain": "rajdhaninews.com",
        "rss_url": None,
        "default_bias": 0.0,
        "language": "ne",
        "category": "Nepal",
    },
    {
        "name": "Pardafas",
        "domain": "pardafas.com",
        "rss_url": "https://www.pardafas.com/feed",
        "default_bias": 0.0,
        "language": "ne",
        "category": "Nepal",
    },
    {
        "name": "Taksaarn News",
        "domain": "taksaarnews.com",
        "rss_url": None,
        "default_bias": 0.0,
        "language": "ne",
        "category": "Nepal",
    },
    {
        "name": "Thaha Khabar",
        "domain": "thahakhabar.com",
        "rss_url": None,
        "default_bias": 0.0,
        "language": "ne",
        "category": "Nepal",
    },
    {
        "name": "Himalaya Darpan",
        "domain": "himalayadarpan.com",
        "rss_url": "https://himalayadarpan.com/feed",
        "default_bias": 0.0,
        "language": "ne",
        "category": "Nepal",
    },
    {
        "name": "OS Nepal",
        "domain": "osnepal.com",
        "rss_url": None,
        "default_bias": 0.0,
        "language": "ne",
        "category": "Nepal",
    },
    {
        "name": "Kharibot",
        "domain": "kharibot.com",
        "rss_url": "https://www.kharibot.com/feed",
        "default_bias": 0.0,
        "language": "ne",
        "category": "Nepal",
    },
    {
        "name": "Kathmandu Today",
        "domain": "kathmandutoday.com",
        "rss_url": None,          # 403
        "default_bias": 0.0,
        "language": "ne",
        "category": "Nepal",
    },
    {
        "name": "Nepali Patra",
        "domain": "nepalipatra.com",
        "rss_url": None,
        "default_bias": 0.0,
        "language": "ne",
        "category": "Nepal",
    },
    {
        "name": "Ujyaalo Online",
        "domain": "ujyaaloonline.com",
        "rss_url": "https://ujyaaloonline.com/feed",
        "default_bias": 0.0,
        "language": "ne",
        "category": "Nepal",
    },
    {
        "name": "Barhakhari",
        "domain": "barhakhari.com",
        "rss_url": None,
        "default_bias": 0.0,
        "language": "ne",
        "category": "Nepal",
    },
    {
        "name": "KTM Samachar",
        "domain": "ktmsamachar.com",
        "rss_url": None,
        "default_bias": 0.0,
        "language": "ne",
        "category": "Nepal",
    },
    {
        "name": "Purba Dharka Khabar",
        "domain": "purbadharkhabar.com",
        "rss_url": None,
        "default_bias": 0.0,
        "language": "ne",
        "category": "Nepal",
    },
    {
        "name": "Koshi Online",
        "domain": "koshionline.com",
        "rss_url": None,
        "default_bias": 0.0,
        "language": "ne",
        "category": "Nepal",
    },
    {
        "name": "Hamro Kura",
        "domain": "hamrokura.com",
        "rss_url": None,
        "default_bias": 0.0,
        "language": "ne",
        "category": "Nepal",
    },
    {
        "name": "17 Wadapalika",
        "domain": "17wadapalika.com",
        "rss_url": None,
        "default_bias": 0.0,
        "language": "ne",
        "category": "Nepal",
    },
    {
        "name": "Aashtha News",
        "domain": "aasthanews.com",
        "rss_url": None,
        "default_bias": 0.0,
        "language": "ne",
        "category": "Nepal",
    },
    {
        "name": "Sunaulo Nepal",
        "domain": "sunaulonepal.com",
        "rss_url": None,
        "default_bias": 0.0,
        "language": "ne",
        "category": "Nepal",
    },
    {
        "name": "Khabar Purwanchal",
        "domain": "khabarpurwanchal.com",
        "rss_url": None,
        "default_bias": 0.0,
        "language": "ne",
        "category": "Nepal",
    },
    {
        "name": "Radio Nepal",
        "domain": "radionepal.com",
        "rss_url": None,
        "default_bias": 0.0,
        "language": "ne",
        "category": "Nepal",
    },
    {
        "name": "Radio Sagarmatha",
        "domain": "radiosagarmatha.com",
        "rss_url": None,
        "default_bias": 0.0,
        "language": "ne",
        "category": "Nepal",
    },
    {
        "name": "Nepali Post",
        "domain": "nepalipost.com",
        "rss_url": None,
        "default_bias": 0.0,
        "language": "ne",
        "category": "Nepal",
    },
    {
        "name": "Janakpur Today",
        "domain": "janakpurtoday.com",
        "rss_url": None,
        "default_bias": 0.0,
        "language": "ne",
        "category": "Nepal",
    },
    # ── Nepal Business / Finance ─────────────────────────────────────────────
    {
        "name": "Bizmandu",
        "domain": "bizmandu.com",
        "rss_url": "https://bizmandu.com/feed",
        "default_bias": 0.0,
        "language": "ne",
        "category": "Business",
    },
    {
        "name": "Arthakoartha",
        "domain": "arthakoartha.com",
        "rss_url": "https://arthakoartha.com/feed",
        "default_bias": 0.0,
        "language": "ne",
        "category": "Business",
    },
    {
        "name": "Artha Sarokar",
        "domain": "arthasarokar.com",
        "rss_url": "https://arthasarokar.com/feed",
        "default_bias": 0.0,
        "language": "ne",
        "category": "Business",
    },
    {
        "name": "Lagani News",
        "domain": "laganinews.com",
        "rss_url": "https://laganinews.com/feed",
        "default_bias": 0.0,
        "language": "ne",
        "category": "Business",
    },
    {
        "name": "Aarthik Khabar",
        "domain": "aarthikkhabar.com",
        "rss_url": None,
        "default_bias": 0.0,
        "language": "ne",
        "category": "Business",
    },
    {
        "name": "Bizsala",
        "domain": "bizsala.com",
        "rss_url": None,
        "default_bias": 0.0,
        "language": "ne",
        "category": "Business",
    },
    {
        "name": "Samachar Patra",
        "domain": "samacharpatra.com",
        "rss_url": None,          # 406
        "default_bias": 0.0,
        "language": "ne",
        "category": "Nepal",
    },
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


def get_or_create_source(db: Session, feed_info: dict) -> Source:
    source = db.query(Source).filter(Source.domain == feed_info["domain"]).first()
    if not source:
        source = Source(
            name=feed_info["name"],
            domain=feed_info["domain"],
            rss_url=feed_info.get("rss_url"),
            default_bias=feed_info.get("default_bias", 0.0),
            language=feed_info.get("language", "en"),
        )
        db.add(source)
        db.commit()
        db.refresh(source)
    else:
        # Update RSS URL and name if we have better info
        changed = False
        if feed_info.get("rss_url") and not source.rss_url:
            source.rss_url = feed_info["rss_url"]
            changed = True
        if changed:
            db.commit()
    return source


def extract_thumbnail(entry) -> str | None:
    """Extract thumbnail URL from an RSS entry, trying multiple common tag formats."""
    # media:thumbnail (used by many portals)
    if hasattr(entry, "media_thumbnail") and entry.media_thumbnail:
        return entry.media_thumbnail[0].get("url")
    # media:content
    if hasattr(entry, "media_content") and entry.media_content:
        for mc in entry.media_content:
            url = mc.get("url")
            if url and any(ext in url.lower() for ext in [".jpg", ".jpeg", ".png", ".webp", ".gif"]):
                return url
        url = entry.media_content[0].get("url")
        if url:
            return url
    # <enclosure>
    if hasattr(entry, "enclosures") and entry.enclosures:
        url = entry.enclosures[0].get("url") or entry.enclosures[0].get("href")
        if url:
            return url
    # Parse image from description HTML
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


def get_or_create_story(db: Session, headline: str, category: str = "Nepal") -> Story:
    """Simple keyword-based deduplication — good enough for MVP."""
    words = [w.lower() for w in headline.split() if len(w) > 5]
    if words:
        # Try the first two meaningful words
        for word in words[:2]:
            story = (
                db.query(Story)
                .filter(Story.ai_headline.ilike(f"%{word}%"))
                .first()
            )
            if story:
                return story

    new_story = Story(
        ai_headline=headline,
        topic=category,
        bias_left_pct=33.3,
        bias_center_pct=33.3,
        bias_right_pct=33.3,
    )
    db.add(new_story)
    db.commit()
    db.refresh(new_story)
    return new_story


def _update_story_bias(story: Story, source_bias: float):
    if source_bias < -0.1:
        story.bias_left_pct += 15
        story.bias_center_pct -= 5
        story.bias_right_pct -= 10
    elif source_bias > 0.1:
        story.bias_right_pct += 15
        story.bias_center_pct -= 5
        story.bias_left_pct -= 10
    else:
        story.bias_center_pct += 15
        story.bias_left_pct -= 7
        story.bias_right_pct -= 8

    # Clamp
    story.bias_left_pct = max(0, min(100, story.bias_left_pct))
    story.bias_center_pct = max(0, min(100, story.bias_center_pct))
    story.bias_right_pct = max(0, min(100, story.bias_right_pct))

    # Normalise to 100
    total = story.bias_left_pct + story.bias_center_pct + story.bias_right_pct
    if total > 0:
        story.bias_left_pct = round((story.bias_left_pct / total) * 100, 1)
        story.bias_center_pct = round((story.bias_center_pct / total) * 100, 1)
        story.bias_right_pct = round((story.bias_right_pct / total) * 100, 1)


# ---------------------------------------------------------------------------
# Main crawl function
# ---------------------------------------------------------------------------

def crawl_rss():
    init_db()
    db = SessionLocal()

    print("=" * 60)
    print("Starting SajhaNews RSS Crawl")
    print("=" * 60)

    new_articles = 0
    failed_feeds = []

    for feed_info in RSS_FEEDS:
        # Always ensure source exists in DB (even without RSS)
        source = get_or_create_source(db, feed_info)

        if not feed_info.get("rss_url"):
            print(f"  [-] {feed_info['name']} - no RSS URL, skipped")
            continue

        print(f"\n[*] Fetching {feed_info['name']} ...")

        try:
            # Use requests so we can pass headers and timeout
            resp = requests.get(
                feed_info["rss_url"],
                headers=HEADERS,
                timeout=12,
            )
            resp.raise_for_status()
            feed = feedparser.parse(resp.content)
        except Exception as exc:
            print(f"  [!] Failed to fetch {feed_info['name']}: {exc}")
            failed_feeds.append(feed_info["name"])
            continue

        if not feed.entries:
            print(f"  [?] No entries found in feed for {feed_info['name']}")
            continue

        count = 0
        for entry in feed.entries[:20]:
            url = getattr(entry, "link", None)
            title = getattr(entry, "title", None)
            if not url or not title:
                continue

            existing = db.query(Article).filter(Article.url == url).first()
            if existing:
                continue

            try:
                pub = (
                    datetime.datetime(*entry.published_parsed[:6])
                    if hasattr(entry, "published_parsed") and entry.published_parsed
                    else datetime.datetime.utcnow()
                )
            except Exception:
                pub = datetime.datetime.utcnow()

            thumbnail = extract_thumbnail(entry)
            category = feed_info.get("category", "Nepal")
            story = get_or_create_story(db, title, category)
            _update_story_bias(story, source.default_bias or 0.0)

            article = Article(
                source_id=source.id,
                story_id=story.id,
                original_headline=title,
                url=url,
                thumbnail_url=thumbnail,
                content_text=getattr(entry, "summary", "") or "",
                published_at=pub,
            )
            db.add(article)
            count += 1
            new_articles += 1

        db.commit()
        print(f"  [+] {count} new articles from {feed_info['name']}")

    db.close()

    print("\n" + "=" * 60)
    print(f"Crawl complete - {new_articles} new articles added")
    if failed_feeds:
        print(f"Failed feeds ({len(failed_feeds)}): {', '.join(failed_feeds)}")
    print("=" * 60)


if __name__ == "__main__":
    crawl_rss()
