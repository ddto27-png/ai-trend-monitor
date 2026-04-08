"""
Brief extractor — queries the Notion digest page and parses
content briefs from today's digest into structured dicts.

Reuses NOTION_API_KEY and NOTION_PARENT_PAGE_ID from the existing
trend monitor environment — no new credentials needed.
"""

import os
import re
from datetime import datetime, timezone

from notion_client import Client


def extract_todays_briefs() -> list[dict]:
    """
    Find today's AI Trend Digest page in Notion and return all
    'Publish Now' content briefs as structured dicts.
    """
    notion = Client(auth=os.environ["NOTION_API_KEY"])

    today_str = datetime.now(timezone.utc).strftime("%B %d, %Y")
    page_title = f"AI Trend Digest — {today_str}"
    print(f"  Searching for: {page_title}")

    results = notion.search(
        query=page_title,
        filter={"property": "object", "value": "page"},
    )

    pages = [
        p for p in results.get("results", [])
        if _page_title(p) == page_title
    ]

    if not pages:
        print(f"  No digest page found for today ({today_str}). "
              "Has the trend monitor run yet?")
        return []

    page_id = pages[0]["id"]
    print(f"  Found page: {page_id}")

    blocks = _get_all_blocks(notion, page_id)
    briefs = _parse_briefs(blocks)

    publish_now = [b for b in briefs if b.get("recommended_action") == "Publish Now"]
    print(f"  Parsed {len(briefs)} trend(s) — {len(publish_now)} marked 'Publish Now'")
    return publish_now


# ── Notion helpers ────────────────────────────────────────────────────────────

def _page_title(page: dict) -> str:
    """Extract the plain-text title from a Notion page object."""
    props = page.get("properties", {})
    title_prop = props.get("title", {})
    rich_text = title_prop.get("title", [])
    return "".join(rt.get("plain_text", "") for rt in rich_text)


def _get_all_blocks(notion: Client, block_id: str) -> list[dict]:
    """Fetch all top-level blocks for a page, handling pagination."""
    blocks = []
    cursor = None
    while True:
        kwargs = {"block_id": block_id}
        if cursor:
            kwargs["start_cursor"] = cursor
        response = notion.blocks.children.list(**kwargs)
        blocks.extend(response.get("results", []))
        if not response.get("has_more"):
            break
        cursor = response.get("next_cursor")
    return blocks


def _get_text(rich_text_list: list) -> str:
    """Concatenate plain_text from a Notion rich_text array."""
    return "".join(rt.get("plain_text", "") for rt in rich_text_list)


# ── Block parser ──────────────────────────────────────────────────────────────

def _parse_briefs(blocks: list[dict]) -> list[dict]:
    """
    Walk the block list and assemble one dict per trend.

    Page structure (produced by publishers/notion.py):
      H2  — category section heading
      H3  — trend title (may be prefixed with "⭐ PRIORITY — ")
      Callout (✍️) — content brief text
      Bullets — action, trend curve, audiences, signal, gap, sources
      Paragraph " " — spacer between trends
    """
    briefs: list[dict] = []
    current_title: str | None = None
    current_brief: dict | None = None
    reading_bullets = False  # True once we've seen the ✍️ callout for this trend

    for block in blocks:
        btype = block.get("type")

        if btype == "heading_3":
            # Flush any completed brief before starting the next trend
            if current_brief:
                briefs.append(current_brief)

            raw_title = _get_text(block["heading_3"]["rich_text"])
            current_title = re.sub(r"^⭐\s+PRIORITY\s+—\s+", "", raw_title).strip()
            current_brief = None
            reading_bullets = False

        elif btype == "callout" and current_title:
            icon = block["callout"].get("icon", {})
            emoji = icon.get("emoji", "") if icon.get("type") == "emoji" else ""

            if emoji == "✍️":
                text = _get_text(block["callout"]["rich_text"])
                parsed = _parse_brief_callout(text)
                current_brief = {
                    "title": current_title,
                    **parsed,
                    "recommended_action": None,
                    "audiences": [],
                    "trend_curve": None,
                    "signal_quality": None,
                }
                reading_bullets = True

        elif btype == "bulleted_list_item" and reading_bullets and current_brief:
            text = _get_text(block["bulleted_list_item"]["rich_text"])

            if "Action:" in text:
                # e.g. "🟢 Action: Publish Now"
                current_brief["recommended_action"] = (
                    text.split("Action:", 1)[-1].strip()
                )
            elif text.startswith("Trend curve:"):
                # e.g. "Trend curve: Rising · Vendor sales pitch risk..."
                curve = text.split("·")[0].replace("Trend curve:", "").strip()
                current_brief["trend_curve"] = curve
            elif text.startswith("Audiences:"):
                raw = text.replace("Audiences:", "").strip()
                current_brief["audiences"] = [a.strip() for a in raw.split("·")]
            elif text.startswith("Signal:"):
                current_brief["signal_quality"] = text.replace("Signal:", "").strip()

        elif btype in ("heading_2", "divider"):
            # Section boundary — flush any pending brief
            if current_brief:
                briefs.append(current_brief)
            current_brief = None
            current_title = None
            reading_bullets = False

    # Don't drop the last trend on the page
    if current_brief:
        briefs.append(current_brief)

    return briefs


def _parse_brief_callout(text: str) -> dict:
    """
    Parse the raw string from a ✍️ callout into structured fields.

    Expected format (mirrors publishers/notion.py _trend_block):
      ✍️  CONTENT BRIEF
      Purpose: ...
      Angle: ...

      Content points:
        • point 1
        • point 2

      Format options: option 1 · option 2 · option 3
    """
    purpose = ""
    angle = ""
    content_points: list[str] = []
    format_options: list[str] = []
    in_points = False

    for line in text.split("\n"):
        stripped = line.strip()

        if stripped.startswith("Purpose:"):
            purpose = stripped[len("Purpose:"):].strip()
            in_points = False
        elif stripped.startswith("Angle:"):
            angle = stripped[len("Angle:"):].strip()
            in_points = False
        elif stripped.startswith("Content points:"):
            in_points = True
        elif stripped.startswith("Format options:"):
            in_points = False
            opts_str = stripped[len("Format options:"):].strip()
            format_options = [o.strip() for o in opts_str.split("·") if o.strip()]
        elif in_points and stripped.startswith("•"):
            content_points.append(stripped[1:].strip())

    return {
        "purpose": purpose,
        "angle": angle,
        "content_points": content_points,
        "format_options": format_options,
    }
