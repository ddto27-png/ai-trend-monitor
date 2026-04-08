"""
Content generator — takes a structured content brief and uses Claude
to write a complete first-draft article, then saves it as markdown.
"""

import re
from datetime import datetime, timezone
from pathlib import Path

from shared.claude_client import get_client


SYSTEM_PROMPT = """You are a technology journalist writing for enterprise buyers and the technical \
people who advise them. Your job is to take a content brief and write a complete first-draft article.

Voice and style:
- Specific and concrete. Name things. Avoid vague generalities.
- Clear, direct sentences. No flowery language, no marketing speak.
- Use analogies, comparisons, or metaphors sparingly — aim for about 2 per piece — \
only where they genuinely clarify a complex idea.
- Write for smart readers who are busy. Respect their time.
- Active voice. Short paragraphs (2–4 sentences max).

Structure (write all four sections — no skipping):
1. HEADLINE: One line. Clear, specific, honest about what the piece covers.
2. LEDE: 2–3 sentences that hook the reader by stating the specific tension, shift, or stakes. \
Do not start with "In recent years..." or any slow wind-up.
3. BODY: Fully written prose paragraphs organized into clear sections. \
No bullet points. Each section flows naturally into the next.
4. CONCLUSION: 2–3 sentences that close the argument and give the reader \
something concrete to think about or act on.

Length: 600–700 words total across all four sections.

Format selection: You will be given 2–3 format options. Choose the one that best fits \
the topic, the audience, and where the piece can deliver the most distinct value. \
On your very first line, state your choice like this:
Format: [your chosen format]

Then write the full article, starting with the headline on the next line."""


def generate_draft(brief: dict) -> str:
    """
    Call Claude to generate a full article draft from a content brief.
    Returns the raw draft text (includes the Format: line at top).
    """
    client = get_client()

    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": _build_prompt(brief)}],
    )

    return message.content[0].text.strip()


def save_draft(brief: dict, draft: str, output_dir: Path) -> Path:
    """
    Save a draft to a markdown file with a YAML front-matter header.
    Returns the path of the saved file.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    slug = _slugify(brief["title"])
    filepath = output_dir / f"{today}_{slug}.md"

    audiences = ", ".join(brief.get("audiences", []))
    front_matter = (
        f"---\n"
        f"title: {brief['title']}\n"
        f"date: {today}\n"
        f"angle: {brief.get('angle', '')}\n"
        f"audiences: {audiences}\n"
        f"trend_curve: {brief.get('trend_curve', '')}\n"
        f"recommended_action: {brief.get('recommended_action', '')}\n"
        f"---\n\n"
    )

    filepath.write_text(front_matter + draft + "\n", encoding="utf-8")
    return filepath


# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_prompt(brief: dict) -> str:
    points = "\n".join(f"  - {p}" for p in brief.get("content_points", []))
    formats = "\n".join(f"  - {f}" for f in brief.get("format_options", []))
    audiences = ", ".join(brief.get("audiences", []))

    return f"""Write a complete first-draft article from the brief below.

TOPIC: {brief["title"]}

PURPOSE (what this piece achieves for the reader):
{brief.get("purpose", "")}

ANGLE (the specific take):
{brief.get("angle", "")}

TARGET AUDIENCES: {audiences}

CONTENT POINTS TO ADDRESS:
{points}

FORMAT OPTIONS — pick the best fit and state it on line 1:
{formats}

SIGNAL CONTEXT (use to calibrate tone and urgency):
{brief.get("signal_quality", "")}

Write the full article now."""


def _slugify(text: str) -> str:
    """Convert a title to a filename-safe slug, max 60 characters."""
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text[:60].strip("-")
