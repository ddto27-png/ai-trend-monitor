"""
Semantic relevance filter — uses Claude Haiku to verify each collected item
is genuinely about AI/ML before it reaches the main analysis step.

This prevents keyword false positives (e.g. "inference" in a statistics paper,
"planning" in operations research, "edge" in graph theory) from polluting the digest.
"""

import json
import anthropic


def filter_relevant_items(items: list[dict]) -> tuple[list[dict], dict]:
    """
    Use Claude Haiku to verify items are genuinely about AI/ML.
    Returns (kept_items, report) where report describes what was dropped and why.
    Falls back to keeping all items if the API call fails.
    """
    if not items:
        return [], {"kept": 0, "dropped": [], "status": "skipped — no items"}

    client = anthropic.Anthropic()

    lines = []
    for i, item in enumerate(items, 1):
        title = item.get("title", "")
        abstract = item.get("abstract", "")[:250]
        source = item.get("source", "")
        lines.append(f"[{i}] {title}\n    Source: {source}\n    Summary: {abstract}")

    items_text = "\n\n".join(lines)

    try:
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=512,
            messages=[
                {
                    "role": "user",
                    "content": f"""You are a relevance filter for an AI industry newsletter.

Review these {len(items)} items. Return the item numbers that are GENUINELY about AI/ML — meaning large language models, foundation models, generative AI, AI agents, ML training or inference, AI deployment, or AI tooling and infrastructure.

EXCLUDE:
- Papers about unrelated fields that incidentally use math or statistics (pavement engineering, climate science, pure finance, bioinformatics — unless the paper is explicitly using or building AI/ML models)
- Pure theoretical computer science with no practical AI/ML connection
- Adjacent fields like robotics hardware or classical signal processing unless they directly involve AI/ML models

Return ONLY a JSON array of item numbers to keep, like: [1, 3, 5]
No explanation. No other text.

Items to review:
{items_text}""",
                }
            ],
        )

        raw = message.content[0].text.strip()

        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]

        keep_indices = set(json.loads(raw.strip()))

        if not isinstance(keep_indices, set):
            return items, {"kept": len(items), "dropped": [], "status": "fallback — bad response"}

        kept = [item for i, item in enumerate(items, 1) if i in keep_indices]
        dropped = [item for i, item in enumerate(items, 1) if i not in keep_indices]

        dropped_list = [
            {"title": item.get("title", "Unknown"), "source": item.get("source", "?")}
            for item in dropped
        ]

        if dropped_list:
            print(f"  Relevance filter: removed {len(dropped_list)} off-topic item(s):")
            for d in dropped_list:
                print(f"    ✗ [{d['source']}] {d['title'][:80]}")

        print(f"  Relevance filter: {len(kept)}/{len(items)} items confirmed relevant")

        report = {
            "kept": len(kept),
            "total": len(items),
            "dropped": dropped_list,
            "status": "ok",
        }
        return kept, report

    except Exception as e:
        print(f"  Relevance filter: skipped due to error ({e}) — keeping all items")
        return items, {"kept": len(items), "total": len(items), "dropped": [], "status": f"error — {e}"}
