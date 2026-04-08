"""
RSS collector — fetches posts from company blogs and newsletters via RSS/Atom feeds.
Free, no API keys required. Add or remove feeds in the FEEDS list below.
"""

import time
import feedparser
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime


# ── Feed list — add or remove as needed ─────────────────────────────────────
FEEDS = [
    # Company blogs
    {"name": "Anthropic Blog",       "url": "https://www.anthropic.com/rss.xml"},
    {"name": "OpenAI Blog",          "url": "https://openai.com/news/rss.xml"},
    {"name": "Google DeepMind Blog", "url": "https://deepmind.google/blog/rss/"},
    {"name": "HuggingFace Blog",     "url": "https://huggingface.co/blog/feed.xml"},
    {"name": "LangChain Blog",       "url": "https://blog.langchain.dev/rss/"},
    {"name": "Mistral Blog",         "url": "https://mistral.ai/news/rss"},
    # Newsletters
    {"name": "Import AI",            "url": "https://importai.substack.com/feed"},
    {"name": "The Batch",            "url": "https://www.deeplearning.ai/the-batch/feed/"},
    {"name": "Interconnects",        "url": "https://www.interconnects.ai/feed"},
]


def fetch_entries(days_back: int = 2) -> list[dict]:
    """
    Fetch recent entries from all RSS feeds.
    Uses days_back=2 by default because some blogs don't publish every day.
    Returns items in the same format as other collectors.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
    all_entries = []

    for feed_config in FEEDS:
        name = feed_config["name"]
        url = feed_config["url"]

        try:
            feed = feedparser.parse(url)

            # feedparser doesn't raise on failure — check bozo flag
            if feed.bozo and not feed.entries:
                continue

            for entry in feed.entries:
                published = _parse_date(entry)
                if published is None or published < cutoff:
                    continue

                title = entry.get("title", "").strip()
                if not title:
                    continue

                # Get summary text — strip HTML tags roughly
                summary = entry.get("summary", "") or entry.get("description", "") or ""
                summary = _strip_html(summary)[:400]

                link = entry.get("link", url)

                # Authors
                authors = []
                if hasattr(entry, "author"):
                    authors = [entry.author]
                elif hasattr(entry, "authors"):
                    authors = [a.get("name", "") for a in entry.authors if a.get("name")]

                all_entries.append({
                    "title": title,
                    "abstract": summary,
                    "authors": authors[:2],
                    "url": link,
                    "published": published,
                    "source": name,
                    "engagement": {},
                })

        except Exception:
            # Skip broken feeds silently — don't break the pipeline
            continue

        time.sleep(0.2)

    return all_entries


def filter_relevant_entries(entries: list[dict], topic_keywords: dict) -> list[dict]:
    """Tag each entry with the best-matching topic bucket."""
    scored = []
    for entry in entries:
        text = (entry["title"] + " " + entry["abstract"]).lower()
        best_topic = None
        best_score = 0

        for topic, keywords in topic_keywords.items():
            score = sum(1 for kw in keywords if kw in text)
            if score > best_score:
                best_score = score
                best_topic = topic

        # Keep all blog/newsletter entries regardless of score — they're pre-curated
        entry["topic"] = best_topic or "LLMs"
        entry["relevance_score"] = best_score + 1  # slight boost vs raw community posts
        scored.append(entry)

    return scored


# ── Helpers ──────────────────────────────────────────────────────────────────

def _parse_date(entry) -> datetime | None:
    """Try multiple date fields to get a timezone-aware datetime."""
    for field in ("published", "updated", "created"):
        raw = entry.get(f"{field}_parsed") or entry.get(field)
        if raw is None:
            continue
        try:
            if isinstance(raw, str):
                dt = parsedate_to_datetime(raw)
                return dt.astimezone(timezone.utc)
            # feedparser returns time.struct_time for *_parsed fields
            import calendar
            ts = calendar.timegm(raw)
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        except Exception:
            continue
    return None


def _strip_html(text: str) -> str:
    """Very lightweight HTML tag stripper."""
    import re
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()
