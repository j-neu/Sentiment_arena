"""
Unit tests for LLM Agent.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from decimal import Decimal

from backend.services.llm_agent import LLMAgent
from backend.models.model import Model
from backend.models.portfolio import Portfolio
from backend.models.position import Position


class TestLLMAgent:
    """Test suite for LLMAgent."""

    @pytest.fixture
    def db_session(self):
        """Mock database session."""
        return MagicMock()

    @pytest.fixture
    def mock_model(self):
        """Mock Model object."""
        model = Mock(spec=Model)
        model.id = 1
        model.name = "GPT-4 Test"
        model.api_identifier = "openai/gpt-4"
        model.starting_balance = 1000.0
        return model

    @pytest.fixture
    def mock_portfolio(self):
        """Mock Portfolio object."""
        portfolio = Mock(spec=Portfolio)
        portfolio.model_id = 1
        portfolio.current_balance = Decimal('850.00')
        portfolio.total_value = Decimal('950.00')
        portfolio.total_pl = Decimal('-50.00')
        return portfolio

    @pytest.fixture
    def mock_position(self):
        """Mock Position object."""
        position = Mock(spec=Position)
        position.model_id = 1
        position.symbol = "SAP.DE"
        position.quantity = 5
        position.avg_price = Decimal('120.00')
        position.current_price = Decimal('125.00')
        position.unrealized_pl = Decimal('25.00')
        return position

    @pytest.fixture
    def agent(self, db_session, mock_model):
        """Create LLMAgent with mocked dependencies."""
        # Mock database query
        db_session.query.return_value.filter.return_value.first.return_value = mock_model

        with patch('backend.services.llm_agent.OpenRouterClient'):
            with patch('backend.services.llm_agent.ResearchService'):
                with patch('backend.services.llm_agent.MarketDataService'):
                    with patch('backend.services.llm_agent.TradingEngine'):
                        agent = LLMAgent(db_session, model_id=1, api_key="test-key")
                        return agent

    def test_agent_initialization(self, db_session, mock_model):
        """Test agent initializes correctly."""
        db_session.query.return_value.filter.return_value.first.return_value = mock_model

        with patch('backend.services.llm_agent.OpenRouterClient'):
            with patch('backend.services.llm_agent.ResearchService'):
                with patch('backend.services.llm_agent.MarketDataService'):
                    with patch('backend.services.llm_agent.TradingEngine'):
                        agent = LLMAgent(db_session, model_id=1)
                        assert agent.model_id == 1
                        assert agent.model == mock_model

    def test_agent_initialization_model_not_found(self, db_session):
        """Test agent raises error if model not found."""
        db_session.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(ValueError, match="Model with id 1 not found"):
            LLMAgent(db_session, model_id=1)

    def test_get_portfolio_state(self, agent, db_session, mock_portfolio):
        """Test getting portfolio state."""
        db_session.query.return_value.filter.return_value.first.return_value = mock_portfolio

        portfolio = agent._get_portfolio_state()
        assert portfolio == mock_portfolio

    def test_get_portfolio_state_creates_if_missing(self, agent, db_session):
        """Test portfolio is created if it doesn't exist."""
        db_session.query.return_value.filter.return_value.first.return_value = None

        mock_new_portfolio = Mock(spec=Portfolio)
        agent.trading_engine.initialize_portfolio = Mock(return_value=mock_new_portfolio)

        portfolio = agent._get_portfolio_state()
        assert portfolio == mock_new_portfolio
        agent.trading_engine.initialize_portfolio.assert_called_once_with(1)

    def test_get_positions(self, agent, db_session, mock_position):
        """Test getting positions."""
        db_session.query.return_value.filter.return_value.all.return_value = [mock_position]

        positions = agent._get_positions()
        assert len(positions) == 1
        assert positions[0] == mock_position

    def test_get_market_data(self, agent, mock_position):
        """Test getting market data for positions."""
        agent.market_data.fetch_price = Mock(return_value={
            'price': 125.50,
            'high': 127.00,
            'low': 124.00,
            'volume': 100000
        })

        market_data = agent._get_market_data([mock_position])

        assert "SAP.DE" in market_data
        assert market_data["SAP.DE"]["price"] == 125.50
        agent.market_data.fetch_price.assert_called_once_with("SAP.DE")

    def test_get_market_data_handles_error(self, agent, mock_position):
        """Test market data handles errors gracefully."""
        agent.market_data.fetch_price = Mock(side_effect=Exception("API Error"))

        market_data = agent._get_market_data([mock_position])

        # Should return empty dict on error
        assert market_data == {}

    def test_perform_research(self, agent, mock_position):
        """Test performing research."""
        mock_research_data = {
            "timestamp": "2024-01-01T12:00:00",
            "stock_news": {"SAP.DE": [{"title": "SAP earnings beat"}]},
            "market_sentiment": [{"title": "DAX rises"}],
            "summary": "Research complete"
        }

        agent.research.aggregate_research = Mock(return_value=mock_research_data)
        agent.research.format_research_for_llm = Mock(return_value="Formatted research")

        research = agent._perform_research([mock_position], ["German stocks"])

        assert research == "Formatted research"
        agent.research.aggregate_research.assert_called_once()

    def test_parse_decision_valid_json(self, agent):
        """Test parsing valid decision JSON."""
        json_response = json.dumps({
            "action": "BUY",
            "symbol": "SAP.DE",
            "quantity": 10,
            "reasoning": "Good earnings report",
            "confidence": "HIGH",
            "market_outlook": "Bullish",
            "risk_assessment": "Low"
        })

        decision = agent._parse_decision(json_response)

        assert decision["action"] == "BUY"
        assert decision["symbol"] == "SAP.DE"
        assert decision["quantity"] == 10

    def test_parse_decision_with_markdown(self, agent):
        """Test parsing decision with markdown code blocks."""
        markdown_response = """```json
{
    "action": "SELL",
    "symbol": "BMW.DE",
    "quantity": 5,
    "reasoning": "Taking profits",
    "confidence": "MEDIUM"
}
```"""

        decision = agent._parse_decision(markdown_response)

        assert decision["action"] == "SELL"
        assert decision["symbol"] == "BMW.DE"

    def test_parse_decision_missing_field(self, agent):
        """Test parsing decision with missing required field."""
        invalid_json = json.dumps({
            "action": "BUY",
            "symbol": "SAP.DE"
            # Missing "reasoning" and "confidence"
        })

        with pytest.raises(ValueError, match="Missing required field"):
            agent._parse_decision(invalid_json)

    def test_parse_decision_invalid_action(self, agent):
        """Test parsing decision with invalid action."""
        invalid_json = json.dumps({
            "action": "INVALID",
            "reasoning": "Test",
            "confidence": "HIGH"
        })

        with pytest.raises(ValueError, match="Invalid action"):
            agent._parse_decision(invalid_json)

    def test_parse_decision_buy_missing_symbol(self, agent):
        """Test parsing BUY decision without symbol."""
        invalid_json = json.dumps({
            "action": "BUY",
            "quantity": 10,
            "reasoning": "Test",
            "confidence": "HIGH"
            # Missing "symbol"
        })

        with pytest.raises(ValueError, match="require symbol and quantity"):
            agent._parse_decision(invalid_json)

    def test_parse_decision_invalid_json(self, agent):
        """Test parsing invalid JSON."""
        invalid_json = "This is not JSON"

        with pytest.raises(ValueError, match="Invalid JSON response"):
            agent._parse_decision(invalid_json)

    def test_execute_decision_hold(self, agent):
        """Test executing HOLD decision."""
        decision = {"action": "HOLD", "reasoning": "Wait for better opportunity"}

        result = agent._execute_decision(decision)

        assert result["success"] is True
        assert result["action"] == "HOLD"

    def test_execute_decision_buy(self, agent):
        """Test executing BUY decision."""
        decision = {
            "action": "BUY",
            "symbol": "SAP.DE",
            "quantity": 10,
            "reasoning": "Strong earnings"
        }

        agent.trading_engine.execute_buy = Mock(return_value={
            "success": True,
            "position": Mock()
        })

        result = agent._execute_decision(decision)

        agent.trading_engine.execute_buy.assert_called_once_with(
            model_id=1,
            symbol="SAP.DE",
            quantity=10
        )
        assert result["success"] is True

    def test_execute_decision_sell(self, agent):
        """Test executing SELL decision."""
        decision = {
            "action": "SELL",
            "symbol": "BMW.DE",
            "quantity": 5,
            "reasoning": "Taking profits"
        }

        agent.trading_engine.execute_sell = Mock(return_value={
            "success": True,
            "realized_pl": 50.0
        })

        result = agent._execute_decision(decision)

        agent.trading_engine.execute_sell.assert_called_once_with(
            model_id=1,
            symbol="BMW.DE",
            quantity=5
        )
        assert result["success"] is True

    def test_execute_decision_error(self, agent):
        """Test executing decision with error."""
        decision = {
            "action": "BUY",
            "symbol": "SAP.DE",
            "quantity": 10,
            "reasoning": "Test"
        }

        agent.trading_engine.execute_buy = Mock(side_effect=Exception("Insufficient funds"))

        result = agent._execute_decision(decision)

        assert result["success"] is False
        assert "error" in result

    def test_store_reasoning(self, agent, db_session):
        """Test storing reasoning in database."""
        research = "Market research content"
        decision = {"action": "BUY", "reasoning": "Good opportunity"}

        agent._store_reasoning(research, decision)

        db_session.add.assert_called_once()
        db_session.commit.assert_called_once()

    def test_format_prompt(self, agent, mock_portfolio, mock_position):
        """Test formatting the trading prompt."""
        market_data = {
            "SAP.DE": {
                "price": 125.50,
                "high": 127.00,
                "low": 124.00,
                "volume": 100000
            }
        }

        prompt = agent._format_prompt(
            mock_portfolio,
            [mock_position],
            market_data,
            "Research content"
        )

        assert "GPT-4 Test" in prompt
        assert "€850.00" in prompt  # current balance
        assert "SAP.DE" in prompt
        assert "Research content" in prompt
        assert "TRADING RULES" in prompt

    def test_make_trading_decision_success(self, agent, db_session, mock_portfolio, mock_position):
        """Test complete trading decision flow."""
        # Mock all dependencies
        db_session.query.return_value.filter.return_value.first.return_value = mock_portfolio
        db_session.query.return_value.filter.return_value.all.return_value = [mock_position]

        agent.market_data.fetch_price = Mock(return_value={"price": 125.50})
        agent.research.aggregate_research = Mock(return_value={"summary": "test"})
        agent.research.format_research_for_llm = Mock(return_value="Research")

        agent.openrouter.get_completion_text = Mock(return_value=json.dumps({
            "action": "HOLD",
            "reasoning": "Wait for better entry",
            "confidence": "MEDIUM",
            "market_outlook": "Neutral",
            "risk_assessment": "Low"
        }))

        result = agent.make_trading_decision(perform_research=True)

        assert result["success"] is True
        assert "decision" in result
        assert result["decision"]["action"] == "HOLD"

    def test_make_trading_decision_error(self, agent, db_session):
        """Test trading decision handles errors."""
        db_session.query.side_effect = Exception("Database error")

        result = agent.make_trading_decision()

        assert result["success"] is False
        assert "error" in result

    def test_context_manager(self, db_session, mock_model):
        """Test agent works as context manager."""
        db_session.query.return_value.filter.return_value.first.return_value = mock_model

        with patch('backend.services.llm_agent.OpenRouterClient') as mock_or:
            with patch('backend.services.llm_agent.ResearchService') as mock_rs:
                with patch('backend.services.llm_agent.MarketDataService'):
                    with patch('backend.services.llm_agent.TradingEngine'):
                        with LLMAgent(db_session, model_id=1) as agent:
                            assert agent is not None

                        # Verify close was called
                        mock_or.return_value.close.assert_called_once()
                        mock_rs.return_value.close.assert_called_once()
