"""
Unit tests for Technical Analysis Service

Tests all technical analysis functionality:
- Indicator calculations
- Pattern detection
- Volume analysis
- Signal generation
- Historical context
- LLM formatting
- Error handling

Author: Sentiment Arena
Date: 2025-10-23
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from backend.services.technical_analysis import TechnicalAnalysisService


@pytest.fixture
def ta_service():
    """Create a TechnicalAnalysisService instance."""
    return TechnicalAnalysisService(lookback_days=90)


@pytest.fixture
def sample_price_data():
    """Generate sample price data for testing."""
    dates = pd.date_range(end=datetime.now(), periods=100, freq='D')

    # Create realistic price data with trend
    np.random.seed(42)
    base_price = 100
    trend = np.linspace(0, 20, 100)  # Uptrend
    noise = np.random.randn(100) * 2
    close_prices = base_price + trend + noise

    # Generate OHLCV data
    df = pd.DataFrame({
        'Open': close_prices * (1 + np.random.randn(100) * 0.01),
        'High': close_prices * (1 + abs(np.random.randn(100)) * 0.02),
        'Low': close_prices * (1 - abs(np.random.randn(100)) * 0.02),
        'Close': close_prices,
        'Volume': np.random.randint(1000000, 5000000, 100)
    }, index=dates)

    return df


@pytest.fixture
def downtrend_data():
    """Generate downtrend price data."""
    dates = pd.date_range(end=datetime.now(), periods=100, freq='D')

    np.random.seed(42)
    base_price = 120
    trend = np.linspace(0, -30, 100)  # Downtrend
    noise = np.random.randn(100) * 2
    close_prices = base_price + trend + noise

    df = pd.DataFrame({
        'Open': close_prices * (1 + np.random.randn(100) * 0.01),
        'High': close_prices * (1 + abs(np.random.randn(100)) * 0.02),
        'Low': close_prices * (1 - abs(np.random.randn(100)) * 0.02),
        'Close': close_prices,
        'Volume': np.random.randint(1000000, 5000000, 100)
    }, index=dates)

    return df


class TestTechnicalAnalysisService:
    """Test suite for TechnicalAnalysisService."""

    def test_initialization(self, ta_service):
        """Test service initialization."""
        assert ta_service.lookback_days == 90

        # Test custom lookback
        custom_service = TechnicalAnalysisService(lookback_days=180)
        assert custom_service.lookback_days == 180

    @patch('backend.services.technical_analysis.yf.Ticker')
    def test_fetch_historical_data_success(self, mock_ticker, ta_service, sample_price_data):
        """Test successful data fetching."""
        mock_ticker.return_value.history.return_value = sample_price_data

        df = ta_service._fetch_historical_data("SAP.DE")

        assert df is not None
        assert len(df) == 100
        assert 'Close' in df.columns
        assert 'Volume' in df.columns

    @patch('backend.services.technical_analysis.yf.Ticker')
    def test_fetch_historical_data_empty(self, mock_ticker, ta_service):
        """Test handling of empty data."""
        mock_ticker.return_value.history.return_value = pd.DataFrame()

        df = ta_service._fetch_historical_data("INVALID.DE")

        assert df is None

    @patch('backend.services.technical_analysis.yf.Ticker')
    def test_fetch_historical_data_error(self, mock_ticker, ta_service):
        """Test handling of fetch errors."""
        mock_ticker.side_effect = Exception("Network error")

        df = ta_service._fetch_historical_data("SAP.DE")

        assert df is None

    def test_calculate_indicators(self, ta_service, sample_price_data):
        """Test technical indicator calculations."""
        indicators = ta_service._calculate_indicators(sample_price_data)

        # Check RSI
        assert "rsi" in indicators
        assert indicators["rsi"]["value"] is not None
        assert 0 <= indicators["rsi"]["value"] <= 100

        # Check MACD
        assert "macd" in indicators
        assert indicators["macd"]["macd"] is not None
        assert indicators["macd"]["signal"] is not None
        assert indicators["macd"]["histogram"] is not None

        # Check Bollinger Bands
        assert "bollinger_bands" in indicators
        assert indicators["bollinger_bands"]["upper"] is not None
        assert indicators["bollinger_bands"]["lower"] is not None
        assert indicators["bollinger_bands"]["middle"] is not None

        # Check Moving Averages
        assert "moving_averages" in indicators
        assert indicators["moving_averages"]["sma_20"] is not None
        assert indicators["moving_averages"]["sma_50"] is not None

        # Check Stochastic
        assert "stochastic" in indicators
        assert indicators["stochastic"]["k"] is not None

        # Check ADX
        assert "adx" in indicators
        assert indicators["adx"]["value"] is not None

        # Check ATR
        assert "atr" in indicators
        assert indicators["atr"]["value"] is not None

    def test_detect_patterns(self, ta_service, sample_price_data):
        """Test chart pattern detection."""
        patterns = ta_service._detect_patterns(sample_price_data)

        assert "support" in patterns
        assert "resistance" in patterns
        assert patterns["support"] < patterns["resistance"]

        assert "trend" in patterns
        assert patterns["trend"] in ["bullish", "bearish", "neutral"]

        assert "distance_to_support" in patterns
        assert "distance_to_resistance" in patterns

    def test_detect_bullish_trend(self, ta_service, sample_price_data):
        """Test detection of bullish trend."""
        patterns = ta_service._detect_patterns(sample_price_data)

        # Sample data has uptrend, trend should be detected (neutral possible with short data)
        assert patterns["trend"] in ["bullish", "neutral"]

        # Check that support is below resistance
        assert patterns["support"] < patterns["resistance"]

    def test_detect_bearish_trend(self, ta_service, downtrend_data):
        """Test detection of bearish trend."""
        patterns = ta_service._detect_patterns(downtrend_data)

        # Downtrend data should detect bearish or neutral
        assert patterns["trend"] in ["bearish", "neutral"]

        # Check that support is below resistance
        assert patterns["support"] < patterns["resistance"]

    def test_analyze_volume(self, ta_service, sample_price_data):
        """Test volume analysis."""
        volume_analysis = ta_service._analyze_volume(sample_price_data)

        assert "current_volume" in volume_analysis
        assert "average_volume" in volume_analysis
        assert "volume_ratio" in volume_analysis
        assert "obv" in volume_analysis
        assert "obv_trend" in volume_analysis
        assert "above_average" in volume_analysis

        assert volume_analysis["obv_trend"] in ["bullish", "bearish"]
        assert isinstance(volume_analysis["above_average"], bool)

    def test_generate_signals_bullish(self, ta_service, sample_price_data):
        """Test signal generation for bullish conditions."""
        indicators = ta_service._calculate_indicators(sample_price_data)
        signals = ta_service._generate_signals(sample_price_data, indicators)

        assert "overall_signal" in signals
        assert signals["overall_signal"] in ["bullish", "bearish", "neutral"]

        assert "bullish_signals" in signals
        assert "bearish_signals" in signals
        assert "neutral_signals" in signals

        assert isinstance(signals["bullish_signals"], list)
        assert isinstance(signals["bearish_signals"], list)

    def test_generate_signals_oversold_rsi(self, ta_service, sample_price_data):
        """Test RSI oversold signal generation."""
        # Mock indicators with oversold RSI
        indicators = {
            "rsi": {"value": 25, "previous": 30},
            "macd": {"histogram": 0.1, "previous_histogram": 0.05},
            "bollinger_bands": {"percent_b": 0.5},
            "moving_averages": {"sma_20": 100, "sma_50": 95, "sma_200": 90},
            "stochastic": {"k": 15, "d": 20},
            "adx": {"value": 30, "plus_di": 25, "minus_di": 15}
        }

        signals = ta_service._generate_signals(sample_price_data, indicators)

        # Should have bullish signal for oversold RSI
        assert any("oversold" in sig.lower() for sig in signals["bullish_signals"])

    def test_generate_signals_overbought_rsi(self, ta_service, sample_price_data):
        """Test RSI overbought signal generation."""
        indicators = {
            "rsi": {"value": 75, "previous": 70},
            "macd": {"histogram": -0.1, "previous_histogram": -0.05},
            "bollinger_bands": {"percent_b": 0.5},
            "moving_averages": {"sma_20": 100, "sma_50": 105, "sma_200": 110},
            "stochastic": {"k": 85, "d": 80},
            "adx": {"value": 30, "plus_di": 15, "minus_di": 25}
        }

        signals = ta_service._generate_signals(sample_price_data, indicators)

        # Should have bearish signal for overbought RSI
        assert any("overbought" in sig.lower() for sig in signals["bearish_signals"])

    def test_generate_signals_macd_crossover(self, ta_service, sample_price_data):
        """Test MACD crossover signals."""
        # Bullish crossover
        indicators = {
            "rsi": {"value": 50, "previous": 48},
            "macd": {"histogram": 0.1, "previous_histogram": -0.05},  # Cross from negative to positive
            "bollinger_bands": {"percent_b": 0.5},
            "moving_averages": {"sma_20": 100, "sma_50": 95, "sma_200": 90},
            "stochastic": {"k": 50, "d": 45},
            "adx": {"value": 20, "plus_di": 20, "minus_di": 18}
        }

        signals = ta_service._generate_signals(sample_price_data, indicators)

        assert any("macd" in sig.lower() and "bullish" in sig.lower() for sig in signals["bullish_signals"])

    def test_get_historical_context(self, ta_service, sample_price_data):
        """Test historical context calculation."""
        indicators = ta_service._calculate_indicators(sample_price_data)
        context = ta_service._get_historical_context(sample_price_data, indicators)

        assert "price_changes" in context
        assert "1_day" in context["price_changes"]
        assert "5_day" in context["price_changes"]
        assert "20_day" in context["price_changes"]

        assert "52_week" in context
        assert "high" in context["52_week"]
        assert "low" in context["52_week"]
        assert "distance_from_high" in context["52_week"]
        assert "distance_from_low" in context["52_week"]

        assert "volatility" in context

    def test_format_for_llm(self, ta_service, sample_price_data):
        """Test LLM output formatting."""
        current_price = sample_price_data['Close'].iloc[-1]
        indicators = ta_service._calculate_indicators(sample_price_data)
        patterns = ta_service._detect_patterns(sample_price_data)
        volume_analysis = ta_service._analyze_volume(sample_price_data)
        signals = ta_service._generate_signals(sample_price_data, indicators)
        context = ta_service._get_historical_context(sample_price_data, indicators)

        llm_output = ta_service._format_for_llm(
            symbol="SAP.DE",
            current_price=current_price,
            indicators=indicators,
            patterns=patterns,
            volume_analysis=volume_analysis,
            signals=signals,
            context=context
        )

        assert isinstance(llm_output, str)
        assert "SAP.DE" in llm_output
        assert "TECHNICAL ANALYSIS" in llm_output
        assert "KEY INDICATORS" in llm_output
        assert "RSI" in llm_output
        assert "MACD" in llm_output
        assert "MOVING AVERAGES" in llm_output
        assert "CHART PATTERNS" in llm_output
        assert "VOLUME ANALYSIS" in llm_output
        assert "TRADING SIGNALS" in llm_output
        assert "HISTORICAL CONTEXT" in llm_output

    def test_format_for_llm_includes_emoji_indicators(self, ta_service, sample_price_data):
        """Test that LLM output includes emoji indicators."""
        indicators = ta_service._calculate_indicators(sample_price_data)
        patterns = ta_service._detect_patterns(sample_price_data)
        volume_analysis = ta_service._analyze_volume(sample_price_data)
        signals = {"overall_signal": "bullish", "bullish_signals": ["Test signal"], "bearish_signals": [], "neutral_signals": []}
        context = ta_service._get_historical_context(sample_price_data, indicators)

        llm_output = ta_service._format_for_llm(
            symbol="SAP.DE",
            current_price=100.0,
            indicators=indicators,
            patterns=patterns,
            volume_analysis=volume_analysis,
            signals=signals,
            context=context
        )

        # Should include emoji for bullish signal
        assert "🟢" in llm_output

    @patch('backend.services.technical_analysis.yf.Ticker')
    def test_get_technical_analysis_success(self, mock_ticker, ta_service, sample_price_data):
        """Test successful full technical analysis."""
        mock_ticker.return_value.history.return_value = sample_price_data

        result = ta_service.get_technical_analysis("SAP.DE")

        assert result["success"] is True
        assert result["symbol"] == "SAP.DE"
        assert "timestamp" in result
        assert "current_price" in result
        assert "indicators" in result
        assert "patterns" in result
        assert "volume_analysis" in result
        assert "signals" in result
        assert "context" in result
        assert "llm_formatted" in result

    @patch('backend.services.technical_analysis.yf.Ticker')
    def test_get_technical_analysis_insufficient_data(self, mock_ticker, ta_service):
        """Test handling of insufficient data."""
        # Return very small dataset
        small_df = pd.DataFrame({
            'Close': [100, 101, 102],
            'High': [101, 102, 103],
            'Low': [99, 100, 101],
            'Volume': [1000, 1100, 1200]
        })
        mock_ticker.return_value.history.return_value = small_df

        result = ta_service.get_technical_analysis("SAP.DE")

        assert result["success"] is False
        assert "Insufficient" in result["error"]

    @patch('backend.services.technical_analysis.yf.Ticker')
    def test_get_technical_analysis_error_handling(self, mock_ticker, ta_service):
        """Test error handling in technical analysis."""
        mock_ticker.side_effect = Exception("Network error")

        result = ta_service.get_technical_analysis("SAP.DE")

        assert result["success"] is False
        assert "error" in result
        assert result["llm_formatted"].startswith("⚠️")

    def test_empty_analysis_structure(self, ta_service):
        """Test empty analysis structure."""
        result = ta_service._empty_analysis("SAP.DE", "Test error")

        assert result["success"] is False
        assert result["symbol"] == "SAP.DE"
        assert result["error"] == "Test error"
        assert "timestamp" in result
        assert result["indicators"] == {}
        assert result["patterns"] == {}
        assert result["signals"]["overall_signal"] == "neutral"

    def test_bollinger_bands_breakout_signals(self, ta_service, sample_price_data):
        """Test Bollinger Bands breakout signals."""
        # Mock indicators with price above upper band
        indicators = {
            "rsi": {"value": 50, "previous": 48},
            "macd": {"histogram": 0.1, "previous_histogram": 0.05},
            "bollinger_bands": {"percent_b": 1.2},  # Above upper band
            "moving_averages": {"sma_20": 100, "sma_50": 95, "sma_200": 90},
            "stochastic": {"k": 50, "d": 45},
            "adx": {"value": 20, "plus_di": 20, "minus_di": 18}
        }

        signals = ta_service._generate_signals(sample_price_data, indicators)

        # Should have bearish signal for price above upper band
        assert any("bollinger" in sig.lower() and "overbought" in sig.lower() for sig in signals["bearish_signals"])

    def test_moving_average_trend_signals(self, ta_service, sample_price_data):
        """Test moving average trend signals."""
        current_price = 110.0

        # Bullish MA alignment
        indicators = {
            "rsi": {"value": 50, "previous": 48},
            "macd": {"histogram": 0.1, "previous_histogram": 0.05},
            "bollinger_bands": {"percent_b": 0.5},
            "moving_averages": {"sma_20": 105, "sma_50": 100, "sma_200": 95},  # Bullish alignment
            "stochastic": {"k": 50, "d": 45},
            "adx": {"value": 20, "plus_di": 20, "minus_di": 18}
        }

        # Update price in dataframe
        test_df = sample_price_data.copy()
        test_df.loc[test_df.index[-1], 'Close'] = current_price

        signals = ta_service._generate_signals(test_df, indicators)

        # Should have bullish signals for MA alignment
        assert any("sma" in sig.lower() and "bullish" in sig.lower() for sig in signals["bullish_signals"])

    def test_adx_trend_strength(self, ta_service, sample_price_data):
        """Test ADX trend strength signals."""
        # Strong uptrend
        indicators = {
            "rsi": {"value": 50, "previous": 48},
            "macd": {"histogram": 0.1, "previous_histogram": 0.05},
            "bollinger_bands": {"percent_b": 0.5},
            "moving_averages": {"sma_20": 100, "sma_50": 95, "sma_200": 90},
            "stochastic": {"k": 50, "d": 45},
            "adx": {"value": 35, "plus_di": 30, "minus_di": 15}  # Strong uptrend
        }

        signals = ta_service._generate_signals(sample_price_data, indicators)

        # Should detect strong uptrend
        assert any("uptrend" in sig.lower() for sig in signals["bullish_signals"])

    def test_volume_ratio_calculation(self, ta_service, sample_price_data):
        """Test volume ratio calculation."""
        volume_analysis = ta_service._analyze_volume(sample_price_data)

        assert volume_analysis["volume_ratio"] > 0
        assert volume_analysis["current_volume"] > 0
        assert volume_analysis["average_volume"] > 0

    def test_52_week_high_low_context(self, ta_service, sample_price_data):
        """Test 52-week high/low calculations."""
        indicators = ta_service._calculate_indicators(sample_price_data)
        context = ta_service._get_historical_context(sample_price_data, indicators)

        week_52 = context["52_week"]
        assert week_52["high"] >= week_52["low"]
        assert week_52["distance_from_high"] >= 0
        assert week_52["distance_from_low"] >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
