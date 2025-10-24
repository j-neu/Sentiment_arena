"""
Unit tests for Market Data Service
"""

import pytest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database.base import Base
from backend.models.market_data import MarketData
from backend.services.market_data import MarketDataService
from backend.config import settings


@pytest.fixture
def db_session():
    """Create an in-memory SQLite database for testing"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def market_service(db_session):
    """Create a MarketDataService instance for testing"""
    return MarketDataService(db_session)


class TestMarketHoursAndDays:
    """Test market hours and trading day validation"""

    def test_is_trading_day_weekday(self, market_service):
        """Test that weekdays are trading days"""
        # Monday, Jan 8, 2024
        monday = datetime(2024, 1, 8, 12, 0, 0, tzinfo=ZoneInfo("Europe/Berlin"))
        assert market_service.is_trading_day(monday) is True

    def test_is_trading_day_weekend(self, market_service):
        """Test that weekends are not trading days"""
        # Saturday, Jan 6, 2024
        saturday = datetime(2024, 1, 6, 12, 0, 0, tzinfo=ZoneInfo("Europe/Berlin"))
        assert market_service.is_trading_day(saturday) is False

        # Sunday, Jan 7, 2024
        sunday = datetime(2024, 1, 7, 12, 0, 0, tzinfo=ZoneInfo("Europe/Berlin"))
        assert market_service.is_trading_day(sunday) is False

    def test_is_trading_day_holiday(self, market_service):
        """Test that holidays are not trading days"""
        # New Year's Day 2024
        new_year = datetime(2024, 1, 1, 12, 0, 0, tzinfo=ZoneInfo("Europe/Berlin"))
        assert market_service.is_trading_day(new_year) is False

        # Christmas 2024
        christmas = datetime(2024, 12, 25, 12, 0, 0, tzinfo=ZoneInfo("Europe/Berlin"))
        assert market_service.is_trading_day(christmas) is False

    def test_is_market_open_during_hours(self, market_service):
        """Test that market is open during trading hours"""
        # Monday, Jan 8, 2024 at 10:00 AM CET
        trading_time = datetime(2024, 1, 8, 10, 0, 0, tzinfo=ZoneInfo("Europe/Berlin"))
        assert market_service.is_market_open(trading_time) is True

    def test_is_market_open_before_hours(self, market_service):
        """Test that market is closed before trading hours"""
        # Monday, Jan 8, 2024 at 8:00 AM CET
        before_market = datetime(2024, 1, 8, 8, 0, 0, tzinfo=ZoneInfo("Europe/Berlin"))
        assert market_service.is_market_open(before_market) is False

    def test_is_market_open_after_hours(self, market_service):
        """Test that market is closed after trading hours"""
        # Monday, Jan 8, 2024 at 6:00 PM CET
        after_market = datetime(2024, 1, 8, 18, 0, 0, tzinfo=ZoneInfo("Europe/Berlin"))
        assert market_service.is_market_open(after_market) is False

    def test_is_market_open_at_open(self, market_service):
        """Test that market is open at exactly opening time"""
        # Monday, Jan 8, 2024 at 9:00 AM CET
        market_open = datetime(2024, 1, 8, 9, 0, 0, tzinfo=ZoneInfo("Europe/Berlin"))
        assert market_service.is_market_open(market_open) is True

    def test_is_market_open_at_close(self, market_service):
        """Test that market is open at exactly closing time"""
        # Monday, Jan 8, 2024 at 5:30 PM CET
        market_close = datetime(2024, 1, 8, 17, 30, 0, tzinfo=ZoneInfo("Europe/Berlin"))
        assert market_service.is_market_open(market_close) is True

    def test_is_market_open_weekend(self, market_service):
        """Test that market is closed on weekends"""
        # Saturday, Jan 6, 2024 at 10:00 AM CET
        saturday = datetime(2024, 1, 6, 10, 0, 0, tzinfo=ZoneInfo("Europe/Berlin"))
        assert market_service.is_market_open(saturday) is False


class TestSymbolValidation:
    """Test stock symbol validation"""

    def test_validate_symbol_valid(self, market_service):
        """Test validation of valid German stock symbols"""
        assert market_service.validate_symbol("SAP.DE") is True
        assert market_service.validate_symbol("VOW3.DE") is True
        assert market_service.validate_symbol("DBK.DE") is True
        assert market_service.validate_symbol("BMW.DE") is True

    def test_validate_symbol_invalid_format(self, market_service):
        """Test validation of invalid symbol formats"""
        assert market_service.validate_symbol("SAP") is False  # Missing .DE
        assert market_service.validate_symbol("AAPL") is False  # US stock
        assert market_service.validate_symbol("SAP.US") is False  # Wrong exchange

    def test_validate_symbol_empty(self, market_service):
        """Test validation of empty symbols"""
        assert market_service.validate_symbol("") is False
        assert market_service.validate_symbol(None) is False

    def test_validate_symbol_too_long(self, market_service):
        """Test validation of symbols that are too long"""
        assert market_service.validate_symbol("VERYLONGSYMBOL.DE") is False

    def test_validate_symbol_only_extension(self, market_service):
        """Test validation of symbol with only extension"""
        assert market_service.validate_symbol(".DE") is False


class TestPriceFetching:
    """Test price fetching functionality"""

    @patch('backend.services.market_data.yf.Ticker')
    def test_fetch_price_success(self, mock_ticker, market_service):
        """Test successful price fetching"""
        # Mock yfinance response
        mock_ticker_instance = Mock()
        mock_ticker_instance.info = {
            "currentPrice": 150.50,
            "volume": 1000000,
            "bid": 150.45,
            "ask": 150.55,
            "dayHigh": 152.00,
            "dayLow": 149.00,
        }
        mock_ticker.return_value = mock_ticker_instance

        result = market_service.fetch_price("SAP.DE", use_cache=False)

        assert result is not None
        assert result["symbol"] == "SAP.DE"
        assert result["price"] == 150.50
        assert result["volume"] == 1000000
        assert result["bid"] == 150.45
        assert result["ask"] == 150.55

    @patch('backend.services.market_data.yf.Ticker')
    def test_fetch_price_with_fast_info_fallback(self, mock_ticker, market_service):
        """Test price fetching with fast_info fallback"""
        # Mock yfinance response with no currentPrice
        mock_ticker_instance = Mock()
        mock_ticker_instance.info = {}
        mock_ticker_instance.fast_info.last_price = 150.50
        mock_ticker.return_value = mock_ticker_instance

        result = market_service.fetch_price("SAP.DE", use_cache=False)

        assert result is not None
        assert result["price"] == 150.50

    @patch('backend.services.market_data.yf.Ticker')
    def test_fetch_price_invalid_symbol(self, mock_ticker, market_service):
        """Test price fetching with invalid symbol"""
        result = market_service.fetch_price("INVALID", use_cache=False)
        assert result is None

    @patch('backend.services.market_data.yf.Ticker')
    def test_fetch_price_api_error(self, mock_ticker, market_service):
        """Test price fetching when API fails"""
        mock_ticker.side_effect = Exception("API Error")

        result = market_service.fetch_price("SAP.DE", use_cache=False)
        assert result is None


class TestCaching:
    """Test price caching functionality"""

    @patch('backend.services.market_data.yf.Ticker')
    def test_cache_stores_data(self, mock_ticker, market_service, db_session):
        """Test that fetched prices are stored in cache"""
        # Mock yfinance response
        mock_ticker_instance = Mock()
        mock_ticker_instance.info = {
            "currentPrice": 150.50,
            "volume": 1000000,
        }
        mock_ticker.return_value = mock_ticker_instance

        # Fetch price (should cache it)
        market_service.fetch_price("SAP.DE", use_cache=False)

        # Check cache entry exists
        cache_entry = db_session.query(MarketData).filter_by(symbol="SAP.DE").first()
        assert cache_entry is not None
        assert cache_entry.price == 150.50
        assert cache_entry.volume == 1000000

    @patch('backend.services.market_data.yf.Ticker')
    def test_cache_hit_returns_cached_data(self, mock_ticker, market_service, db_session):
        """Test that valid cache is used instead of fetching"""
        # Add cache entry with explicit timestamp
        current_time = datetime.now(ZoneInfo("Europe/Berlin"))
        cache_entry = MarketData(
            symbol="SAP.DE",
            price=150.50,
            volume=1000000,
            timestamp=current_time,
        )
        db_session.add(cache_entry)
        db_session.commit()

        # Fetch price (should use cache)
        result = market_service.fetch_price("SAP.DE", use_cache=True)

        # Should not call yfinance
        mock_ticker.assert_not_called()

        # Should return cached data
        assert result is not None
        assert result["price"] == 150.50

    @patch('backend.services.market_data.yf.Ticker')
    def test_cache_expires_after_ttl(self, mock_ticker, market_service, db_session):
        """Test that expired cache is not used"""
        # Add old cache entry
        old_timestamp = datetime.now(ZoneInfo("Europe/Berlin")) - timedelta(seconds=400)
        cache_entry = MarketData(
            symbol="SAP.DE",
            price=150.50,
            volume=1000000,
            timestamp=old_timestamp,
        )
        db_session.add(cache_entry)
        db_session.commit()

        # Mock fresh data
        mock_ticker_instance = Mock()
        mock_ticker_instance.info = {
            "currentPrice": 151.00,
        }
        mock_ticker.return_value = mock_ticker_instance

        # Fetch price (should bypass cache)
        result = market_service.fetch_price("SAP.DE", use_cache=True)

        # Should call yfinance
        mock_ticker.assert_called_once()

        # Should return fresh data
        assert result["price"] == 151.00


class TestMarketStatus:
    """Test market status functionality"""

    def test_get_market_status_open(self, market_service):
        """Test market status when market is open"""
        with patch.object(market_service, 'is_market_open', return_value=True):
            with patch.object(market_service, 'is_trading_day', return_value=True):
                status = market_service.get_market_status()

                assert status["is_open"] is True
                assert status["is_trading_day"] is True
                assert status["status_message"] == "Market open"

    def test_get_market_status_closed_weekend(self, market_service):
        """Test market status on weekend"""
        with patch.object(market_service, 'is_market_open', return_value=False):
            with patch.object(market_service, 'is_trading_day', return_value=False):
                status = market_service.get_market_status()

                assert status["is_open"] is False
                assert status["is_trading_day"] is False
                assert "closed" in status["status_message"].lower()

    def test_get_market_status_premarket(self, market_service):
        """Test market status before market opens"""
        # Mock time before market open
        premarket_time = datetime(2024, 1, 8, 8, 30, 0, tzinfo=ZoneInfo("Europe/Berlin"))

        with patch.object(market_service, 'get_current_time_cet', return_value=premarket_time):
            with patch.object(market_service, 'is_market_open', return_value=False):
                with patch.object(market_service, 'is_trading_day', return_value=True):
                    status = market_service.get_market_status()

                    assert status["is_open"] is False
                    assert status["is_trading_day"] is True
                    assert status["status_message"] == "Pre-market"
                    assert "opens_in_minutes" in status


class TestMultiplePrices:
    """Test fetching multiple prices"""

    @patch('backend.services.market_data.yf.Ticker')
    def test_fetch_multiple_prices(self, mock_ticker, market_service):
        """Test fetching prices for multiple symbols"""
        # Mock yfinance responses
        def ticker_side_effect(symbol):
            mock_instance = Mock()
            if symbol == "SAP.DE":
                mock_instance.info = {"currentPrice": 150.50}
            elif symbol == "BMW.DE":
                mock_instance.info = {"currentPrice": 95.20}
            return mock_instance

        mock_ticker.side_effect = ticker_side_effect

        symbols = ["SAP.DE", "BMW.DE"]
        results = market_service.fetch_multiple_prices(symbols, use_cache=False)

        assert len(results) == 2
        assert results["SAP.DE"]["price"] == 150.50
        assert results["BMW.DE"]["price"] == 95.20
