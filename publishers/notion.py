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

    # Priority trends
    blocks.append(_heading2("🔥 Priority Trends — Business Buyer · Technical DM · Internal Champion"))
    if priority_trends:
        for trend in priority_trends:
            blocks.extend(_trend_block(trend, is_priority=True))
    else:
        blocks.append(_paragraph("No priority trends identified today."))

    blocks.append(_divider())

    # LLMs
    blocks.append(_heading2("📌 Large Language Models (LLMs)"))
    if llm_trends:
        for trend in llm_trends:
            blocks.extend(_trend_block(trend))
    else:
        blocks.append(_paragraph("No new LLM trends today beyond priority items."))

    blocks.append(_divider())

    # AI Agents
    blocks.append(_heading2("📌 AI Agents & Automation"))
    if agent_trends:
        for trend in agent_trends:
            blocks.extend(_trend_block(trend))
    else:
        blocks.append(_paragraph("No new agent trends today beyond priority items."))

    blocks.append(_divider())

    # GPU & Infrastructure
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
                f"{item.get('title', 'Unknown')}  ({item.get('category', '')})\n"
                f"{item.get('why_watching', '')}\n"
                f"Signal so far: {item.get('signal_so_far', 'Emerging')}",
                emoji="👀"
            ))
    else:
        blocks.append(_paragraph("Nothing on the watch list today."))

    # Create the page
    response = notion.pages.create(
        parent={"page_id": parent_page_id},
        properties={
            "title": [{"type": "text", "text": {"content": title}}]
        },
        children=blocks[:100],
    )

    page_id = response["id"]
    page_url = response.get("url", f"https://notion.so/{page_id.replace('-', '')}")

    # Append remaining blocks if over the 100-block API limit
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


def _trend_block(trend: dict, is_priority: bool = False) -> list[dict]:
    """Render a single trend as a sequence of Notion blocks."""
    blocks = []

    title = trend.get("title", "Untitled Trend")
    prefix = "⭐ PRIORITY — " if is_priority else ""
    blocks.append(_heading3(f"{prefix}{title}"))

    # ── Content Brief ────────────────────────────────────────────
    brief = trend.get("content_brief", {})
    if brief:
        purpose = brief.get("purpose", "")
        topic = brief.get("topic", "")
        points = brief.get("content_points", [])
        formats = brief.get("format_options", [])

        brief_lines = ["✍️  CONTENT BRIEF"]
        if purpose:
            brief_lines.append(f"Purpose: {purpose}")
        if topic:
            brief_lines.append(f"Angle: {topic}")
        if points:
            brief_lines.append("\nContent points:")
            for p in points:
                brief_lines.append(f"  • {p}")
        if formats:
            brief_lines.append(f"\nFormat options: {' · '.join(formats)}")

        blocks.append(_callout("\n".join(brief_lines), emoji="✍️"))

    # ── Action & Metadata ────────────────────────────────────────
    action_emoji = {"Publish Now": "🟢", "Watch 2 Weeks": "🟡", "Skip": "🔴"}.get(
        trend.get("recommended_action", ""), "⚪"
    )
    blocks.append(_bullet(
        f"{action_emoji} Action: {trend.get('recommended_action', 'Unknown')}"
    ))

    blocks.append(_bullet(
        f"Trend curve: {trend.get('trend_curve', 'Unknown')} · "
        f"Vendor sales pitch risk (90 days): {trend.get('sales_pitch_risk', 'Unknown')} "
        f"— likely to appear in sales calls; buyers should know how to evaluate it"
    ))

    # Audience lanes — always listed individually
    lanes = trend.get("audience_lanes", [])
    if lanes:
        blocks.append(_bullet(f"Audiences: {' · '.join(lanes)}"))

    # Signal quality
    blocks.append(_bullet(f"Signal: {trend.get('signal_quality', 'No assessment.')}"))

    # Content gap — with current coverage context
    gap_data = trend.get("content_gap", {})
    if isinstance(gap_data, dict):
        current = gap_data.get("current_coverage", "")
        gap = gap_data.get("gap", "")
        if current:
            blocks.append(_bullet(f"Current coverage: {current}"))
        if gap:
            blocks.append(_bullet(f"Content gap: {gap}"))
    elif isinstance(gap_data, str):
        blocks.append(_bullet(f"Content gap: {gap_data}"))

    # Supporting papers with authors and dates
    papers = trend.get("supporting_papers", [])
    for paper in papers[:3]:
        if isinstance(paper, dict):
            p_title = paper.get("title", "Unknown")
            p_authors = paper.get("authors", [])
            p_date = paper.get("date", "")
            author_str = ", ".join(p_authors[:2])
            if len(p_authors) > 2:
                author_str += " et al."
            cite = f"📄 {p_title}"
            if author_str:
                cite += f" — {author_str}"
            if p_date:
                cite += f" ({p_date})"
            blocks.append(_bullet(cite))
        elif isinstance(paper, str):
            blocks.append(_bullet(f"📄 {paper}"))

    blocks.append(_paragraph(" "))
    return blocks
