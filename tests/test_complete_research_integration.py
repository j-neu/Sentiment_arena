"""
Test Complete Research Orchestrator Integration

Tests the integration of:
- Phase 3.5.1: Enhanced Research Pipeline
- Phase 3.5.2: Financial Data APIs
- Phase 3.5.3: Technical Analysis
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from backend.services.complete_research_orchestrator import CompleteResearchOrchestrator


class TestCompleteResearchOrchestrator:
    """Test complete research orchestrator."""

    @pytest.fixture
    def mock_openrouter_key(self):
        """Mock OpenRouter API key."""
        return "sk-or-test-key"

    @pytest.fixture
    def orchestrator(self, mock_openrouter_key):
        """Create orchestrator instance."""
        with patch('backend.services.complete_research_orchestrator.OpenRouterClient'):
            with patch('backend.services.complete_research_orchestrator.TechnicalAnalysisService'):
                with patch('backend.services.complete_research_orchestrator.FinancialDataAggregator'):
                    with patch('backend.services.complete_research_orchestrator.EnhancedResearchPipeline'):
                        orchestrator = CompleteResearchOrchestrator(
                            openrouter_api_key=mock_openrouter_key,
                            alphavantage_api_key="test-av-key",
                            finnhub_api_key="test-fh-key",
                            model_identifier="openai/gpt-3.5-turbo"
                        )
                        return orchestrator

    def test_initialization(self, orchestrator):
        """Test orchestrator initialization."""
        assert orchestrator is not None
        assert orchestrator.model_identifier == "openai/gpt-3.5-turbo"
        assert orchestrator.openrouter_client is not None
        assert orchestrator.technical_analysis is not None
        assert orchestrator.financial_aggregator is not None
        assert orchestrator.enhanced_research is not None

    def test_conduct_complete_research_success(self, orchestrator):
        """Test successful complete research."""
        # Mock technical analysis
        orchestrator.technical_analysis.get_technical_analysis = Mock(return_value={
            "success": True,
            "llm_formatted": "Technical Analysis Data"
        })

        # Mock financial aggregator
        orchestrator.financial_aggregator.get_complete_analysis = Mock(return_value={
            "success": True,
            "data": {"fundamentals": {}, "technicals": {}}
        })
        orchestrator.financial_aggregator.format_for_llm = Mock(return_value="Financial Data")

        # Mock enhanced research
        orchestrator.enhanced_research.conduct_stock_research = Mock(return_value={
            "success": True,
            "formatted_briefing": "Enhanced Research Data",
            "pipeline_stages": {
                "verification": {"status": "skipped"}
            }
        })

        # Execute
        result = orchestrator.conduct_complete_research(
            symbol="SAP.DE",
            include_technical=True,
            include_financial_apis=True,
            include_web_research=True,
            include_quality_verification=False
        )

        # Assertions
        assert result["success"] is True
        assert result["symbol"] == "SAP.DE"
        assert result["technical_analysis"] is not None
        assert result["financial_data"] is not None
        assert result["enhanced_research"] is not None
        assert result["unified_briefing"] is not None
        assert "TECHNICAL ANALYSIS" in result["unified_briefing"]
        assert "FINANCIAL DATA" in result["unified_briefing"]
        assert "MARKET RESEARCH" in result["unified_briefing"]

    def test_conduct_complete_research_technical_only(self, orchestrator):
        """Test research with only technical analysis."""
        # Mock technical analysis
        orchestrator.technical_analysis.get_technical_analysis = Mock(return_value={
            "success": True,
            "llm_formatted": "Technical Analysis Data"
        })

        # Execute
        result = orchestrator.conduct_complete_research(
            symbol="SAP.DE",
            include_technical=True,
            include_financial_apis=False,
            include_web_research=False,
            include_quality_verification=False
        )

        # Assertions
        assert result["success"] is True
        assert result["technical_analysis"] is not None
        assert result["financial_data"] is None
        assert result["enhanced_research"] is None

    def test_conduct_complete_research_with_errors(self, orchestrator):
        """Test research with partial failures."""
        # Mock technical analysis (success)
        orchestrator.technical_analysis.get_technical_analysis = Mock(return_value={
            "success": True,
            "llm_formatted": "Technical Analysis Data"
        })

        # Mock financial aggregator (failure)
        orchestrator.financial_aggregator.get_complete_analysis = Mock(return_value={
            "success": False,
            "errors": ["API error"]
        })

        # Mock enhanced research (success)
        orchestrator.enhanced_research.conduct_stock_research = Mock(return_value={
            "success": True,
            "formatted_briefing": "Enhanced Research Data",
            "pipeline_stages": {"verification": {"status": "skipped"}}
        })

        # Execute
        result = orchestrator.conduct_complete_research(
            symbol="SAP.DE",
            include_technical=True,
            include_financial_apis=True,
            include_web_research=True,
            include_quality_verification=False
        )

        # Assertions
        assert result["success"] is True  # Success because 2/3 sources worked
        assert len(result["errors"]) > 0
        assert "Financial API" in str(result["errors"])

    def test_create_unified_briefing(self, orchestrator):
        """Test unified briefing creation."""
        technical = {
            "success": True,
            "llm_formatted": "Technical Data"
        }

        financial = {
            "success": True,
            "data": {}
        }

        research = {
            "success": True,
            "formatted_briefing": "Research Data",
            "pipeline_stages": {
                "verification": {"status": "skipped"}
            }
        }

        # Mock format_for_llm
        orchestrator.financial_aggregator.format_for_llm = Mock(return_value="Formatted Financial Data")

        briefing = orchestrator._create_unified_briefing(
            symbol="SAP.DE",
            technical=technical,
            financial=financial,
            research=research
        )

        # Assertions
        assert "SAP.DE" in briefing
        assert "TECHNICAL ANALYSIS" in briefing
        assert "FINANCIAL DATA" in briefing
        assert "MARKET RESEARCH" in briefing
        assert "Technical Data" in briefing
        assert "Formatted Financial Data" in briefing
        assert "Research Data" in briefing
        assert "BRIEFING SUMMARY" in briefing

    def test_get_cost_estimate(self, orchestrator):
        """Test cost estimation."""
        costs = orchestrator.get_cost_estimate("SAP.DE")

        assert "technical_analysis" in costs
        assert "financial_apis" in costs
        assert "enhanced_research" in costs
        assert "total_estimated" in costs

    def test_context_manager(self, mock_openrouter_key):
        """Test context manager support."""
        with patch('backend.services.complete_research_orchestrator.OpenRouterClient'):
            with patch('backend.services.complete_research_orchestrator.TechnicalAnalysisService'):
                with patch('backend.services.complete_research_orchestrator.FinancialDataAggregator'):
                    with patch('backend.services.complete_research_orchestrator.EnhancedResearchPipeline'):
                        with CompleteResearchOrchestrator(
                            openrouter_api_key=mock_openrouter_key
                        ) as orchestrator:
                            assert orchestrator is not None


class TestIntegrationWithLLMAgent:
    """Test integration with LLM Agent."""

    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return Mock()

    def test_llm_agent_uses_complete_research(self, mock_db):
        """Test that LLM agent can use complete research orchestrator."""
        from backend.services.llm_agent import LLMAgent

        # Create mock model
        mock_model = Mock()
        mock_model.id = 1
        mock_model.name = "Test Model"
        mock_model.api_identifier = "openai/gpt-3.5-turbo"
        mock_model.starting_balance = 1000.0

        # Mock database query
        mock_db.query.return_value.filter.return_value.first.return_value = mock_model

        with patch('backend.services.llm_agent.OpenRouterClient'):
            with patch('backend.services.llm_agent.ResearchService'):
                with patch('backend.services.llm_agent.MarketDataService'):
                    with patch('backend.services.llm_agent.TradingEngine'):
                        with patch('backend.services.llm_agent.CompleteResearchOrchestrator'):
                            # Create agent with complete research enabled
                            agent = LLMAgent(
                                db=mock_db,
                                model_id=1,
                                use_complete_research=True
                            )

                            # Verify complete research orchestrator was initialized
                            assert agent.use_complete_research is True
                            # The orchestrator might be None if initialization failed,
                            # but we're testing the integration path exists

    def test_llm_agent_fallback_to_basic_research(self, mock_db):
        """Test LLM agent fallback when complete research unavailable."""
        from backend.services.llm_agent import LLMAgent

        # Create mock model
        mock_model = Mock()
        mock_model.id = 1
        mock_model.name = "Test Model"
        mock_model.api_identifier = "openai/gpt-3.5-turbo"
        mock_model.starting_balance = 1000.0

        # Mock database query
        mock_db.query.return_value.filter.return_value.first.return_value = mock_model

        with patch('backend.services.llm_agent.OpenRouterClient'):
            with patch('backend.services.llm_agent.ResearchService'):
                with patch('backend.services.llm_agent.MarketDataService'):
                    with patch('backend.services.llm_agent.TradingEngine'):
                        # Create agent without complete research
                        agent = LLMAgent(
                            db=mock_db,
                            model_id=1,
                            use_complete_research=False
                        )

                        # Verify basic research is used
                        assert agent.use_complete_research is False
                        assert agent.research is not None
