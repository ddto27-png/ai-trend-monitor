"""
arXiv collector — fetches recent AI papers from the arXiv API.
No API key required. Covers cs.AI, cs.LG, cs.CL categories.
"""

import time
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone


ARXIV_API_URL = "http://export.arxiv.org/api/query"

# The three topic buckets we care about
TOPIC_KEYWORDS = {
    "LLMs": [
        "large language model", "llm", "gpt", "transformer", "fine-tuning",
        "instruction tuning", "rlhf", "alignment", "chat", "tokenizer",
        "foundation model", "language model", "pre-training",
    ],
    "AI Agents & Automation": [
        "agent", "agentic", "tool use", "function calling", "multi-agent",
        "autonomous", "workflow", "orchestration", "reasoning", "planning",
        "retrieval augmented", "rag", "code generation", "copilot",
    ],
    "GPU & Infrastructure": [
        "inference", "quantization", "serving", "throughput", "latency",
        "gpu", "hardware", "accelerator", "memory efficient", "speculative",
        "distillation", "pruning", "deployment", "edge", "tpu",
    ],
}

# Minimum relevance: paper must match at least this many keywords in any bucket
MIN_KEYWORD_MATCHES = 1


def fetch_papers(days_back: int = 1, max_results: int = 100) -> list[dict]:
    """
    Fetch recent papers from arXiv in AI-related categories.
    Returns a list of paper dicts with title, abstract, authors, url, published.
    """
    # arXiv API query: cs.AI OR cs.LG OR cs.CL, sorted by submission date
    params = {
        "search_query": "cat:cs.AI OR cat:cs.LG OR cat:cs.CL",
        "start": 0,
        "max_results": max_results,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }

    # Retry with exponential backoff on 429 rate limit
    for attempt in range(3):
        response = requests.get(ARXIV_API_URL, params=params, timeout=30)
        if response.status_code == 429:
            wait = 15 * (attempt + 1)
            print(f"  arXiv rate limit hit, waiting {wait}s before retry...")
            time.sleep(wait)
            continue
        response.raise_for_status()
        break

    papers = _parse_arxiv_response(response.text)

    # Filter to papers submitted within the window
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
    recent = [p for p in papers if p["published"] >= cutoff]

    # If it's a weekend or holiday and there are few recent papers, extend window
    if len(recent) < 5:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days_back + 2)
        recent = [p for p in papers if p["published"] >= cutoff]

    return recent


def filter_relevant_papers(papers: list[dict]) -> list[dict]:
    """
    Score each paper against topic keywords and tag it with the best-matching
    bucket. Drops papers with no keyword matches.
    """
    scored = []
    for paper in papers:
        text = (paper["title"] + " " + paper["abstract"]).lower()
        best_topic = None
        best_score = 0

        for topic, keywords in TOPIC_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text)
            if score > best_score:
                best_score = score
                best_topic = topic

        if best_score >= MIN_KEYWORD_MATCHES:
            paper["topic"] = best_topic
            paper["relevance_score"] = best_score
            scored.append(paper)

    # Sort by relevance score descending, keep top 40 to manage Claude API cost
    scored.sort(key=lambda p: p["relevance_score"], reverse=True)
    return scored[:40]


def _parse_arxiv_response(xml_text: str) -> list[dict]:
    """Parse arXiv Atom XML response into a list of paper dicts."""
    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "arxiv": "http://arxiv.org/schemas/atom",
    }
    root = ET.fromstring(xml_text)
    papers = []

    for entry in root.findall("atom:entry", ns):
        title_el = entry.find("atom:title", ns)
        summary_el = entry.find("atom:summary", ns)
        published_el = entry.find("atom:published", ns)
        id_el = entry.find("atom:id", ns)

        if not all([title_el is not None, summary_el is not None,
                    published_el is not None, id_el is not None]):
            continue

        authors = [
            author.find("atom:name", ns).text
            for author in entry.findall("atom:author", ns)
            if author.find("atom:name", ns) is not None
        ]

        # Parse ISO 8601 date
        pub_str = published_el.text.strip()
        published = datetime.fromisoformat(pub_str.replace("Z", "+00:00"))

        papers.append({
            "title": title_el.text.strip().replace("\n", " "),
            "abstract": summary_el.text.strip().replace("\n", " "),
            "authors": authors[:3],  # first 3 authors
            "url": id_el.text.strip(),
            "published": published,
        })

    return papers
