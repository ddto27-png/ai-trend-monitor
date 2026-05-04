"""
Quick smoke test for Notion connectivity.
Publishes a minimal test page using the same publisher code as the real pipelines.
Run this to verify NOTION_API_KEY and NOTION_PARENT_PAGE_ID are correct.

Usage:
    python test_notion.py           # test AI digest publisher
    python test_notion.py --skitsa  # test Skitsa monitor publisher
"""

import argparse
import os
from dotenv import load_dotenv

load_dotenv()


def test_ai_digest():
    from publishers.notion import publish_digest

    sample_analysis = {
        "trends": [
            {
                "title": "Test Trend — delete me",
                "category": "LLMs",
                "priority": True,
                "recommended_action": "Publish Now",
                "trend_curve": "Accelerating",
                "sales_pitch_risk": "Medium",
                "signal_quality": "This is a test entry to verify Notion connectivity. Safe to delete.",
                "audience_lanes": ["Technical DM", "Business Buyer"],
                "content_gap": {"current_coverage": "None", "gap": "N/A"},
                "content_brief": {
                    "purpose": "Connectivity test",
                    "topic": "Verify the Notion publisher is working",
                    "content_points": ["Connection confirmed", "Delete this page"],
                    "format_options": ["N/A"],
                },
                "supporting_sources": [],
                "reviewer_note": None,
            }
        ],
        "watch_list": [],
    }

    qa_report = {
        "filter":           {"kept": 1, "total": 1, "dropped": [], "status": "ok"},
        "url_verification": {"fabricated": []},
        "accuracy":         {"corrected": [], "clean_count": 1, "status": "ok"},
    }

    print("Publishing test page to Notion (AI digest format)...")
    url = publish_digest(
        sample_analysis,
        item_count=1,
        source_counts={"test": 1},
        qa_report=qa_report,
    )
    print(f"\n  Success! Page created: {url}")
    print("  You can delete this page from Notion.")


def test_skitsa_monitor():
    from skitsa_monitor.publisher_notion import publish_field_digest

    sample_result = {
        "field": "Fashion & Luxury",
        "field_summary": "This is a test entry to verify the Skitsa monitor Notion publisher. Safe to delete.",
        "insights": [
            {
                "title": "Test Insight — delete me",
                "field_signal": "Connectivity test signal.",
                "ai_marketing_connection": "Connectivity test connection.",
                "teaching_moment": "If you can read this, Notion is working.",
                "content_angle": "Write a test post confirming the pipeline works.",
                "recommended_action": "Publish Now",
                "priority": True,
                "sources": [],
            }
        ],
        "watch_list": ["Test watch item 1", "Test watch item 2"],
        "_fabricated_urls": [],
    }

    print("Publishing test page to Notion (Skitsa monitor format)...")
    url = publish_field_digest(sample_result, article_count=1)
    print(f"\n  Success! Page created: {url}")
    print("  You can delete this page from Notion.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--skitsa", action="store_true",
                        help="Test the Skitsa monitor publisher instead of the AI digest")
    args = parser.parse_args()

    if not os.environ.get("NOTION_API_KEY"):
        print("ERROR: NOTION_API_KEY not set. Add it to your .env file.")
        raise SystemExit(1)
    if not os.environ.get("NOTION_PARENT_PAGE_ID"):
        print("ERROR: NOTION_PARENT_PAGE_ID not set. Add it to your .env file.")
        raise SystemExit(1)

    try:
        if args.skitsa:
            test_skitsa_monitor()
        else:
            test_ai_digest()
    except Exception as e:
        print(f"\n  FAILED: {e}")
        raise SystemExit(1)
