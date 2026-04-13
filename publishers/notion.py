"""
Notion publisher — creates a daily digest page in Notion.
Uses the official notion-client Python library.
"""

import os
from datetime import datetime, timezone
from notion_client import Client


def publish_digest(analysis: dict, item_count: int = 0, paper_count: int = 0,
                   source_counts: dict = None, qa_report: dict = None) -> str:
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
    total = item_count or paper_count
    sources_str = ""
    if source_counts:
        sources_str = " · ".join(f"{s}: {c}" for s, c in source_counts.items())
    else:
        sources_str = "arXiv"

    blocks.append(_callout(
        f"Analysed {total} items — {sources_str} · "
        f"{len(trends)} trends identified · {len(priority_trends)} priority · "
        f"Generated {datetime.now(timezone.utc).strftime('%H:%M UTC')}",
        emoji="🤖"
    ))

    blocks.append(_divider())

    # QA audit block
    if qa_report:
        blocks.append(_qa_block(qa_report))
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


def _bullet_with_link(prefix: str, link_text: str, url: str, suffix: str = "") -> dict:
    """Bullet point where one part of the text is a clickable link."""
    rich_text = []
    if prefix:
        rich_text.append({"type": "text", "text": {"content": prefix}})
    rich_text.append({
        "type": "text",
        "text": {"content": link_text, "link": {"url": url}},
        "annotations": {"underline": True},
    })
    if suffix:
        rich_text.append({"type": "text", "text": {"content": suffix}})
    return {
        "object": "block",
        "type": "bulleted_list_item",
        "bulleted_list_item": {"rich_text": rich_text},
    }


def _qa_block(qa_report: dict) -> dict:
    """Render a quality assurance summary callout showing what each check did."""
    lines = ["🔬  Quality Checks — what ran before this was published\n"]

    # Relevance filter
    f = qa_report.get("filter", {})
    kept = f.get("kept", "?")
    total = f.get("total", "?")
    dropped = f.get("dropped", [])
    if dropped:
        dropped_str = ", ".join(f"[{d['source']}] {d['title'][:50]}" for d in dropped)
        lines.append(f"Semantic filter: {kept}/{total} items kept — removed: {dropped_str}")
    else:
        lines.append(f"Semantic filter: all {total} items confirmed relevant — nothing dropped")

    # URL verification
    u = qa_report.get("url_verification", {})
    fabricated = u.get("fabricated", [])
    if fabricated:
        fab_str = "; ".join(f['url'][:60] for f in fabricated)
        lines.append(f"URL verification: {len(fabricated)} fabricated link(s) stripped — {fab_str}")
    else:
        lines.append("URL verification: all source URLs verified against input data")

    # Accuracy review
    a = qa_report.get("accuracy", {})
    corrected = a.get("corrected", [])
    clean_count = a.get("clean_count", 0)
    status = a.get("status", "unknown")
    if status.startswith("error"):
        lines.append(f"Accuracy review: skipped ({status})")
    elif corrected:
        corrections_str = "; ".join(
            f"\"{c['title'][:40]}\" — {c['note'][:80]}" for c in corrected
        )
        lines.append(
            f"Accuracy review: {len(corrected)} correction(s) applied, {clean_count} passed — {corrections_str}"
        )
    else:
        lines.append(f"Accuracy review: all {clean_count} trend(s) passed — no corrections needed")

    return _callout("\n".join(lines), emoji="🔬")


def _trend_block(trend: dict, is_priority: bool = False) -> list[dict]:
    """Render a single trend as a sequence of Notion blocks."""
    blocks = []

    title = trend.get("title", "Untitled Trend")
    prefix = "⭐ PRIORITY — " if is_priority else ""
    blocks.append(_heading3(f"{prefix}{title}"))

    # ── Accuracy review note ─────────────────────────────────────
    reviewer_note = trend.get("reviewer_note")
    if reviewer_note:
        blocks.append(_callout(f"Accuracy review: {reviewer_note}", emoji="🔍"))
    else:
        blocks.append(_callout("Accuracy reviewed — no issues found", emoji="✅"))

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

    # Supporting sources — papers, HN stories, Reddit posts (with clickable links)
    sources = trend.get("supporting_sources", trend.get("supporting_papers", []))
    source_icons = {
        "arXiv": "📄",
        "Hacker News": "🔶",
        "Reddit r/MachineLearning": "🟠",
        "Reddit r/LocalLLaMA": "🟠",
    }
    for item in sources[:3]:
        if isinstance(item, dict):
            s_title = item.get("title", "Unknown")
            s_source = item.get("source", "arXiv")
            s_url = item.get("url", "")
            s_authors = item.get("authors", [])
            s_date = item.get("date", "")
            icon = source_icons.get(s_source, "📄")
            author_str = ", ".join(s_authors[:2])
            if len(s_authors) > 2:
                author_str += " et al."
            prefix = f"{icon} [{s_source}] "
            suffix = ""
            if author_str:
                suffix += f" — {author_str}"
            if s_date:
                suffix += f" ({s_date})"
            if s_url:
                blocks.append(_bullet_with_link(prefix, s_title, s_url, suffix))
            else:
                blocks.append(_bullet(f"{prefix}{s_title}{suffix}"))
        elif isinstance(item, str):
            blocks.append(_bullet(f"📄 {item}"))

    blocks.append(_paragraph(" "))
    return blocks
