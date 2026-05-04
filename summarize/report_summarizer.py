"""Report summarizer using Circuit LLM.

Generates executive briefings from evaluated articles in markdown or Word format.
"""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from langchain_openai import AzureChatOpenAI

from clients.inoreader import ArticleItem
from evaluation.circuit_client import CircuitClient

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent
PROMPT_PATH = PROJECT_ROOT / "prompts" / "summarization.txt"

DEFAULT_PROMPT = """You are a regulatory intelligence analyst preparing an executive briefing.

Summarize the following article for a busy executive. Be concise but capture:
- Key regulatory changes or proposals
- Affected industries or business areas
- Required actions or deadlines
- Potential business impact

Article Title: {title}
URL: {url}
Published: {published_at}

Content:
{content}

Provide a 2-3 paragraph summary in clear, professional language."""


class ReportSummarizer:
    """Generates markdown reports from evaluated articles."""

    def __init__(self, llm: AzureChatOpenAI | None = None):
        """Initialize with optional pre-built LLM instance."""
        if llm is None:
            circuit = CircuitClient()
            self._llm = circuit.get_llm(temperature=0.3)
        else:
            self._llm = llm

    def _load_prompt(self) -> str:
        """Load summarization prompt from disk, or use default."""
        if PROMPT_PATH.exists():
            return PROMPT_PATH.read_text(encoding="utf-8")
        return DEFAULT_PROMPT

    def summarize_article(self, article: ArticleItem) -> str:
        """Generate a summary for a single article.

        Args:
            article: ArticleItem with full_content populated.

        Returns:
            Summary text string.
        """
        template = self._load_prompt()
        content = article.full_content or article.summary or ""

        prompt = template.format(
            title=article.title or "Untitled",
            url=article.url or "",
            published_at=article.published_at.isoformat() if article.published_at else "",
            content=content[:8000],  # Truncate to avoid token limits
        )

        response = self._llm.invoke(prompt)
        return response.content.strip()

    def generate_report(
        self,
        articles: list[ArticleItem],
        title: str = "Regulatory Intelligence Briefing",
    ) -> str:
        """Generate a full markdown report from multiple articles.

        Args:
            articles: List of ArticleItem instances (should have full_content).
            title: Report title.

        Returns:
            Complete markdown document as a string.
        """
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        lines = [
            f"# {title}",
            f"*Generated: {now}*",
            "",
            f"**Articles Reviewed:** {len(articles)}",
            "",
            "---",
            "",
        ]

        for i, article in enumerate(articles, 1):
            score = article.relevance_score or 0
            action = ""
            if article.evaluation:
                action = article.evaluation.get("action_needed", "")

            lines.append(f"## {i}. {article.title or 'Untitled'}")
            lines.append("")
            lines.append(f"- **URL:** [{article.url}]({article.url})")
            lines.append(f"- **Published:** {article.published_at.strftime('%Y-%m-%d') if article.published_at else 'N/A'}")
            lines.append(f"- **Relevance Score:** {score}/10")
            if action:
                lines.append(f"- **Action Needed:** {action}")
            lines.append("")

            print(f"\n[{i}/{len(articles)}] Summarizing: {article.title}")
            try:
                summary = self.summarize_article(article)
                lines.append("### Summary")
                lines.append("")
                lines.append(summary)
            except Exception as e:
                logger.warning(f"Summarization failed for '{article.title}': {e}")
                lines.append(f"*Summarization failed: {e}*")

            lines.append("")
            lines.append("---")
            lines.append("")

        return "\n".join(lines)

    def generate_docx(
        self,
        articles: list[ArticleItem],
        output_path: str | Path,
        title: str = "Regulatory Intelligence Briefing",
    ) -> Path:
        """Generate a Word document report from multiple articles.

        Args:
            articles: List of ArticleItem instances (should have full_content).
            output_path: Path to save the .docx file.
            title: Report title.

        Returns:
            Path to the saved document.
        """
        doc = Document()
        output_path = Path(output_path)

        # Title
        heading = doc.add_heading(title, level=0)
        heading.alignment = WD_ALIGN_PARAGRAPH.CENTER

        # Metadata
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        meta = doc.add_paragraph()
        meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
        meta.add_run(f"Generated: {now}").italic = True
        doc.add_paragraph(f"Articles Reviewed: {len(articles)}")
        doc.add_paragraph()

        # Articles
        for i, article in enumerate(articles, 1):
            score = article.relevance_score or 0
            action = article.evaluation.get("action_needed", "") if article.evaluation else ""

            doc.add_heading(f"{i}. {article.title or 'Untitled'}", level=1)

            # Metadata table
            info = doc.add_paragraph()
            info.add_run("URL: ").bold = True
            info.add_run(article.url or "N/A")
            info.add_run("\n")
            info.add_run("Published: ").bold = True
            info.add_run(article.published_at.strftime("%Y-%m-%d") if article.published_at else "N/A")
            info.add_run("\n")
            info.add_run("Relevance Score: ").bold = True
            info.add_run(f"{score}/10")
            if action:
                info.add_run("\n")
                info.add_run("Action Needed: ").bold = True
                info.add_run(action)

            # Summary
            print(f"\n[{i}/{len(articles)}] Summarizing: {article.title}")
            try:
                summary = self.summarize_article(article)
                doc.add_heading("Summary", level=2)
                doc.add_paragraph(summary)
            except Exception as e:
                logger.warning(f"Summarization failed for '{article.title}': {e}")
                doc.add_paragraph(f"Summarization failed: {e}").italic = True

            doc.add_paragraph()  # Spacing

        doc.save(output_path)
        return output_path
