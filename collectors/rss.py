"""
RSS collector — fetches posts from company blogs and newsletters.
Uses requests + stdlib xml parsing — no feedparser dependency.
Add or remove feeds in the FEEDS list below.
"""

import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

import requests

_ATOM = "http://www.w3.org/2005/Atom"
_UA   = "AI-Trend-Monitor/1.0 (https://github.com/ddto27-png/ai-trend-monitor)"


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
    cutoff      = datetime.now(timezone.utc) - timedelta(days=days_back)
    all_entries = []

    for feed_config in FEEDS:
        name = feed_config["name"]
        url  = feed_config["url"]
        try:
            items = _fetch_feed(url)
            for item in items:
                if item["published"] and item["published"] >= cutoff:
                    item["source"]  = name
                    item["authors"] = []
                    item["engagement"] = {}
                    all_entries.append(item)
        except Exception:
            continue
        time.sleep(0.2)

    return all_entries


def filter_relevant_entries(entries: list[dict], topic_keywords: dict) -> list[dict]:
    """Tag each entry with the best-matching topic bucket."""
    scored = []
    for entry in entries:
        text       = (entry["title"] + " " + entry["abstract"]).lower()
        best_topic = None
        best_score = 0
        for topic, keywords in topic_keywords.items():
            score = sum(1 for kw in keywords if kw in text)
            if score > best_score:
                best_score = score
                best_topic = topic
        entry["topic"]           = best_topic or "LLMs"
        entry["relevance_score"] = best_score + 1  # slight boost vs raw community posts
        scored.append(entry)
    return scored


# ── Feed parsing ─────────────────────────────────────────────────────────────

def _fetch_feed(url: str) -> list[dict]:
    resp = requests.get(
        url, timeout=10,
        headers={"User-Agent": _UA,
                 "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*"}
    )
    resp.raise_for_status()
    root = ET.fromstring(resp.content)
    return _parse_atom(root) if "feed" in root.tag.lower() else _parse_rss(root)


def _parse_rss(root: ET.Element) -> list[dict]:
    items   = []
    channel = root.find("channel") or root
    for item in channel.findall("item"):
        title = _text(item, "title")
        link  = _text(item, "link") or _text(item, "guid")
        desc  = _strip_html(_text(item, "description") or "")[:400]
        pub   = _parse_rfc2822(_text(item, "pubDate") or "")
        if title:
            items.append({"title": title, "url": link or "", "abstract": desc, "published": pub})
    return items


def _parse_atom(root: ET.Element) -> list[dict]:
    items = []
    ns    = {"a": _ATOM}

    def _entries(node):
        return node.findall("a:entry", ns) or node.findall("entry")

    for entry in _entries(root):
        title = (_nstext(entry, "title", ns) or _text(entry, "title") or "").strip()
        link  = ""
        for lel in (entry.findall("a:link", ns) or entry.findall("link")):
            if lel.get("rel", "alternate") in ("alternate", "") or not link:
                link = lel.get("href", "")
        summary = _strip_html(
            _nstext(entry, "summary", ns) or _nstext(entry, "content", ns)
            or _text(entry, "summary") or _text(entry, "content") or ""
        )[:400]
        pub_raw = (
            _nstext(entry, "published", ns) or _nstext(entry, "updated", ns)
            or _text(entry, "published") or _text(entry, "updated") or ""
        )
        pub = _parse_iso(pub_raw) or _parse_rfc2822(pub_raw)
        if title:
            items.append({"title": title, "url": link, "abstract": summary, "published": pub})
    return items


# ── Helpers ───────────────────────────────────────────────────────────────────

def _text(node: ET.Element, tag: str) -> str:
    el = node.find(tag)
    return (el.text or "").strip() if el is not None else ""


def _nstext(node: ET.Element, tag: str, ns: dict) -> str:
    el = node.find(f"a:{tag}", ns)
    return (el.text or "").strip() if el is not None else ""


def _parse_rfc2822(s: str) -> datetime | None:
    if not s:
        return None
    try:
        return parsedate_to_datetime(s).astimezone(timezone.utc)
    except Exception:
        return None


def _parse_iso(s: str) -> datetime | None:
    if not s:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(s[:19] + (s[19:] if len(s) > 19 else "Z"), fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except ValueError:
            continue
    return None


def _strip_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()
