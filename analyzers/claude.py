"""
Claude analyzer — sends collected papers to Claude and gets back
structured trend analysis with content briefs.
"""

import json
import anthropic


SYSTEM_PROMPT = """You are an expert AI industry analyst who helps content strategists
identify which AI research trends are worth writing about for enterprise technology audiences.

You receive a batch of recent arXiv papers and must identify the most meaningful trends
from three buckets: LLMs, AI Agents & Automation, and GPU & Infrastructure.

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
      "supporting_papers": [
        {
          "title": "Full paper title",
          "authors": ["Last, First", "Last, First"],
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
- Skip papers that are purely theoretical with no near-term industry relevance
- supporting_papers: include up to 3, with real author names and dates from the paper metadata
- Return valid JSON only — no markdown fences, no explanation text
"""


def analyze_trends(papers: list[dict]) -> dict:
    """
    Send papers to Claude for trend analysis.
    Returns a dict with 'trends' and 'watch_list' keys.
    """
    if not papers:
        return {"trends": [], "watch_list": []}

    papers_text = _format_papers_for_prompt(papers)

    client = anthropic.Anthropic()

    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=8192,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"""Here are {len(papers)} recent arXiv papers from the past 24–48 hours.
Identify the most meaningful trends and provide your analysis.

{papers_text}""",
            }
        ],
    )

    raw = message.content[0].text.strip()

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        result = json.loads(raw.strip())

    return result


def _format_papers_for_prompt(papers: list[dict]) -> str:
    """Format papers into a clean text block for the prompt."""
    lines = []
    for i, paper in enumerate(papers, 1):
        authors_str = ", ".join(paper.get("authors", []))
        pub_date = paper["published"].strftime("%Y-%m-%d")
        lines.append(
            f"[{i}] {paper['title']}\n"
            f"    Category hint: {paper.get('topic', 'unknown')}\n"
            f"    Authors: {authors_str}\n"
            f"    Published: {pub_date}\n"
            f"    Abstract: {paper['abstract'][:400]}...\n"
        )
    return "\n".join(lines)
