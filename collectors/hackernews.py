"""
Hacker News collector — fetches recent AI-related stories via the Algolia API.
Free, no API key required.
"""

import time
import requests
from datetime import datetime, timedelta, timezone


HN_ALGOLIA_URL = "https://hn.algolia.com/api/v1/search"

# Search terms to run against HN — broad enough to catch real discussions
SEARCH_TERMS = [
    "LLM",
    "large language model",
    "AI agent",
    "GPT",
    "Claude AI",
    "Gemini AI",
    "open source AI",
    "local LLM",
    "RAG retrieval",
    "AI inference",
    "fine tuning LLM",
    "AI automation",
]

# Minimum points to filter out noise
MIN_POINTS = 5


def fetch_stories(days_back: int = 1) -> list[dict]:
    """
    Fetch recent AI-related HN stories using the Algolia search API.
    Returns items in the same format as the arXiv collector.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
    cutoff_ts = int(cutoff.timestamp())

    seen_ids = set()
    stories = []

    for term in SEARCH_TERMS:
        params = {
            "query": term,
            "tags": "story",
            "numericFilters": f"created_at_i>{cutoff_ts},points>={MIN_POINTS}",
            "hitsPerPage": 30,
        }

        try:
            response = requests.get(HN_ALGOLIA_URL, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
        except Exception:
            continue

        for hit in data.get("hits", []):
            story_id = hit.get("objectID")
            if story_id in seen_ids:
                continue
            seen_ids.add(story_id)

            title = hit.get("title", "").strip()
            if not title:
                continue

            points = hit.get("points", 0) or 0
            comments = hit.get("num_comments", 0) or 0
            url = hit.get("url") or f"https://news.ycombinator.com/item?id={story_id}"
            created_ts = hit.get("created_at_i", 0)
            published = datetime.fromtimestamp(created_ts, tz=timezone.utc)

            stories.append({
                "title": title,
                "abstract": f"Hacker News discussion — {points} points, {comments} comments. URL: {url}",
                "authors": [],
                "url": url,
                "hn_url": f"https://news.ycombinator.com/item?id={story_id}",
                "published": published,
                "source": "Hacker News",
                "engagement": {"points": points, "comments": comments},
            })

        # Be polite to the API
        time.sleep(0.3)

    # Sort by points descending, keep top 30
    stories.sort(key=lambda s: s["engagement"]["points"], reverse=True)
    return stories[:30]


def filter_relevant_stories(stories: list[dict], topic_keywords: dict) -> list[dict]:
    """Tag each story with the best-matching topic bucket."""
    scored = []
    for story in stories:
        text = story["title"].lower()
        best_topic = None
        best_score = 0

        for topic, keywords in topic_keywords.items():
            score = sum(1 for kw in keywords if kw in text)
            if score > best_score:
                best_score = score
                best_topic = topic

        # HN stories are already filtered by search term so keep even with score 0
        story["topic"] = best_topic or "LLMs"
        story["relevance_score"] = best_score
        scored.append(story)

    return scored
