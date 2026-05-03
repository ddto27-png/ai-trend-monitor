"""
Generic RSS collector for the Skitsa cross-disciplinary monitor.
No keyword filtering — feeds are pre-curated per field.
"""

import re
import time
import calendar
import feedparser
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime


def fetch_field_articles(feeds: list[dict], days_back: int = 3) -> list[dict]:
    """
    Fetch recent articles from a list of RSS/Atom feed configs.
    Each config: {"name": str, "url": str}
    Returns a list of article dicts with title, abstract, url, published, source.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
    articles = []

    for feed_config in feeds:
        name = feed_config["name"]
        url  = feed_config["url"]

        try:
            feed = feedparser.parse(url)
            if feed.bozo and not feed.entries:
                continue

            for entry in feed.entries:
                published = _parse_date(entry)
                if published is None or published < cutoff:
                    continue

                title = entry.get("title", "").strip()
                if not title:
                    continue

                summary = (
                    entry.get("summary", "")
                    or entry.get("description", "")
                    or ""
                )
                summary = _strip_html(summary)[:500]

                link = entry.get("link", url)

                articles.append({
                    "title":     title,
                    "abstract":  summary,
                    "url":       link,
                    "published": published,
                    "source":    name,
                })

        except Exception:
            continue

        time.sleep(0.3)

    return articles


def _parse_date(entry) -> datetime | None:
    for field in ("published", "updated", "created"):
        raw = entry.get(f"{field}_parsed") or entry.get(field)
        if raw is None:
            continue
        try:
            if isinstance(raw, str):
                return parsedate_to_datetime(raw).astimezone(timezone.utc)
            ts = calendar.timegm(raw)
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        except Exception:
            continue
    return None


def _strip_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()
