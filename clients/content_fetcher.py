"""Content fetcher with fallback chain for article extraction.

Fallback order:
1. Playwright stealth browser (most stealthy, avoids bot detection)
   -> Populates ArticleItem.full_content
2. GCP Gemini with grounding search (summarize via Google Search)
   -> Populates ArticleItem.ai_summary
"""
from __future__ import annotations

import logging
import os
import re
from typing import Optional, TYPE_CHECKING
from bs4 import BeautifulSoup

if TYPE_CHECKING:
    from clients.inoreader import ArticleItem

logger = logging.getLogger(__name__)


class ContentFetcher:
    """Fetches article content with multiple fallback strategies."""

    def __init__(self):
        self._gemini_client = None

    def fetch_content(self, article: "ArticleItem", use_playwright: bool = True) -> bool:
        """Fetch article content using fallback chain.
        
        Modifies the article in-place:
        - Playwright success -> sets article.full_content
        - Gemini grounding success -> sets article.ai_summary
        
        Args:
            article: ArticleItem to populate
            use_playwright: If True, try Playwright first. If False, skip to Gemini.
            
        Returns:
            True if any method succeeded, False otherwise.
        """
        # Skip if already has content
        if article.full_content:
            logger.info(f"Skipping {article.url} — already has full_content")
            return True

        url = article.url
        title = article.title or ""

        # Method 1: Playwright stealth -> full_content (if enabled)
        if use_playwright:
            logger.info(f"[Fallback 1] Trying Playwright stealth for: {url}")
            content = self._fetch_with_playwright(url)
            if content and len(content.strip()) > 100:
                logger.info(f"[Fallback 1] ✅ Playwright succeeded ({len(content)} chars)")
                article.full_content = content
                return True

        # Method 2: Gemini grounding with search -> ai_summary
        logger.info(f"[{'Fallback 2' if use_playwright else 'Primary'}] Trying Gemini grounding for: {url}")
        content = self._fetch_with_gemini_search(article)
        if content and len(content.strip()) > 100:
            logger.info(f"[Fallback 2] ✅ Gemini grounding succeeded ({len(content)} chars)")
            article.ai_summary = content
            return True

        logger.warning(f"All fallback methods failed for: {url}")
        return False

    def _fetch_with_playwright(self, url: str) -> Optional[str]:
        """Fetch content using Playwright with stealth settings."""
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as e:
            logger.warning(f"Playwright import failed: {e}")
            return None

        try:
            with sync_playwright() as p:
                # Use Chromium (most reliable cross-platform)
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    viewport={"width": 1920, "height": 1080},
                    user_agent=(
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                    java_script_enabled=True,
                )
                
                page = context.new_page()
                
                # Block unnecessary resources for speed
                page.route("**/*.{png,jpg,jpeg,gif,svg,ico,woff,woff2}", 
                          lambda route: route.abort())
                
                page.goto(url, wait_until="networkidle", timeout=30000)
                
                # Wait for content to load
                page.wait_for_timeout(2000)
                
                # Extract main content
                content = self._extract_article_content(page.content())
                
                browser.close()
                return content
                
        except Exception as e:
            logger.warning(f"Playwright failed: {e}")
            return None

    def _fetch_with_gemini_search(self, article: "ArticleItem") -> Optional[str]:
        """Fetch content using Gemini with Google Search grounding."""
        try:
            from google import genai
            from google.genai import types
        except ImportError:
            logger.warning("google-genai not installed")
            return None

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.warning("GEMINI_API_KEY not set")
            return None

        try:
            client = genai.Client(api_key=api_key)

            # Build context from article metadata
            published = article.published_at.strftime("%Y-%m-%d") if article.published_at else "Unknown"
            rss_summary = article.summary or "No summary available"
            
            prompt = f"""Try to find the comprehensive content of this article using the details below:

Headline: {article.title}
URL: {article.url}
Date Published: {published}
Source: {article.source or 'Unknown'}
RSS Summary: {rss_summary}

Please provide the full article content including:
1. All key points and arguments made in the article
2. Important facts, figures, statistics, and quotes
3. Any regulatory implications, deadlines, or action items
4. Context and background information

Be as comprehensive as possible - include all substantive information from the article."""

            response = client.models.generate_content(
                model="gemini-3-flash-preview",
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[types.Tool(google_search=types.GoogleSearch())],
                    temperature=0.1,
                )
            )

            if response.text:
                return response.text
            return None

        except Exception as e:
            logger.warning(f"Gemini grounding failed: {e}")
            return None

    def _extract_article_content(self, html: str) -> Optional[str]:
        """Extract main article text from HTML."""
        soup = BeautifulSoup(html, "html.parser")

        # Remove unwanted elements
        for tag in soup.find_all(["script", "style", "nav", "header", 
                                   "footer", "aside", "iframe", "noscript"]):
            tag.decompose()

        # Try common article containers
        selectors = [
            "article",
            "[role='main']",
            ".article-content",
            ".post-content", 
            ".entry-content",
            ".content-body",
            "#article-body",
            "main",
        ]

        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                text = element.get_text(separator="\n", strip=True)
                if len(text) > 200:
                    return self._clean_text(text)

        # Fallback: get body text
        body = soup.find("body")
        if body:
            text = body.get_text(separator="\n", strip=True)
            return self._clean_text(text)

        return None

    @staticmethod
    def _clean_text(text: str) -> str:
        """Clean extracted text."""
        # Remove excessive whitespace
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r" {2,}", " ", text)
        # Remove common boilerplate patterns
        lines = text.split("\n")
        filtered = [
            line for line in lines 
            if not any(skip in line.lower() for skip in [
                "cookie", "privacy policy", "terms of use",
                "subscribe", "newsletter", "sign up",
                "share this", "follow us", "copyright"
            ])
        ]
        return "\n".join(filtered).strip()


# Convenience function
def fetch_content_with_fallback(article: "ArticleItem", use_playwright: bool = True) -> bool:
    """Fetch article content using fallback chain.
    
    Modifies the article in-place:
    - Playwright success -> sets article.full_content
    - Gemini grounding success -> sets article.ai_summary
    
    Args:
        article: ArticleItem to populate (must have url, optionally title)
        use_playwright: If True, try Playwright first. If False, skip to Gemini.
        
    Returns:
        True if content was fetched, False otherwise.
    """
    fetcher = ContentFetcher()
    return fetcher.fetch_content(article, use_playwright=use_playwright)
