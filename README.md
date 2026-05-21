# Regulatory Intelligence

Automated retrieval, summarization, and editorial filtering of regulatory publications using RSS feeds and LLM-powered analysis.

## Architecture

```
[ User / Frontend ]
        |
        v
+------------------+         +------------------+
|    RSS.app API   | ------> |  Inoreader API   |
| Creates feeds    |         | Aggregates feeds |
| from site URLs   |         | Organizes by     |
+------------------+         | topic folders    |
                              +------------------+
                                       |
                                       v
                              +------------------+
                              |  Circuit LLM     |
                              | (Azure OpenAI)   |
                              | - Evaluate       |
                              | - Summarize      |
                              +------------------+
                                       |
                                       v
                              [ Email Report ]
```

## Workflows

### Onboarding (one-time per site)
1. User provides a site URL and selects a topic
2. **RSS.app** generates an RSS feed URL for the site
3. Feed is subscribed in **Inoreader** and placed in the topic's folder

### Report Generation (recurring)
1. Download entries from each **Inoreader** folder for a specified timeframe
2. Evaluate each source for relevance using **Circuit LLM**
3. Summarize each relevant article
4. Compile and email the report

## Directory Structure

```
regulatory_intelligence/
├── clients/
│   ├── __init__.py
│   ├── rss_app.py              # RSS.app feed generation client
│   └── inoreader.py            # Inoreader aggregation + OAuth client
├── config/
│   ├── __init__.py
│   ├── settings.py             # Pydantic Settings (env vars)
│   └── logging_config.py       # Structured JSON logging
├── schemas/
│   ├── __init__.py
│   ├── topic.py                # Topic Pydantic models
│   ├── feed.py                 # Feed Pydantic models
│   ├── article.py              # Article Pydantic models
│   └── report.py               # Report Pydantic models
├── scripts/
│   └── test_workflow.py        # End-to-end onboarding test
├── circuit_scrapegraph_example.py  # Circuit LLM auth reference
├── .env                        # API credentials (not committed)
├── .gitignore
├── AGENTS.md
├── GEMINI.md
├── README.md
├── requirements.txt
├── pyproject.toml
└── setup.sh
```

## Setup

```bash
# Create conda environment
bash setup.sh

# Or manually:
conda create -n reg_intel python=3.11 -y
conda activate reg_intel
pip install -r requirements.txt
```

## Configuration

Copy `.env.example` to `.env` and fill in your credentials:

| Variable | Description |
|---|---|
| `CIRCUIT_CLIENT_ID` | Circuit API OAuth2 client ID |
| `CIRCUIT_CLIENT_SECRET` | Circuit API OAuth2 client secret |
| `CIRCUIT_APPKEY` | Circuit API application key |
| `CLIENT_ID_INOREADER` | Inoreader OAuth2 application ID |
| `CLIENT_SECRET_INOREADER` | Inoreader OAuth2 application secret |
| `INOREADER_ACCESS_TOKEN` | Inoreader OAuth2 access token |
| `INOREADER_REFRESH_TOKEN` | Inoreader OAuth2 refresh token |
| `RSS_APP_KEY` | RSS.app API key |
| `RSS_APP_SECRET` | RSS.app API secret |

## Database Schema

SQLite database stored in GCS (`regulatory.db`):

```
┌─────────────────┐       ┌─────────────────┐
│   Countries     │       │     Topics      │
├─────────────────┤       ├─────────────────┤
│ country_code PK │       │ topic_id PK     │
│ country_name    │       │ topic_name      │
└────────┬────────┘       └────────┬────────┘
         │                         │
         │    ┌─────────────────┐  │
         │    │    Sources      │  │
         │    ├─────────────────┤  │
         └───►│ source_id PK    │  │
              │ source_name     │  │
              │ country_code FK │  │
              │ inoreader_stream│  │
              │ feed_url        │  │
              │ last_fetched_at │  │
              │ is_active       │  │
              └────────┬────────┘  │
                       │           │
              ┌────────▼───────────▼─┐
              │   Source_Topics      │
              ├──────────────────────┤
              │ source_id FK         │
              │ topic_id FK          │
              │ (composite PK)       │
              └──────────────────────┘
```

### Database Management

```bash
# Initialize DB from CSVs and upload to GCS
python scripts/add_sqlite.py init

# Download DB from GCS for local editing
python scripts/add_sqlite.py download

# Upload local changes back to GCS
python scripts/add_sqlite.py upload

# Show table row counts
python scripts/add_sqlite.py stats

# Delete local copy
python scripts/add_sqlite.py delete
```

## Usage

### Test the onboarding workflow
```bash
python scripts/test_workflow.py
```

This runs the full flow: RSS.app feed generation → Inoreader subscription → article retrieval.