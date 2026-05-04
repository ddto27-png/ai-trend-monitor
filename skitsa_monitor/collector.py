"""
Generic RSS/Atom collector for the Skitsa cross-disciplinary monitor.
Uses requests + stdlib xml parsing — no feedparser dependency.
No keyword filtering — feeds are pre-curated per field.
"""

import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

import requests

_ATOM = "http://www.w3.org/2005/Atom"
_UA   = "Skitsa-Monitor/1.0 (https://github.com/ddto27-png/ai-trend-monitor)"


def fetch_field_articles(feeds: list[dict], days_back: int = 3) -> list[dict]:
    """
    Fetch recent articles from a list of RSS/Atom feed configs.
    Each config: {"name": str, "url": str}
    """
    cutoff   = datetime.now(timezone.utc) - timedelta(days=days_back)
    articles = []

    for feed_config in feeds:
        name = feed_config["name"]
        url  = feed_config["url"]
        try:
            items = _fetch_feed(url)
            for item in items:
                if item["published"] and item["published"] >= cutoff:
                    item["source"] = name
                    articles.append(item)
        except Exception:
            continue
        time.sleep(0.3)

    return articles


def _fetch_feed(url: str) -> list[dict]:
    resp = requests.get(url, timeout=10,
                        headers={"User-Agent": _UA, "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*"})
    resp.raise_for_status()

    root = ET.fromstring(resp.content)
    tag  = root.tag.lower()

    if "feed" in tag:
        return _parse_atom(root)
    else:
        return _parse_rss(root)


def _parse_rss(root: ET.Element) -> list[dict]:
    items = []
    channel = root.find("channel") or root
    for item in channel.findall("item"):
        title = _text(item, "title")
        link  = _text(item, "link") or _text(item, "guid")
        desc  = _strip_html(_text(item, "description") or "")[:500]
        pub   = _parse_rfc2822(_text(item, "pubDate") or _text(item, "dc:date") or "")
        if title:
            items.append({"title": title, "url": link or "", "abstract": desc, "published": pub})
    return items


def _parse_atom(root: ET.Element) -> list[dict]:
    items = []
    ns    = {"a": _ATOM}

    def find_entries(node):
        # Handle both namespaced and bare <entry> tags
        found = node.findall(f"a:entry", ns) or node.findall("entry")
        return found

    for entry in find_entries(root):
        title = (_nstext(entry, "title", ns) or _text(entry, "title") or "").strip()
        link  = ""
        for lel in (entry.findall(f"a:link", ns) or entry.findall("link")):
            rel = lel.get("rel", "alternate")
            if rel in ("alternate", "") or not link:
                link = lel.get("href", "")
        summary = _strip_html(
            _nstext(entry, "summary", ns)
            or _nstext(entry, "content", ns)
            or _text(entry, "summary")
            or _text(entry, "content")
            or ""
        )[:500]
        pub_raw = (
            _nstext(entry, "published", ns)
            or _nstext(entry, "updated", ns)
            or _text(entry, "published")
            or _text(entry, "updated")
            or ""
        )
        pub = _parse_iso(pub_raw) or _parse_rfc2822(pub_raw)
        if title:
            items.append({"title": title, "url": link, "abstract": summary, "published": pub})
    return items


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
