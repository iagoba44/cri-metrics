"""Tests para News Validator y Sentiment Extractor."""
import pytest
from app.services.news_validator import NewsValidator
from app.services.sentiment_extractor import SentimentExtractor

def test_news_validator_initialization():
    """Verifica que el modelo de embeddings se cargue."""
    validator = NewsValidator()
    assert validator.model is not None
    assert validator.control_embeddings is not None

def test_news_validator_empty():
    validator = NewsValidator()
    result = validator.validate_batch([])
    assert result == []

def test_news_validator_relevant_article():
    validator = NewsValidator()
    articles = [
        {"title": "NVIDIA announces massive oversupply of GPUs", "summary": "Data centers delaying purchases"},
        {"title": "Elon Musk says something", "summary": "Nothing about AI infrastructure"},
    ]
    result = validator.validate_batch(articles)
    assert len(result) >= 1
    for r in result:
        assert "semantic_score" in r
        assert r["semantic_score"] >= 0

def test_news_validator_relevance_score():
    validator = NewsValidator()
    articles = [
        {"title": "Data center cancellation wave hits cloud providers", "summary": "Major capex cuts announced"},
        {"title": "AI token market surges as demand grows", "summary": "Strong inference demand"},
    ]
    score = validator.compute_relevance_score(articles)
    assert score is not None
    assert 0 <= score <= 100

def test_sentiment_extractor_empty():
    extractor = SentimentExtractor()
    result = extractor.extract([])
    assert result["capex_score"] == 50.0
    assert result["demand_score"] == 50.0
    assert result["regulatory_score"] == 50.0
    assert result["article_count"] == 0

def test_sentiment_extractor_capex_positive():
    extractor = SentimentExtractor()
    articles = [
        {"title": "Major investment in AI data centers", "summary": "Company announces massive expansion plan"},
        {"title": "New GPU purchase order placed", "summary": "Largest contract ever for AI chips"},
    ]
    result = extractor.extract(articles)
    assert result["capex_score"] > 50
    assert result["article_count"] == 2
