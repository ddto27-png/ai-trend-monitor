"""
Email publisher for the Skitsa cross-disciplinary monitor.
Sends a Skitsa-branded digest via Resend — same palette, adapted for field × AI content.

Required env vars: RESEND_API_KEY, DIGEST_EMAIL
"""

import os
import requests
from datetime import datetime, timezone


# Skitsa palette
CREAM      = "#f5f2ec"
WARM_WHITE = "#faf9f6"
INK        = "#1c1a16"
INK_MUTED  = "#6b6760"
INK_FAINT  = "#b0aea8"
PLUM       = "#5b2d82"
PLUM_DARK  = "#1e0a33"
PLUM_LIGHT = "#dcc8f0"
GOLD       = "#c8930a"
GOLD_LIGHT = "#f5e9cc"
BORDER     = "#e2ddd6"
WHITE      = "#ffffff"

# Font constants to avoid quote conflicts inside f-strings
SERIF = "font-family:'Libre Baskerville',Georgia,'Times New Roman',serif"
SANS  = "font-family:'DM Sans',-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"


def send_field_digest(analysis: dict, field_config: dict,
                      notion_url: str, article_count: int,
                      notes: list[dict] | None = None) -> None:
    """
    Send the cross-disciplinary digest email via Resend.
    notes: optional list of {"insight": dict, "note": str} for Publish Now insights.
    """
    api_key    = os.environ["RESEND_API_KEY"]
    to_emails  = [e.strip() for e in os.environ["DIGEST_EMAIL"].split(",") if e.strip()]

    today       = datetime.now(timezone.utc).strftime("%B %d, %Y")
    field_name  = field_config["name"]
    insights    = analysis.get("insights", [])
    priority    = [i for i in insights if i.get("priority")]
    p_count     = len(priority)

    subject = (
        f"Skitsa · {field_name} · {today} — "
        f"{p_count} cross-disciplinary signal{'s' if p_count != 1 else ''}"
    )

    html = _build_html(analysis, field_config, notion_url, article_count, today, notes)

    response = requests.post(
        "https://api.resend.com/emails",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "from":    "Skitsa <onboarding@resend.dev>",
            "to":      to_emails,
            "subject": subject,
            "html":    html,
        },
        timeout=15,
    )
    if not response.ok:
        print(f"  Resend error: {response.text}")
    response.raise_for_status()
    print(f"  Email sent to {', '.join(to_emails)}")


def _build_html(analysis: dict, field_config: dict,
                notion_url: str, article_count: int, today: str,
                notes: list[dict] | None = None) -> str:

    field_name    = field_config["name"]
    field_lens    = field_config["lens"]
    insights      = analysis.get("insights", [])
    watch_list    = analysis.get("watch_list", [])
    field_summary = analysis.get("field_summary", "")

    # Top 3: priority first, then Publish Now, then the rest
    priority    = [i for i in insights if i.get("priority")]
    publish_now = [i for i in insights if not i.get("priority") and i.get("recommended_action") == "Publish Now"]
    rest        = [i for i in insights if not i.get("priority") and i.get("recommended_action") != "Publish Now"]
    featured    = (priority + publish_now + rest)[:3]

    total_insights = len(insights)
    day_of_week    = datetime.now(timezone.utc).strftime("%A").upper()

    cards_html = "".join(_insight_card(i) for i in featured)
    watch_html = _watch_section(watch_list) if watch_list else ""
    notes_html = _notes_section(notes) if notes else ""
    summary_html = (
        f'<div style="font-size:14px;color:{INK_MUTED};line-height:1.7;'
        f'margin-bottom:28px;padding:20px 24px;background:{WARM_WHITE};'
        f'border:1px solid {BORDER};border-radius:8px;border-left:3px solid {PLUM};">'
        f'{field_summary}</div>'
    ) if field_summary else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Skitsa — {field_name}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Libre+Baskerville:ital,wght@0,400;0,700;1,400&family=DM+Sans:wght@300;400;500&display=swap" rel="stylesheet">
</head>
<body style="margin:0;padding:0;background-color:{CREAM};{SANS};-webkit-font-smoothing:antialiased;">

  <div style="max-width:600px;margin:0 auto;padding:40px 24px 48px;">

    <!-- Wordmark -->
    <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:36px;">
      <tr>
        <td>
          <span style="{SERIF};font-size:26px;font-weight:400;color:{INK};letter-spacing:0.02em;">
            Skitsa<span style="color:{PLUM};">.</span>
          </span>
        </td>
        <td align="right" style="vertical-align:middle;">
          <span style="font-size:10px;font-weight:500;letter-spacing:0.12em;text-transform:uppercase;
                       color:{PLUM};border:1px solid {PLUM_LIGHT};padding:4px 10px;
                       border-radius:999px;background:{WHITE};">
            {field_lens}
          </span>
        </td>
      </tr>
    </table>

    <!-- Date line -->
    <div style="font-size:10px;font-weight:500;letter-spacing:0.16em;text-transform:uppercase;
                color:{PLUM};margin-bottom:12px;">
      {day_of_week} &nbsp;&middot;&nbsp; {today}
    </div>

    <!-- Hero headline -->
    <div style="{SERIF};font-size:38px;font-weight:300;line-height:1.1;color:{INK};
                margin-bottom:14px;letter-spacing:-0.01em;">
      {article_count} stories from {field_name}.<br>
      <span style="font-style:italic;color:{PLUM};">{total_insights} crossed</span> into AI.
    </div>

    <!-- Sub-headline -->
    <div style="font-size:12px;color:{INK_FAINT};line-height:1.6;margin-bottom:28px;">
      {total_insights} cross-disciplinary insight{'s' if total_insights != 1 else ''} surfaced this week
      &nbsp;&middot;&nbsp; {len([i for i in insights if i.get('priority')])} priority
    </div>

    <!-- Divider -->
    <div style="height:1px;background-color:{BORDER};margin-bottom:28px;"></div>

    <!-- Field summary -->
    {summary_html}

    <!-- Top 3 insight cards -->
    {cards_html}

    <!-- CTA -->
    <div style="text-align:center;margin-top:36px;margin-bottom:8px;">
      <a href="{notion_url}"
         style="display:inline-block;background-color:{PLUM};color:{WHITE};{SANS};
                font-size:13px;font-weight:500;letter-spacing:0.04em;
                padding:14px 36px;border-radius:6px;text-decoration:none;">
        Open the full digest &nbsp;&rarr;
      </a>
    </div>
    <div style="text-align:center;font-size:11px;color:{INK_FAINT};margin-top:10px;">
      Every insight, teaching moment, and source — in one place.
    </div>

    {watch_html}

    {notes_html}

    <!-- Divider -->
    <div style="height:1px;background-color:{BORDER};margin-top:40px;margin-bottom:24px;"></div>

    <!-- Footer -->
    <table width="100%" cellpadding="0" cellspacing="0">
      <tr>
        <td>
          <span style="{SERIF};font-size:18px;font-weight:300;font-style:italic;color:{INK_FAINT};">
            Skitsa<span style="color:{PLUM_LIGHT};">.</span>
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


def _insight_card(insight: dict) -> str:
    title       = insight.get("title", "")
    teaching    = insight.get("teaching_moment", "")
    angle       = insight.get("content_angle", "")
    connection  = insight.get("ai_marketing_connection", "")
    action      = insight.get("recommended_action", "")
    is_priority = insight.get("priority", False)

    # Action badge
    action_styles = {
        "Publish Now":   (f"background:#f0e8f8;color:{PLUM_DARK};border:1px solid {PLUM_LIGHT};", "Publish Now"),
        "Watch 2 Weeks": (f"background:{GOLD_LIGHT};color:#7a5a00;border:1px solid #e8d5a0;",      "Watch 2 Weeks"),
        "Hold":          (f"background:{CREAM};color:{INK_FAINT};border:1px solid {BORDER};",       "Hold"),
    }
    badge_style, badge_label = action_styles.get(
        action,
        (f"border:1px solid {BORDER};color:{INK_FAINT};", action)
    )

    priority_pill = (
        f'<span style="font-size:9px;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;'
        f'color:{PLUM};border:1px solid {PLUM_LIGHT};padding:2px 7px;border-radius:999px;'
        f'margin-right:8px;">Priority</span>'
    ) if is_priority else ""

    connection_snip = connection[:200] + ("…" if len(connection) > 200 else "")

    angle_html = (
        f'<div style="font-size:12px;color:{PLUM};font-style:italic;{SERIF};'
        f'border-top:1px solid {BORDER};padding-top:10px;margin-top:10px;line-height:1.6;">'
        f'&#x270d;&nbsp; {angle}</div>'
    ) if angle else ""

    teaching_html = (
        f'<div style="font-size:13px;font-weight:500;color:{INK};line-height:1.55;'
        f'margin-top:10px;padding:10px 14px;background:{WARM_WHITE};'
        f'border-left:3px solid {PLUM};border-radius:0 4px 4px 0;">'
        f'&#10022;&nbsp; {teaching}</div>'
    ) if teaching else ""

    return f"""
    <div style="background:{WHITE};border:1px solid {BORDER};border-radius:12px;
                border-left:3px solid {PLUM};padding:24px 24px 20px;margin-bottom:12px;">

      <!-- Top row -->
      <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:12px;">
        <tr>
          <td style="vertical-align:middle;">
            {priority_pill}<span style="font-size:10px;font-weight:500;letter-spacing:0.14em;
            text-transform:uppercase;color:{PLUM};">Cross-disciplinary</span>
          </td>
          <td align="right" style="vertical-align:middle;">
            <span style="font-size:10px;font-weight:500;padding:3px 10px;border-radius:999px;{badge_style}">
              {badge_label}
            </span>
          </td>
        </tr>
      </table>

      <!-- Title -->
      <div style="{SERIF};font-size:21px;font-weight:400;color:{INK};
                  line-height:1.25;margin-bottom:10px;">
        {title}
      </div>

      <!-- AI / Marketing connection -->
      <div style="font-size:13px;color:{INK_MUTED};line-height:1.65;margin-bottom:4px;">
        {connection_snip}
      </div>

      <!-- Teaching moment -->
      {teaching_html}

      <!-- Content angle -->
      {angle_html}

    </div>"""


def _watch_section(watch_list: list) -> str:
    items_html = "".join(
        f'<div style="padding:8px 0;border-bottom:1px solid {BORDER};'
        f'font-size:13px;color:{INK_MUTED};line-height:1.5;">'
        f'<span style="color:{PLUM};margin-right:8px;">&rarr;</span>'
        f'{str(item)}'
        f'</div>'
        for item in watch_list
    )
    return f"""
    <div style="margin-top:32px;padding:20px 24px;background:{WARM_WHITE};
                border:1px solid {BORDER};border-radius:12px;">
      <div style="font-size:9px;font-weight:500;letter-spacing:0.18em;text-transform:uppercase;
                  color:{INK_FAINT};margin-bottom:14px;">
        On the radar
      </div>
      {items_html}
      <div style="margin-top:14px;font-size:12px;color:{INK_FAINT};font-style:italic;{SERIF};">
        Not ready. Not ignorable.
      </div>
    </div>"""


def _notes_section(notes: list[dict]) -> str:
    """Render Substack notes as email-friendly prose cards."""
    cards = ""
    for i, entry in enumerate(notes):
        insight = entry["insight"]
        note_text = entry["note"]
        title = insight.get("title", "")
        tip = entry.get("tip", "")

        # Convert double-newlines into paragraph breaks
        paras = [p.strip() for p in note_text.split("\n\n") if p.strip()]
        paras_html = "".join(
            f'<p style="font-size:15px;color:{INK};line-height:1.8;'
            f'margin:0 0 14px;{SERIF};">{p}</p>'
            for p in paras
        )

        tip_html = (
            f'<div style="margin-top:20px;padding:14px 16px;background:{GOLD_LIGHT};'
            f'border-left:3px solid {GOLD};border-radius:0 6px 6px 0;">'
            f'<div style="font-size:9px;font-weight:600;letter-spacing:0.14em;'
            f'text-transform:uppercase;color:{GOLD};margin-bottom:6px;">Personal story prompt</div>'
            f'<div style="font-size:13px;color:{INK};line-height:1.7;{SERIF};'
            f'font-style:italic;">{tip}</div>'
            f'</div>'
        ) if tip else ""

        border_top = (
            f'border-top:1px solid {BORDER};margin-top:28px;padding-top:28px;'
            if i > 0 else ""
        )

        cards += f"""
        <div style="{border_top}">
          <div style="font-size:9px;font-weight:500;letter-spacing:0.18em;
                      text-transform:uppercase;color:{PLUM};margin-bottom:8px;">
            Substack Note &nbsp;&middot;&nbsp; Publish Now
          </div>
          <div style="{SERIF};font-size:17px;font-weight:400;color:{INK};
                      line-height:1.3;margin-bottom:18px;">
            {title}
          </div>
          {paras_html}
          {tip_html}
        </div>"""

    return f"""
    <div style="margin-top:40px;padding:24px 24px 20px;background:{WARM_WHITE};
                border:1px solid {BORDER};border-radius:12px;border-left:3px solid {PLUM};">
      <div style="font-size:9px;font-weight:500;letter-spacing:0.18em;text-transform:uppercase;
                  color:{INK_FAINT};margin-bottom:20px;">
        Substack drafts — ready to copy
      </div>
      {cards}
      <div style="margin-top:20px;font-size:12px;color:{INK_FAINT};font-style:italic;{SERIF};">
        ~500 words each &nbsp;·&nbsp; Dana's voice &nbsp;·&nbsp; moment → texture → turn → closer
      </div>
    </div>"""
