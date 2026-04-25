"""Relevance classification service using Gemini LLM."""

from dataclasses import dataclass
from sqlalchemy.orm import Session

from clients import GeminiClient
from db.models import Topic, Article


@dataclass
class ClassificationResult:
    article_id: str
    is_relevant: bool
    reasoning: str
    confidence: float


class RelevanceClassifier:
    """Classifies articles for relevance to topics using LLM.
    
    Uses Gemini to evaluate articles against topic-specific criteria.
    """
    
    DEFAULT_CRITERIA = [
        "Contains regulatory announcements or rule changes",
        "Discusses enforcement actions or compliance updates",
        "Mentions proposed regulations or public comment periods",
        "Covers guidance documents or policy interpretations"
    ]
    
    def __init__(
        self,
        db: Session,
        llm_client: GeminiClient,
        topic_criteria: dict[str, list[str]] | None = None
    ):
        self.db = db
        self.llm_client = llm_client
        self.topic_criteria = topic_criteria or {}
    
    def get_criteria(self, topic_name: str) -> list[str]:
        """Get relevance criteria for a topic.
        
        Args:
            topic_name: The topic name.
            
        Returns:
            List of criteria strings.
        """
        return self.topic_criteria.get(topic_name, self.DEFAULT_CRITERIA)
    
    async def classify(
        self,
        article: Article,
        topic: Topic
    ) -> ClassificationResult:
        """Classify a single article for relevance.
        
        Args:
            article: The article to classify.
            topic: The topic context.
            
        Returns:
            ClassificationResult with decision and reasoning.
        """
        criteria = self.get_criteria(topic.name)
        
        result = await self.llm_client.classify_relevance(
            article_content=article.content_markdown,
            topic_name=topic.name,
            topic_criteria=criteria
        )
        
        article.is_relevant = result.is_relevant
        article.relevance_reasoning = result.reasoning
        self.db.commit()
        
        return ClassificationResult(
            article_id=str(article.id),
            is_relevant=result.is_relevant,
            reasoning=result.reasoning,
            confidence=result.confidence
        )
    
    async def classify_batch(
        self,
        articles: list[Article],
        topic: Topic
    ) -> list[ClassificationResult]:
        """Classify multiple articles.
        
        Args:
            articles: List of articles to classify.
            topic: The topic context.
            
        Returns:
            List of ClassificationResult objects.
        """
        results = []
        for article in articles:
            result = await self.classify(article, topic)
            results.append(result)
        return results
    
    async def classify_unclassified(self, topic: Topic) -> list[ClassificationResult]:
        """Classify all unclassified articles for a topic.
        
        Args:
            topic: The topic to process.
            
        Returns:
            List of ClassificationResult objects.
        """
        from services.article_extractor import ArticleExtractor
        
        extractor = ArticleExtractor(self.db, None)
        articles = extractor.get_unclassified_articles(topic.id)
        
        return await self.classify_batch(articles, topic)
