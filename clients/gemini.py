"""Gemini LLM client for relevance classification and summarization."""

from dataclasses import dataclass
from typing import Optional
import google.generativeai as genai


@dataclass
class ClassificationResult:
    is_relevant: bool
    reasoning: str
    confidence: float


class GeminiClient:
    """Client for Google Gemini API.
    
    Used for article relevance classification and report summarization.
    """
    
    def __init__(self, api_key: str, model: str = "gemini-1.5-flash"):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model)
    
    async def classify_relevance(
        self,
        article_content: str,
        topic_name: str,
        topic_criteria: list[str]
    ) -> ClassificationResult:
        """Classify whether an article is relevant to a topic.
        
        Args:
            article_content: The article text to classify.
            topic_name: Name of the topic.
            topic_criteria: List of criteria that define relevance.
            
        Returns:
            ClassificationResult with relevance decision and reasoning.
        """
        criteria_text = "\n".join(f"- {c}" for c in topic_criteria)
        
        prompt = f"""Analyze whether this article is relevant to the topic "{topic_name}".

Relevance criteria:
{criteria_text}

Article content:
{article_content[:8000]}

Respond in this exact format:
RELEVANT: [yes/no]
CONFIDENCE: [0.0-1.0]
REASONING: [1-2 sentence explanation]
"""
        response = await self.model.generate_content_async(prompt)
        text = response.text
        
        is_relevant = "RELEVANT: yes" in text.lower()
        
        confidence = 0.5
        if "CONFIDENCE:" in text:
            try:
                conf_line = [l for l in text.split("\n") if "CONFIDENCE:" in l][0]
                confidence = float(conf_line.split(":")[-1].strip())
            except (IndexError, ValueError):
                pass
        
        reasoning = ""
        if "REASONING:" in text:
            reasoning = text.split("REASONING:")[-1].strip()
        
        return ClassificationResult(
            is_relevant=is_relevant,
            reasoning=reasoning,
            confidence=confidence
        )
    
    async def summarize_articles(
        self,
        articles: list[dict],
        topic_name: str,
        max_length: int = 500
    ) -> str:
        """Synthesize multiple articles into a topic summary.
        
        Args:
            articles: List of article dicts with 'title', 'url', 'content'.
            topic_name: Name of the topic for context.
            max_length: Target summary length in words.
            
        Returns:
            Markdown-formatted summary with source citations.
        """
        articles_text = ""
        for i, article in enumerate(articles, 1):
            articles_text += f"""
### Article {i}: {article['title']}
Source: {article['url']}
{article['content'][:2000]}
---
"""
        
        prompt = f"""Synthesize these articles about "{topic_name}" into an executive briefing.

Requirements:
- Write {max_length} words maximum
- Use clear, professional language
- Group related findings
- Include source citations as markdown links
- Highlight key regulatory changes or actions

Articles:
{articles_text}

Write the executive briefing in markdown format:
"""
        response = await self.model.generate_content_async(prompt)
        return response.text
    
    async def generate_report_intro(
        self,
        topic_summaries: list[dict],
        date_range: str
    ) -> str:
        """Generate an introduction for a multi-topic report.
        
        Args:
            topic_summaries: List of dicts with 'topic' and 'summary'.
            date_range: Human-readable date range string.
            
        Returns:
            Brief introduction paragraph.
        """
        topics = [ts['topic'] for ts in topic_summaries]
        
        prompt = f"""Write a brief (2-3 sentence) introduction for a regulatory intelligence report.

Covered topics: {', '.join(topics)}
Time period: {date_range}

The introduction should be professional and highlight that this is a summary of recent regulatory developments.
"""
        response = await self.model.generate_content_async(prompt)
        return response.text
