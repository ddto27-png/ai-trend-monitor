"""
Notion publisher for the Skitsa cross-disciplinary monitor.
Creates one page per run: "[Field] Digest — [date]" as a child of NOTION_PARENT_PAGE_ID.
"""

import os
from datetime import datetime, timezone
from notion_client import Client


def publish_field_digest(analysis: dict, field_config: dict,
                         article_count: int, source_counts: dict) -> str:
    """
    Publish the cross-disciplinary digest to Notion.
    Returns the URL of the created page.
    """
    notion = Client(auth=os.environ["NOTION_API_KEY"])
    parent_page_id = os.environ["NOTION_PARENT_PAGE_ID"]

    today = datetime.now(timezone.utc).strftime("%B %d, %Y")
    field_name = field_config["name"]
    title = f"{field_name} × AI — {today}"

    insights   = analysis.get("insights", [])
    watch_list = analysis.get("watch_list", [])
    field_summary = analysis.get("field_summary", "")
    fabricated = analysis.get("_fabricated_urls", [])
    priority_insights = [i for i in insights if i.get("priority")]

    blocks = []

    # ── Header ────────────────────────────────────────────────────────────────
    sources_str = " · ".join(f"{s}: {c}" for s, c in source_counts.items())
    blocks.append(_callout(
        f"{field_name} × AI / Marketing  ·  {article_count} articles scanned  ·  "
        f"{len(insights)} insight{'s' if len(insights) != 1 else ''} identified  ·  "
        f"{len(priority_insights)} priority  ·  "
        f"Generated {datetime.now(timezone.utc).strftime('%H:%M UTC')}",
        emoji="✦"
    ))

    # ── URL check ─────────────────────────────────────────────────────────────
    if fabricated:
        fab_lines = "\n".join(f"  ✗ {u[:100]}" for u in fabricated)
        url_text = f"URL check: {len(fabricated)} fabricated link(s) stripped before publish\n{fab_lines}"
    else:
        url_text = "URL check: all source links verified against input articles — none fabricated"
    blocks.append(_callout(url_text[:1990], emoji="🔗"))

    blocks.append(_divider())

    # ── Field summary ─────────────────────────────────────────────────────────
    blocks.append(_heading2(f"This week in {field_name}"))
    if field_summary:
        blocks.append(_paragraph(field_summary))

    blocks.append(_divider())

    # ── Insights ──────────────────────────────────────────────────────────────
    blocks.append(_heading2(f"Insights — {field_config['lens']}"))

    if insights:
        for insight in insights:
            blocks.extend(_insight_block(insight))
    else:
        blocks.append(_paragraph("No strong cross-disciplinary insights found today."))

    blocks.append(_divider())

    # ── Watch list ────────────────────────────────────────────────────────────
    blocks.append(_heading2("On the Radar — Not Ready Yet"))
    if watch_list:
        for item in watch_list:
            blocks.append(_callout(str(item), emoji="👁"))
    else:
        blocks.append(_paragraph("Nothing on the radar today."))

    # ── Create page ───────────────────────────────────────────────────────────
    response = notion.pages.create(
        parent={"page_id": parent_page_id},
        properties={
            "title": [{"type": "text", "text": {"content": title}}]
        },
        children=blocks[:100],
    )

    page_id = response["id"]
    page_url = response.get("url", f"https://notion.so/{page_id.replace('-', '')}")

    if len(blocks) > 100:
        for start in range(100, len(blocks), 100):
            notion.blocks.children.append(
                block_id=page_id,
                children=blocks[start:start + 100],
            )

    return page_url


# ── Block helpers ─────────────────────────────────────────────────────────────

def _heading2(text: str) -> dict:
    return {
        "object": "block",
        "type": "heading_2",
        "heading_2": {"rich_text": [{"type": "text", "text": {"content": text}}]},
    }


def _heading3(text: str) -> dict:
    return {
        "object": "block",
        "type": "heading_3",
        "heading_3": {"rich_text": [{"type": "text", "text": {"content": text}}]},
    }


def _paragraph(text: str) -> dict:
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {"rich_text": [{"type": "text", "text": {"content": text}}]},
    }


def _callout(text: str, emoji: str = "💡") -> dict:
    return {
        "object": "block",
        "type": "callout",
        "callout": {
            "rich_text": [{"type": "text", "text": {"content": text}}],
            "icon": {"type": "emoji", "emoji": emoji},
        },
    }


def _divider() -> dict:
    return {"object": "block", "type": "divider", "divider": {}}


def _bullet(text: str) -> dict:
    return {
        "object": "block",
        "type": "bulleted_list_item",
        "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": text}}]},
    }


def _bullet_link(prefix: str, link_text: str, url: str, suffix: str = "") -> dict:
    rich = []
    if prefix:
        rich.append({"type": "text", "text": {"content": prefix}})
    rich.append({
        "type": "text",
        "text": {"content": link_text, "link": {"url": url}},
        "annotations": {"underline": True},
    })
    if suffix:
        rich.append({"type": "text", "text": {"content": suffix}})
    return {
        "object": "block",
        "type": "bulleted_list_item",
        "bulleted_list_item": {"rich_text": rich},
    }


def _insight_block(insight: dict) -> list[dict]:
    blocks = []

    title = insight.get("title", "Untitled")
    prefix = "⭐ PRIORITY — " if insight.get("priority") else ""
    blocks.append(_heading3(f"{prefix}{title}"))

    # Field signal
    field_signal = insight.get("field_signal", "")
    if field_signal:
        blocks.append(_callout(f"In the field: {field_signal}", emoji="🏛"))

    # AI / Marketing connection
    connection = insight.get("ai_marketing_connection", "")
    if connection:
        blocks.append(_callout(f"AI / Marketing: {connection}", emoji="⚡"))

    # Teaching moment — the key insight
    teaching = insight.get("teaching_moment", "")
    if teaching:
        blocks.append(_callout(f"The insight: {teaching}", emoji="✦"))

    # Content angle
    angle = insight.get("content_angle", "")
    if angle:
        blocks.append(_callout(f"Skitsa angle: {angle}", emoji="✍️"))

    # Action
    action = insight.get("recommended_action", "?")
    marker = "🟢" if action == "Publish Now" else "🟡" if action == "Watch 2 Weeks" else "🔴"
    blocks.append(_bullet(f"{marker} {action}"))

    # Sources
    for url in insight.get("sources", [])[:3]:
        blocks.append(_bullet_link("Source: ", url, url))

    blocks.append(_paragraph(" "))
    return blocks
