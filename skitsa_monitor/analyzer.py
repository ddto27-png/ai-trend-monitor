"""
Cross-disciplinary analyst for the Skitsa monitor.

Given articles from a field (Fashion, Architecture, Film, Retail), Claude Opus
identifies insights where that field's logic teaches something meaningful about
AI, product, or marketing strategy — framed as Skitsa content opportunities.
"""

import json
import anthropic


_PROMPT = """\
You are an analyst for Skitsa — a content brand at the intersection of complexity and beauty, \
built for non-technical executives and creative professionals.

Today's field: {field_name}
Today's lens: {field_lens}

Given the articles below, identify 3–5 powerful cross-disciplinary insights where \
{field_name} teaches something meaningful about AI, product, or marketing strategy.

The core question for each insight: "What does {field_name}'s way of thinking teach \
a smart executive about how intelligence, systems, or human behaviour actually works?"

For each insight return:
- title: A compelling Skitsa-style headline that juxtaposes the two domains \
  (e.g. "What runway timing teaches us about model deployment windows")
- field_signal: What is happening in {field_name} right now, based on the sources \
  — 2–3 sentences, specific and factual
- ai_marketing_connection: How this connects to AI or marketing strategy — 2–3 sentences
- teaching_moment: The powerful universal insight — the one thing the reader walks away \
  understanding better about how the world works — 1–2 sharp sentences
- content_angle: The specific Skitsa piece this becomes — one sentence starting with a \
  verb: "Explain...", "Show...", "Map...", "Compare..."
- recommended_action: one of "Publish Now" | "Watch 2 Weeks" | "Hold"
- priority: true if this is an unusually strong cross-disciplinary insight
- sources: list of article URLs that directly support this insight — ONLY URLs from the \
  articles list below, never invent a URL

Also return:
- watch_list: 2–3 short strings — signals emerging in {field_name} not yet ready for a \
  full piece but worth tracking
- field_summary: 1-paragraph overview of what is moving in {field_name} this week, \
  written for a smart non-technical reader

CRITICAL: Only use URLs that appear verbatim in the articles list below. \
If you are unsure of a URL, omit it. Never guess or fabricate a link.

Return ONLY valid JSON — no explanation, no markdown, just the JSON object:
{{
  "field": "{field_name}",
  "insights": [
    {{
      "title": "...",
      "field_signal": "...",
      "ai_marketing_connection": "...",
      "teaching_moment": "...",
      "content_angle": "...",
      "recommended_action": "Publish Now",
      "priority": true,
      "sources": ["https://..."]
    }}
  ],
  "watch_list": ["...", "..."],
  "field_summary": "..."
}}

Articles:
{articles_text}\
"""


def analyze_field(field_config: dict, articles: list[dict]) -> dict:
    """
    Run Claude Opus on articles from the given field.
    Returns the parsed analysis dict. Strips any fabricated source URLs.
    """
    client = anthropic.Anthropic()
    valid_urls = {a["url"] for a in articles}

    lines = []
    for i, article in enumerate(articles, 1):
        lines.append(
            f"[{i}] {article['title']}\n"
            f"    Source: {article['source']}\n"
            f"    URL: {article['url']}\n"
            f"    Summary: {article['abstract'][:300]}"
        )
    articles_text = "\n\n".join(lines)

    prompt = _PROMPT.format(
        field_name=field_config["name"],
        field_lens=field_config["lens"],
        articles_text=articles_text,
    )

    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()
    if "```" in raw:
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    result = json.loads(raw.strip())

    # Strip any fabricated URLs before returning
    fabricated = []
    for insight in result.get("insights", []):
        clean, bad = [], []
        for url in insight.get("sources", []):
            (clean if url in valid_urls else bad).append(url)
        insight["sources"] = clean
        fabricated.extend(bad)

    result["_fabricated_urls"] = fabricated
    return result
