"""
Investigator Agent Core
=======================

Orchestrates LLM-powered investigation of a target website to discover
available ingestion methods.

Responsibilities:
    - Accept a validated site URL
    - Probe well-known paths (RSS, sitemap, robots.txt) via HTTP
    - Parse homepage HTML <link> tags for RSS autodiscovery
    - Delegate deep, autonomous analysis to GPT Researcher
    - Parse the research report into a structured result via Circuit
    - Merge deterministic probe results with the agent's findings
    - Pass the merged result to strategy_selector for waterfall decision

Tools:
    - GPT Researcher (``gpt-researcher`` package) — autonomous web
      research agent that browses the site and writes a report.
    - Circuit API (firm's enterprise LLM gateway) via LangChain's
      ``AzureChatOpenAI`` + ``with_structured_output`` for the final
      parse into a Pydantic ``SiteInvestigationResult``.  See
      ``circuit_scrapegraph_example.py`` for the Circuit auth pattern.
    - httpx for lightweight HTTP probing.

Input:
    - url (str): The target website URL to investigate

Output:
    - SiteInvestigationResult (schemas.investigation) — raw findings
    - StrategyDecision       (schemas.investigation) — final waterfall pick

Notes:
    - Investigation should respect robots.txt and rate limits.
    - If the LLM fails or returns incomplete results, the agent
      logs the failure and defaults to ScrapeGraphAI with low confidence.
"""

from __future__ import annotations

import asyncio
import json
import re
from urllib.parse import urljoin, urlparse

import httpx
from pydantic import BaseModel, Field

from agents.investigator.prompts import (
    FALLBACK_RESEARCH_QUERY_TEMPLATE,
    INVESTIGATION_PROMPT,
    RESEARCH_QUERY_TEMPLATE,
)
from agents.investigator.strategy_selector import select_strategy
from agents.llm_client import configure_gpt_researcher_env, get_circuit_llm
from config.logging_config import get_logger
from config.settings import settings
from schemas.investigation import (
    RSSFeedInfo,
    SitemapInfo,
    SiteInvestigationResult,
    StrategyDecision,
)
from schemas.site import StrategyEnum

logger = get_logger(__name__)

# ── Well-known paths probed before the LLM call ─────────────────────────

_RSS_CANDIDATES = [
    "/feed",
    "/rss",
    "/rss.xml",
    "/atom.xml",
    "/feeds",
    "/feed.xml",
    # Common CMS section feeds (Drupal, WordPress, etc.) — only meaningful
    # when probed at the site root, but cheap to try against any base.
    "/blog/feed",
    "/news/feed",
    "/events/feed",
    "/press-releases/feed",
    "/newsroom/feed",
    "/updates/feed",
]
_SITEMAP_CANDIDATES = ["/sitemap.xml", "/sitemap_index.xml"]
_PROBE_TIMEOUT = 10  # seconds per request


# ── GPT Researcher + Circuit structured-output pipeline ─────────────────

async def _run_gpt_researcher(target_url: str, query_template: str) -> str:
    """
    Launch GPT Researcher with *query_template* formatted against
    *target_url* and return its raw research report as markdown/text.

    GPT Researcher browses the web on its own, collects evidence,
    and writes a report.  Its internal LLM calls are routed through
    Circuit via ``configure_gpt_researcher_env()``.
    """
    configure_gpt_researcher_env()
    # Imported lazily so env vars are in place before the package
    # initializes its LLM / embedding providers.
    from gpt_researcher import GPTResearcher

    query = query_template.format(target_url=target_url)
    researcher = GPTResearcher(query=query, report_type="research_report")
    await researcher.conduct_research()
    return await researcher.write_report()


async def _structure_report(
    target_url: str, report: str
) -> SiteInvestigationResult:
    """
    Feed the raw GPT Researcher *report* into Circuit and coerce it
    into a validated ``SiteInvestigationResult`` using LangChain's
    ``with_structured_output``.
    """
    schema_json = SiteInvestigationResult.model_json_schema()
    prompt = INVESTIGATION_PROMPT.format(
        target_url=target_url,
        schema=json.dumps(schema_json, indent=2),
    ) + f"\n\nRESEARCH REPORT:\n{report}\n"

    def _invoke() -> SiteInvestigationResult:
        llm = get_circuit_llm()
        return llm.with_structured_output(SiteInvestigationResult).invoke(prompt)

    return await asyncio.to_thread(_invoke)


async def _investigate_with_llm(
    target_url: str,
    query_template: str = RESEARCH_QUERY_TEMPLATE,
) -> SiteInvestigationResult:
    """
    Run GPT Researcher against *target_url* using *query_template*
    and return a validated ``SiteInvestigationResult`` parsed from
    its report.
    """
    report = await asyncio.wait_for(
        _run_gpt_researcher(target_url, query_template),
        timeout=settings.investigation_timeout_seconds,
    )
    return await _structure_report(target_url, report)


# ── Lightweight HTTP probing ─────────────────────────────────────────────

def _probe_bases(base_url: str) -> list[str]:
    """
    Return the list of base URLs to probe well-known paths against.

    Always includes the input URL (with any trailing slash stripped)
    so path-relative feeds like ``.../section/feed`` are still tried.
    Additionally includes the site root (``scheme://netloc``) so that
    when the input URL is a deep path — e.g. a SPA results page —
    we still discover site-wide feeds like ``/blog/feed`` hosted at
    the domain root.  Duplicates are removed while preserving order.
    """
    parsed = urlparse(base_url)
    bases: list[str] = [base_url.rstrip("/")]
    if parsed.scheme and parsed.netloc:
        root = f"{parsed.scheme}://{parsed.netloc}"
        if root not in bases:
            bases.append(root)
    return bases


async def _probe_rss(base_url: str) -> list[RSSFeedInfo]:
    """Try common RSS/Atom feed paths and return any that respond with XML."""
    found: list[RSSFeedInfo] = []
    seen: set[str] = set()
    async with httpx.AsyncClient(
        timeout=_PROBE_TIMEOUT,
        follow_redirects=True,
        headers={"User-Agent": "RegulatoryIntelBot/1.0"},
    ) as client:
        for base in _probe_bases(base_url):
            for path in _RSS_CANDIDATES:
                url = f"{base}{path}"
                if url in seen:
                    continue
                seen.add(url)
                try:
                    resp = await client.get(url)
                    ct = resp.headers.get("content-type", "")
                    if resp.status_code == 200 and any(
                        t in ct for t in ("xml", "rss", "atom")
                    ):
                        found.append(RSSFeedInfo(url=url, is_active=True))
                        logger.info("Probed RSS candidate: %s", url, extra={"url": url})
                except Exception:
                    continue
    return found


async def _probe_sitemaps(base_url: str) -> list[SitemapInfo]:
    """Try common sitemap paths and check robots.txt for Sitemap directives."""
    found: list[SitemapInfo] = []
    seen: set[str] = set()
    async with httpx.AsyncClient(
        timeout=_PROBE_TIMEOUT,
        follow_redirects=True,
        headers={"User-Agent": "RegulatoryIntelBot/1.0"},
    ) as client:
        for base in _probe_bases(base_url):
            # Check robots.txt for Sitemap directives.
            robots_url = f"{base}/robots.txt"
            if robots_url not in seen:
                seen.add(robots_url)
                try:
                    resp = await client.get(robots_url)
                    if resp.status_code == 200:
                        for line in resp.text.splitlines():
                            if line.lower().startswith("sitemap:"):
                                sm_url = line.split(":", 1)[1].strip()
                                if not any(s.url == sm_url for s in found):
                                    found.append(SitemapInfo(url=sm_url))
                                    logger.info(
                                        "Robots.txt sitemap: %s", sm_url,
                                        extra={"url": sm_url},
                                    )
                except Exception:
                    pass

            # Probe well-known sitemap paths.
            for path in _SITEMAP_CANDIDATES:
                url = f"{base}{path}"
                if url in seen or any(s.url == url for s in found):
                    continue
                seen.add(url)
                try:
                    resp = await client.get(url)
                    ct = resp.headers.get("content-type", "")
                    if resp.status_code == 200 and "xml" in ct:
                        stype = "index" if "sitemapindex" in resp.text[:500].lower() else "standard"
                        found.append(SitemapInfo(url=url, type=stype))
                        logger.info("Probed sitemap candidate: %s", url, extra={"url": url})
                except Exception:
                    continue
    return found


async def _probe_html_head(base_url: str) -> list[RSSFeedInfo]:
    """
    Fetch the homepage and look for <link rel="alternate"
    type="application/rss+xml"> tags advertising feeds.
    """
    feeds: list[RSSFeedInfo] = []
    try:
        async with httpx.AsyncClient(
            timeout=_PROBE_TIMEOUT,
            follow_redirects=True,
            headers={"User-Agent": "RegulatoryIntelBot/1.0"},
        ) as client:
            resp = await client.get(base_url)
            if resp.status_code != 200:
                return feeds
        pattern = re.compile(
            r'<link[^>]+type=["\']application/(rss|atom)\+xml["\'][^>]*href=["\']([^"\']+)["\']',
            re.IGNORECASE,
        )
        for match in pattern.finditer(resp.text):
            href = match.group(2)
            if not href.startswith("http"):
                href = base_url.rstrip("/") + "/" + href.lstrip("/")
            feeds.append(RSSFeedInfo(url=href, is_active=True))
            logger.info("HTML <link> feed: %s", href, extra={"url": href})
    except Exception:
        pass
    return feeds


# ── Off-domain mirror discovery via robots.txt ───────────────────────────
# For targets whose authoritative RSS / sitemap lives on an aggregator
# (govinfo.gov, data.europa.eu, the agency's parent department, etc.),
# those aggregators typically:
#   - expose the full list of sitemap XMLs via `Sitemap:` directives
#     in /robots.txt
#   - expose RSS feeds at a predictable /rss/{collection_code}.xml
#     pattern (govinfo), /feed/{code}.xml, or similar
# This deterministic step runs after the fallback LLM pass, mines
# /robots.txt on every off-domain host the LLM surfaced, and asks
# the LLM to pick the ones that actually cover the target's content.


class _MirrorSelection(BaseModel):
    """Structured output for the off-domain mirror picker."""

    sitemap_urls: list[str] = Field(default_factory=list)
    rss_urls: list[str] = Field(default_factory=list)


# Govinfo and similar aggregators embed a collection code in their
# sitemap URLs.  Extracting it lets us synthesize the matching RSS URL.
_SITEMAP_CODE_PATTERNS = [
    re.compile(r"/sitemap/([A-Z][A-Z0-9]+)_sitemap_index\.xml$"),
    re.compile(r"/sitemap/bulkdata/([A-Z][A-Z0-9]+)/sitemapindex\.xml$"),
]

_OFFDOMAIN_PICKER_PROMPT = """\
The target website is {target_url}.  Below are candidate \
machine-readable data source URLs that were discovered on mirror / \
aggregator sites (for example govinfo.gov hosts content for many US \
federal publications, keyed by a short collection code).

Your job: select ONLY the URLs whose content covers the target \
website's publications.  Skip URLs for unrelated collections.

Worked example: for target https://www.federalregister.gov/documents/current, \
the correct picks from GovInfo include URLs whose path contains the \
"FR" collection code — e.g. \
https://www.govinfo.gov/sitemap/FR_sitemap_index.xml and \
https://www.govinfo.gov/rss/fr.xml.  URLs for unrelated collections \
(BILLS, CFR, CREC, PLAW, etc.) must be skipped.

Candidate sitemap URLs:
{sitemap_candidates}

Candidate RSS/Atom feed URLs:
{rss_candidates}

Return JSON with the selected URLs.  Return empty lists if nothing \
is clearly relevant to {target_url}.
"""


def _looks_like_feed(body: str) -> bool:
    """Return True if *body* starts with an RSS or Atom document."""
    head = body.lstrip()[:400].lower()
    return "<rss" in head or "<feed" in head


async def _discover_offdomain_mirrors(
    target_url: str,
    candidate_hosts: set[str],
) -> tuple[list[SitemapInfo], list[RSSFeedInfo]]:
    """
    Mine off-domain aggregators' /robots.txt for sitemap and RSS
    candidates, then ask the LLM which ones cover *target_url*.
    """
    if not candidate_hosts:
        return [], []

    sitemap_candidates: list[str] = []
    rss_candidates: list[str] = []

    async with httpx.AsyncClient(
        timeout=_PROBE_TIMEOUT,
        follow_redirects=True,
        headers={"User-Agent": "RegulatoryIntelBot/1.0"},
    ) as client:
        for host in sorted(candidate_hosts):
            try:
                resp = await client.get(f"https://{host}/robots.txt")
            except Exception as exc:
                logger.debug("robots.txt fetch failed for %s: %s", host, exc)
                continue
            if resp.status_code != 200:
                continue

            host_sitemaps: list[str] = []
            host_codes: set[str] = set()
            for line in resp.text.splitlines():
                if not line.lower().startswith("sitemap:"):
                    continue
                sm_url = line.split(":", 1)[1].strip()
                if not sm_url:
                    continue
                host_sitemaps.append(sm_url)
                for pat in _SITEMAP_CODE_PATTERNS:
                    m = pat.search(sm_url)
                    if m:
                        host_codes.add(m.group(1))
                        break
            sitemap_candidates.extend(host_sitemaps)

            # Synthesize and verify RSS feed URLs from collection codes.
            for code in host_codes:
                rss_url = f"https://{host}/rss/{code.lower()}.xml"
                try:
                    rresp = await client.get(rss_url)
                except Exception:
                    continue
                ct = rresp.headers.get("content-type", "").lower()
                if (
                    rresp.status_code == 200
                    and any(t in ct for t in ("xml", "rss", "atom"))
                    and _looks_like_feed(rresp.text)
                ):
                    rss_candidates.append(rss_url)

            logger.info(
                "Off-domain mirror candidates from %s: %d sitemaps, %d feeds",
                host, len(host_sitemaps), len(host_codes),
                extra={"url": f"https://{host}"},
            )

    if not sitemap_candidates and not rss_candidates:
        return [], []

    prompt = _OFFDOMAIN_PICKER_PROMPT.format(
        target_url=target_url,
        sitemap_candidates="\n".join(f"- {u}" for u in sitemap_candidates) or "(none)",
        rss_candidates="\n".join(f"- {u}" for u in rss_candidates) or "(none)",
    )

    def _invoke() -> _MirrorSelection:
        llm = get_circuit_llm()
        return llm.with_structured_output(_MirrorSelection).invoke(prompt)

    try:
        selection = await asyncio.to_thread(_invoke)
    except Exception as exc:
        logger.warning(
            "Off-domain mirror picker failed: %s — skipping",
            exc, extra={"url": target_url},
        )
        return [], []

    chosen_sitemaps = [
        SitemapInfo(url=u) for u in selection.sitemap_urls
        if u in sitemap_candidates
    ]
    chosen_rss = [
        RSSFeedInfo(url=u, is_active=True) for u in selection.rss_urls
        if u in rss_candidates
    ]
    logger.info(
        "Off-domain picker selected %d sitemap(s), %d feed(s) for %s",
        len(chosen_sitemaps), len(chosen_rss), target_url,
        extra={"url": target_url},
    )
    return chosen_sitemaps, chosen_rss


# ── Main investigation entry point ───────────────────────────────────────

async def investigate(url: str) -> tuple[SiteInvestigationResult, StrategyDecision]:
    """
    Run the full investigation workflow for *url*:

    1. Probe well-known RSS and sitemap paths via HTTP.
    2. Parse the homepage HTML head for <link> feed tags.
    3. Run GPT Researcher for autonomous deep analysis of the site.
    4. Parse its report into a SiteInvestigationResult via Circuit.
    5. If no active RSS feed and no sitemap were found, run a second
       GPT Researcher pass focused on off-domain aggregators / mirrors
       (govinfo, data.gov, parent agency sites, etc.) and merge.
    6. Merge probe results with the agent's discoveries.
    7. Run the strategy-selector waterfall.

    Returns the raw investigation result and the final strategy decision.
    """
    logger.info("Starting investigation for %s", url, extra={"url": url})

    # ── Phase 1: deterministic HTTP probes ────────────────────────────────
    probed_rss = await _probe_rss(url)
    html_rss = await _probe_html_head(url)
    probed_sitemaps = await _probe_sitemaps(url)

    # Deduplicate RSS feeds by URL.
    seen_urls: set[str] = set()
    all_rss: list[RSSFeedInfo] = []
    for feed in probed_rss + html_rss:
        if feed.url not in seen_urls:
            seen_urls.add(feed.url)
            all_rss.append(feed)

    # ── Phase 2: autonomous research via GPT Researcher ──────────────────
    llm_result: SiteInvestigationResult | None = None
    try:
        llm_result = await _investigate_with_llm(url)
        logger.info("GPT Researcher investigation completed", extra={"url": url})
    except Exception as exc:
        logger.warning(
            "GPT Researcher investigation failed, relying on probe results: %s",
            exc,
            extra={"url": url},
        )

    # ── Phase 3: merge LLM findings with probe results ───────────────────
    # LLMs routinely return bare paths (e.g. "sitemap.xml", "/feed") or
    # protocol-less hosts ("www.example.com/x").  Normalize everything
    # against the target URL so the strategy selector sees valid HTTP
    # URLs, and drop anything that still can't be made absolute.
    def _absolutize(raw: str) -> str | None:
        if not raw:
            return None
        candidate = raw.strip()
        if candidate.startswith(("http://", "https://")):
            return candidate
        if candidate.startswith("//"):
            return "https:" + candidate
        # Bare host like "www.example.com/path" — assume https.
        if "/" not in candidate and "." in candidate:
            return f"https://{candidate}"
        # Relative path.
        return urljoin(url, candidate if candidate.startswith("/") else f"/{candidate}")

    content_paths: list[str] = []
    notes_parts: list[str] = []
    llm_recommendations: list[tuple[StrategyEnum, float]] = []

    def _merge(result: SiteInvestigationResult, note_prefix: str = "") -> None:
        for feed in result.rss_feeds:
            norm = _absolutize(feed.url)
            if not norm or norm in seen_urls:
                continue
            seen_urls.add(norm)
            all_rss.append(feed.model_copy(update={"url": norm}))
        existing_sm = {s.url for s in probed_sitemaps}
        for smap in result.sitemaps:
            norm = _absolutize(smap.url)
            if not norm or norm in existing_sm:
                continue
            existing_sm.add(norm)
            probed_sitemaps.append(smap.model_copy(update={"url": norm}))
        for path in result.content_paths or []:
            norm = _absolutize(path)
            if norm and norm not in content_paths:
                content_paths.append(norm)
        if result.notes:
            notes_parts.append(f"{note_prefix}{result.notes}" if note_prefix else result.notes)
        llm_recommendations.append((result.recommended_strategy, result.confidence))

    if llm_result:
        _merge(llm_result)
    else:
        notes_parts.append("Pass 1 (on-domain) failed; relying on HTTP probes.")

    # ── Phase 4a: first strategy-selection attempt ───────────────────────
    def _build_investigation() -> SiteInvestigationResult:
        if llm_recommendations:
            best_strategy, best_conf = max(
                (
                    r for r in llm_recommendations
                    if r[0] != StrategyEnum.SCRAPEGRAPHAI
                ),
                default=max(llm_recommendations, key=lambda r: r[1]),
                key=lambda r: r[1],
            )
        else:
            best_strategy, best_conf = StrategyEnum.SCRAPEGRAPHAI, 0.2
        return SiteInvestigationResult(
            rss_feeds=all_rss,
            sitemaps=probed_sitemaps,
            content_paths=content_paths,
            recommended_strategy=best_strategy,
            confidence=best_conf,
            notes=" | ".join(notes_parts) if notes_parts else None,
        )

    investigation = _build_investigation()
    decision = await select_strategy(investigation)

    # ── Phase 4b: if we're about to settle for SCRAPEGRAPHAI, run the
    # cross-domain fallback to double-check for an off-domain feed or
    # sitemap before giving up.  Skip it if we didn't even get pass 1
    # to run (GPT Researcher is dead — fallback will fail too).
    if decision.strategy == StrategyEnum.SCRAPEGRAPHAI and llm_result is not None:
        logger.info(
            "Primary selection is SCRAPEGRAPHAI; running cross-domain "
            "fallback to double-check for an off-domain feed or sitemap",
            extra={"url": url},
        )
        try:
            fallback_result = await _investigate_with_llm(
                url, query_template=FALLBACK_RESEARCH_QUERY_TEMPLATE
            )
            logger.info("Cross-domain fallback completed", extra={"url": url})
            _merge(fallback_result, note_prefix="Cross-domain: ")
            investigation = _build_investigation()
            decision = await select_strategy(investigation)
        except Exception as exc:
            logger.warning(
                "Cross-domain fallback failed: %s", exc, extra={"url": url}
            )

        # ── Phase 4c: robots.txt mining on off-domain aggregators ─────────
        # Run this whenever the fallback surfaced off-domain hosts,
        # regardless of the interim strategy.  The fallback LLM may
        # produce a direct sitemap URL (upgrading the decision from
        # SCRAPEGRAPHAI to SITEMAP) without finding the matching RSS
        # feed, and we always want to upgrade SITEMAP → RSS when the
        # aggregator exposes an RSS feed for the same collection.
        target_host = urlparse(url).netloc
        offdomain_hosts: set[str] = set()
        for candidate in (
            [f.url for f in all_rss]
            + [s.url for s in probed_sitemaps]
            + list(content_paths)
        ):
            host = urlparse(candidate).netloc
            if host and host != target_host:
                offdomain_hosts.add(host)

        if offdomain_hosts:
            logger.info(
                "Mining robots.txt on %d off-domain host(s): %s",
                len(offdomain_hosts),
                ", ".join(sorted(offdomain_hosts)),
                extra={"url": url},
            )
            extra_sm, extra_rss = await _discover_offdomain_mirrors(
                url, offdomain_hosts
            )
            existing_sm = {s.url for s in probed_sitemaps}
            for s in extra_sm:
                if s.url not in existing_sm:
                    existing_sm.add(s.url)
                    probed_sitemaps.append(s)
            for f in extra_rss:
                if f.url not in seen_urls:
                    seen_urls.add(f.url)
                    all_rss.append(f)
            if extra_sm or extra_rss:
                llm_recommendations.append(
                    (
                        StrategyEnum.RSS if extra_rss else StrategyEnum.SITEMAP,
                        0.75,
                    )
                )
                notes_parts.append(
                    f"Off-domain robots.txt mining: +{len(extra_sm)} "
                    f"sitemap(s), +{len(extra_rss)} feed(s)."
                )
                investigation = _build_investigation()
                decision = await select_strategy(investigation)
    if decision.confidence < 0.5:
        logger.warning(
            "Low-confidence strategy (%.2f) for %s — flagging for review",
            decision.confidence,
            url,
            extra={"url": url},
        )

    logger.info(
        "Investigation complete: strategy=%s  confidence=%.2f  target=%s",
        decision.strategy.value,
        decision.confidence,
        decision.target_url,
        extra={"url": url},
    )
    return investigation, decision
