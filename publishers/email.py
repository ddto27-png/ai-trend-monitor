"""
Email publisher — sends a Skitsa-branded teaser digest via Resend.
Shows top 3 trends with a CTA to the full Notion digest.

Brand: Skitsa — complexity, made beautiful.
Palette: cream (#f5f2ec), ink (#1c1a16), teal (#01696f)
Typography: Cormorant Garamond (headlines) · DM Sans (body)

Required environment variables:
    RESEND_API_KEY  — your Resend API key (re_...)
    DIGEST_EMAIL    — comma-separated list of recipient addresses
"""

import os
import requests
from datetime import datetime, timezone


# Skitsa palette (inline — email clients don't support CSS variables)
CREAM       = "#f5f2ec"
WARM_WHITE  = "#faf9f6"
INK         = "#1c1a16"
INK_MUTED   = "#6b6760"
INK_FAINT   = "#b0aea8"
TEAL        = "#01696f"
TEAL_DARK   = "#0c4e54"
TEAL_LIGHT  = "#cedcd8"
GOLD        = "#c8930a"
GOLD_LIGHT  = "#f5e9cc"
BORDER      = "#e2ddd6"
WHITE       = "#ffffff"


def send_digest(analysis: dict, notion_url: str, source_counts: dict,
                item_count: int) -> None:
    """Send the Skitsa digest teaser email via Resend."""
    api_key = os.environ["RESEND_API_KEY"]
    to_emails = [e.strip() for e in os.environ["DIGEST_EMAIL"].split(",") if e.strip()]

    today = datetime.now(timezone.utc).strftime("%B %d, %Y")
    trends = analysis.get("trends", [])
    priority = [t for t in trends if t.get("priority")]
    priority_count = len(priority)

    subject = (
        f"Skitsa · {today} — "
        f"{priority_count} signal{'s' if priority_count != 1 else ''} worth moving on"
    )

    html = _build_html(analysis, notion_url, source_counts, item_count, today)

    response = requests.post(
        "https://api.resend.com/emails",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "from": "Skitsa <onboarding@resend.dev>",
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

    # Top 3: priority first, then Publish Now, then the rest
    priority    = [t for t in trends if t.get("priority")]
    publish_now = [t for t in trends if not t.get("priority") and t.get("recommended_action") == "Publish Now"]
    rest        = [t for t in trends if not t.get("priority") and t.get("recommended_action") != "Publish Now"]
    featured    = (priority + publish_now + rest)[:3]

    total_trends = len(trends)
    watch_count  = len(watch_list)
    day_of_week  = datetime.now(timezone.utc).strftime("%A").upper()

    sources_str = " &nbsp;&middot;&nbsp; ".join(
        f"{c} {s}" for s, c in source_counts.items()
    )

    trend_cards_html = "".join(_trend_card(t) for t in featured)
    watch_html = _watch_section(watch_list, watch_count) if watch_list else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Skitsa</title>
</head>
<body style="margin:0;padding:0;background-color:{CREAM};font-family:'DM Sans',-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;-webkit-font-smoothing:antialiased;">

  <div style="max-width:600px;margin:0 auto;padding:40px 24px 48px;">

    <!-- Wordmark -->
    <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:36px;">
      <tr>
        <td>
          <span style="font-family:Georgia,'Cormorant Garamond',serif;font-size:26px;font-weight:400;color:{INK};letter-spacing:0.02em;">
            Skitsa<span style="color:{TEAL};">.</span>
          </span>
        </td>
        <td align="right" style="vertical-align:middle;">
          <span style="font-size:10px;font-weight:500;letter-spacing:0.12em;text-transform:uppercase;color:{INK_FAINT};border:1px solid {BORDER};padding:4px 10px;border-radius:999px;background:{WHITE};">
            AI Intelligence
          </span>
        </td>
      </tr>
    </table>

    <!-- Date line -->
    <div style="font-size:10px;font-weight:500;letter-spacing:0.16em;text-transform:uppercase;color:{TEAL};margin-bottom:12px;">
      {day_of_week} &nbsp;&middot;&nbsp; {today}
    </div>

    <!-- Hero headline -->
    <div style="font-family:Georgia,'Cormorant Garamond',serif;font-size:40px;font-weight:300;line-height:1.1;color:{INK};margin-bottom:16px;letter-spacing:-0.01em;">
      {total_trends} signals came in.<br>
      <span style="font-style:italic;color:{TEAL};">Three</span> earned it.
    </div>

    <!-- Source line -->
    <div style="font-size:12px;color:{INK_FAINT};line-height:1.6;margin-bottom:32px;">
      This morning across {item_count} sources &nbsp;&middot;&nbsp; {sources_str}
    </div>

    <!-- Divider -->
    <div style="height:1px;background-color:{BORDER};margin-bottom:32px;"></div>

    <!-- Top 3 trend cards -->
    {trend_cards_html}

    <!-- CTA -->
    <div style="text-align:center;margin-top:36px;margin-bottom:8px;">
      <a href="{notion_url}"
         style="display:inline-block;background-color:{TEAL};color:{WHITE};
                font-family:'DM Sans',-apple-system,Helvetica,Arial,sans-serif;
                font-size:13px;font-weight:500;letter-spacing:0.04em;
                padding:14px 36px;border-radius:6px;text-decoration:none;">
        Open the full digest &nbsp;&rarr;
      </a>
    </div>
    <div style="text-align:center;font-size:11px;color:{INK_FAINT};margin-top:10px;line-height:1.6;">
      Every signal, brief, and source — all in one place.
    </div>

    {watch_html}

    <!-- Divider -->
    <div style="height:1px;background-color:{BORDER};margin-top:40px;margin-bottom:24px;"></div>

    <!-- Footer -->
    <table width="100%" cellpadding="0" cellspacing="0">
      <tr>
        <td>
          <span style="font-family:Georgia,'Cormorant Garamond',serif;font-size:18px;font-weight:300;font-style:italic;color:{INK_FAINT};">
            Skitsa<span style="color:{TEAL_LIGHT};">.</span>
          </span>
        </td>
        <td align="right" style="vertical-align:middle;">
          <span style="font-size:10px;color:{INK_FAINT};letter-spacing:0.05em;">
            Built in public &nbsp;&middot;&nbsp; at the intersection of complexity and beauty
          </span>
        </td>
      </tr>
    </table>

  </div>
</body>
</html>"""


def _trend_card(trend: dict) -> str:
    title    = trend.get("title", "")
    category = trend.get("category", "")
    action   = trend.get("recommended_action", "")
    lanes    = trend.get("audience_lanes", [])
    curve    = trend.get("trend_curve", "")
    signal   = trend.get("signal_quality", "")
    is_priority = trend.get("priority", False)

    brief = trend.get("content_brief", {})
    angle = brief.get("topic", "") if isinstance(brief, dict) else ""

    # Category accent colour — teal for LLMs, gold for Agents, muted for GPU
    cat_colours = {
        "LLMs":                    TEAL,
        "AI Agents & Automation":  GOLD,
        "GPU & Infrastructure":    INK_MUTED,
    }
    accent = cat_colours.get(category, INK_FAINT)

    # Action badge
    action_styles = {
        "Publish Now":   (f"background-color:#edf6f4;color:{TEAL_DARK};border:1px solid {TEAL_LIGHT};", "Publish Now"),
        "Watch 2 Weeks": (f"background-color:{GOLD_LIGHT};color:#7a5a00;border:1px solid #e8d5a0;",    "Watch 2 Weeks"),
        "Skip":          (f"background-color:#f5f2ec;color:{INK_FAINT};border:1px solid {BORDER};",    "Skip"),
    }
    badge_style, badge_label = action_styles.get(action, (f"border:1px solid {BORDER};color:{INK_FAINT};", action))

    priority_pill = (
        f'<span style="font-size:9px;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;'
        f'color:{TEAL};border:1px solid {TEAL_LIGHT};padding:2px 7px;border-radius:999px;'
        f'margin-right:8px;">Priority</span>'
    ) if is_priority else ""

    lanes_str  = " &nbsp;&middot;&nbsp; ".join(lanes) if lanes else ""
    signal_snip = signal[:180] + ("..." if len(signal) > 180 else "")
    angle_html  = _angle_html(angle)

    return f"""
    <div style="background-color:{WHITE};border:1px solid {BORDER};border-radius:12px;
                border-left:3px solid {accent};padding:24px 24px 20px;margin-bottom:12px;">

      <!-- Category row -->
      <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:12px;">
        <tr>
          <td style="vertical-align:middle;">
            {priority_pill}<span style="font-size:10px;font-weight:500;letter-spacing:0.14em;
            text-transform:uppercase;color:{accent};">{category}</span>
          </td>
          <td align="right" style="vertical-align:middle;">
            <span style="font-size:10px;font-weight:500;padding:3px 10px;border-radius:999px;{badge_style}">
              {badge_label}
            </span>
          </td>
        </tr>
      </table>

      <!-- Title -->
      <div style="font-family:Georgia,'Cormorant Garamond',serif;font-size:22px;font-weight:400;
                  color:{INK};line-height:1.25;margin-bottom:10px;">
        {title}
      </div>

      <!-- Signal -->
      <div style="font-size:13px;color:{INK_MUTED};line-height:1.65;margin-bottom:12px;">
        {signal_snip}
      </div>

      {angle_html}

      <!-- Meta -->
      <div style="margin-top:14px;font-size:10px;color:{INK_FAINT};letter-spacing:0.04em;">
        {curve} &nbsp;&middot;&nbsp; {lanes_str}
      </div>

    </div>"""


def _angle_html(angle: str) -> str:
    if not angle:
        return ""
    return (
        f'<div style="font-size:12px;color:{TEAL};font-style:italic;font-family:Georgia,serif;'
        f'border-top:1px solid {BORDER};padding-top:10px;margin-top:4px;line-height:1.6;">'
        f'&#x270d;&nbsp; {angle}</div>'
    )


def _watch_section(watch_list: list, watch_count: int) -> str:
    items_html = "".join(
        f'<div style="padding:8px 0;border-bottom:1px solid {BORDER};'
        f'font-size:13px;color:{INK_MUTED};line-height:1.5;">'
        f'<span style="color:{TEAL};margin-right:8px;">&rarr;</span>'
        f'{w.get("title", "")}'
        f'<span style="color:{INK_FAINT};font-size:11px;margin-left:8px;">{w.get("category", "")}</span>'
        f'</div>'
        for w in watch_list
    )
    return f"""
    <div style="margin-top:32px;padding:20px 24px;background-color:{WARM_WHITE};
                border:1px solid {BORDER};border-radius:12px;">
      <div style="font-size:9px;font-weight:500;letter-spacing:0.18em;text-transform:uppercase;
                  color:{INK_FAINT};margin-bottom:14px;">
        On the radar
      </div>
      {items_html}
      <div style="margin-top:14px;font-size:12px;color:{INK_FAINT};font-style:italic;font-family:Georgia,serif;">
        Not ready. Not ignorable.
      </div>
    </div>"""
