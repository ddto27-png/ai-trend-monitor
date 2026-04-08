"""
Email publisher — sends a teaser digest email via Resend.
Shows top 3 trends with a CTA to the full Notion digest.

Required environment variables:
    RESEND_API_KEY  — your Resend API key (re_...)
    DIGEST_EMAIL    — comma-separated list of recipient addresses
"""

import os
import requests
from datetime import datetime, timezone


def send_digest(analysis: dict, notion_url: str, source_counts: dict,
                item_count: int) -> None:
    """Send the digest teaser email via Resend."""
    api_key = os.environ["RESEND_API_KEY"]
    to_emails = [e.strip() for e in os.environ["DIGEST_EMAIL"].split(",") if e.strip()]

    today = datetime.now(timezone.utc).strftime("%B %d, %Y")
    trends = analysis.get("trends", [])
    watch_list = analysis.get("watch_list", [])
    priority = [t for t in trends if t.get("priority")]

    # Subject line: direct and informative
    priority_count = len(priority)
    subject = f"[AI Trends] {today} — {priority_count} priority trend{'s' if priority_count != 1 else ''} today"

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

    trends = analysis.get("trends", [])
    watch_list = analysis.get("watch_list", [])

    # Top 3 to feature: priority first, then "Publish Now", then whatever's left
    priority = [t for t in trends if t.get("priority")]
    publish_now = [t for t in trends if not t.get("priority") and t.get("recommended_action") == "Publish Now"]
    remaining = [t for t in trends if not t.get("priority") and t.get("recommended_action") != "Publish Now"]
    featured = (priority + publish_now + remaining)[:3]

    total_trends = len(trends)
    watch_count = len(watch_list)
    sources_str = " &nbsp;·&nbsp; ".join(f"<strong>{c}</strong> {s}" for s, c in source_counts.items())
    day_of_week = datetime.now(timezone.utc).strftime("%A")

    trend_cards = "".join(_trend_card(t) for t in featured)

    # Watch list teaser — titles only, no detail
    watch_teaser = ""
    if watch_list:
        watch_titles = "".join(
            f'<div style="padding:6px 0;border-bottom:1px solid #1e1e1e;font-size:13px;color:#888;">'
            f'<span style="color:#555;margin-right:8px;">○</span>{w.get("title","")}'
            f'<span style="color:#444;font-size:11px;margin-left:8px;">{w.get("category","")}</span>'
            f'</div>'
            for w in watch_list
        )
        watch_teaser = f"""
        <div style="margin-top:32px;padding:20px 24px;background:#111;border-radius:8px;">
          <div style="font-size:11px;font-weight:700;color:#555;letter-spacing:1px;margin-bottom:12px;">
            WATCH LIST — {watch_count} SIGNAL{'S' if watch_count != 1 else ''} EMERGING
          </div>
          {watch_titles}
          <div style="margin-top:12px;font-size:12px;color:#444;font-style:italic;">
            Too early to publish. Worth knowing.
          </div>
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AI Trend Monitor</title>
</head>
<body style="margin:0;padding:0;background:#0a0a0a;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;">
  <div style="max-width:620px;margin:0 auto;padding:32px 20px;">

    <!-- Wordmark -->
    <div style="margin-bottom:32px;">
      <span style="font-size:11px;font-weight:700;letter-spacing:2px;color:#444;text-transform:uppercase;">
        AI Trend Monitor
      </span>
    </div>

    <!-- Hero -->
    <div style="margin-bottom:8px;">
      <div style="font-size:12px;color:#555;margin-bottom:8px;letter-spacing:0.5px;">
        {day_of_week}, {today}
      </div>
      <div style="font-size:32px;font-weight:800;color:#ffffff;line-height:1.15;margin-bottom:16px;">
        {total_trends} trends.<br>3 worth your time right now.
      </div>
      <div style="font-size:13px;color:#555;line-height:1.6;">
        Pulled from {item_count} sources today &nbsp;·&nbsp; {sources_str}
      </div>
    </div>

    <!-- Divider -->
    <div style="height:1px;background:#1a1a1a;margin:28px 0;"></div>

    <!-- Top 3 trend cards -->
    {trend_cards}

    <!-- CTA -->
    <div style="margin-top:32px;text-align:center;">
      <a href="{notion_url}"
         style="display:inline-block;background:#ffffff;color:#0a0a0a;font-size:14px;
                font-weight:700;padding:14px 32px;border-radius:6px;text-decoration:none;
                letter-spacing:0.3px;">
        Read the full digest →
      </a>
      <div style="margin-top:12px;font-size:12px;color:#444;">
        Full briefs, content gaps, citations, and watch list in Notion
      </div>
    </div>

    {watch_teaser}

    <!-- Footer -->
    <div style="margin-top:40px;padding-top:20px;border-top:1px solid #1a1a1a;
                font-size:11px;color:#333;text-align:center;line-height:1.8;">
      AI Trend Monitor &nbsp;·&nbsp; Runs daily at 7am UTC<br>
      Sources: arXiv · Hacker News · Reddit · Company blogs · Newsletters
    </div>

  </div>
</body>
</html>"""


def _angle_html(angle: str) -> str:
    if not angle:
        return ""
    return (
        '<div style="font-size:13px;color:#c7d2fe;font-style:italic;'
        'border-top:1px solid #1e1e1e;padding-top:10px;margin-top:4px;">'
        f'&#x270d; {angle}</div>'
    )


def _trend_card(trend: dict) -> str:
    title = trend.get("title", "")
    category = trend.get("category", "")
    action = trend.get("recommended_action", "")
    lanes = trend.get("audience_lanes", [])
    curve = trend.get("trend_curve", "")
    signal = trend.get("signal_quality", "")
    is_priority = trend.get("priority", False)

    # Get the one-line angle from the content brief
    brief = trend.get("content_brief", {})
    angle = ""
    if isinstance(brief, dict):
        angle = brief.get("topic", "")

    # Category colour coding
    cat_colours = {
        "LLMs": "#6366f1",
        "AI Agents & Automation": "#10b981",
        "GPU & Infrastructure": "#f59e0b",
    }
    cat_colour = cat_colours.get(category, "#888")

    # Action badge
    action_styles = {
        "Publish Now":    ("background:#052e16;color:#4ade80;", "● Publish Now"),
        "Watch 2 Weeks":  ("background:#1c1408;color:#fbbf24;", "◐ Watch 2 Weeks"),
        "Skip":           ("background:#1c0a0a;color:#f87171;", "○ Skip"),
    }
    badge_style, badge_text = action_styles.get(action, ("background:#1a1a1a;color:#888;", action))

    priority_marker = f'<span style="font-size:10px;font-weight:700;letter-spacing:1px;color:#f59e0b;margin-right:8px;">★ PRIORITY</span>' if is_priority else ""

    lanes_str = " · ".join(lanes) if lanes else ""

    return f"""
    <div style="margin-bottom:2px;padding:20px 24px;background:#111;border-radius:8px;border-left:3px solid {cat_colour};">

      <!-- Category + action row -->
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;flex-wrap:wrap;gap:8px;">
        <span style="font-size:10px;font-weight:700;letter-spacing:1px;color:{cat_colour};text-transform:uppercase;">
          {priority_marker}{category}
        </span>
        <span style="font-size:11px;font-weight:600;padding:3px 10px;border-radius:20px;{badge_style}">
          {badge_text}
        </span>
      </div>

      <!-- Title -->
      <div style="font-size:17px;font-weight:700;color:#ffffff;line-height:1.3;margin-bottom:10px;">
        {title}
      </div>

      <!-- Signal — one line -->
      <div style="font-size:13px;color:#888;line-height:1.5;margin-bottom:12px;">
        {signal[:160]}{'...' if len(signal) > 160 else ''}
      </div>

      <!-- Angle — the content hook -->
      {_angle_html(angle)}

      <!-- Meta row -->
      <div style="margin-top:12px;font-size:11px;color:#444;">
        {curve} &nbsp;·&nbsp; {lanes_str}
      </div>

    </div>
    <div style="height:4px;"></div>"""
