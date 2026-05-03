"""
Substack note generator for the Skitsa cross-disciplinary monitor.

For each "Publish Now" insight, generates a ~500-word Substack note
in Dana's voice: moment → texture → turn → closer.
"""

import re
from datetime import datetime, timezone
from pathlib import Path

import anthropic


_SYSTEM = """\
You write Substack Notes for Skitsa in Dana's voice.

Dana's voice in one line: Confident in perspective. Approachable in presence. Simple in delivery.

CORE PATTERNS:
1. Lines as beats, not paragraphs — each line is its own moment. Break for rhythm, not structure.
2. Deliberate repetition — repeat a word or phrase; the second time is more specific, more hers.
   Example: "The level of curation was immaculate. The someone-has-handpicked-all-these-stories-just-for-me immaculate."
3. "You" pulls the reader in — write across to the reader, not up or down.
4. Warmth in small words — "loveliest", "beautiful", "elegant". Don't perform emotion; let it show.
5. The connection lands in one sentence — tie observation to Skitsa in one sentence and move on.
6. Endings are generous — a fun fact, a quiet intention, a question. Never a call to action.

STRUCTURE (follow this exactly):
1. The moment — a specific, recent, real-world observation. Sensory. No grand opener.
2. The texture — 2-3 lines showing *why* it was interesting. Specific details, not adjectives.
3. The turn — one sentence connecting it to the reader's world or Skitsa. Simple. Direct.
4. The closer — a generous ending. Fun fact, quiet intention, question. Optional ":)".

LANGUAGE TO USE:
- "Loveliest," "immaculate," "beautiful," "elegant," "precise" — unapologetically
- Specific sensory or categorical details
- Invented compound phrases for emphasis
- "You" and "I" in equal measure
- Short sentences after longer ones. For emphasis.
- ":)" sparingly, where warmth is genuine

LANGUAGE TO AVOID:
- "Hopefully," "I think," "I just" — hedges
- "Game-changer," "revolutionary," "unlock" — hype
- "Even non-technical people can..." — condescending
- Bullet-pointed takeaways at the end
- Performed vulnerability ("I've been struggling with...")
- AI-sounding constructions — smooth, generic, no texture
- Over-explaining the Skitsa connection

TARGET LENGTH: ~500 words. No headers. No bullets. Pure prose, line-broken like poetry.

REFERENCE EXAMPLE (Dana's approved voice):
"I had the loveliest bookstore experience about 6 hours ago.
The level of curation was immaculate. The someone-has-handpicked-all-these-stories-just-for-me immaculate.

A smaller space with just about four shelves of fiction, but rich to the brim with Pulitzer winners, rising authors, international bestsellers, and locals. And when you go beyond the surface, you discover you have a lottery winner for just about anything you might want, from character studies to letter-based short stories to multigenerational sagas…

That's the feeling I'm aiming to evoke with Skitsa, my Substack publication :).
I want to build a treasure chest you prop open out of curiosity, and all of a sudden you've spent hours exploring every keepsake buried there.

Fun fact: Skitsa is the Bulgarian word for sketch or a preliminary outline. The first mark that contains the whole idea. I picked it to mark the start of this blog, and to represent the way my content will hopefully make people feel :)"
"""

_PROMPT = """\
Write a Skitsa Substack Note (~500 words) inspired by this cross-disciplinary insight.

Field: {field_name}
Insight title: {title}

What's happening in the field: {field_signal}
The connection to AI / strategy: {ai_marketing_connection}
The core teaching moment: {teaching_moment}
The content angle: {content_angle}

The note should feel like Dana noticed something in {field_name} — a real moment, a specific \
detail — and traced it to a deeper idea about how AI, strategy, or human behaviour works. \
It should not read like a listicle or a trend report. It should read like a letter from \
someone whose eye catches things others miss.

Do not start with "I" as the very first word. Find a way to open with the observation itself.
Write in the exact voice described in the system prompt.
No title. No headers. Pure prose, line-broken for rhythm.
"""


def generate_note(insight: dict, field_config: dict) -> str:
    """Generate a ~500-word Substack note for a single Skitsa insight."""
    client = anthropic.Anthropic()

    prompt = _PROMPT.format(
        field_name=field_config["name"],
        title=insight.get("title", ""),
        field_signal=insight.get("field_signal", ""),
        ai_marketing_connection=insight.get("ai_marketing_connection", ""),
        teaching_moment=insight.get("teaching_moment", ""),
        content_angle=insight.get("content_angle", ""),
    )

    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=1500,
        system=_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )

    return message.content[0].text.strip()


def save_note(insight: dict, note: str, field_config: dict, output_dir: Path) -> Path:
    """Save a Substack note as a markdown file."""
    output_dir.mkdir(parents=True, exist_ok=True)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    slug = _slugify(insight.get("title", "note"))
    filename = f"{today}_skitsa_{slug}.md"
    path = output_dir / filename

    field_name = field_config["name"]
    title = insight.get("title", "")

    front_matter = f"""---
date: {today}
field: {field_name}
title: "{title}"
type: substack-note
action: Publish Now
---

"""

    path.write_text(front_matter + note, encoding="utf-8")
    return path


def _slugify(text: str) -> str:
    slug = text.lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_-]+", "-", slug)
    slug = slug.strip("-")
    return slug[:55]
