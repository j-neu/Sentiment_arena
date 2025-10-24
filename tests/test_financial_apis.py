"""
Unit tests for Financial Data API Integration (Phase 3.5.2).

Tests for:
- AlphaVantageClient
- FinnhubClient
- FinancialDataAggregator
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path.parent))

from backend.services.alphavantage_client import AlphaVantageClient
from backend.services.finnhub_client import FinnhubClient
from backend.services.financial_data_aggregator import FinancialDataAggregator


# ============================================================================
# AlphaVantageClient Tests
# ============================================================================

class TestAlphaVantageClient:
    """Tests for AlphaVantageClient."""

    @pytest.fixture
    def av_client(self):
        """Create AlphaVantageClient with mock API key."""
        return AlphaVantageClient(api_key="test_key")

    def test_initialization(self, av_client):
        """Test client initialization."""
        assert av_client.api_key == "test_key"
        assert av_client.min_call_interval == 12

    def test_rate_limiting(self, av_client):
        """Test rate limiting enforcement."""
        import time

        start = time.time()
        av_client._rate_limit()
        av_client._rate_limit()
        elapsed = time.time() - start

        # Should wait at least min_call_interval
        assert elapsed >= av_client.min_call_interval

    @patch('backend.services.alphavantage_client.requests.Session.get')
    def test_get_company_overview_success(self, mock_get, av_client):
        """Test successful company overview fetch."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "Symbol": "SAP",
            "Name": "SAP SE",
            "Sector": "Technology",
            "Industry": "Software",
            "MarketCapitalization": "150000000000",
            "PERatio": "25.5",
            "ForwardPE": "22.3",
            "EPS": "5.45",
            "ProfitMargin": "0.22",
            "Beta": "1.15",
            "52WeekHigh": "135.50",
            "52WeekLow": "105.20"
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = av_client.get_company_overview("SAP.DE")

        assert result is not None
        assert result["symbol"] == "SAP"
        assert result["name"] == "SAP SE"
        assert result["sector"] == "Technology"
        assert result["pe_ratio"] == 25.5
        assert result["market_cap"] == 150000000000.0

    @patch('backend.services.alphavantage_client.requests.Session.get')
    def test_get_company_overview_error(self, mock_get, av_client):
        """Test company overview with API error."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "Error Message": "Invalid API call"
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = av_client.get_company_overview("INVALID")

        assert result is None

    @patch('backend.services.alphavantage_client.requests.Session.get')
    def test_get_earnings_success(self, mock_get, av_client):
        """Test successful earnings fetch."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "symbol": "SAP",
            "quarterlyEarnings": [
                {
                    "fiscalDateEnding": "2024-09-30",
                    "reportedEPS": "1.45",
                    "estimatedEPS": "1.38",
                    "surprise": "0.07",
                    "surprisePercentage": "5.07"
                }
            ],
            "annualEarnings": [
                {
                    "fiscalDateEnding": "2023-12-31",
                    "reportedEPS": "5.45"
                }
            ]
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = av_client.get_earnings("SAP")

        assert result is not None
        assert result["symbol"] == "SAP"
        assert result["latest_quarter"] is not None
        assert result["latest_quarter"]["reported_eps"] == 1.45
        assert result["latest_quarter"]["surprise_percentage"] == 5.07

    @patch('backend.services.alphavantage_client.requests.Session.get')
    def test_get_rsi_success(self, mock_get, av_client):
        """Test successful RSI fetch."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "Technical Analysis: RSI": {
                "2024-10-23": {"RSI": "45.67"},
                "2024-10-22": {"RSI": "43.21"}
            }
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = av_client.get_rsi("SAP")

        assert result is not None
        assert result["symbol"] == "SAP"
        assert result["rsi"] == 45.67
        assert result["interpretation"] == "neutral"

    @patch('backend.services.alphavantage_client.requests.Session.get')
    def test_get_rsi_overbought(self, mock_get, av_client):
        """Test RSI interpretation for overbought."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "Technical Analysis: RSI": {
                "2024-10-23": {"RSI": "75.5"}
            }
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = av_client.get_rsi("SAP")

        assert result["interpretation"] == "overbought"

    @patch('backend.services.alphavantage_client.requests.Session.get')
    def test_get_rsi_oversold(self, mock_get, av_client):
        """Test RSI interpretation for oversold."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "Technical Analysis: RSI": {
                "2024-10-23": {"RSI": "25.3"}
            }
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = av_client.get_rsi("SAP")

        assert result["interpretation"] == "oversold"

    @patch('backend.services.alphavantage_client.requests.Session.get')
    def test_get_macd_success(self, mock_get, av_client):
        """Test successful MACD fetch."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "Technical Analysis: MACD": {
                "2024-10-23": {
                    "MACD": "1.2345",
                    "MACD_Signal": "1.1234",
                    "MACD_Hist": "0.1111"
                },
                "2024-10-22": {
                    "MACD": "1.1234",
                    "MACD_Signal": "1.1500",
                    "MACD_Hist": "-0.0266"
                }
            }
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = av_client.get_macd("SAP")

        assert result is not None
        assert result["symbol"] == "SAP"
        assert result["macd"] == 1.2345
        assert result["crossover"] == "bullish"

    @patch('backend.services.alphavantage_client.requests.Session.get')
    def test_get_sma_success(self, mock_get, av_client):
        """Test successful SMA fetch."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "Technical Analysis: SMA": {
                "2024-10-23": {"SMA": "125.50"}
            }
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = av_client.get_sma("SAP", time_period=50)

        assert result is not None
        assert result["symbol"] == "SAP"
        assert result["sma"] == 125.50
        assert result["period"] == 50

    def test_context_manager(self):
        """Test context manager usage."""
        with AlphaVantageClient(api_key="test") as client:
            assert client.api_key == "test"


# ============================================================================
# FinnhubClient Tests
# ============================================================================

class TestFinnhubClient:
    """Tests for FinnhubClient."""

    @pytest.fixture
    def fh_client(self):
        """Create FinnhubClient with mock API key."""
        return FinnhubClient(api_key="test_key")

    def test_initialization(self, fh_client):
        """Test client initialization."""
        assert fh_client.api_key == "test_key"
        assert fh_client.min_call_interval == 1.0

    @patch('backend.services.finnhub_client.requests.Session.get')
    def test_get_company_news_success(self, mock_get, fh_client):
        """Test successful company news fetch."""
        mock_response = Mock()
        mock_response.json.return_value = [
            {
                "headline": "SAP Reports Strong Q3 Earnings",
                "summary": "SAP beats expectations",
                "source": "Reuters",
                "url": "https://example.com/news1",
                "datetime": 1698000000,
                "category": "company"
            }
        ]
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = fh_client.get_company_news("SAP", days_back=7)

        assert result is not None
        assert len(result) == 1
        assert result[0]["headline"] == "SAP Reports Strong Q3 Earnings"
        assert result[0]["source"] == "Reuters"
        assert "sentiment" in result[0]

    @patch('backend.services.finnhub_client.requests.Session.get')
    def test_get_recommendation_trends_success(self, mock_get, fh_client):
        """Test successful recommendation trends fetch."""
        mock_response = Mock()
        mock_response.json.return_value = [
            {
                "period": "2024-10",
                "strongBuy": 10,
                "buy": 8,
                "hold": 5,
                "sell": 2,
                "strongSell": 0
            }
        ]
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = fh_client.get_recommendation_trends("SAP")

        assert result is not None
        assert result["symbol"] == "SAP"
        assert result["strong_buy"] == 10
        assert result["total_analysts"] == 25
        assert result["consensus"] == "strong_buy"

    @patch('backend.services.finnhub_client.requests.Session.get')
    def test_get_price_target_success(self, mock_get, fh_client):
        """Test successful price target fetch."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "targetHigh": 145.0,
            "targetLow": 115.0,
            "targetMean": 130.0,
            "targetMedian": 128.0,
            "numberOfAnalysts": 25
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = fh_client.get_price_target("SAP")

        assert result is not None
        assert result["target_mean"] == 130.0
        assert result["num_analysts"] == 25

    @patch('backend.services.finnhub_client.requests.Session.get')
    def test_get_sentiment_success(self, mock_get, fh_client):
        """Test successful sentiment fetch."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "buzz": {
                "articlesInLastWeek": 45,
                "weeklyAverage": 38.5
            },
            "sentiment": {
                "bullishPercent": 65.0,
                "bearishPercent": 35.0
            },
            "companyNewsScore": 0.72,
            "sectorAverageNewsScore": 0.65
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = fh_client.get_sentiment("SAP")

        assert result is not None
        assert result["sentiment_bullish"] == 65.0
        # 65% - 35% = 30% difference, so it's "very_bullish" (>20% difference)
        assert result["interpretation"] == "very_bullish"

    def test_analyze_headline_sentiment_positive(self, fh_client):
        """Test positive headline sentiment."""
        sentiment = fh_client._analyze_headline_sentiment("Stock soars on earnings beat")
        assert sentiment == "positive"

    def test_analyze_headline_sentiment_negative(self, fh_client):
        """Test negative headline sentiment."""
        sentiment = fh_client._analyze_headline_sentiment("Company shares plunge on miss")
        assert sentiment == "negative"

    def test_analyze_headline_sentiment_neutral(self, fh_client):
        """Test neutral headline sentiment."""
        sentiment = fh_client._analyze_headline_sentiment("Company announces new CEO")
        assert sentiment == "neutral"

    def test_calculate_consensus_strong_buy(self, fh_client):
        """Test consensus calculation for strong buy."""
        consensus = fh_client._calculate_consensus({
            "strongBuy": 10, "buy": 5, "hold": 2, "sell": 0, "strongSell": 0
        })
        assert consensus == "strong_buy"

    def test_calculate_consensus_hold(self, fh_client):
        """Test consensus calculation for hold."""
        # 5 buys out of 20 total = 25% buy ratio, which falls into "sell" category (<30%)
        consensus = fh_client._calculate_consensus({
            "strongBuy": 2, "buy": 3, "hold": 10, "sell": 3, "strongSell": 2
        })
        assert consensus == "sell"  # 25% buy ratio is <30%, so "sell" consensus


# ============================================================================
# FinancialDataAggregator Tests
# ============================================================================

class TestFinancialDataAggregator:
    """Tests for FinancialDataAggregator."""

    @pytest.fixture
    def aggregator(self):
        """Create aggregator with mocked clients."""
        with patch('backend.services.financial_data_aggregator.SessionLocal'):
            agg = FinancialDataAggregator(
                alphavantage_key="test_av",
                finnhub_key="test_fh",
                use_cache=False
            )
            agg.av_client = Mock()
            agg.fh_client = Mock()
            return agg

    def test_initialization(self, aggregator):
        """Test aggregator initialization."""
        assert aggregator.use_cache is False
        assert aggregator.av_client is not None
        assert aggregator.fh_client is not None

    def test_get_complete_analysis_success(self, aggregator):
        """Test complete analysis with all data."""
        # Mock Alpha Vantage responses
        aggregator.av_client.get_company_overview.return_value = {
            "symbol": "SAP",
            "name": "SAP SE",
            "sector": "Technology",
            "market_cap": 150000000000,
            "pe_ratio": 25.5
        }
        aggregator.av_client.get_earnings.return_value = {
            "symbol": "SAP",
            "latest_quarter": {
                "fiscal_date_ending": "2024-09-30",
                "reported_eps": 1.45,
                "surprise_percentage": 5.0
            }
        }
        aggregator.av_client.get_rsi.return_value = {
            "rsi": 55.5,
            "interpretation": "neutral"
        }
        aggregator.av_client.get_macd.return_value = {
            "macd": 1.23,
            "interpretation": "bullish_crossover"
        }
        aggregator.av_client.get_sma.return_value = {"sma": 125.0}

        # Mock Finnhub responses
        aggregator.fh_client.get_company_news.return_value = [
            {
                "headline": "Good news",
                "sentiment": "positive",
                "source": "Reuters",
                "datetime": datetime.now()
            }
        ]
        aggregator.fh_client.get_sentiment.return_value = {
            "sentiment_bullish": 65.0,
            "interpretation": "bullish"
        }
        aggregator.fh_client.get_recommendation_trends.return_value = {
            "consensus": "buy",
            "total_analysts": 25
        }
        aggregator.fh_client.get_price_target.return_value = {
            "target_mean": 135.0
        }

        result = aggregator.get_complete_analysis("SAP.DE")

        assert result["success"] is True
        assert len(result["errors"]) == 0
        assert "fundamentals" in result["data"]
        assert "technicals" in result["data"]
        assert "news" in result["data"]
        assert "analyst_ratings" in result["data"]

    def test_format_for_llm(self, aggregator):
        """Test LLM formatting."""
        analysis = {
            "symbol": "SAP.DE",
            "timestamp": datetime.now().isoformat(),
            "success": True,
            "errors": [],
            "data": {
                "fundamentals": {
                    "overview": {
                        "name": "SAP SE",
                        "sector": "Technology",
                        "market_cap": 150000000000,
                        "pe_ratio": 25.5
                    }
                },
                "technicals": {
                    "rsi": {"rsi": 55.0, "interpretation": "neutral"}
                },
                "news": {
                    "sentiment_score": {
                        "sentiment_bullish": 65.0,
                        "interpretation": "bullish"
                    }
                },
                "analyst_ratings": {
                    "recommendations": {
                        "consensus": "buy",
                        "total_analysts": 25
                    }
                }
            }
        }

        formatted = aggregator.format_for_llm(analysis)

        assert "SAP.DE" in formatted
        assert "FUNDAMENTALS" in formatted
        assert "TECHNICAL" in formatted
        assert "NEWS" in formatted
        assert "ANALYST" in formatted

    def test_format_for_llm_with_errors(self, aggregator):
        """Test LLM formatting with errors."""
        analysis = {
            "success": False,
            "errors": ["API error", "Network timeout"]
        }

        formatted = aggregator.format_for_llm(analysis)

        assert "Failed" in formatted
        assert "API error" in formatted


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
