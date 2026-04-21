"""
Investigator Prompts
====================

Prompt templates for the site investigation agent.

Prompts:
    RESEARCH_QUERY_TEMPLATE
        - Natural-language query handed to GPT Researcher so it can
          autonomously investigate the target website and produce
          a research report.

    FALLBACK_RESEARCH_QUERY_TEMPLATE
        - Second-pass query used when the primary research pass
          returns no active RSS feed and no usable sitemap.  It
          steers the agent toward *off-domain* aggregators,
          mirrors, and bulk-data portals that may publish the
          target's content on its behalf.

    INVESTIGATION_PROMPT
        - Parses the GPT Researcher report into a JSON object
          matching ``SiteInvestigationResult`` via Circuit's
          ``with_structured_output``.

    STRATEGY_VALIDATION_PROMPT
        - Used to verify a discovered RSS feed or sitemap is actually
          valid and active (not stale or empty)

Template Variables:
    {target_url}  - The website URL being investigated
    {schema}      - JSON schema of SiteInvestigationResult for output formatting

Notes:
    - Prompts should be version-controlled. Changes to prompts can
      significantly affect investigation quality.
    - Keep prompts focused and specific — vague instructions lead to
      inconsistent results from GPT Researcher.
"""

RESEARCH_QUERY_TEMPLATE = """\
Investigate the regulatory / government website at {target_url} and \
identify the best machine-readable data sources ON THIS DOMAIN for \
monitoring its new publications.  (A separate follow-up pass handles \
cross-domain mirrors if this pass finds nothing usable, so focus \
here on what {target_url} itself publishes.)

Specifically, find and document:
  1. RSS or Atom feeds on {target_url}.  Try these patterns:
       - /feed, /rss, /rss.xml, /atom.xml, /feeds, /feed.xml
       - Appending .rss or .atom to the current listing URL \
         (e.g., {target_url}.rss, {target_url}.atom) — common for \
         Rails/Sinatra sites.
       - <link rel="alternate" type="application/rss+xml"> tags in \
         the HTML <head> of the homepage and of listing pages.
     For each feed, note the URL, what it contains, and whether it \
     appears active (entries within the last 90 days).
  2. XML sitemaps on {target_url}.  Try:
       - /sitemap.xml, /sitemap_index.xml
       - Any `Sitemap:` directives inside /robots.txt (these are \
         authoritative — follow them).
     Classify each sitemap as "standard" or "index" and estimate the \
     number of URLs.
  3. The main content listing pages where new rules, notices, or \
     press releases are published (e.g., /news, /updates, /rules, \
     /press-releases).  These are fallback targets for LLM-driven \
     scraping.

Important: a URL counts as an RSS feed or sitemap only if it \
directly returns RSS/Atom/sitemap XML.  Do NOT classify help pages, \
documentation pages, or HTML listings as feeds or sitemaps.

Report every URL you find with enough detail that an engineer could \
subscribe to or crawl it directly.  Finish by recommending the best \
ingestion strategy (RSS, sitemap, or fallback scraping) for this \
site, and explain your reasoning.
"""


FALLBACK_RESEARCH_QUERY_TEMPLATE = """\
The primary investigation of {target_url} did not surface a working \
RSS/Atom feed or a validatable XML sitemap on the target's own \
domain.  Before we give up and resort to LLM-driven HTML scraping, \
double-check whether an authoritative machine-readable source for \
this publication exists ON A DIFFERENT DOMAIN — a mirror, \
aggregator, parent agency, or bulk-data portal.

Worked example.  The Federal Register at federalregister.gov does \
not expose a useful RSS feed or sitemap on its own domain.  Its \
authoritative XML sitemaps live on GovInfo at \
https://www.govinfo.gov/sitemap/ (including per-year files such as \
https://www.govinfo.gov/sitemap/FR_2024_sitemap.xml) and its bulk \
XML at https://www.govinfo.gov/bulkdata/FR.  A researcher who \
stopped at federalregister.gov would miss the real answer — you must \
search beyond the target's own domain.

Do the following, in order:

  Step 1 — Identify the human-readable name and parent agency of \
  {target_url} (e.g. "Federal Register", "Food and Drug \
  Administration", "Environmental Protection Agency").

  Step 2 — Run cross-domain searches.  At minimum, issue each of \
  these queries and scrape the top results:
    - "<publication name>" rss feed
    - "<publication name>" atom feed
    - "<publication name>" sitemap xml
    - site:govinfo.gov "<publication name>"
    - site:govinfo.gov "<publication name>" sitemap
    - site:regulations.gov "<publication name>"
    - site:data.gov "<publication name>"
    - filetype:xml "<publication name>" sitemap
  For non-US publications substitute the relevant aggregator \
  (data.europa.eu, eur-lex.europa.eu, the state's open-data portal, \
  etc.).

  Step 3 — Follow through to concrete XML endpoints.  A help page, \
  documentation page, or landing page on an aggregator is a lead, \
  not an answer.  Read its HTML and extract the actual RSS, Atom, or \
  sitemap XML URL it points to.

Also consider:
  - Parent-agency or sister-agency sites whose feed or sitemap \
    indirectly covers the target.
  - Commercial or nonprofit regulatory trackers that syndicate the \
    content and expose RSS / JSON / sitemap endpoints.
  - Archive or mirror services (Internet Archive scheduled \
    snapshots, academic repositories).

For every alternate source, record the full URL (a direct XML/feed \
endpoint, not a landing page), what it contains, how often it \
updates, and the target-to-mirror relationship.  Recommend the \
single best ingestion URL for monitoring {target_url}.
"""


INVESTIGATION_PROMPT = """\
You are a web-infrastructure analyst.  You will be given a research \
report produced by an autonomous web-research agent about the site \
{target_url}.  Your job is to extract that report's findings into a \
strict JSON object that matches the schema below.

Target schema:

```json
{schema}
```

Extraction rules:
- ``rss_feeds``: only include URLs that DIRECTLY SERVE RSS or Atom \
  XML.  Do NOT include help pages, documentation pages, news-listing \
  HTML pages, or robots.txt.  Feeds hosted on a DIFFERENT domain \
  than {target_url} (for example govinfo.gov for a federalregister.gov \
  target) ARE valid and must be included.  Set ``is_active`` to true \
  only if the report indicates entries within the last 90 days.
- ``sitemaps``: only include URLs that DIRECTLY SERVE sitemap XML \
  (i.e. a document whose root element is ``<urlset>`` or \
  ``<sitemapindex>``).  Do NOT include robots.txt, help pages, or \
  landing pages that merely describe a sitemap.  Off-domain sitemaps \
  (e.g. on govinfo.gov, data.gov, data.europa.eu) ARE valid.  \
  Classify ``type`` as ``"index"`` or ``"standard"``.
- ``content_paths``: main listing pages (news, rules, press \
  releases, search pages) useful for LLM scraping.  Help pages, \
  documentation pages, and landing pages that were mistakenly \
  surfaced as feeds or sitemaps belong here, not in rss_feeds or \
  sitemaps.
- ``recommended_strategy``:
    - ``"RSS"`` if any valid, active feed was found (on- or off-domain)
    - otherwise ``"SITEMAP"`` if any valid sitemap XML was found \
      (on- or off-domain)
    - otherwise ``"SCRAPEGRAPHAI"``
- ``confidence``: 0.0-1.0 based on how reliable the recommended \
  source looks for ongoing ingestion.
- ``notes``: 1-3 sentence summary.  If the recommended source lives \
  on a mirror / aggregator domain rather than {target_url} itself, \
  state that explicitly (e.g. "Primary sitemap is published on \
  govinfo.gov rather than federalregister.gov").
- Do not invent URLs that are not present in the report.
"""

STRATEGY_VALIDATION_PROMPT = """\
You are validating a data source discovered during site investigation.

Source type: {source_type}
Source URL:  {source_url}

Content sample (first 2000 chars):
{content_sample}

Answer these questions in JSON:
{{
  "is_valid": true/false,
  "has_recent_entries": true/false,
  "most_recent_date": "ISO-8601 date or null",
  "entry_count_estimate": integer,
  "issues": ["list of any problems found"]
}}

Rules:
- is_valid: the content is well-formed XML/RSS/Atom and contains entries.
- has_recent_entries: at least one entry has a date within the last 90 days.
- Return ONLY the JSON object, no other text.
"""
