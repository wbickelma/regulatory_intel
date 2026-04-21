# Regulatory News Summarizer

A multi-agent system that monitors government regulatory websites, extracts updates, evaluates their relevance, and produces concise regulatory briefings with links back to original sources.

Built with Python and deployed on Google Cloud Platform.

---

## What It Does

1. **Onboard** a government website by submitting its URL
2. **Automatically determine** the best way to pull content from that site (RSS, Sitemap, or LLM-powered scraping)
3. **Discover** new articles on a recurring schedule
4. **Extract** article content as clean markdown
5. **Evaluate** each article against relevance criteria using an LLM
6. **Summarize** all relevant findings into a single briefing where every section links back to its source

No per-website custom code is required. A new site can be onboarded in minutes.

---

## How It Works

The system has two main flows:

**Onboarding (one-time per site):**
- User submits a URL
- An investigator agent probes the site and selects an ingestion strategy
- The strategy and configuration are saved to the database

**Scheduled Runs (recurring):**
- Gather new article links using the site's configured strategy
- Extract content from those links
- Evaluate each article for relevance
- Summarize the approved articles into a briefing with source links

### Strategy Waterfall

When a new site is onboarded, the system selects the most reliable available method:

1. **RSS / Atom Feed** — preferred, most stable and metadata-rich
2. **Sitemap XML** — good coverage, less metadata
3. **ScrapeGraphAI** — fallback when no structured feeds exist

### Summarization

Approved articles go through a map-reduce summarization process:
- **Map:** Each article is individually summarized
- **Reduce:** All summaries are synthesized into a single cohesive briefing

Every section of the final output links back to the original government source.

---