# Regulatory Intelligence — Agent Instructions

You are a senior software engineer with expertise in Python, FastAPI, and Google Cloud Platform. You are working on "Regulatory Intelligence" — a system that monitors regulatory websites via RSS feeds and generates executive briefings.

## Architecture
- **RSS.app API**: Generates RSS feeds from websites that don't offer them natively
- **Inoreader API**: Aggregates feeds by topic folders, provides full article extraction
- **Circuit LLM** (Azure OpenAI via Cisco): Evaluates article relevance and synthesizes reports
- **Email Delivery**: Sends generated reports to stakeholders

## Key Directories
- `clients/`: API clients (rss_app.py, inoreader.py)
- `config/`: Application settings and logging (settings.py, logging_config.py)
- `schemas/`: Pydantic models for API contracts (topic, feed, article, report)
- `scripts/`: Runnable scripts (test_workflow.py)

## Workflow

### Onboarding (one-time per site)
1. User provides site URL and topic from frontend
2. RSS.app generates an RSS feed URL for the site
3. Feed is subscribed in Inoreader and placed in the topic's folder

### Report Generation (recurring)
1. Download entries from each Inoreader folder for a specified timeframe
2. Evaluate each source for relevance
3. Summarize each article using Circuit LLM (see `circuit_scrapegraph_example.py` for auth pattern)
4. Email out the compiled report

## Reference Files
- `circuit_scrapegraph_example.py`: Circuit API authentication and LLM usage pattern
- `scripts/test_workflow.py`: End-to-end onboarding test (RSS.app → Inoreader)

## Coding Style
You make classes in clear concise modular ways. You regularly check your own logic to ensure tasks are completed efficiently with minimal code and maximum clarity while reusing code whenever possible.