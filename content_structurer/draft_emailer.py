"""
Draft emailer — sends one email containing all generated first drafts via Resend.
Reuses RESEND_API_KEY and DIGEST_EMAIL from the existing environment.
"""

import os
import re
import requests
from datetime import datetime, timezone


def send_drafts(briefs_and_drafts: list[dict]) -> None:
    """
    Send one email with all generated drafts.

    Each item in briefs_and_drafts should have:
        title, draft (raw text from Claude), angle,
        audiences (list), trend_curve
    """
    api_key = os.environ.get("RESEND_API_KEY", "")
    to_raw = os.environ.get("DIGEST_EMAIL", "")

    if not api_key or not to_raw:
        print("  Email skipped — RESEND_API_KEY / DIGEST_EMAIL not configured")
        return

    to_emails = [e.strip() for e in to_raw.split(",") if e.strip()]
    today = datetime.now(timezone.utc).strftime("%B %d, %Y")
    n = len(briefs_and_drafts)
    subject = (
        f"[Content Drafts] {today} — "
        f"{n} first draft{'s' if n != 1 else ''} ready"
    )

    html = _build_html(briefs_and_drafts, today)

    response = requests.post(
        "https://api.resend.com/emails",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "from": "Content Structurer <onboarding@resend.dev>",
            "to": to_emails,
            "subject": subject,
            "html": html,
        },
        timeout=15,
    )
    if not response.ok:
        print(f"  Resend error: {response.text}")
    response.raise_for_status()
    print(f"  Email sent to {', '.join(to_emails)}")


# ── HTML builder ──────────────────────────────────────────────────────────────

def _build_html(briefs_and_drafts: list[dict], today: str) -> str:
    n = len(briefs_and_drafts)
    day_of_week = datetime.now(timezone.utc).strftime("%A")

    articles_html = ""
    for i, item in enumerate(briefs_and_drafts, 1):
        title = item["title"]
        draft = item["draft"]
        angle = item.get("angle", "")
        audiences = " · ".join(item.get("audiences", []))
        trend_curve = item.get("trend_curve", "")

        format_choice, article_html = _md_to_html(draft)

        format_badge = (
            f'<span style="font-size:11px;font-weight:600;padding:3px 10px;'
            f'border-radius:20px;background:#1e3a5f;color:#60a5fa;">'
            f'{format_choice}</span> &nbsp;'
        ) if format_choice else ""

        angle_line = (
            f'<div style="font-size:13px;color:#6366f1;font-style:italic;'
            f'margin-bottom:16px;">Angle: {angle}</div>'
        ) if angle else ""

        separator = (
            '<div style="height:1px;background:#1e1e1e;margin:40px 0;"></div>'
            if i < n else ""
        )

        articles_html += f"""
        <div style="margin-bottom:40px;">
          <div style="font-size:10px;font-weight:700;letter-spacing:2px;
                      color:#555;margin-bottom:12px;">DRAFT {i} OF {n}</div>
          <div style="font-size:20px;font-weight:800;color:#ffffff;
                      line-height:1.3;margin-bottom:10px;">{title}</div>
          <div style="margin-bottom:8px;">
            {format_badge}
            <span style="font-size:11px;color:#555;">{trend_curve}</span>
            <span style="font-size:11px;color:#444;"> &nbsp;·&nbsp; {audiences}</span>
          </div>
          {angle_line}
          <div style="height:1px;background:#1a1a1a;margin:16px 0 24px;"></div>
          <div style="font-family:Georgia,'Times New Roman',serif;">
            {article_html}
          </div>
        </div>
        {separator}"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin:0;padding:0;background:#0a0a0a;font-family:-apple-system,
             BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;">
  <div style="max-width:680px;margin:0 auto;padding:32px 20px;">

    <div style="margin-bottom:32px;">
      <span style="font-size:11px;font-weight:700;letter-spacing:2px;
                   color:#444;text-transform:uppercase;">Content Structurer</span>
    </div>

    <div style="margin-bottom:32px;">
      <div style="font-size:12px;color:#555;margin-bottom:8px;letter-spacing:0.5px;">
        {day_of_week}, {today}
      </div>
      <div style="font-size:28px;font-weight:800;color:#ffffff;
                  line-height:1.2;margin-bottom:12px;">
        {n} first draft{'s' if n != 1 else ''} ready for review.
      </div>
      <div style="font-size:13px;color:#555;">
        From today's Publish Now trends. Edit freely — these are starting points.
      </div>
    </div>

    <div style="height:1px;background:#1a1a1a;margin-bottom:36px;"></div>

    {articles_html}

    <div style="margin-top:40px;padding-top:20px;border-top:1px solid #1a1a1a;
                font-size:11px;color:#333;text-align:center;line-height:1.8;">
      Content Structurer &nbsp;·&nbsp; Runs 30 min after AI Trend Monitor<br>
      First drafts only — review, edit, and verify before publishing
    </div>

  </div>
</body>
</html>"""


# ── Markdown → HTML ───────────────────────────────────────────────────────────

def _md_to_html(text: str) -> tuple[str, str]:
    """
    Convert a Claude draft to HTML.
    Extracts the 'Format: ...' first line, returns (format_choice, html).
    """
    lines = text.strip().split("\n")

    format_choice = ""
    if lines and lines[0].lower().startswith("format:"):
        format_choice = lines[0].split(":", 1)[-1].strip()
        lines = lines[1:]

    # Split into paragraph blocks (separated by blank lines)
    blocks: list[list[str]] = []
    current: list[str] = []
    for line in lines:
        if line.strip() == "":
            if current:
                blocks.append(current)
                current = []
        else:
            current.append(line)
    if current:
        blocks.append(current)

    html_parts = []
    for block in blocks:
        raw = " ".join(ln.strip() for ln in block)

        if raw.startswith("## "):
            content = _inline_md(raw[3:])
            html_parts.append(
                f'<h2 style="font-size:16px;font-weight:700;color:#e2e8f0;'
                f'margin:24px 0 8px;font-family:-apple-system,sans-serif;">'
                f'{content}</h2>'
            )
        elif raw.startswith("# "):
            content = _inline_md(raw[2:])
            html_parts.append(
                f'<h1 style="font-size:22px;font-weight:800;color:#ffffff;'
                f'line-height:1.3;margin:0 0 20px;font-family:-apple-system,sans-serif;">'
                f'{content}</h1>'
            )
        else:
            content = _inline_md(raw)
            html_parts.append(
                f'<p style="font-size:15px;color:#a0aec0;line-height:1.75;'
                f'margin:0 0 18px;">{content}</p>'
            )

    return format_choice, "\n".join(html_parts)


def _inline_md(text: str) -> str:
    """Convert **bold** and *italic* to HTML inline tags."""
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<em>\1</em>', text)
    return text
