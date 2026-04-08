"""
Reddit collector — fetches recent posts from AI-related subreddits.
Uses Reddit's public JSON API. No API key required.
"""

import time
import requests
from datetime import datetime, timedelta, timezone


SUBREDDITS = [
    "MachineLearning",
    "LocalLLaMA",
]

# Minimum score to filter noise
MIN_SCORE = 5

# Reddit requires a descriptive User-Agent to avoid 429s
HEADERS = {
    "User-Agent": "ai-trend-monitor/1.0 (automated research digest)"
}


def fetch_posts(days_back: int = 1) -> list[dict]:
    """
    Fetch recent posts from AI subreddits.
    Returns items in the same format as the arXiv collector.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
    all_posts = []
    seen_ids = set()

    for subreddit in SUBREDDITS:
        for sort in ["new", "hot"]:
            url = f"https://www.reddit.com/r/{subreddit}/{sort}.json"
            params = {"limit": 50}

            try:
                response = requests.get(url, headers=HEADERS, params=params, timeout=15)
                response.raise_for_status()
                data = response.json()
            except Exception:
                continue

            posts = data.get("data", {}).get("children", [])

            for post in posts:
                p = post.get("data", {})
                post_id = p.get("id")

                if post_id in seen_ids:
                    continue
                seen_ids.add(post_id)

                score = p.get("score", 0) or 0
                if score < MIN_SCORE:
                    continue

                created_ts = p.get("created_utc", 0)
                published = datetime.fromtimestamp(created_ts, tz=timezone.utc)

                if published < cutoff:
                    continue

                title = p.get("title", "").strip()
                if not title:
                    continue

                selftext = (p.get("selftext", "") or "").strip()
                num_comments = p.get("num_comments", 0) or 0
                post_url = f"https://reddit.com{p.get('permalink', '')}"
                external_url = p.get("url", post_url)

                # Use selftext as abstract if available, otherwise just metadata
                if selftext and len(selftext) > 50:
                    abstract = selftext[:400]
                else:
                    abstract = f"Reddit r/{subreddit} — {score} upvotes, {num_comments} comments."

                all_posts.append({
                    "title": title,
                    "abstract": abstract,
                    "authors": [],
                    "url": external_url,
                    "reddit_url": post_url,
                    "published": published,
                    "source": f"Reddit r/{subreddit}",
                    "engagement": {"score": score, "comments": num_comments},
                })

            time.sleep(0.5)

    # Sort by score descending, keep top 30
    all_posts.sort(key=lambda p: p["engagement"]["score"], reverse=True)
    return all_posts[:30]


def filter_relevant_posts(posts: list[dict], topic_keywords: dict) -> list[dict]:
    """Tag each post with the best-matching topic bucket."""
    scored = []
    for post in posts:
        text = (post["title"] + " " + post["abstract"]).lower()
        best_topic = None
        best_score = 0

        for topic, keywords in topic_keywords.items():
            score = sum(1 for kw in keywords if kw in text)
            if score > best_score:
                best_score = score
                best_topic = topic

        post["topic"] = best_topic or "LLMs"
        post["relevance_score"] = best_score
        scored.append(post)

    return scored
