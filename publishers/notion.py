"""
Notion publisher — creates a daily digest page in Notion.
Uses the official notion-client Python library.
"""

import os
from datetime import datetime, timezone
from notion_client import Client


def publish_digest(analysis: dict, paper_count: int) -> str:
    """
    Create a new Notion page with today's AI trend digest.
    Returns the URL of the created page.
    """
    notion = Client(auth=os.environ["NOTION_API_KEY"])
    parent_page_id = os.environ["NOTION_PARENT_PAGE_ID"]

    today = datetime.now(timezone.utc).strftime("%B %d, %Y")
    title = f"AI Trend Digest — {today}"

    trends = analysis.get("trends", [])
    watch_list = analysis.get("watch_list", [])

    # Separate priority trends from category-specific ones
    priority_trends = [t for t in trends if t.get("priority")]
    llm_trends = [t for t in trends if t.get("category") == "LLMs" and not t.get("priority")]
    agent_trends = [t for t in trends if t.get("category") == "AI Agents & Automation" and not t.get("priority")]
    gpu_trends = [t for t in trends if t.get("category") == "GPU & Infrastructure" and not t.get("priority")]

    blocks = []

    # Header callout
    blocks.append(_callout(
        f"Analysed {paper_count} papers from arXiv (cs.AI, cs.LG, cs.CL) · "
        f"{len(trends)} trends identified · {len(priority_trends)} priority · "
        f"Generated {datetime.now(timezone.utc).strftime('%H:%M UTC')}",
        emoji="🤖"
    ))

    blocks.append(_divider())

    # Priority trends section
    blocks.append(_heading2("🔥 Priority Trends — Serves All Three Audiences"))

    if priority_trends:
        for trend in priority_trends:
            blocks.extend(_trend_block(trend, is_priority=True))
    else:
        blocks.append(_paragraph("No priority trends identified today."))

    blocks.append(_divider())

    # LLMs section
    blocks.append(_heading2("📌 Large Language Models (LLMs)"))
    if llm_trends:
        for trend in llm_trends:
            blocks.extend(_trend_block(trend))
    else:
        blocks.append(_paragraph("No new LLM trends today beyond priority items."))

    blocks.append(_divider())

    # AI Agents section
    blocks.append(_heading2("📌 AI Agents & Automation"))
    if agent_trends:
        for trend in agent_trends:
            blocks.extend(_trend_block(trend))
    else:
        blocks.append(_paragraph("No new agent trends today beyond priority items."))

    blocks.append(_divider())

    # GPU & Infrastructure section
    blocks.append(_heading2("📌 GPU & Infrastructure"))
    if gpu_trends:
        for trend in gpu_trends:
            blocks.extend(_trend_block(trend))
    else:
        blocks.append(_paragraph("No new GPU/infrastructure trends today beyond priority items."))

    blocks.append(_divider())

    # Watch list
    blocks.append(_heading2("💡 Watch List — Too Early to Publish"))
    if watch_list:
        for item in watch_list:
            blocks.append(_callout(
                f"**{item.get('title', 'Unknown')}** ({item.get('category', '')})\n"
                f"{item.get('why_watching', '')}\n"
                f"Signal so far: {item.get('signal_so_far', 'Emerging')}",
                emoji="👀"
            ))
    else:
        blocks.append(_paragraph("Nothing on the watch list today."))

    # Notion API: create the page
    # Split blocks into chunks of 100 (Notion API limit per request)
    response = notion.pages.create(
        parent={"page_id": parent_page_id},
        properties={
            "title": [{"type": "text", "text": {"content": title}}]
        },
        children=blocks[:100],
    )

    page_id = response["id"]
    page_url = response.get("url", f"https://notion.so/{page_id.replace('-', '')}")

    # Append remaining blocks if we hit the 100-block limit
    if len(blocks) > 100:
        for chunk_start in range(100, len(blocks), 100):
            notion.blocks.children.append(
                block_id=page_id,
                children=blocks[chunk_start:chunk_start + 100],
            )

    return page_url


# ── Block builder helpers ────────────────────────────────────────────────────

def _heading2(text: str) -> dict:
    return {
        "object": "block",
        "type": "heading_2",
        "heading_2": {
            "rich_text": [{"type": "text", "text": {"content": text}}]
        },
    }


def _heading3(text: str) -> dict:
    return {
        "object": "block",
        "type": "heading_3",
        "heading_3": {
            "rich_text": [{"type": "text", "text": {"content": text}}]
        },
    }


def _paragraph(text: str, bold: bool = False) -> dict:
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {
            "rich_text": [
                {
                    "type": "text",
                    "text": {"content": text},
                    "annotations": {"bold": bold},
                }
            ]
        },
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
        "bulleted_list_item": {
            "rich_text": [{"type": "text", "text": {"content": text}}]
        },
    }


def _trend_block(trend: dict, is_priority: bool = False) -> list[dict]:
    """
    Render a single trend as a sequence of Notion blocks.
    """
    blocks = []

    title = trend.get("title", "Untitled Trend")
    prefix = "⭐ PRIORITY — " if is_priority else ""

    # Trend title as H3
    blocks.append(_heading3(f"{prefix}{title}"))

    # Content brief — the most important line
    brief = trend.get("content_brief", "")
    if brief:
        blocks.append(_callout(f"BRIEF: {brief}", emoji="✍️"))

    # Metadata bullets
    action_emoji = {"Publish Now": "🟢", "Watch 2 Weeks": "🟡", "Skip": "🔴"}.get(
        trend.get("recommended_action", ""), "⚪"
    )
    blocks.append(_bullet(
        f"{action_emoji} Action: {trend.get('recommended_action', 'Unknown')}"
    ))
    blocks.append(_bullet(
        f"Trend curve: {trend.get('trend_curve', 'Unknown')} · "
        f"Vendor pitch in 90 days: {trend.get('vendor_pitch_likelihood', 'Unknown')}"
    ))
    blocks.append(_bullet(
        f"Audience: {trend.get('audience_lane', 'Unknown')}"
    ))
    blocks.append(_bullet(
        f"Signal: {trend.get('signal_quality', 'No assessment.')}"
    ))
    blocks.append(_bullet(
        f"Content gap: {trend.get('content_gap', 'No gap identified.')}"
    ))

    # Supporting papers
    papers = trend.get("supporting_papers", [])
    if papers:
        blocks.append(_bullet(
            f"From papers: {' · '.join(papers[:3])}"
        ))

    # Spacer paragraph
    blocks.append(_paragraph(" "))

    return blocks
