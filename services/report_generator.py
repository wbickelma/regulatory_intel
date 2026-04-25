"""Report generation service for creating executive briefings."""

from uuid import UUID, uuid4
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from clients import GeminiClient
from db.models import Topic, Article, Report
from services.article_extractor import ArticleExtractor
from services.relevance_classifier import RelevanceClassifier


class ReportGenerator:
    """Generates executive briefings from extracted articles.
    
    Full pipeline: extract → classify → summarize → deliver.
    """
    
    def __init__(
        self,
        db: Session,
        extractor: ArticleExtractor,
        classifier: RelevanceClassifier,
        llm_client: GeminiClient
    ):
        self.db = db
        self.extractor = extractor
        self.classifier = classifier
        self.llm_client = llm_client
    
    async def generate_report(
        self,
        topic_id: UUID | None = None,
        days: int = 7
    ) -> Report:
        """Generate a report for one or all topics.
        
        Args:
            topic_id: Specific topic, or None for all topics.
            days: Number of days to look back.
            
        Returns:
            Generated Report object.
        """
        now = datetime.utcnow()
        since = now - timedelta(days=days)
        
        if topic_id:
            topics = [self.db.query(Topic).filter(Topic.id == topic_id).first()]
        else:
            topics = self.db.query(Topic).filter(Topic.is_active == True).all()
        
        topic_summaries = []
        total_articles = 0
        
        for topic in topics:
            if not topic:
                continue
                
            await self.extractor.extract_articles(topic.id, days)
            
            await self.classifier.classify_unclassified(topic)
            
            relevant_articles = self.extractor.get_relevant_articles(topic.id, days)
            total_articles += len(relevant_articles)
            
            if relevant_articles:
                summary = await self._summarize_topic(topic, relevant_articles)
                topic_summaries.append({
                    "topic": topic.name,
                    "summary": summary,
                    "article_count": len(relevant_articles)
                })
        
        report_markdown = await self._compile_report(topic_summaries, since, now)
        
        report = Report(
            id=uuid4(),
            topic_id=topic_id,
            date_range_start=since,
            date_range_end=now,
            summary_markdown=report_markdown,
            article_count=total_articles,
            generated_at=now
        )
        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)
        
        return report
    
    async def _summarize_topic(
        self,
        topic: Topic,
        articles: list[Article]
    ) -> str:
        """Generate summary for a single topic.
        
        Args:
            topic: The topic.
            articles: Relevant articles for the topic.
            
        Returns:
            Markdown summary text.
        """
        article_data = [
            {
                "title": a.title,
                "url": a.source_url,
                "content": a.content_markdown
            }
            for a in articles
        ]
        
        return await self.llm_client.summarize_articles(article_data, topic.name)
    
    async def _compile_report(
        self,
        topic_summaries: list[dict],
        since: datetime,
        until: datetime
    ) -> str:
        """Compile topic summaries into a full report.
        
        Args:
            topic_summaries: List of topic summary dicts.
            since: Start of date range.
            until: End of date range.
            
        Returns:
            Full report markdown.
        """
        date_range = f"{since.strftime('%B %d, %Y')} - {until.strftime('%B %d, %Y')}"
        
        intro = await self.llm_client.generate_report_intro(topic_summaries, date_range)
        
        sections = [f"# Regulatory Intelligence Report\n\n*{date_range}*\n\n{intro}\n\n---\n"]
        
        for ts in topic_summaries:
            sections.append(f"## {ts['topic']}\n\n*{ts['article_count']} articles reviewed*\n\n{ts['summary']}\n\n---\n")
        
        return "\n".join(sections)
    
    def get_report(self, report_id: UUID) -> Report | None:
        """Get a report by ID."""
        return self.db.query(Report).filter(Report.id == report_id).first()
    
    def list_reports(self, limit: int = 10) -> list[Report]:
        """List recent reports."""
        return self.db.query(Report).order_by(
            Report.generated_at.desc()
        ).limit(limit).all()
