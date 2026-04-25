"""
API clients for external services.

- RssAppClient: Generate RSS feeds from website URLs
- InoreaderClient: Feed aggregation and article extraction  
- InoreaderAuthManager: OAuth2 token management for Inoreader
- GeminiClient: LLM for relevance classification and summarization (requires google-generativeai)
"""

from .rss_app import RssAppClient
from .inoreader import InoreaderClient, InoreaderAuthManager

# GeminiClient is optional - only import if google-generativeai is installed
try:
    from .gemini import GeminiClient
    __all__ = ["RssAppClient", "InoreaderClient", "InoreaderAuthManager", "GeminiClient"]
except ImportError:
    __all__ = ["RssAppClient", "InoreaderClient", "InoreaderAuthManager"]
