
# Specification: Agentic News Synthesizer 

## 1. System Overview
This web application leverages the Antigravity framework and Gemini to automate the retrieval, summarization, and editorial filtering of recent publications from targeted websites. The system operates autonomously on a defined schedule (defaulting to weekly) while providing a conversational UI for users to dynamically adjust their extraction preferences, target URLs, and editorial guidelines.

## 2. Infrastructure & GCP Architecture
The application is designed for serverless scalability on Google Cloud Platform, utilizing tools well-suited for data-intensive workflows and seamless model integration.

* **Frontend & Authentication:** * **Firebase Authentication:** Manages user identity and secure login access.
    * **Cloud Run:** Hosts the web interface (e.g., Streamlit, Next.js, or React) where users view reports and chat with the configuration agent.
* **Orchestration & Scheduling:**
    * **Cloud Scheduler:** Triggers the automated workflow based on the user's defined cron expression (default: `0 8 * * 1` for Monday mornings).
    * **Pub/Sub:** Decouples the scheduling trigger from the agent execution, ensuring reliable delivery and enabling robust retry mechanisms.
* **Compute & AI Integration:**
    * **Cloud Run (Agent Execution):** Hosts the Antigravity multi-agent backend. Containerizing the agents ensures consistent execution environments for routing and processing.
    * **Vertex AI (Gemini API):** Powers the reasoning, summarization, and editorial capabilities of the agents, utilizing Gemini 3.1 Pro for complex orchestration/editing and Gemini Flash for rapid extraction.
* **Data Storage:**
    * **Firestore:** Stores user profiles, natural language configuration states, scheduling metadata, and target website lists.
    * **BigQuery:** Archives raw extracted text and final news reports, allowing for historical trend analysis or future custom model tuning.


```text
===================================================================================================
                                MULTI-STRATEGY PIPELINE ARCHITECTURE                               
===================================================================================================

[ 🖥️ FRONTEND CLIENT ] --- POST /onboard {url, topic} ---> [ FastAPI Router ]
                                                                 |
+----------------------------------------------------------------|--------------------------------+
| [ PHASE 1: THE ONBOARDING ENGINE ]                             v                                |
|                                                    +-------------------------+                  |
|                                                    | FrontendController      |                  |
|                                                    +-------------------------+                  |
|                                                                | (Background Task)              |
|                                                                v                                |
|  +-----------------------------------+             +-------------------------+                  |
|  | LangGraph State (Dict)            | <---------- | SiteResearchAgent       |                  |
|  | - Tracks tool outputs & errors    |             | (Agentic Harness)       |                  |
|  +-----------------------------------+             +-------------------------+                  |
|                                                                | (Yields JSON)                  |
|                                                                v                                |
|                                                    +-------------------------+                  |
|                                                    | <<Pydantic>> SiteConfig |                  |
|                                                    +-------------------------+                  |
+----------------------------------------------------------------|--------------------------------+
                                                                 v
===================================================================================================
  [ 🗄️ LOCAL POSTGRESQL DATABASE ]  <-- Stores: SiteConfigs, Document Metadata, Run Logs
===================================================================================================
                                                                 |
+----------------------------------------------------------------|--------------------------------+
| [ PHASE 2: DETERMINISTIC EXECUTION ]                           | (Cron triggers Daily)          |
|                                                                v                                |
|                                                    +-------------------------+                  |
|                                                    | DailyPipelineExecutor   |                  |
|                                                    +-------------------------+                  |
|                                                                | (Instantiates via Factory)     |
|                                                                v                                |
|                                                    +-------------------------+                  |
|  +-------------------------+                       | <<Base>>                |                  |
|  | Crawl4AI / Playwright   | <=== (Uses) ========= | ExtractionStrategy      |                  |
|  | (Headless Browser)      |                       | - constructor(config)   |                  |
|  +-------------------------+                       +-------------------------+                  |
|                                                                ^                                |
|                        [Inherits Blueprint]--------------------+-----------------------+        |
|                        |                   |                   |                       |        |
|            +-------------------+ +-------------------+ +-------------------+ +-------------------+|
|            | ApiStrategy       | | RssStrategy       | | SitemapStrategy   | | IndexStrategy     ||
|            +-------------------+ +-------------------+ +-------------------+ +-------------------+|
|                        |                   |                   |                       |        |
|                        +-------------------+-------------------+-----------------------+        |
|                                                                | (Returns)                      |
|                                                                v                                |
|                                                    +-------------------------+                  |
|                                                    | <<Pydantic>> Document   |                  |
|                                                    +-------------------------+                  |
+----------------------------------------------------------------|--------------------------------+
                                                                 |
+----------------------------------------------------------------|--------------------------------+
| [ PHASE 3: EVALUATION & SYNTHESIS ]                            v                                |
|                                                    +-------------------------+                  |
|  +-------------------------+                       | RelevanceClassifier     |                  |
|  | GEMINI LLM API          | <=== (Prompts) ====== +-------------------------+                  |
|  |                         |                                   | (Filters out noise)            |
|  +-------------------------+                                   v                                |
|                                                    +-------------------------+                  |
|                                                    | WeeklyReportSynthesizer |                  |
|                                                    +-------------------------+                  |
|                                                                | (Formats & Emails)             |
|                                                                v                                |
|                                                     [ 📩 LEGAL DEPARTMENT ]                     |
+-------------------------------------------------------------------------------------------------+
```

### 1. Data Objects & Persistence Strategy
We use Pydantic Models mapped to a PostgreSQL Database via SQLAlchemy. Postgres is ideal here because its JSONB column type allows us to store the highly variable `SiteConfig.parameters` without altering the database schema every time a new API requires a weird header.

**SiteConfig (Pydantic Model -> Postgres Table `site_configs`)**
* **Structure:** `id` (UUID), `domain_url` (String), `strategy_type` (Enum: API, RSS, SITEMAP, INDEX), `target_endpoint` (String), `parameters` (JSONB - e.g., auth headers, specific HTML tags to avoid), `is_active` (Boolean).
* **Usage:** Defines the exact, deterministic rules for how to scrape a specific domain. Saved to the database by the Onboarding Engine, and read daily by the Execution Engine.

**Document (Pydantic Model -> Postgres Table `extracted_documents`)**
* **Structure:** `document_id` (UUID), `site_id` (Foreign Key), `title` (String), `source_url` (String, UNIQUE constraint to prevent duplicates), `published_date` (DateTime), `raw_markdown` (Text), `is_relevant` (Boolean).
* **Usage:** The standardized container for an article. Saving this to the DB allows your legal team to search historical data, not just read the weekly report.

---

### 2. The Agentic Harness (LangGraph)
For the `SiteResearchAgent`, you should use LangGraph. It defines the agent's workflow as a state machine, which is critical for web research because it allows you to set a hard limit on loops (e.g., "If you don't find the API in 5 turns, fail gracefully").

**Tools provided to the Agent:**
* **PlaywrightTool (via Crawl4AI):** Allows the agent to read web pages and bypass government firewalls.
* **GoogleSearchTool (Tavily or Serper API):** Allows the agent to search "Federal Register developer API documentation".
* **PythonREPLTool:** Crucial. Allows the agent to write a quick Python script to test the API or RSS feed it just found to verify it actually returns data before it finalizes the `SiteConfig`.

---

### 3. Class Specifications

#### Phase 1: The Onboarding Engine

**FrontendController**
* **Constructor Needs:** `db_session` (SQLAlchemy Session), `agent_runner` (Instance of LangGraph application).
* **Description:** This class acts as the API router for your user interface. It receives a new domain from the user, immediately creates a "pending" database entry, and offloads the heavy lifting to the background agent. It returns a 202 Accepted status to the UI so the user isn't waiting 3 minutes for a response.
* **Called by:** FastApi/Flask router when the frontend clicks "Add Site".

**SiteResearchAgent**
* **Constructor Needs:** `llm_client` (Connection to your local M3 reasoning model, like Llama-3-70b-Instruct), `tools` (List of the LangGraph tools defined above).
* **Description:** This stateful agent executes the "Waterfall" discovery logic. It uses search and Playwright to locate APIs or feeds, uses the Python REPL to test if they work, and outputs a strict JSON representation of the `SiteConfig`. If it fails, it flags the domain for human intervention.
* **Called by:** `FrontendController` (via an asynchronous background task).

#### Phase 2: Deterministic Execution

**DailyPipelineExecutor**
* **Constructor Needs:** `db_session` (SQLAlchemy Session), `strategy_factory` (A factory class to instantiate strategies).
* **Description:** This is the orchestrator of the daily run. It queries the database for all active `SiteConfig`s, loops through them, and uses the factory to spin up the correct extraction class. It collects all the returned `Document`s and passes them to the evaluation phase.
* **Called by:** A system Cron job, Airflow, or Celery beat schedule.

**ExtractionStrategy (Abstract Base Class)**
* **Constructor Needs:** `config` (A specific `SiteConfig` Pydantic object).
* **Description:** This abstract class enforces a strict contract for all scraping methods, ensuring they all possess a `execute()` method. It takes the configuration data (like endpoints and parameters) so its child classes know exactly where to go.
* **Called by:** Never called directly; instantiated by the `strategy_factory` inside `DailyPipelineExecutor`.

**ApiStrategy / RssStrategy / SitemapStrategy / IndexStrategy (Child Classes)**
* **Constructor Needs:** Inherits `config` from the base class; `crawler` (An instance of Crawl4AI's `AsyncWebCrawler`, passed in if the strategy requires web navigation).
* **Description:** These concrete classes implement the actual data gathering logic. `ApiStrategy` executes HTTP requests and parses JSON, while `IndexStrategy` uses Crawl4AI to pull DOM links and extract markdown. They all convert their raw findings into standardized `Document` objects.
* **Called by:** Instantiated dynamically by the `DailyPipelineExecutor` based on the `strategy_type` enum in the config.

#### Phase 3: Evaluation & Synthesis

**RelevanceClassifier**
* **Constructor Needs:** `local_llm_client` (Connection to your M3 inference server), `legal_topics` (List of strings defining the firm's priorities).
* **Description:** This class acts as the filter. It takes the `raw_markdown` from each `Document` and prompts the local LLM to classify it as relevant or irrelevant based on the firm's specific legal topics. It updates the `is_relevant` boolean in the database for each document.
* **Called by:** `DailyPipelineExecutor` immediately after the extraction phase completes.

**WeeklyReportSynthesizer**
* **Constructor Needs:** `db_session` (SQLAlchemy Session), `email_client` or `slack_webhook` (Integration for delivery).
* **Description:** This class queries the database for all `Document`s from the past 7 days where `is_relevant == True`. It groups them by topic, uses the LLM to generate a brief executive summary for each topic, and formats the final report for distribution.
* **Called by:** A separate weekly Cron job (e.g., every Friday at 8:00 AM).