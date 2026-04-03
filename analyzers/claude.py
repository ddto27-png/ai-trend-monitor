"""
Claude analyzer — sends collected papers to Claude and gets back
structured trend analysis with content briefs.
"""

import json
import anthropic


SYSTEM_PROMPT = """You are an expert AI industry analyst who helps content strategists
identify which AI research trends are worth writing about for enterprise technology audiences.

You receive a mixed batch of recent items from three sources:
- arXiv: academic papers (research signal — what's being studied)
- Hacker News: practitioner discussions (attention signal — what builders are talking about)
- Reddit (r/MachineLearning, r/LocalLLaMA): community posts (adoption signal — what's being used)

Identify the most meaningful trends across three buckets: LLMs, AI Agents & Automation, and GPU & Infrastructure.

When a trend appears across multiple source types (e.g. an arXiv paper AND HN discussion), that's
a stronger signal than research alone — weight it accordingly in your signal quality assessment.

For each trend you identify, assess it across six dimensions:

1. SIGNAL QUALITY: Is this real signal or hype? Is it practitioner-driven or vendor-driven?
   Is it a genuine shift or a rebrand? (1-2 sentences)

2. SALES PITCH RISK: Will vendors likely start pitching this to enterprise buyers within
   the next 90 days — meaning buyers will start hearing about it in sales calls and need
   to know how to evaluate it?
   Answer: Yes / Likely / Unlikely / No

3. TREND CURVE: Where is this on the adoption curve?
   (Emerging = <5% aware | Rising = gaining traction | Peak = mainstream buzz | Mature = commoditising)

4. AUDIENCE LANES: List every audience this trend is relevant to. Choose from:
   - "Business Buyer" — cares about ROI, risk, cost, competitive advantage
   - "Technical DM" — cares about architecture, feasibility, vendor evaluation
   - "Internal Champion" — cares about implementation, team adoption, making the case internally
   List all that apply. If all three apply, also set priority: true.

5. CONTENT GAP: What angle on this trend has NOT been covered yet?
   First give a brief educated guess at what current coverage looks like (flag it as an
   educated guess). Then state what's missing.

6. RECOMMENDED ACTION: Publish Now / Watch 2 Weeks / Skip

7. CONTENT BRIEF: A light roadmap for a writer — not a rigid script, just enough direction.
   Include: the purpose of the piece, the specific topic/angle, 3–5 content points to hit
   (these are starting points, not a checklist), and 2–3 format options the writer could choose.

OUTPUT FORMAT — respond with valid JSON only, no other text:
{
  "trends": [
    {
      "title": "Short descriptive trend title",
      "category": "LLMs" | "AI Agents & Automation" | "GPU & Infrastructure",
      "signal_quality": "...",
      "sales_pitch_risk": "Yes" | "Likely" | "Unlikely" | "No",
      "trend_curve": "Emerging" | "Rising" | "Peak" | "Mature",
      "audience_lanes": ["Business Buyer", "Technical DM", "Internal Champion"],
      "content_gap": {
        "current_coverage": "Educated guess: current content tends to...",
        "gap": "What's missing and why it matters..."
      },
      "recommended_action": "Publish Now" | "Watch 2 Weeks" | "Skip",
      "content_brief": {
        "purpose": "Why this piece matters and what it achieves for the reader",
        "topic": "The specific angle to take",
        "content_points": [
          "Point or question the piece should address",
          "Point or question the piece should address",
          "Point or question the piece should address"
        ],
        "format_options": [
          "Format option 1 (e.g. Explainer for technical buyers)",
          "Format option 2 (e.g. Buyer's checklist)",
          "Format option 3 (e.g. Opinion piece)"
        ]
      },
      "priority": true | false,
      "supporting_sources": [
        {
          "title": "Title of paper, story, or post",
          "source": "arXiv or Hacker News or Reddit r/MachineLearning or Reddit r/LocalLLaMA",
          "url": "https://... (the url field from the item)",
          "authors": ["Last, First"],
          "date": "YYYY-MM-DD"
        }
      ]
    }
  ],
  "watch_list": [
    {
      "title": "Trend title",
      "category": "LLMs" | "AI Agents & Automation" | "GPU & Infrastructure",
      "why_watching": "One sentence on why this is worth monitoring",
      "signal_so_far": "Emerging"
    }
  ]
}

Rules:
- Identify 5–12 trends total across all three categories (quality over quantity)
- Set priority: true ONLY when all three audience lanes apply
- audience_lanes must always be a list — never use "All Three" as a string
- The watch_list is for signals too early to act on but worth tracking (2–5 items)
- Skip items that are purely theoretical with no near-term industry relevance
- supporting_sources: include up to 3 items per trend — copy title, source, url, authors, and date exactly from the item data above. NEVER fabricate or guess a URL. If an item has no URL, omit the url field entirely.
- A trend supported by both research (arXiv) and community discussion (HN/Reddit) is stronger signal
- Return valid JSON only — no markdown fences, no explanation text
"""


def analyze_trends(papers: list[dict]) -> dict:
    """
    Send papers to Claude for trend analysis.
    Returns a dict with 'trends' and 'watch_list' keys.
    """
    if not papers:
        return {"trends": [], "watch_list": []}

    items_text = _format_items_for_prompt(papers)

    client = anthropic.Anthropic()

    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=8192,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"""Here are {len(papers)} recent items from arXiv, Hacker News, and Reddit (past 24–48 hours).
Identify the most meaningful trends and provide your analysis.

{items_text}""",
            }
        ],
    )

    raw = message.content[0].text.strip()

    try:
        result = _parse_json(raw)
    except json.JSONDecodeError:
        # Response was truncated — retry with fewer items
        print(f"  JSON truncated, retrying with {len(papers[:15])} items...")
        return analyze_trends(papers[:15])

    return result


def _parse_json(raw: str) -> dict:
    """Parse JSON, stripping markdown fences if present."""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw.strip())


def _format_items_for_prompt(items: list[dict]) -> str:
    """Format mixed-source items into a clean text block for the prompt."""
    lines = []
    for i, item in enumerate(items, 1):
        source = item.get("source", "unknown")
        pub_date = item["published"].strftime("%Y-%m-%d")
        authors_str = ", ".join(item.get("authors", []))

        url = item.get("url", "")
        line = (
            f"[{i}] {item['title']}\n"
            f"    Source: {source}\n"
            f"    URL: {url}\n"
            f"    Category hint: {item.get('topic', 'unknown')}\n"
            f"    Date: {pub_date}\n"
        )

        if authors_str:
            line += f"    Authors: {authors_str}\n"

        if item.get("engagement"):
            eng = item["engagement"]
            if "points" in eng:
                line += f"    Engagement: {eng['points']} HN points, {eng.get('comments', 0)} comments\n"
            elif "score" in eng:
                line += f"    Engagement: {eng['score']} upvotes, {eng.get('comments', 0)} comments\n"

        abstract = item.get("abstract", "")
        if abstract:
            line += f"    Summary: {abstract[:350]}\n"

        lines.append(line)
    return "\n".join(lines)
