# Skitsa AI Trend Monitor

An automated intelligence pipeline that reads the AI research landscape every morning and delivers a structured, fact-checked digest — to Notion and to your inbox.

Built to power [Skitsa](https://skitsa.substack.com) — a content brand at the intersection of complexity and beauty.

---

## What this is

Most AI newsletters are either written for engineers who already understand everything, or simplified past the point of usefulness. This pipeline sits between those two failure modes.

It monitors four live sources daily, runs collected items through a multi-stage quality filter, asks Claude to identify and frame meaningful trends, fact-checks those trends against the original source material, and delivers a digest in two forms: a structured Notion page with full citations and briefs, and a clean email teaser that surfaces the three signals most worth acting on.

The goal is accurate, actionable intelligence — not noise dressed up as insight.

---

## Pipeline

```
┌─────────────────────────────────────────────────────┐
│  COLLECT                                            │
│  arXiv (cs.AI, cs.LG, cs.CL)                       │
│  Hacker News (Algolia search API)                   │
│  Reddit (r/MachineLearning, r/LocalLLaMA)           │
│  RSS (Anthropic, OpenAI, DeepMind, HuggingFace,     │
│       LangChain, Mistral, Import AI, The Batch...)  │
└──────────────────────┬──────────────────────────────┘
                       │  ~50–80 raw items
                       ▼
┌─────────────────────────────────────────────────────┐
│  GATE 1 — Semantic relevance filter                 │
│  Claude Haiku reads every title + abstract.         │
│  Drops anything not genuinely about AI/ML.          │
│  Logs every removed item by name and source.        │
└──────────────────────┬──────────────────────────────┘
                       │  ~25 verified items
                       ▼
┌─────────────────────────────────────────────────────┐
│  ANALYSE                                            │
│  Claude Opus identifies 5–12 trends across:         │
│  LLMs · AI Agents & Automation · GPU & Infra        │
│                                                     │
│  Each trend assessed across 6 dimensions:           │
│  Signal quality · Sales pitch risk · Trend curve    │
│  Audience lanes · Content gap · Recommended action  │
│  + Content brief for a writer                       │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│  GATE 2 — URL verification                          │
│  Every citation URL is checked against the          │
│  URLs we actually sent in. Fabricated links         │
│  are stripped before anything is published.         │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│  GATE 3 — Accuracy review                           │
│  Claude Haiku re-reads each trend against its       │
│  source abstracts and checks for:                   │
│  · Technical terms used incorrectly                 │
│  · Claims that go beyond what sources support       │
│  · Overconfident trend curve or signal quality      │
│  · Content brief points that would mislead          │
│  Corrections applied directly. Notes visible        │
│  in Notion per trend.                               │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│  PUBLISH                                            │
│  Notion page — full digest with citations,          │
│  content briefs, QA audit trail per trend           │
│                                                     │
│  Email — Skitsa-branded teaser, top 3 trends,       │
│  watch list, CTA to Notion                          │
└─────────────────────────────────────────────────────┘
```

Runs daily at 7am UTC via GitHub Actions. Also triggerable manually.

---

## Why three quality gates

The naive version of this pipeline — collect keywords, send to Claude, publish — produces confident-sounding content that is sometimes wrong. A paper about pavement thermal computation matches the keyword "inference." Claude, given no URL to copy, will generate a plausible-looking one. A trend framed as production-ready may be based on a single benchmark paper.

Each gate addresses one of those failure modes:

**Gate 1** catches what keyword matching can't. Semantic understanding of whether something is actually about AI, not just adjacent to it.

**Gate 2** ensures every link published is a link that existed in the source data. Not a guess. Not a hallucination. A URL we received and passed in.

**Gate 3** is the hardest one to skip. The accuracy reviewer reads what Claude wrote and checks it against what the sources actually said. If the signal quality overstates adoption, it gets corrected. If a content brief point would mislead a developer, it gets flagged. Both technical and non-technical readers deserve accurate information.

The QA audit trail for each run is visible at the top of every Notion digest page.

---

## Output

### Notion digest
Each page contains:
- **QA summary** — what each gate found and removed
- **Priority trends** — signals relevant to all three audience types (Business Buyer · Technical DM · Internal Champion)
- **Trends by category** — LLMs · AI Agents & Automation · GPU & Infrastructure
- **Per trend**: signal quality, trend curve, sales pitch risk, audience lanes, content gap, content brief, citations with links
- **Watch list** — emerging signals not yet ready to act on

### Email
Skitsa-branded teaser sent via Resend. Top 3 trends with category, action badge, signal snippet, and content angle. Watch list titles. Single CTA to the full Notion digest.

---

## Stack

| Layer | Tool | Why |
|---|---|---|
| Collection | arXiv Atom API, HN Algolia, Reddit JSON, feedparser | Free, no rate-limit issues at this volume |
| Relevance filter | Claude Haiku (`claude-haiku-4-5`) | Fast and cheap for binary classification |
| Analysis | Claude Opus (`claude-opus-4-6`) | Best reasoning for nuanced trend assessment |
| Accuracy review | Claude Haiku | Sufficient for factual consistency checks |
| Notion | `notion-client` Python SDK | Structured output with rich text, callouts, links |
| Email | Resend API | Simple, reliable, no SMTP credentials |
| Automation | GitHub Actions (cron `0 7 * * *`) | Free, cloud-hosted, no server to maintain |

---

## Setup

### 1. Clone and install

```bash
git clone https://github.com/ddto27-png/ai-trend-monitor.git
cd ai-trend-monitor
pip install -r requirements.txt
```

### 2. Configure keys

Create a `.env` file in the project root:

```
ANTHROPIC_API_KEY=sk-ant-...
NOTION_API_KEY=secret_...
NOTION_PARENT_PAGE_ID=<32-char hex ID from your Notion page URL>
RESEND_API_KEY=re_...          # optional — skip to disable email
DIGEST_EMAIL=you@example.com  # comma-separated for multiple recipients
```

**Getting each key:**

- **Anthropic** — [console.anthropic.com](https://console.anthropic.com) → API Keys
- **Notion token** — [notion.so/my-integrations](https://www.notion.so/my-integrations) → New integration → copy token. Then share your target page with the integration.
- **Notion page ID** — open the page in Notion, copy the 32-character hex string from the URL (after the last `-`, before any `?`)
- **Resend** — [resend.com](https://resend.com) → API Keys

### 3. Run

```bash
# Standard run — last 24 hours
python main.py

# Extend lookback (after a weekend or holiday)
python main.py --days 2

# Dry run — analyse but don't publish
python main.py --dry-run
```

### 4. Automate with GitHub Actions

Add these secrets to your repository (Settings → Secrets → Actions):

```
ANTHROPIC_API_KEY
NOTION_API_KEY
NOTION_PARENT_PAGE_ID
RESEND_API_KEY
DIGEST_EMAIL
```

The workflow at `.github/workflows/daily_digest.yml` runs automatically at 7am UTC. Trigger manually from the Actions tab at any time.

---

## Project structure

```
collectors/
  arxiv.py              — arXiv Atom API
  hackernews.py         — Hacker News via Algolia
  reddit.py             — Reddit public JSON API
  rss.py                — RSS/Atom feeds (blogs + newsletters)
  relevance_filter.py   — semantic filter (Gate 1)

analyzers/
  claude.py             — trend analysis + URL verification (Gate 2)
  fact_checker.py       — accuracy review (Gate 3)

publishers/
  notion.py             — Notion digest with QA audit trail
  email.py              — Skitsa-branded email teaser

main.py                 — pipeline orchestration
requirements.txt
.github/workflows/
  daily_digest.yml      — GitHub Actions schedule
```

---

*Skitsa — complexity, made beautiful.*
