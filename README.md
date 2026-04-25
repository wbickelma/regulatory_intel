# Regulatory Intelligence

An automated system that monitors regulatory websites, aggregates content via RSS feeds, evaluates relevance, and generates executive briefings.

Built with Python, FastAPI, and deployed on Google Cloud Platform.

---

## What It Does

1. **Create Topics** — Define regulatory areas to monitor (e.g., "FDA Regulations", "SEC Filings")
2. **Add Feeds** — Submit website URLs; the system generates RSS feeds via RSS.app and subscribes via Inoreader
3. **Extract Articles** — Pull full article content from Inoreader within a configurable date range (default: 7 days)
4. **Evaluate Relevance** — LLM classifies each article against topic-specific criteria
5. **Generate Reports** — Synthesize relevant articles into executive briefings grouped by topic

---

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  RSS.app    │────▶│  Inoreader  │────▶│   FastAPI   │
│ (Feed Gen)  │     │ (Aggregator)│     │  (Backend)  │
└─────────────┘     └─────────────┘     └─────────────┘
                                               │
                    ┌──────────────────────────┼──────────────────────────┐
                    ▼                          ▼                          ▼
             ┌─────────────┐            ┌─────────────┐            ┌─────────────┐
             │ PostgreSQL  │            │   Gemini    │            │   Report    │
             │  (Storage)  │            │   (LLM)     │            │  Delivery   │
             └─────────────┘            └─────────────┘            └─────────────┘
```

### Key Components

- **RSS.app API**: Generates RSS feeds from websites that don't natively offer them
- **Inoreader API**: Aggregates feeds, organizes by folders (topics), extracts full article content
- **Gemini LLM**: Evaluates article relevance and synthesizes summaries
- **PostgreSQL**: Stores topics, feeds, articles, and reports

---

## How It Works

### Onboarding a Feed
1. Create a topic (maps to an Inoreader folder)
2. Submit a source URL
3. RSS.app generates a feed URL
4. Inoreader subscribes to the feed in the topic's folder

### Weekly Report Generation
1. Extract articles from past 7 days via Inoreader API
2. Classify each article for relevance using Gemini
3. Synthesize relevant articles into a report grouped by topic
4. Deliver via email or Slack

---

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Run the API
uvicorn api.main:app --reload
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/topics` | Create a new topic |
| GET | `/topics` | List all topics |
| POST | `/topics/{id}/feeds` | Add a feed to a topic |
| GET | `/topics/{id}/articles?days=7` | Get recent articles |
| POST | `/reports/generate` | Generate a report |
| GET | `/reports/{id}` | Get report content |

---

## Configuration

See `.env.example` for required environment variables:

- `RSSAPP_API_KEY` — RSS.app API key
- `INOREADER_API_KEY` — Inoreader API key  
- `INOREADER_APP_ID` — Inoreader application ID
- `GEMINI_API_KEY` — Google Gemini API key
- `DATABASE_URL` — PostgreSQL connection string

---