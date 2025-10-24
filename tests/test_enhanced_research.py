"""
Unit Tests for Enhanced Research Pipeline (Phase 3.5.1)

Tests:
- Research model mapper
- Query generator
- Research synthesizer
- Quality verifier
- Enhanced research pipeline
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json

from backend.services.research_model_mapper import ResearchModelMapper
from backend.services.query_generator import QueryGenerator
from backend.services.research_synthesis import ResearchSynthesizer
from backend.services.quality_verifier import QualityVerifier
from backend.services.enhanced_research import EnhancedResearchPipeline


class TestResearchModelMapper:
    """Test research model mapping functionality."""

    def test_get_research_model_premium_to_cheap(self):
        """Test mapping premium model to cheaper variant."""
        assert ResearchModelMapper.get_research_model("openai/gpt-4-turbo") == "openai/gpt-3.5-turbo"
        assert ResearchModelMapper.get_research_model("anthropic/claude-3-opus-20240229") == "anthropic/claude-3-haiku-20240307"

    def test_get_research_model_already_cheap(self):
        """Test that cheap models map to themselves."""
        assert ResearchModelMapper.get_research_model("openai/gpt-3.5-turbo") == "openai/gpt-3.5-turbo"
        assert ResearchModelMapper.get_research_model("deepseek/deepseek-chat") == "deepseek/deepseek-chat"
        assert ResearchModelMapper.get_research_model("google/gemini-pro") == "google/gemini-pro"

    def test_get_research_model_unknown(self):
        """Test fallback for unknown models."""
        unknown_model = "unknown/model-v1"
        assert ResearchModelMapper.get_research_model(unknown_model) == unknown_model

    def test_get_model_company(self):
        """Test company extraction."""
        assert ResearchModelMapper.get_model_company("openai/gpt-4-turbo") == "OpenAI"
        assert ResearchModelMapper.get_model_company("anthropic/claude-3-opus") == "Anthropic"
        assert ResearchModelMapper.get_model_company("google/gemini-pro") == "Google"
        assert ResearchModelMapper.get_model_company("deepseek/deepseek-chat") == "DeepSeek"

    def test_is_cheap_model(self):
        """Test cheap model detection."""
        assert ResearchModelMapper.is_cheap_model("openai/gpt-3.5-turbo") is True
        assert ResearchModelMapper.is_cheap_model("deepseek/deepseek-chat") is True
        assert ResearchModelMapper.is_cheap_model("openai/gpt-4-turbo") is False
        assert ResearchModelMapper.is_cheap_model("anthropic/claude-3-opus") is False

    def test_get_cost_estimate(self):
        """Test cost estimation."""
        cost_info = ResearchModelMapper.get_cost_estimate("openai/gpt-4-turbo")
        assert cost_info["trading_model"] == "openai/gpt-4-turbo"
        assert cost_info["research_model"] == "openai/gpt-3.5-turbo"
        assert cost_info["is_same_model"] is False

        cost_info_cheap = ResearchModelMapper.get_cost_estimate("deepseek/deepseek-chat")
        assert cost_info_cheap["is_same_model"] is True

    def test_list_supported_models(self):
        """Test listing supported models."""
        supported = ResearchModelMapper.list_supported_models()
        assert isinstance(supported, dict)
        assert "OpenAI" in supported
        assert "Anthropic" in supported
        assert len(supported) > 0


class TestQueryGenerator:
    """Test intelligent query generation."""

    @pytest.fixture
    def mock_client(self):
        """Create mock OpenRouter client."""
        client = Mock()
        return client

    @pytest.fixture
    def query_generator(self, mock_client):
        """Create QueryGenerator instance."""
        return QueryGenerator(mock_client, "openai/gpt-4-turbo")

    def test_initialization(self, query_generator):
        """Test proper initialization."""
        assert query_generator.trading_model == "openai/gpt-4-turbo"
        assert query_generator.research_model == "openai/gpt-3.5-turbo"

    def test_generate_stock_queries_success(self, query_generator, mock_client):
        """Test successful query generation."""
        mock_response = json.dumps([
            "SAP Q3 2024 earnings",
            "SAP cloud revenue growth",
            "SAP vs Oracle competition"
        ])
        mock_client.get_completion_text.return_value = mock_response

        queries = query_generator.generate_stock_queries("SAP.DE", num_queries=3)

        assert len(queries) == 3
        assert all(isinstance(q, str) for q in queries)
        mock_client.get_completion_text.assert_called_once()

    def test_generate_stock_queries_with_existing_data(self, query_generator, mock_client):
        """Test query generation with context."""
        mock_response = '["SAP earnings beat", "SAP risks 2024"]'
        mock_client.get_completion_text.return_value = mock_response

        existing_data = {
            "portfolio": {"balance": 1000},
            "positions": [{"symbol": "SAP.DE", "quantity": 10}]
        }

        queries = query_generator.generate_stock_queries(
            "SAP.DE",
            existing_data=existing_data,
            num_queries=2
        )

        assert len(queries) == 2

    def test_generate_stock_queries_fallback(self, query_generator, mock_client):
        """Test fallback when LLM fails."""
        mock_client.get_completion_text.side_effect = Exception("API error")

        queries = query_generator.generate_stock_queries("SAP.DE", num_queries=3)

        # Should return fallback queries
        assert len(queries) > 0
        assert all(isinstance(q, str) for q in queries)

    def test_generate_market_queries(self, query_generator, mock_client):
        """Test market query generation."""
        mock_response = '["DAX outlook 2024", "German economy trends"]'
        mock_client.get_completion_text.return_value = mock_response

        queries = query_generator.generate_market_queries(num_queries=2)

        assert len(queries) == 2
        mock_client.get_completion_text.assert_called_once()

    def test_parse_queries_valid_json(self, query_generator):
        """Test parsing valid JSON queries."""
        response = '["query 1", "query 2", "query 3"]'
        queries = query_generator._parse_queries(response, 3)

        assert len(queries) == 3
        assert queries == ["query 1", "query 2", "query 3"]

    def test_parse_queries_markdown_codeblock(self, query_generator):
        """Test parsing queries from markdown code block."""
        response = '''```json
["query 1", "query 2"]
```'''
        queries = query_generator._parse_queries(response, 2)

        assert len(queries) == 2

    def test_get_model_info(self, query_generator):
        """Test model info retrieval."""
        info = query_generator.get_model_info()

        assert info["trading_model"] == "openai/gpt-4-turbo"
        assert info["research_model"] == "openai/gpt-3.5-turbo"
        assert info["company"] == "OpenAI"


class TestResearchSynthesizer:
    """Test research synthesis functionality."""

    @pytest.fixture
    def mock_client(self):
        """Create mock OpenRouter client."""
        return Mock()

    @pytest.fixture
    def mock_research_service(self):
        """Create mock research service."""
        return Mock()

    @pytest.fixture
    def synthesizer(self, mock_client, mock_research_service):
        """Create ResearchSynthesizer instance."""
        return ResearchSynthesizer(
            mock_client,
            mock_research_service,
            "openai/gpt-4-turbo"
        )

    def test_initialization(self, synthesizer):
        """Test proper initialization."""
        assert synthesizer.trading_model == "openai/gpt-4-turbo"
        assert synthesizer.research_model == "openai/gpt-3.5-turbo"

    def test_assess_source_credibility(self, synthesizer):
        """Test source credibility assessment."""
        raw_results = [
            {"url": "https://reuters.com/article", "title": "Test 1"},
            {"url": "https://bloomberg.com/news", "title": "Test 2"},
            {"url": "https://random-blog.com/post", "title": "Test 3"},
            {"url": "https://seekingalpha.com/article", "title": "Test 4"}
        ]

        ratings = synthesizer._assess_source_credibility(raw_results)

        assert ratings["https://reuters.com/article"] == "high"
        assert ratings["https://bloomberg.com/news"] == "high"
        assert ratings["https://random-blog.com/post"] == "low"
        assert ratings["https://seekingalpha.com/article"] == "medium"

    def test_credibility_breakdown(self, synthesizer):
        """Test credibility breakdown calculation."""
        ratings = {
            "url1": "high",
            "url2": "high",
            "url3": "medium",
            "url4": "low"
        }

        breakdown = synthesizer._credibility_breakdown(ratings)

        assert breakdown["high"] == 2
        assert breakdown["medium"] == 1
        assert breakdown["low"] == 1

    def test_synthesize_stock_research_success(self, synthesizer, mock_client):
        """Test successful research synthesis."""
        raw_results = [
            {
                "url": "https://reuters.com/article",
                "title": "SAP earnings beat expectations",
                "snippet": "SAP reported strong Q3 results..."
            }
        ]

        mock_response = json.dumps({
            "recent_events": "SAP Q3 earnings beat",
            "sentiment_analysis": "Positive",
            "risk_factors": "Some risks identified",
            "opportunities": "Cloud growth",
            "source_quality": "High credibility sources",
            "key_takeaways": ["Earnings beat", "Strong cloud revenue"],
            "contradictions_found": [],
            "data_gaps": [],
            "confidence_level": "HIGH"
        })

        mock_client.get_completion_text.return_value = mock_response

        briefing = synthesizer.synthesize_stock_research(
            "SAP.DE",
            raw_results
        )

        assert briefing["recent_events"] == "SAP Q3 earnings beat"
        assert briefing["confidence_level"] == "HIGH"
        assert "metadata" in briefing
        assert briefing["metadata"]["symbol"] == "SAP.DE"

    def test_format_for_trading_llm(self, synthesizer):
        """Test formatting briefing for trading LLM."""
        briefing = {
            "recent_events": "Test events",
            "sentiment_analysis": "Positive",
            "risk_factors": "Low risk",
            "opportunities": "Growth potential",
            "source_quality": "High",
            "key_takeaways": ["Takeaway 1", "Takeaway 2"],
            "metadata": {
                "symbol": "SAP.DE",
                "num_sources": 5,
                "credibility_breakdown": {"high": 3, "medium": 1, "low": 1}
            }
        }

        formatted = synthesizer.format_for_trading_llm(briefing)

        assert "SAP.DE" in formatted
        assert "Test events" in formatted
        assert "Takeaway 1" in formatted
        assert "SOURCES: 5 total" in formatted


class TestQualityVerifier:
    """Test quality verification functionality."""

    @pytest.fixture
    def mock_client(self):
        """Create mock OpenRouter client."""
        return Mock()

    @pytest.fixture
    def verifier(self, mock_client):
        """Create QualityVerifier instance."""
        return QualityVerifier(mock_client, "openai/gpt-4-turbo")

    def test_initialization(self, verifier):
        """Test proper initialization."""
        assert verifier.trading_model == "openai/gpt-4-turbo"
        assert verifier.research_model == "openai/gpt-3.5-turbo"

    def test_verify_briefing_success(self, verifier, mock_client):
        """Test successful briefing verification."""
        briefing = {
            "recent_events": "Test",
            "sentiment_analysis": "Positive",
            "risk_factors": "Low",
            "opportunities": "High",
            "source_quality": "Good",
            "key_takeaways": ["Test"]
        }

        source_data = [
            {"title": "Test article", "snippet": "Test content", "url": "test.com"}
        ]

        mock_response = json.dumps({
            "accuracy_score": 20,
            "completeness_score": 20,
            "objectivity_score": 20,
            "usefulness_score": 20,
            "quality_score": 80,
            "issues_found": [],
            "strengths": ["Well written"],
            "recommendations": [],
            "overall_assessment": "PASS",
            "confidence_in_verification": "HIGH"
        })

        mock_client.get_completion_text.return_value = mock_response

        verification = verifier.verify_briefing(briefing, source_data)

        assert verification["quality_score"] == 80
        assert verification["overall_assessment"] == "PASS"
        assert "verified_at" in verification

    def test_should_use_briefing_pass(self, verifier):
        """Test briefing pass decision."""
        verification = {
            "quality_score": 75,
            "overall_assessment": "PASS"
        }

        assert verifier.should_use_briefing(verification) is True

    def test_should_use_briefing_fail(self, verifier):
        """Test briefing fail decision."""
        verification = {
            "quality_score": 50,
            "overall_assessment": "FAIL"
        }

        assert verifier.should_use_briefing(verification) is False

    def test_get_quality_tier(self, verifier):
        """Test quality tier determination."""
        assert verifier.get_quality_tier(85) == "EXCELLENT"
        assert verifier.get_quality_tier(75) == "GOOD"
        assert verifier.get_quality_tier(65) == "ACCEPTABLE"
        assert verifier.get_quality_tier(45) == "POOR"
        assert verifier.get_quality_tier(30) == "VERY_POOR"

    def test_create_quality_report(self, verifier):
        """Test quality report generation."""
        briefing = {
            "metadata": {"symbol": "SAP.DE"}
        }

        verification = {
            "quality_score": 80,
            "overall_assessment": "PASS",
            "accuracy_score": 20,
            "completeness_score": 20,
            "objectivity_score": 20,
            "usefulness_score": 20,
            "strengths": ["Good analysis"],
            "issues_found": [],
            "recommendations": ["Keep up the good work"],
            "verified_by": "gpt-3.5-turbo",
            "confidence_in_verification": "HIGH",
            "verified_at": "2024-10-22T10:00:00"
        }

        report = verifier.create_quality_report(briefing, verification)

        assert "SAP.DE" in report
        assert "80/100" in report
        assert "PASS" in report
        assert "Good analysis" in report


class TestEnhancedResearchPipeline:
    """Test complete enhanced research pipeline."""

    @pytest.fixture
    def mock_client(self):
        """Create mock OpenRouter client."""
        return Mock()

    @pytest.fixture
    def pipeline(self, mock_client):
        """Create EnhancedResearchPipeline instance."""
        return EnhancedResearchPipeline(
            mock_client,
            "openai/gpt-4-turbo"
        )

    def test_initialization(self, pipeline):
        """Test proper initialization."""
        assert pipeline.trading_model == "openai/gpt-4-turbo"
        assert pipeline.research_model == "openai/gpt-3.5-turbo"
        assert pipeline.query_generator is not None
        assert pipeline.synthesizer is not None
        assert pipeline.verifier is not None

    @patch('backend.services.enhanced_research.QueryGenerator')
    @patch('backend.services.enhanced_research.ResearchSynthesizer')
    @patch('backend.services.enhanced_research.QualityVerifier')
    def test_conduct_stock_research_success(
        self,
        mock_verifier_class,
        mock_synthesizer_class,
        mock_query_gen_class,
        pipeline
    ):
        """Test successful full pipeline execution."""
        # Mock query generator
        mock_query_gen = Mock()
        mock_query_gen.generate_stock_queries.return_value = [
            "SAP earnings 2024",
            "SAP cloud growth",
            "SAP risks"
        ]
        pipeline.query_generator = mock_query_gen

        # Mock research service
        mock_research = Mock()
        mock_research.search_stock_news.return_value = [
            {"url": "test.com", "title": "Test", "snippet": "Content"}
        ]
        pipeline.research_service = mock_research

        # Mock synthesizer
        mock_synth = Mock()
        mock_synth.synthesize_stock_research.return_value = {
            "recent_events": "Test",
            "sentiment_analysis": "Positive",
            "risk_factors": "Low",
            "opportunities": "High",
            "source_quality": "Good",
            "key_takeaways": ["Test"],
            "confidence_level": "HIGH",
            "metadata": {"symbol": "SAP.DE"}
        }
        mock_synth.format_for_trading_llm.return_value = "Formatted briefing"
        pipeline.synthesizer = mock_synth

        # Mock verifier
        mock_ver = Mock()
        mock_ver.verify_briefing.return_value = {
            "quality_score": 80,
            "overall_assessment": "PASS"
        }
        mock_ver.should_use_briefing.return_value = True
        pipeline.verifier = mock_ver

        # Run pipeline
        results = pipeline.conduct_stock_research("SAP.DE")

        assert results["success"] is True
        assert results["symbol"] == "SAP.DE"
        assert "pipeline_stages" in results
        assert "timing" in results
        assert results["pipeline_stages"]["query_generation"]["status"] == "success"
        assert results["pipeline_stages"]["data_collection"]["status"] == "success"
        assert results["pipeline_stages"]["synthesis"]["status"] == "success"
        assert results["pipeline_stages"]["verification"]["status"] == "success"

    def test_get_cost_estimate(self, pipeline):
        """Test cost estimation."""
        cost_info = pipeline.get_cost_estimate()

        assert "trading_model" in cost_info
        assert "research_model" in cost_info
        assert "pipeline_stages" in cost_info
        assert cost_info["pipeline_stages"]["total_research_calls"] == 3

    def test_get_model_info(self, pipeline):
        """Test model info retrieval."""
        info = pipeline.get_model_info()

        assert info["trading_model"] == "openai/gpt-4-turbo"
        assert info["research_model"] == "openai/gpt-3.5-turbo"
        assert info["company"] == "OpenAI"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
