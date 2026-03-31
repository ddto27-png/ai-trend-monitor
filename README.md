# AI Trend Monitor

Monitors AI research trends daily (arXiv → Claude analysis → Notion digest).

## What it does

Each run:
1. Fetches recent papers from arXiv (cs.AI, cs.LG, cs.CL categories)
2. Filters to papers relevant to LLMs, AI Agents, and GPU/Infrastructure
3. Sends them to Claude for analysis across 6 dimensions
4. Publishes a structured digest to a Notion page

## Output structure

Each Notion digest page contains:
- 🔥 **Priority Trends** — trends that serve all three audience types
- 📌 **LLMs** — large language model trends
- 📌 **AI Agents & Automation** — agentic AI trends
- 📌 **GPU & Infrastructure** — hardware and serving trends
- 💡 **Watch List** — emerging signals not yet ready to publish

## Setup

### 1. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure API keys

```bash
cp .env.example .env
```

Then edit `.env` with your three keys (see below).

### 3. Get your API keys

**Anthropic API key** (for Claude analysis):
- Go to https://console.anthropic.com → API Keys → Create key
- Add to `.env` as `ANTHROPIC_API_KEY`

**Notion integration token**:
- Go to https://www.notion.so/my-integrations → New integration
- Give it a name (e.g. "AI Trend Monitor"), select your workspace
- Copy the "Internal Integration Token"
- Add to `.env` as `NOTION_API_KEY`

**Notion parent page ID**:
- Create a page in Notion where digests will appear (e.g. "AI Trend Digests")
- Open it, click Share → Invite your integration by name
- Copy the page ID from the URL: `notion.so/Your-Page-Title-`**`abc123...`**
- Add to `.env` as `NOTION_PARENT_PAGE_ID`

### 4. Run

```bash
# Normal run (last 24h of papers)
python main.py

# Extend lookback window (e.g. after a weekend)
python main.py --days 2

# Test without publishing to Notion
python main.py --dry-run
```

## Scheduling (daily automation)

### macOS/Linux — cron

Run every morning at 7am:

```bash
crontab -e
# Add this line:
0 7 * * * cd /path/to/ai-trend-monitor && python main.py >> logs/daily.log 2>&1
```

### GitHub Actions (runs in the cloud, no local setup needed)

Create `.github/workflows/daily.yml` — ask Claude to set this up in Phase 2.

## Phase roadmap

- **Phase 1** (current): arXiv → Claude → Notion ✅
- **Phase 2**: Add Hacker News and Reddit sources
- **Phase 3**: Add scheduling via GitHub Actions (free, runs daily automatically)
