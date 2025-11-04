"""
Market Data Service

Handles fetching real-time German stock prices from XETRA/DAX,
market hours validation, and price caching.
"""

import yfinance as yf
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from zoneinfo import ZoneInfo
from sqlalchemy.orm import Session

from backend.config import settings
from backend.logger import get_logger
from backend.models.market_data import MarketData

logger = get_logger(__name__)


class MarketDataService:
    """Service for fetching and managing market data for German stocks"""

    # German market holidays 2024-2025 (major ones)
    GERMAN_HOLIDAYS = [
        # 2024
        "2024-01-01",  # New Year
        "2024-03-29",  # Good Friday
        "2024-04-01",  # Easter Monday
        "2024-05-01",  # Labour Day
        "2024-12-24",  # Christmas Eve
        "2024-12-25",  # Christmas Day
        "2024-12-26",  # Boxing Day
        "2024-12-31",  # New Year's Eve
        # 2025
        "2025-01-01",  # New Year
        "2025-04-18",  # Good Friday
        "2025-04-21",  # Easter Monday
        "2025-05-01",  # Labour Day
        "2025-12-24",  # Christmas Eve
        "2025-12-25",  # Christmas Day
        "2025-12-26",  # Boxing Day
        "2025-12-31",  # New Year's Eve
    ]

    # Cache TTL in seconds (5 minutes for real-time data)
    CACHE_TTL = 300

    def __init__(self, db: Session):
        """
        Initialize MarketDataService

        Args:
            db: SQLAlchemy database session
        """
        self.db = db
        self.timezone = ZoneInfo(settings.TIMEZONE)

    def get_current_time_cet(self) -> datetime:
        """Get current time in CET timezone"""
        return datetime.now(self.timezone)

    def is_trading_day(self, date: Optional[datetime] = None) -> bool:
        """
        Check if a given date is a trading day (weekday, not holiday)

        Args:
            date: Date to check (defaults to today)

        Returns:
            True if it's a trading day, False otherwise
        """
        if date is None:
            date = self.get_current_time_cet()

        # Check if weekend
        if date.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return False

        # Check if holiday
        date_str = date.strftime("%Y-%m-%d")
        if date_str in self.GERMAN_HOLIDAYS:
            return False

        return True

    def is_market_open(self, check_time: Optional[datetime] = None) -> bool:
        """
        Check if the German stock market is currently open

        Market hours: 9:00 AM - 5:30 PM CET, Monday-Friday (excluding holidays)

        Args:
            check_time: Time to check (defaults to now)

        Returns:
            True if market is open, False otherwise
        """
        if check_time is None:
            check_time = self.get_current_time_cet()

        # Ensure timezone aware
        if check_time.tzinfo is None:
            check_time = check_time.replace(tzinfo=self.timezone)

        # Check if trading day
        if not self.is_trading_day(check_time):
            logger.debug(f"Not a trading day: {check_time.strftime('%Y-%m-%d')}")
            return False

        # Check market hours
        market_open = check_time.replace(
            hour=settings.MARKET_OPEN_HOUR,
            minute=settings.MARKET_OPEN_MINUTE,
            second=0,
            microsecond=0
        )
        market_close = check_time.replace(
            hour=settings.MARKET_CLOSE_HOUR,
            minute=settings.MARKET_CLOSE_MINUTE,
            second=0,
            microsecond=0
        )

        is_open = market_open <= check_time <= market_close
        logger.debug(f"Market open check: {is_open} (time: {check_time.strftime('%H:%M')})")
        return is_open

    def validate_symbol(self, symbol: str) -> bool:
        """
        Validate if a stock symbol is valid for German market

        German stocks typically end with .DE for XETRA
        Examples: SAP.DE, VOW3.DE, DBK.DE

        Args:
            symbol: Stock symbol to validate

        Returns:
            True if symbol format is valid, False otherwise
        """
        if not symbol or not isinstance(symbol, str):
            return False

        # Check if symbol ends with .DE (XETRA/DAX)
        if not symbol.endswith(".DE"):
            logger.warning(f"Invalid symbol format: {symbol}. Must end with .DE")
            return False

        # Check symbol length (reasonable bounds)
        base_symbol = symbol[:-3]  # Remove .DE
        if len(base_symbol) < 1 or len(base_symbol) > 10:
            logger.warning(f"Invalid symbol length: {symbol}")
            return False

        return True

    def get_cached_price(self, symbol: str) -> Optional[Dict]:
        """
        Get cached price data for a symbol if available and not expired

        Args:
            symbol: Stock symbol

        Returns:
            Dictionary with price data or None if cache miss/expired
        """
        try:
            # Query most recent cache entry for symbol
            cache_entry = (
                self.db.query(MarketData)
                .filter(MarketData.symbol == symbol)
                .order_by(MarketData.timestamp.desc())
                .first()
            )

            if not cache_entry:
                return None

            # Check if cache is still valid
            # Handle timestamp conversion (may be string from SQLite)
            cache_timestamp = cache_entry.timestamp

            # Convert string to datetime if needed
            if isinstance(cache_timestamp, str):
                from dateutil import parser
                cache_timestamp = parser.parse(cache_timestamp)

            # Make timestamp timezone-aware if it isn't already
            if cache_timestamp.tzinfo is None:
                cache_timestamp = cache_timestamp.replace(tzinfo=self.timezone)

            cache_age = (self.get_current_time_cet() - cache_timestamp).total_seconds()
            if cache_age > self.CACHE_TTL:
                logger.debug(f"Cache expired for {symbol} (age: {cache_age}s)")
                return None

            logger.debug(f"Cache hit for {symbol} (age: {cache_age}s)")
            return {
                "symbol": cache_entry.symbol,
                "price": cache_entry.price,
                "volume": cache_entry.volume,
                "bid": cache_entry.bid,
                "ask": cache_entry.ask,
                "day_high": cache_entry.day_high,
                "day_low": cache_entry.day_low,
                "timestamp": cache_entry.timestamp,
            }

        except Exception as e:
            logger.error(f"Error retrieving cached price for {symbol}: {e}")
            return None

    def fetch_price(self, symbol: str, use_cache: bool = True) -> Optional[Dict]:
        """
        Fetch current price for a German stock symbol

        Args:
            symbol: Stock symbol (e.g., "SAP.DE")
            use_cache: Whether to use cached data if available

        Returns:
            Dictionary with price data or None if fetch failed
        """
        # Validate symbol format
        if not self.validate_symbol(symbol):
            logger.error(f"Invalid symbol: {symbol}")
            return None

        # Check cache first
        if use_cache:
            cached_data = self.get_cached_price(symbol)
            if cached_data:
                return cached_data

        try:
            logger.info(f"Fetching live price for {symbol}")
            ticker = yf.Ticker(symbol)

            # Get current price data
            info = ticker.info

            # Check if we got valid data
            if not info or "currentPrice" not in info:
                # Try fast_info as fallback
                try:
                    fast_info = ticker.fast_info
                    current_price = fast_info.last_price
                except Exception:
                    logger.error(f"No price data available for {symbol}")
                    return None
            else:
                current_price = info.get("currentPrice")

            # Get additional market data
            price_data = {
                "symbol": symbol,
                "price": current_price,
                "volume": info.get("volume"),
                "bid": info.get("bid"),
                "ask": info.get("ask"),
                "day_high": info.get("dayHigh"),
                "day_low": info.get("dayLow"),
                "timestamp": self.get_current_time_cet(),
            }

            # Cache the result
            self._cache_price_data(price_data)

            logger.info(f"Successfully fetched price for {symbol}: €{current_price}")
            return price_data

        except Exception as e:
            logger.error(f"Error fetching price for {symbol}: {e}")
            return None

    def fetch_multiple_prices(self, symbols: List[str], use_cache: bool = True) -> Dict[str, Optional[Dict]]:
        """
        Fetch prices for multiple symbols

        Args:
            symbols: List of stock symbols
            use_cache: Whether to use cached data if available

        Returns:
            Dictionary mapping symbols to their price data
        """
        results = {}
        for symbol in symbols:
            results[symbol] = self.fetch_price(symbol, use_cache=use_cache)
        return results

    def _cache_price_data(self, price_data: Dict) -> None:
        """
        Store price data in cache

        Args:
            price_data: Dictionary with price information
        """
        try:
            cache_entry = MarketData(
                symbol=price_data["symbol"],
                price=price_data["price"],
                volume=price_data.get("volume"),
                bid=price_data.get("bid"),
                ask=price_data.get("ask"),
                day_high=price_data.get("day_high"),
                day_low=price_data.get("day_low"),
            )
            self.db.add(cache_entry)
            self.db.commit()
            logger.debug(f"Cached price data for {price_data['symbol']}")

        except Exception as e:
            logger.error(f"Error caching price data: {e}")
            self.db.rollback()

    def get_market_status(self) -> Dict:
        """
        Get current market status information

        Returns:
            Dictionary with market status details
        """
        current_time = self.get_current_time_cet()
        is_open = self.is_market_open(current_time)
        is_trading_day = self.is_trading_day(current_time)

        status = {
            "is_open": is_open,
            "is_trading_day": is_trading_day,
            "current_time_cet": current_time.isoformat(),
            "market_open_time": f"{settings.MARKET_OPEN_HOUR:02d}:{settings.MARKET_OPEN_MINUTE:02d} CET",
            "market_close_time": f"{settings.MARKET_CLOSE_HOUR:02d}:{settings.MARKET_CLOSE_MINUTE:02d} CET",
        }

        if not is_open and is_trading_day:
            # Calculate time until market opens/closes
            market_open = current_time.replace(
                hour=settings.MARKET_OPEN_HOUR,
                minute=settings.MARKET_OPEN_MINUTE,
                second=0,
                microsecond=0
            )
            market_close = current_time.replace(
                hour=settings.MARKET_CLOSE_HOUR,
                minute=settings.MARKET_CLOSE_MINUTE,
                second=0,
                microsecond=0
            )

            if current_time < market_open:
                status["status_message"] = "Pre-market"
                status["opens_in_minutes"] = int((market_open - current_time).total_seconds() / 60)
            else:
                status["status_message"] = "After-hours"
        elif is_open:
            status["status_message"] = "Market open"
        else:
            status["status_message"] = "Market closed (weekend/holiday)"

        return status
