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

2. VENDOR PITCH LIKELIHOOD: Will a vendor likely pitch this to enterprise buyers in the
   next 90 days? (Yes / Likely / Unlikely / No)

3. TREND CURVE: Where is this on the adoption curve?
   (Emerging = <5% aware | Rising = gaining traction | Peak = mainstream buzz | Mature = commoditising)

4. AUDIENCE LANE: Who does this serve?
   - Business Buyer (ROI, risk, cost)
   - Technical Decision Maker (architecture, feasibility)
   - Internal Champion (implementation, adoption)
   - All Three

5. CONTENT GAP: What angle on this trend has NOT been taken yet by mainstream tech press?

6. RECOMMENDED ACTION: Publish Now / Watch 2 Weeks / Skip

OUTPUT FORMAT — respond with valid JSON only, no other text:
{
  "trends": [
    {
      "title": "Short descriptive trend title",
      "category": "LLMs" | "AI Agents & Automation" | "GPU & Infrastructure",
      "signal_quality": "...",
      "vendor_pitch_likelihood": "Yes" | "Likely" | "Unlikely" | "No",
      "trend_curve": "Emerging" | "Rising" | "Peak" | "Mature",
      "audience_lane": "Business Buyer" | "Technical DM" | "Internal Champion" | "All Three",
      "content_gap": "...",
      "recommended_action": "Publish Now" | "Watch 2 Weeks" | "Skip",
      "content_brief": "One-line brief: [angle] — [format] — [timing] — [audience]",
      "priority": true | false,
      "supporting_papers": ["Paper title 1", "Paper title 2"]
    }
  ],
  "watch_list": [
    {
      "title": "Trend title",
      "category": "...",
      "why_watching": "One sentence on why this is worth monitoring",
      "signal_so_far": "Emerging"
    }
  ]
}

Rules:
- Identify 5–12 trends total across all three categories (quality over quantity)
- Set priority: true ONLY when audience_lane is "All Three"
- The watch_list is for signals too early to act on but worth tracking (2–5 items)
- Skip papers that are purely theoretical with no near-term industry relevance
- Do NOT include papers about niche sub-problems with no broad applicability
- Return valid JSON only — no markdown fences, no explanation text
"""


def analyze_trends(papers: list[dict]) -> dict:
    """
    Send papers to Claude for trend analysis.
    Returns a dict with 'trends' and 'watch_list' keys.
    """
    if not papers:
        return {"trends": [], "watch_list": []}

    # Format papers for the prompt
    papers_text = _format_papers_for_prompt(papers)

    client = anthropic.Anthropic()

    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=4096,
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

    # Parse JSON response
    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        # If Claude wrapped in markdown fences, strip them
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
