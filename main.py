"""
AI Trend Monitor — main pipeline
Run this script daily to collect, analyse, and publish the digest.

Usage:
    python main.py              # run with defaults (last 24h)
    python main.py --days 2     # extend lookback to 48h (e.g. after a weekend)
    python main.py --dry-run    # analyse but don't publish to Notion
"""

import argparse
import os
import sys
from collections import Counter
from dotenv import load_dotenv

load_dotenv()

from collectors.arxiv import fetch_papers, filter_relevant_papers, TOPIC_KEYWORDS
from collectors.hackernews import fetch_stories, filter_relevant_stories
from collectors.reddit import fetch_posts, filter_relevant_posts
from collectors.rss import fetch_entries, filter_relevant_entries
from analyzers.claude import analyze_trends
from publishers.notion import publish_digest
from publishers.email import send_digest


def main():
    parser = argparse.ArgumentParser(description="AI Trend Monitor")
    parser.add_argument("--days", type=int, default=1)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print("  AI Trend Monitor")
    print(f"{'='*60}\n")

    all_items = []

    # ── Step 1a: arXiv ───────────────────────────────────────────
    print(f"[1/4] Fetching arXiv papers (last {args.days} day(s))...")
    try:
        papers = fetch_papers(days_back=args.days, max_results=100)
        relevant_papers = filter_relevant_papers(papers)
        for p in relevant_papers:
            p["source"] = "arXiv"
        all_items.extend(relevant_papers)
        print(f"  {len(relevant_papers)} relevant papers")
    except Exception as e:
        print(f"  WARNING: arXiv fetch failed — {e}")

    # ── Step 1b: Hacker News ─────────────────────────────────────
    print("[2/4] Fetching Hacker News stories...")
    try:
        stories = fetch_stories(days_back=args.days)
        relevant_stories = filter_relevant_stories(stories, TOPIC_KEYWORDS)
        all_items.extend(relevant_stories)
        print(f"  {len(relevant_stories)} relevant stories")
    except Exception as e:
        print(f"  WARNING: Hacker News fetch failed — {e}")

    # ── Step 1c: Reddit ──────────────────────────────────────────
    print("[3/4] Fetching Reddit posts...")
    try:
        posts = fetch_posts(days_back=args.days)
        relevant_posts = filter_relevant_posts(posts, TOPIC_KEYWORDS)
        all_items.extend(relevant_posts)
        print(f"  {len(relevant_posts)} relevant posts")
    except Exception as e:
        print(f"  WARNING: Reddit fetch failed — {e}")

    # ── Step 1d: RSS feeds ───────────────────────────────────────
    print("[4/4] Fetching RSS feeds (blogs & newsletters)...")
    try:
        # Use days_back=2 for RSS since blogs don't publish every day
        rss_days = max(args.days, 2)
        entries = fetch_entries(days_back=rss_days)
        relevant_entries = filter_relevant_entries(entries, TOPIC_KEYWORDS)
        all_items.extend(relevant_entries)
        print(f"  {len(relevant_entries)} relevant entries")
    except Exception as e:
        print(f"  WARNING: RSS fetch failed — {e}")

    if not all_items:
        print("\n  No items collected from any source. Try --days 2.")
        sys.exit(0)

    # Summary
    print(f"\n  Total items: {len(all_items)}")
    source_counts = Counter(item.get("source", "unknown") for item in all_items)
    topic_counts = Counter(item.get("topic") for item in all_items)
    for source, count in source_counts.items():
        print(f"  • {source}: {count}")
    print()
    for topic, count in topic_counts.items():
        print(f"  • {topic}: {count} items")
    print()

    # Cap total items sent to Claude — 25 keeps response well within token limit
    all_items.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
    items_for_analysis = all_items[:25]

    # ── Step 2: Analyse ──────────────────────────────────────────
    print("[5/5] Analysing trends with Claude...")
    try:
        analysis = analyze_trends(items_for_analysis)
    except Exception as e:
        print(f"  ERROR during analysis: {e}")
        sys.exit(1)

    trends = analysis.get("trends", [])
    watch_list = analysis.get("watch_list", [])
    priority = [t for t in trends if t.get("priority")]

    print(f"  Identified {len(trends)} trends ({len(priority)} priority)")
    print(f"  Watch list: {len(watch_list)} items\n")

    if priority:
        print("  🔥 Priority trends:")
        for t in priority:
            print(f"     • {t['title']}")
        print()

    for t in trends:
        action = t.get("recommended_action", "?")
        marker = "🟢" if action == "Publish Now" else "🟡" if action == "Watch 2 Weeks" else "🔴"
        print(f"  {marker} [{t.get('category', '?')}] {t['title']}")

    print()

    # ── Step 3: Publish ──────────────────────────────────────────
    if args.dry_run:
        print("[5/5] Dry run — skipping Notion publish and email.")
        import json
        print("\n  Full analysis JSON:")
        print(json.dumps(analysis, indent=2))
    else:
        # Notion
        print("[5/5] Publishing digest to Notion...")
        page_url = ""
        try:
            page_url = publish_digest(analysis, item_count=len(items_for_analysis),
                                      source_counts=source_counts)
            print(f"  Done! {page_url}")
        except Exception as e:
            print(f"  ERROR publishing to Notion: {e}")
            sys.exit(1)

        # Email — only if Resend is configured
        if os.environ.get("RESEND_API_KEY") and os.environ.get("DIGEST_EMAIL"):
            print("  Sending email digest...")
            try:
                send_digest(analysis, notion_url=page_url,
                            source_counts=source_counts,
                            item_count=len(items_for_analysis))
            except Exception as e:
                print(f"  WARNING: Email failed — {e}")
                print("  (Notion page was still published successfully)")
        else:
            print("  Email skipped — RESEND_API_KEY / DIGEST_EMAIL not configured")

    print(f"\n{'='*60}")
    print("  Pipeline complete.")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
