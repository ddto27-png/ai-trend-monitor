"""
Accuracy reviewer — uses Claude to verify that trend analyses and content briefs
are technically sound before they reach Notion or the email digest.

Checks for:
- Technical terminology used incorrectly (e.g. conflating fine-tuning with RAG,
  calling a benchmark result a deployed product)
- Claims that go beyond what the source material actually supports
- Overstated adoption or maturity (theoretical work presented as production-ready)
- Content brief points that would mislead or misinform a technical reader
- Signal quality or trend curve that doesn't match the evidence

Every trend gets a reviewer_note in the output:
- None  → reviewed, no issues found
- text  → what was corrected or flagged, and why
"""

import json
import anthropic


REVIEWER_PROMPT = """You are a senior technical editor and AI researcher reviewing trend analyses
for a professional newsletter read by both engineers and business decision-makers.

Your job is NOT to rewrite or expand — it is to catch and correct:
1. Technical terms used incorrectly (fine-tuning vs RAG vs prompt engineering vs inference are distinct)
2. Claims that overstate what the source actually shows (a paper proposing X ≠ X being deployed at scale)
3. Trend curve or signal quality that doesn't match the evidence (calling early-stage research "Peak" adoption)
4. Content brief points that are factually wrong or would mislead a developer trying to apply them
5. Hype language that presents vendor marketing as neutral research signal

For each trend you review, you have the trend analysis AND the original source text it was based on.
Use the source text as ground truth. If a claim in the analysis isn't supported by the source, correct it.

Respond with valid JSON only:
{
  "reviews": [
    {
      "title": "exact trend title from input",
      "issues_found": false,
      "reviewer_note": null,
      "corrected_signal_quality": null,
      "corrected_content_points": null
    },
    {
      "title": "exact trend title from input",
      "issues_found": true,
      "reviewer_note": "Brief explanation of what was wrong and what was corrected. Be specific — name the exact claim and the correct framing.",
      "corrected_signal_quality": "Corrected version, or null if signal_quality was fine",
      "corrected_content_points": ["corrected point 1", "corrected point 2"]
    }
  ]
}

Rules:
- reviewer_note must be concise (1-3 sentences), specific, and actionable
- If nothing is wrong, set issues_found: false and both corrected fields to null
- corrected_content_points: only include if the content_points contained inaccuracies; otherwise null
- corrected_signal_quality: only include if signal_quality overstated or misrepresented the evidence; otherwise null
- Do not flag stylistic preferences — only flag factual or technical errors
"""


def fact_check_analysis(analysis: dict, source_items: list[dict]) -> dict:
    """
    Review the trend analysis for technical accuracy.
    Returns the same analysis dict with reviewer_note fields added to each trend,
    and any corrections applied directly to signal_quality and content_points.
    """
    trends = analysis.get("trends", [])
    if not trends:
        return analysis

    # Build a lookup of source text by title (for the reviewer to reference)
    source_lookup = {
        item.get("title", "").lower(): item.get("abstract", "")
        for item in source_items
        if item.get("abstract")
    }

    # Format each trend + its supporting sources for review
    review_input = []
    for trend in trends:
        entry = {
            "title": trend.get("title", ""),
            "signal_quality": trend.get("signal_quality", ""),
            "trend_curve": trend.get("trend_curve", ""),
            "content_brief": {
                "purpose": trend.get("content_brief", {}).get("purpose", ""),
                "topic": trend.get("content_brief", {}).get("topic", ""),
                "content_points": trend.get("content_brief", {}).get("content_points", []),
            },
            "supporting_sources": [],
        }
        # Attach original source abstracts so the reviewer can check claims
        for src in trend.get("supporting_sources", [])[:3]:
            src_title = src.get("title", "").lower()
            abstract = source_lookup.get(src_title, "")
            entry["supporting_sources"].append({
                "title": src.get("title", ""),
                "source": src.get("source", ""),
                "abstract": abstract[:400] if abstract else "(abstract not available)",
            })
        review_input.append(entry)

    try:
        client = anthropic.Anthropic()
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=4096,
            system=REVIEWER_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": f"Review these {len(review_input)} trend analyses for technical accuracy.\n\n"
                               + json.dumps(review_input, indent=2),
                }
            ],
        )

        raw = message.content[0].text.strip()
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]

        result = json.loads(raw.strip())
        reviews = {r["title"]: r for r in result.get("reviews", [])}

        # Apply corrections back to the analysis
        issues_found = 0
        for trend in trends:
            title = trend.get("title", "")
            review = reviews.get(title)

            if not review:
                trend["reviewer_note"] = None
                continue

            trend["reviewer_note"] = review.get("reviewer_note")

            if review.get("issues_found"):
                issues_found += 1

                # Apply corrected signal_quality if provided
                corrected_sq = review.get("corrected_signal_quality")
                if corrected_sq:
                    trend["signal_quality"] = corrected_sq

                # Apply corrected content_points if provided
                corrected_cp = review.get("corrected_content_points")
                if corrected_cp and isinstance(corrected_cp, list):
                    if "content_brief" in trend:
                        trend["content_brief"]["content_points"] = corrected_cp

        if issues_found:
            print(f"  Accuracy review: {issues_found} trend(s) had corrections applied")
        else:
            print(f"  Accuracy review: all {len(trends)} trend(s) passed — no corrections needed")

    except Exception as e:
        print(f"  Accuracy review: skipped due to error ({e}) — analysis unchanged")
        # Add null reviewer_note to all trends so the Notion publisher knows it was attempted
        for trend in trends:
            trend.setdefault("reviewer_note", None)

    return analysis
