"""
AI Trend Monitor — main pipeline
Run this script daily to collect, analyse, and publish the digest.

Usage:
    python main.py              # run with defaults (last 24h of papers)
    python main.py --days 2     # extend lookback to 48h (e.g. after a weekend)
    python main.py --dry-run    # analyse but don't publish to Notion
"""

import argparse
import sys
from dotenv import load_dotenv

# Load .env file before anything else
load_dotenv()

from collectors.arxiv import fetch_papers, filter_relevant_papers
from analyzers.claude import analyze_trends
from publishers.notion import publish_digest


def main():
    parser = argparse.ArgumentParser(description="AI Trend Monitor")
    parser.add_argument(
        "--days",
        type=int,
        default=1,
        help="How many days back to look for papers (default: 1)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run the full analysis but skip publishing to Notion",
    )
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print("  AI Trend Monitor")
    print(f"{'='*60}\n")

    # ── Step 1: Collect ──────────────────────────────────────────
    print(f"[1/3] Fetching arXiv papers (last {args.days} day(s))...")
    try:
        all_papers = fetch_papers(days_back=args.days, max_results=100)
        relevant_papers = filter_relevant_papers(all_papers)
    except Exception as e:
        print(f"  ERROR fetching papers: {e}")
        sys.exit(1)

    print(f"  Found {len(all_papers)} total papers")
    print(f"  {len(relevant_papers)} matched relevance filter\n")

    if not relevant_papers:
        print("  No relevant papers found. Try --days 2 to extend the window.")
        sys.exit(0)

    # Show what we're working with
    from collections import Counter
    topic_counts = Counter(p.get("topic") for p in relevant_papers)
    for topic, count in topic_counts.items():
        print(f"  • {topic}: {count} papers")
    print()

    # ── Step 2: Analyse ──────────────────────────────────────────
    print("[2/3] Analysing trends with Claude...")
    try:
        analysis = analyze_trends(relevant_papers)
    except Exception as e:
        print(f"  ERROR during analysis: {e}")
        sys.exit(1)

    trends = analysis.get("trends", [])
    watch_list = analysis.get("watch_list", [])
    priority = [t for t in trends if t.get("priority")]

    print(f"  Identified {len(trends)} trends ({len(priority)} priority)")
    print(f"  Watch list: {len(watch_list)} items\n")

    # Print a preview
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
        print("[3/3] Dry run — skipping Notion publish.")
        print("\n  Full analysis JSON:")
        import json
        print(json.dumps(analysis, indent=2))
    else:
        print("[3/3] Publishing digest to Notion...")
        try:
            page_url = publish_digest(analysis, paper_count=len(relevant_papers))
            print(f"  Done! Digest published:")
            print(f"  {page_url}")
        except Exception as e:
            print(f"  ERROR publishing to Notion: {e}")
            print("\n  Tip: Check your NOTION_API_KEY and NOTION_PARENT_PAGE_ID in .env")
            sys.exit(1)

    print(f"\n{'='*60}")
    print("  Pipeline complete.")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
