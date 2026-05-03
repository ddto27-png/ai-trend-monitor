"""
Skitsa Cross-Disciplinary Monitor — pipeline entry point.

Runs on a fixed weekly rotation:
  Monday    → Fashion & Luxury × AI / Marketing
  Tuesday   → Architecture & Design × AI / Marketing
  Thursday  → Film & Entertainment × AI / Marketing
  Friday    → Retail & Consumer × AI / Marketing

Usage:
  python -m skitsa_monitor.main              # today's field (skips Wed / weekends)
  python -m skitsa_monitor.main --field fashion
  python -m skitsa_monitor.main --days 5
  python -m skitsa_monitor.main --dry-run
"""

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from skitsa_monitor.schedule import get_today_field
from skitsa_monitor.collector import fetch_field_articles
from skitsa_monitor.analyzer import analyze_field
from skitsa_monitor.notion_publisher import publish_field_digest
from skitsa_monitor.email_publisher import send_field_digest
from skitsa_monitor.note_generator import generate_note, save_note


def main():
    parser = argparse.ArgumentParser(description="Skitsa Cross-Disciplinary Monitor")
    parser.add_argument("--field", type=str, default=None,
                        help="Field slug to run (fashion/architecture/film/retail). "
                             "Defaults to today's scheduled field.")
    parser.add_argument("--days", type=int, default=3,
                        help="Days back to collect articles (default: 3)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Analyse but don't publish to Notion or send email")
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print("  Skitsa Cross-Disciplinary Monitor")
    print(f"{'='*60}\n")

    # ── Resolve today's field ─────────────────────────────────────
    field_config = get_today_field(override=args.field)
    if field_config is None:
        if args.field:
            print(f"  Unknown field '{args.field}'. "
                  f"Valid slugs: fashion, architecture, film, retail")
        else:
            print("  No field scheduled for today. "
                  "Use --field to run a specific field, or wait for Mon/Tue/Thu/Fri.")
        sys.exit(0)

    print(f"  Field: {field_config['name']}")
    print(f"  Lens:  {field_config['lens']}\n")

    # ── Collect ───────────────────────────────────────────────────
    print(f"[1/4] Collecting articles (last {args.days} days)...")
    try:
        articles = fetch_field_articles(field_config["feeds"], days_back=args.days)
    except Exception as e:
        print(f"  ERROR collecting articles — {e}")
        sys.exit(1)

    if not articles:
        print(f"  No articles found. Try --days 5 or check feed availability.")
        sys.exit(0)

    source_counts = Counter(a["source"] for a in articles)
    print(f"  {len(articles)} articles collected:")
    for source, count in source_counts.items():
        print(f"    • {source}: {count}")

    # Cap at 30 articles sent to Claude — keeps the prompt focused
    articles_for_analysis = articles[:30]
    print(f"\n  Sending {len(articles_for_analysis)} to Claude for analysis...\n")

    # ── Analyse ───────────────────────────────────────────────────
    print("[2/4] Analysing cross-disciplinary insights with Claude Opus...")
    try:
        analysis = analyze_field(field_config, articles_for_analysis)
    except Exception as e:
        print(f"  ERROR during analysis — {e}")
        sys.exit(1)

    insights   = analysis.get("insights", [])
    watch_list = analysis.get("watch_list", [])
    fabricated = analysis.get("_fabricated_urls", [])
    priority   = [i for i in insights if i.get("priority")]

    print(f"  {len(insights)} insights identified ({len(priority)} priority)")
    print(f"  Watch list: {len(watch_list)} item(s)")
    if fabricated:
        print(f"  URL check: {len(fabricated)} fabricated link(s) stripped")
    else:
        print(f"  URL check: all source URLs verified — none fabricated")

    print()
    for insight in insights:
        action = insight.get("recommended_action", "?")
        marker = "🟢" if action == "Publish Now" else "🟡" if action == "Watch 2 Weeks" else "🔴"
        star   = "⭐ " if insight.get("priority") else "   "
        print(f"  {star}{marker} {insight['title']}")

    print()

    # ── Generate Substack notes ───────────────────────────────────
    publish_now = [i for i in insights if i.get("recommended_action") == "Publish Now"]
    notes: list[dict] = []
    output_dir = Path(__file__).parent / "outputs"

    if args.dry_run:
        print(f"[3/4] Dry run — skipping note generation and publish.")
        print("\n  Full analysis JSON:")
        print(json.dumps(analysis, indent=2, default=str))
    else:
        if publish_now:
            print(f"[3/4] Generating Substack notes for {len(publish_now)} "
                  f"'Publish Now' insight{'s' if len(publish_now) != 1 else ''}...\n")
            for insight in publish_now:
                label = insight["title"][:65]
                print(f"  {label}...")
                try:
                    note = generate_note(insight, field_config)
                    path = save_note(insight, note, field_config, output_dir)
                    notes.append({"insight": insight, "note": note})
                    print(f"    ✓ {path.name}\n")
                except Exception as e:
                    print(f"    ✗ Error: {e}\n")
        else:
            print("[3/4] No 'Publish Now' insights — skipping note generation.\n")

        # ── Publish ───────────────────────────────────────────────────
        print("[4/4] Publishing to Notion...")
        page_url = ""
        try:
            page_url = publish_field_digest(
                analysis=analysis,
                field_config=field_config,
                article_count=len(articles_for_analysis),
                source_counts=dict(source_counts),
                notes=notes or None,
            )
            print(f"  Done! {page_url}")
        except Exception as e:
            print(f"  ERROR publishing to Notion — {e}")
            sys.exit(1)

        if os.environ.get("RESEND_API_KEY") and os.environ.get("DIGEST_EMAIL"):
            print("  Sending email...")
            try:
                send_field_digest(
                    analysis=analysis,
                    field_config=field_config,
                    notion_url=page_url,
                    article_count=len(articles_for_analysis),
                    notes=notes or None,
                )
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
