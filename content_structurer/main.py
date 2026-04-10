"""
Content Structurer — main pipeline.

Reads today's 'Publish Now' content briefs from the Notion digest page
and generates complete first-draft articles using Claude.

Usage:
    python -m content_structurer.main            # full run
    python -m content_structurer.main --dry-run  # parse briefs, skip generation
"""

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from content_structurer.brief_extractor import extract_todays_briefs
from content_structurer.content_generator import generate_draft, save_draft
from content_structurer.draft_emailer import send_drafts

OUTPUT_DIR = Path(__file__).parent / "outputs"


def main() -> None:
    parser = argparse.ArgumentParser(description="Content Structurer")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse briefs from Notion but skip article generation",
    )
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print("  Content Structurer")
    print(f"{'='*60}\n")

    # ── Step 1: Extract briefs from Notion ───────────────────────
    print("[1/3] Fetching today's 'Publish Now' briefs from Notion...")
    briefs = extract_todays_briefs()

    if not briefs:
        print("\n  Nothing to generate today.")
        sys.exit(0)

    print(f"\n  {brief_label(len(briefs))} to process:")
    for b in briefs:
        print(f"    • {b['title']}")
    print()

    if args.dry_run:
        print("[2/2] Dry run — skipping article generation.\n")
        print("  Parsed briefs:\n")
        print(json.dumps(briefs, indent=2))
        return

    # ── Step 2: Generate drafts ───────────────────────────────────
    print(f"[2/3] Generating drafts with Claude → {OUTPUT_DIR}\n")
    saved: list[Path] = []
    ready_to_email: list[dict] = []
    failed = 0

    for i, brief in enumerate(briefs, 1):
        label = brief["title"][:70]
        print(f"  [{i}/{len(briefs)}] {label}...")
        try:
            draft = generate_draft(brief)
            path = save_draft(brief, draft, OUTPUT_DIR)
            saved.append(path)
            ready_to_email.append({**brief, "draft": draft})
            print(f"    ✓ {path.name}\n")
        except Exception as exc:
            print(f"    ✗ Error: {exc}\n")
            failed += 1

    print(f"{'='*60}")
    print(f"  Done. {len(saved)} draft(s) saved", end="")
    if failed:
        print(f", {failed} failed", end="")
    print(f"\n  Output directory: {OUTPUT_DIR}")
    print(f"{'='*60}\n")

    # ── Step 3: Email ─────────────────────────────────────────────
    if ready_to_email:
        print("[3/3] Sending drafts by email...")
        try:
            send_drafts(ready_to_email)
        except Exception as exc:
            print(f"  WARNING: Email failed — {exc}")
            print("  (Drafts were still saved as artifacts)")


def brief_label(n: int) -> str:
    return f"{n} brief{'s' if n != 1 else ''}"


if __name__ == "__main__":
    main()
