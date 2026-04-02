"""
Email publisher — sends the daily digest as a formatted HTML email via Resend.
Free tier: 3,000 emails/month. Sign up at resend.com.

Required environment variables:
    RESEND_API_KEY  — your Resend API key (re_...)
    DIGEST_EMAIL    — address to deliver the digest to
"""

import os
import requests
from datetime import datetime, timezone


def send_digest(analysis: dict, notion_url: str, source_counts: dict,
                item_count: int) -> None:
    """Send the digest as an HTML email via Resend."""
    api_key = os.environ["RESEND_API_KEY"]
    to_emails = [e.strip() for e in os.environ["DIGEST_EMAIL"].split(",") if e.strip()]

    today = datetime.now(timezone.utc).strftime("%B %d, %Y")
    trends = analysis.get("trends", [])
    priority = [t for t in trends if t.get("priority")]

    subject = (
        f"AI Trend Digest — {today} · "
        f"{len(trends)} trends · {len(priority)} priority"
    )

    html = _build_html(analysis, notion_url, source_counts, item_count, today)

    response = requests.post(
        "https://api.resend.com/emails",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "from": "AI Trend Monitor <onboarding@resend.dev>",
            "to": to_emails,
            "subject": subject,
            "html": html,
        },
        timeout=15,
    )
    if not response.ok:
        print(f"  Resend error response: {response.text}")
    response.raise_for_status()
    print(f"  Email sent to {', '.join(to_emails)}")


def _build_html(analysis: dict, notion_url: str, source_counts: dict,
                item_count: int, today: str) -> str:
    """Build the HTML email body."""
    trends = analysis.get("trends", [])
    watch_list = analysis.get("watch_list", [])
    priority_trends = [t for t in trends if t.get("priority")]
    llm_trends = [t for t in trends if t.get("category") == "LLMs" and not t.get("priority")]
    agent_trends = [t for t in trends if t.get("category") == "AI Agents & Automation" and not t.get("priority")]
    gpu_trends = [t for t in trends if t.get("category") == "GPU & Infrastructure" and not t.get("priority")]

    sources_str = " · ".join(f"{s}: {c}" for s, c in source_counts.items())

    sections = []

    # ── Priority trends ──────────────────────────────────────────
    if priority_trends:
        items_html = "".join(_trend_html(t, is_priority=True) for t in priority_trends)
        sections.append(_section("🔥 Priority Trends", items_html,
                                  bg="#fff8e1", border="#f59e0b"))

    # ── Category sections ────────────────────────────────────────
    if llm_trends:
        items_html = "".join(_trend_html(t) for t in llm_trends)
        sections.append(_section("📌 Large Language Models (LLMs)", items_html))

    if agent_trends:
        items_html = "".join(_trend_html(t) for t in agent_trends)
        sections.append(_section("📌 AI Agents & Automation", items_html))

    if gpu_trends:
        items_html = "".join(_trend_html(t) for t in gpu_trends)
        sections.append(_section("📌 GPU & Infrastructure", items_html))

    # ── Watch list ───────────────────────────────────────────────
    if watch_list:
        watch_html = "".join(
            f"""<div style="padding:10px 0; border-bottom:1px solid #f0f0f0;">
              <strong>{w.get('title', '')} <span style="color:#888;font-size:12px;">({w.get('category','')})</span></strong><br>
              <span style="color:#555;font-size:14px;">{w.get('why_watching','')}</span><br>
              <span style="color:#aaa;font-size:12px;">Signal: {w.get('signal_so_far','Emerging')}</span>
            </div>"""
            for w in watch_list
        )
        sections.append(_section("💡 Watch List — Too Early to Publish", watch_html,
                                  bg="#f8f8f8"))

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f4f4f4;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <div style="max-width:680px;margin:0 auto;padding:20px;">

    <!-- Header -->
    <div style="background:#111;color:white;padding:24px 28px;border-radius:8px 8px 0 0;">
      <div style="font-size:13px;color:#aaa;margin-bottom:4px;">AI TREND DIGEST</div>
      <div style="font-size:24px;font-weight:700;">{today}</div>
      <div style="font-size:13px;color:#aaa;margin-top:8px;">
        {item_count} items analysed · {sources_str}
      </div>
    </div>

    <!-- Notion link -->
    <div style="background:#222;padding:12px 28px;">
      <a href="{notion_url}" style="color:#60a5fa;font-size:13px;text-decoration:none;">
        → Open full digest in Notion
      </a>
    </div>

    <!-- Sections -->
    <div style="background:white;border-radius:0 0 8px 8px;padding:8px 0;">
      {"".join(sections)}
    </div>

    <!-- Footer -->
    <div style="text-align:center;padding:20px;font-size:12px;color:#aaa;">
      AI Trend Monitor · Runs daily at 7am UTC
    </div>

  </div>
</body>
</html>"""


def _section(title: str, content_html: str, bg: str = "white",
             border: str = "#e5e7eb") -> str:
    return f"""
    <div style="margin:0;padding:20px 28px;border-bottom:2px solid {border};background:{bg};">
      <h2 style="margin:0 0 16px 0;font-size:16px;font-weight:700;color:#111;">{title}</h2>
      {content_html}
    </div>"""


def _trend_html(trend: dict, is_priority: bool = False) -> str:
    title = trend.get("title", "")
    action = trend.get("recommended_action", "")
    lanes = trend.get("audience_lanes", [])
    curve = trend.get("trend_curve", "")
    pitch = trend.get("sales_pitch_risk", trend.get("vendor_pitch_likelihood", ""))
    signal = trend.get("signal_quality", "")

    action_colour = {"Publish Now": "#16a34a", "Watch 2 Weeks": "#d97706", "Skip": "#dc2626"}.get(action, "#888")
    action_dot = {"Publish Now": "🟢", "Watch 2 Weeks": "🟡", "Skip": "🔴"}.get(action, "⚪")

    # Content brief
    brief = trend.get("content_brief", {})
    brief_html = ""
    if isinstance(brief, dict):
        purpose = brief.get("purpose", "")
        topic = brief.get("topic", "")
        points = brief.get("content_points", [])
        formats = brief.get("format_options", [])
        points_html = "".join(f"<li style='margin:3px 0;color:#374151;'>{p}</li>" for p in points)
        formats_str = " · ".join(formats)
        purpose_html = f'<div style="margin-bottom:6px"><strong>Purpose:</strong> <span style="color:#555">{purpose}</span></div>' if purpose else ''
        topic_html = f'<div style="margin-bottom:6px"><strong>Angle:</strong> <span style="color:#555">{topic}</span></div>' if topic else ''
        points_list_html = f'<ul style="margin:4px 0 6px 16px;padding:0">{points_html}</ul>' if points else ''
        formats_html = f'<div style="font-size:12px;color:#888"><strong>Formats:</strong> {formats_str}</div>' if formats else ''
        brief_html = f"""
        <div style="background:#f8fafc;border-left:3px solid #6366f1;padding:12px 14px;margin:10px 0;border-radius:0 4px 4px 0;">
          <div style="font-size:11px;font-weight:700;color:#6366f1;margin-bottom:6px;">CONTENT BRIEF</div>
          {purpose_html}{topic_html}{points_list_html}{formats_html}
        </div>"""

    # Content gap
    gap_data = trend.get("content_gap", {})
    gap_html = ""
    if isinstance(gap_data, dict):
        current = gap_data.get("current_coverage", "")
        gap = gap_data.get("gap", "")
        if current or gap:
            current_html = f'<div style="color:#888;margin-bottom:3px"><em>{current}</em></div>' if current else ''
            gap_text_html = f'<div style="color:#374151"><strong>Gap:</strong> {gap}</div>' if gap else ''
            gap_html = f'<div style="margin:8px 0;font-size:13px;">{current_html}{gap_text_html}</div>'

    # Sources
    sources = trend.get("supporting_sources", trend.get("supporting_papers", []))
    source_icons = {"arXiv": "📄", "Hacker News": "🔶",
                    "Reddit r/MachineLearning": "🟠", "Reddit r/LocalLLaMA": "🟠"}
    sources_html = ""
    for s in sources[:3]:
        if isinstance(s, dict):
            icon = source_icons.get(s.get("source", ""), "📄")
            s_title = s.get("title", "")
            s_url = s.get("url", "")
            s_source = s.get("source", "")
            s_date = s.get("date", "")
            link = f'<a href="{s_url}" style="color:#374151;text-decoration:underline;">{s_title}</a>' if s_url else s_title
            sources_html += f'<div style="font-size:12px;color:#888;margin:2px 0;">{icon} [{s_source}] {link} {s_date}</div>'

    priority_badge = '<span style="background:#f59e0b;color:white;font-size:11px;padding:2px 7px;border-radius:10px;margin-left:8px;">PRIORITY</span>' if is_priority else ""

    return f"""
    <div style="padding:14px 0;border-bottom:1px solid #f0f0f0;">
      <div style="font-size:15px;font-weight:700;color:#111;margin-bottom:6px;">
        {title}{priority_badge}
      </div>
      <div style="font-size:12px;color:#555;margin-bottom:6px;">
        <span style="color:{action_colour};font-weight:600;">{action_dot} {action}</span>
        &nbsp;·&nbsp; {curve}
        &nbsp;·&nbsp; Audiences: {' · '.join(lanes)}
        &nbsp;·&nbsp; Vendor pitch risk: {pitch}
      </div>
      <div style="font-size:13px;color:#555;margin-bottom:6px;">{signal}</div>
      {brief_html}
      {gap_html}
      {sources_html}
    </div>"""
