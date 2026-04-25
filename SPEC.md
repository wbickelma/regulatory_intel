# Specification: Regulatory Intelligence System

## 1. System Overview

This application automates the retrieval, summarization, and editorial filtering of regulatory publications using **RSS.app** for feed generation and **Inoreader** for feed aggregation and full-text extraction. The system operates on a weekly schedule, pulling articles from the past 7 days, evaluating relevance, and generating executive briefings.

### Core Architecture Principles

- **API-First Data Collection**: No custom scraping. All content flows through RSS.app → Inoreader → Application.
- **Topic-Based Organization**: Feeds are organized into Inoreader folders that map to regulatory topics.
- **Date-Range Extraction**: Reports pull articles from configurable time windows (default: 7 days).
- **LLM Evaluation & Synthesis**: Gemini evaluates relevance and synthesizes final reports.

---

## 2. External API Dependencies

### RSS.app API
- **Purpose**: Generate custom RSS feeds for websites that don't natively offer them.
- **Workflow**: Submit a website URL → RSS.app creates a feed → Feed URL is added to Inoreader.
- **API Docs**: https://rss.app/docs/api

### Inoreader API (Professional/Enterprise Tier)
- **Purpose**: Aggregate all RSS feeds, organize by topic folders, and extract full article content.
- **Key Features**:
  - Folder-based feed organization (folders = topics)
  - Full article content extraction via API
  - Date-range filtering for article retrieval
- **API Docs**: https://www.inoreader.com/developers

---

## 3. Infrastructure & GCP Architecture

```text
===================================================================================================
                           RSS-BASED PIPELINE ARCHITECTURE                               
===================================================================================================

[ 🌐 EXTERNAL SERVICES ]
+---------------------------+         +---------------------------+
|       RSS.app API         |         |     Inoreader API         |
| - Creates feeds from URLs | ------> | - Aggregates feeds        |
| - Returns feed URLs       |         | - Organizes by folders    |
+---------------------------+         | - Extracts full articles  |
                                      +---------------------------+
                                                   |
===================================================================================================
                                                   v
[ 🖥️ APPLICATION LAYER ]              +---------------------------+
                                      |     FastAPI Backend       |
                                      +---------------------------+
                                                   |
                     +-----------------------------+-----------------------------+
                     |                             |                             |
                     v                             v                             v
        +-------------------+         +-------------------+         +-------------------+
        | FeedManager       |         | ArticleExtractor  |         | ReportGenerator   |
        | - Create feeds    |         | - Pull by date    |         | - Evaluate        |
        | - Organize topics |         | - Get full text   |         | - Summarize       |
        +-------------------+         +-------------------+         +-------------------+
                                                   |
===================================================================================================
                                                   v
[ 🗄️ POSTGRESQL DATABASE ]  <-- Stores: Topics, FeedConfigs, Articles, Reports
===================================================================================================
                                                   |
                                                   v
                                      +---------------------------+
                                      |     GEMINI LLM API        |
                                      | - Relevance classification|
                                      | - Report synthesis        |
                                      +---------------------------+
                                                   |
                                                   v
                                      [ 📩 REPORT DELIVERY ]
                                      (Email / Slack / Dashboard)
```

### GCP Services

- **Cloud Run**: Hosts FastAPI backend and scheduled jobs
- **Cloud Scheduler**: Triggers weekly report generation (`0 8 * * 1`)
- **Pub/Sub**: Decouples scheduling from execution
- **Cloud SQL (PostgreSQL)**: Stores configuration and article data
- **Vertex AI (Gemini)**: Relevance classification and summarization
- **Secret Manager**: Stores API keys (RSS.app, Inoreader, Gemini)

---

## 4. Data Model

### Topic (Postgres Table `topics`)
```
id: UUID
name: str                    # e.g., "FDA Regulations", "SEC Filings"
description: str
inoreader_folder_id: str     # Maps to Inoreader folder
is_active: bool
created_at: datetime
```

### FeedConfig (Postgres Table `feed_configs`)
```
id: UUID
topic_id: UUID (FK)
source_url: str              # Original website URL
feed_url: str                # RSS.app generated feed URL
inoreader_subscription_id: str
name: str
is_active: bool
created_at: datetime
```

### Article (Postgres Table `articles`)
```
id: UUID
feed_id: UUID (FK)
inoreader_item_id: str (UNIQUE)
title: str
source_url: str
published_at: datetime
content_markdown: text
is_relevant: bool (nullable)
relevance_reasoning: text
extracted_at: datetime
```

### Report (Postgres Table `reports`)
```
id: UUID
topic_id: UUID (FK, nullable)  # null = all topics
date_range_start: datetime
date_range_end: datetime
summary_markdown: text
article_count: int
generated_at: datetime
```

---

## 5. Class Specifications

### API Clients

#### RssAppClient
- **Constructor**: `api_key: str`
- **Methods**:
  - `create_feed(url: str) -> FeedResponse`: Generate RSS feed for a website
  - `get_feed_status(feed_id: str) -> FeedStatus`: Check feed health
- **Called by**: `FeedManager`

#### InoreaderClient
- **Constructor**: `api_key: str, app_id: str`
- **Methods**:
  - `create_folder(name: str) -> FolderResponse`: Create topic folder
  - `subscribe_to_feed(feed_url: str, folder_id: str) -> SubscriptionResponse`: Add feed to folder
  - `get_folder_items(folder_id: str, since: datetime, until: datetime) -> list[ArticleItem]`: Fetch articles by date range
  - `get_article_content(item_id: str) -> ArticleContent`: Get full article text
- **Called by**: `FeedManager`, `ArticleExtractor`

---

### Core Services

#### FeedManager
- **Constructor**: `db: Session, rss_client: RssAppClient, inoreader_client: InoreaderClient`
- **Methods**:
  - `create_topic(name: str, description: str) -> Topic`: Create new topic and Inoreader folder
  - `add_feed(topic_id: UUID, source_url: str, name: str) -> FeedConfig`: Generate RSS feed and subscribe in Inoreader
  - `list_topics() -> list[Topic]`
  - `list_feeds(topic_id: UUID) -> list[FeedConfig]`
- **Called by**: FastAPI endpoints for onboarding

#### ArticleExtractor
- **Constructor**: `db: Session, inoreader_client: InoreaderClient`
- **Methods**:
  - `extract_articles(topic_id: UUID, days: int = 7) -> list[Article]`: Pull articles from date range
  - `extract_all_articles(days: int = 7) -> list[Article]`: Pull from all active topics
- **Called by**: `ReportGenerator`

#### RelevanceClassifier
- **Constructor**: `llm_client: GeminiClient, topic_criteria: dict[str, list[str]]`
- **Methods**:
  - `classify(article: Article, topic: Topic) -> tuple[bool, str]`: Returns (is_relevant, reasoning)
  - `classify_batch(articles: list[Article], topic: Topic) -> list[ClassificationResult]`
- **Called by**: `ReportGenerator`

#### ReportGenerator
- **Constructor**: `db: Session, extractor: ArticleExtractor, classifier: RelevanceClassifier, llm_client: GeminiClient`
- **Methods**:
  - `generate_report(topic_id: UUID | None, days: int = 7) -> Report`: Full pipeline for one topic or all
  - `synthesize_summary(articles: list[Article], topic: Topic) -> str`: LLM-powered summary
- **Called by**: Scheduled Cloud Run job

---

## 6. API Endpoints

### Topics
- `POST /topics` - Create new topic
- `GET /topics` - List all topics
- `GET /topics/{id}` - Get topic details
- `DELETE /topics/{id}` - Deactivate topic

### Feeds
- `POST /topics/{topic_id}/feeds` - Add feed to topic
- `GET /topics/{topic_id}/feeds` - List feeds for topic
- `DELETE /feeds/{id}` - Deactivate feed

### Articles
- `GET /topics/{topic_id}/articles?days=7` - Get recent articles for topic
- `GET /articles/{id}` - Get single article with full content

### Reports
- `POST /reports/generate` - Trigger report generation
- `GET /reports` - List generated reports
- `GET /reports/{id}` - Get report content

---

## 7. Scheduled Jobs

### Weekly Report Generation
- **Cron**: `0 8 * * 1` (Monday 8 AM)
- **Action**: 
  1. Extract articles from past 7 days across all active topics
  2. Classify each article for relevance
  3. Generate synthesized report grouped by topic
  4. Deliver via configured channel (email/Slack)

### Daily Feed Health Check (Optional)
- **Cron**: `0 6 * * *`
- **Action**: Verify all feeds are returning content, alert on failures

---

## 8. Configuration

### Environment Variables
```
# API Keys
RSSAPP_API_KEY=
INOREADER_API_KEY=
INOREADER_APP_ID=
GEMINI_API_KEY=

# Database
DATABASE_URL=postgresql://...

# Scheduling
REPORT_DAYS_LOOKBACK=7
REPORT_CRON="0 8 * * 1"

# Delivery
SMTP_HOST=
SLACK_WEBHOOK_URL=
```

---

## 9. Directory Structure

```
regulatory_intelligence/
├── api/
│   ├── __init__.py
│   ├── main.py              # FastAPI app
│   ├── routes/
│   │   ├── topics.py
│   │   ├── feeds.py
│   │   ├── articles.py
│   │   └── reports.py
│   └── dependencies.py
├── clients/
│   ├── __init__.py
│   ├── rss_app.py           # RSS.app API client
│   ├── inoreader.py         # Inoreader API client
│   └── gemini.py            # Gemini LLM client
├── services/
│   ├── __init__.py
│   ├── feed_manager.py
│   ├── article_extractor.py
│   ├── relevance_classifier.py
│   └── report_generator.py
├── schemas/
│   ├── __init__.py
│   ├── topic.py
│   ├── feed.py
│   ├── article.py
│   └── report.py
├── db/
│   ├── __init__.py
│   ├── models.py            # SQLAlchemy models
│   ├── session.py
│   └── migrations/
├── config/
│   ├── __init__.py
│   └── settings.py          # Pydantic Settings
├── jobs/
│   ├── __init__.py
│   └── weekly_report.py     # Scheduled job entrypoint
├── tests/
│   └── ...
├── .env
├── requirements.txt
├── Dockerfile
└── README.md
```