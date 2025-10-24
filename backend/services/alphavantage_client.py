"""
Alpha Vantage API Client

Provides integration with Alpha Vantage API for:
- Company fundamentals (income statement, balance sheet, cash flow)
- Earnings data and calendar
- Technical indicators (RSI, MACD, SMA, EMA)
- Company overview and sector information

Free tier limitations:
- 25 API calls per day
- 5 API calls per minute
"""

import os
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import requests
from backend.logger import get_logger
from backend.database.base import SessionLocal
from backend.models.market_data import MarketData

logger = get_logger(__name__)


class AlphaVantageClient:
    """Client for Alpha Vantage financial data API."""

    BASE_URL = "https://www.alphavantage.co/query"
    CACHE_DURATION_HOURS = 24  # Cache data for 24 hours

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Alpha Vantage client.

        Args:
            api_key: Alpha Vantage API key (defaults to env var ALPHAVANTAGE_API_KEY)
        """
        self.api_key = api_key or os.getenv("ALPHAVANTAGE_API_KEY")
        if not self.api_key:
            logger.warning("No Alpha Vantage API key found. Set ALPHAVANTAGE_API_KEY environment variable.")

        self.session = requests.Session()
        self.last_call_time = 0
        self.min_call_interval = 12  # 5 calls per minute = 12 seconds between calls

    def _rate_limit(self):
        """Enforce rate limiting (5 calls per minute)."""
        elapsed = time.time() - self.last_call_time
        if elapsed < self.min_call_interval:
            sleep_time = self.min_call_interval - elapsed
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)
        self.last_call_time = time.time()

    def _make_request(self, params: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """
        Make API request with error handling and rate limiting.

        Args:
            params: Query parameters for API request

        Returns:
            JSON response or None on error
        """
        if not self.api_key:
            logger.error("Cannot make request: API key not set")
            return None

        self._rate_limit()

        params["apikey"] = self.api_key

        try:
            response = self.session.get(self.BASE_URL, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()

            # Check for API error messages
            if "Error Message" in data:
                logger.error(f"Alpha Vantage API error: {data['Error Message']}")
                return None

            if "Note" in data:
                logger.warning(f"Alpha Vantage rate limit message: {data['Note']}")
                return None

            return data

        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            return None
        except ValueError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            return None

    def get_company_overview(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get company overview including sector, industry, market cap, P/E ratio, etc.

        Args:
            symbol: Stock symbol (e.g., "SAP" for SAP.DE - remove .DE suffix)

        Returns:
            Company overview data or None on error
        """
        # Remove .DE suffix if present
        clean_symbol = symbol.replace(".DE", "")

        logger.info(f"Fetching company overview for {clean_symbol}")

        params = {
            "function": "OVERVIEW",
            "symbol": clean_symbol
        }

        data = self._make_request(params)
        if not data or not data.get("Symbol"):
            logger.warning(f"No overview data found for {clean_symbol}")
            return None

        # Parse key metrics
        try:
            overview = {
                "symbol": data.get("Symbol"),
                "name": data.get("Name"),
                "sector": data.get("Sector"),
                "industry": data.get("Industry"),
                "market_cap": float(data.get("MarketCapitalization", 0)),
                "pe_ratio": float(data.get("PERatio", 0)) if data.get("PERatio") != "None" else None,
                "forward_pe": float(data.get("ForwardPE", 0)) if data.get("ForwardPE") != "None" else None,
                "peg_ratio": float(data.get("PEGRatio", 0)) if data.get("PEGRatio") != "None" else None,
                "pb_ratio": float(data.get("PriceToBookRatio", 0)) if data.get("PriceToBookRatio") != "None" else None,
                "dividend_yield": float(data.get("DividendYield", 0)) if data.get("DividendYield") != "None" else None,
                "eps": float(data.get("EPS", 0)) if data.get("EPS") != "None" else None,
                "revenue_ttm": float(data.get("RevenueTTM", 0)),
                "profit_margin": float(data.get("ProfitMargin", 0)) if data.get("ProfitMargin") != "None" else None,
                "operating_margin": float(data.get("OperatingMarginTTM", 0)) if data.get("OperatingMarginTTM") != "None" else None,
                "roe": float(data.get("ReturnOnEquityTTM", 0)) if data.get("ReturnOnEquityTTM") != "None" else None,
                "roa": float(data.get("ReturnOnAssetsTTM", 0)) if data.get("ReturnOnAssetsTTM") != "None" else None,
                "beta": float(data.get("Beta", 0)) if data.get("Beta") != "None" else None,
                "52_week_high": float(data.get("52WeekHigh", 0)),
                "52_week_low": float(data.get("52WeekLow", 0)),
                "analyst_target_price": float(data.get("AnalystTargetPrice", 0)) if data.get("AnalystTargetPrice") != "None" else None,
                "description": data.get("Description", "")
            }

            logger.info(f"Successfully fetched overview for {clean_symbol}")
            return overview

        except (ValueError, TypeError) as e:
            logger.error(f"Failed to parse overview data for {clean_symbol}: {e}")
            return None

    def get_earnings(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get earnings data including quarterly and annual reports.

        Args:
            symbol: Stock symbol (without .DE suffix)

        Returns:
            Earnings data or None on error
        """
        clean_symbol = symbol.replace(".DE", "")

        logger.info(f"Fetching earnings for {clean_symbol}")

        params = {
            "function": "EARNINGS",
            "symbol": clean_symbol
        }

        data = self._make_request(params)
        if not data or "quarterlyEarnings" not in data:
            logger.warning(f"No earnings data found for {clean_symbol}")
            return None

        try:
            # Get latest quarterly earnings
            quarterly = data.get("quarterlyEarnings", [])
            annual = data.get("annualEarnings", [])

            latest_quarter = quarterly[0] if quarterly else None
            latest_annual = annual[0] if annual else None

            earnings = {
                "symbol": clean_symbol,
                "latest_quarter": {
                    "fiscal_date_ending": latest_quarter.get("fiscalDateEnding") if latest_quarter else None,
                    "reported_eps": float(latest_quarter.get("reportedEPS", 0)) if latest_quarter else None,
                    "estimated_eps": float(latest_quarter.get("estimatedEPS", 0)) if latest_quarter else None,
                    "surprise": float(latest_quarter.get("surprise", 0)) if latest_quarter else None,
                    "surprise_percentage": float(latest_quarter.get("surprisePercentage", 0)) if latest_quarter else None,
                } if latest_quarter else None,
                "latest_annual": {
                    "fiscal_date_ending": latest_annual.get("fiscalDateEnding") if latest_annual else None,
                    "reported_eps": float(latest_annual.get("reportedEPS", 0)) if latest_annual else None,
                } if latest_annual else None,
                "quarterly_history": [
                    {
                        "date": q.get("fiscalDateEnding"),
                        "reported_eps": float(q.get("reportedEPS", 0)),
                        "estimated_eps": float(q.get("estimatedEPS", 0)),
                        "surprise_pct": float(q.get("surprisePercentage", 0))
                    }
                    for q in quarterly[:4]  # Last 4 quarters
                ]
            }

            logger.info(f"Successfully fetched earnings for {clean_symbol}")
            return earnings

        except (ValueError, TypeError, IndexError) as e:
            logger.error(f"Failed to parse earnings data for {clean_symbol}: {e}")
            return None

    def get_rsi(self, symbol: str, interval: str = "daily", time_period: int = 14) -> Optional[Dict[str, float]]:
        """
        Get Relative Strength Index (RSI) technical indicator.

        Args:
            symbol: Stock symbol (without .DE suffix)
            interval: Time interval (daily, weekly, monthly)
            time_period: Number of periods for RSI calculation (default: 14)

        Returns:
            RSI data or None on error
        """
        clean_symbol = symbol.replace(".DE", "")

        logger.info(f"Fetching RSI for {clean_symbol}")

        params = {
            "function": "RSI",
            "symbol": clean_symbol,
            "interval": interval,
            "time_period": str(time_period),
            "series_type": "close"
        }

        data = self._make_request(params)
        if not data or "Technical Analysis: RSI" not in data:
            logger.warning(f"No RSI data found for {clean_symbol}")
            return None

        try:
            rsi_data = data["Technical Analysis: RSI"]

            # Get latest RSI value
            latest_date = sorted(rsi_data.keys(), reverse=True)[0]
            latest_rsi = float(rsi_data[latest_date]["RSI"])

            result = {
                "symbol": clean_symbol,
                "rsi": latest_rsi,
                "date": latest_date,
                "period": time_period,
                "interpretation": self._interpret_rsi(latest_rsi)
            }

            logger.info(f"Successfully fetched RSI for {clean_symbol}: {latest_rsi:.2f}")
            return result

        except (ValueError, TypeError, IndexError, KeyError) as e:
            logger.error(f"Failed to parse RSI data for {clean_symbol}: {e}")
            return None

    def get_macd(self, symbol: str, interval: str = "daily") -> Optional[Dict[str, float]]:
        """
        Get MACD (Moving Average Convergence Divergence) indicator.

        Args:
            symbol: Stock symbol (without .DE suffix)
            interval: Time interval (daily, weekly, monthly)

        Returns:
            MACD data or None on error
        """
        clean_symbol = symbol.replace(".DE", "")

        logger.info(f"Fetching MACD for {clean_symbol}")

        params = {
            "function": "MACD",
            "symbol": clean_symbol,
            "interval": interval,
            "series_type": "close"
        }

        data = self._make_request(params)
        if not data or "Technical Analysis: MACD" not in data:
            logger.warning(f"No MACD data found for {clean_symbol}")
            return None

        try:
            macd_data = data["Technical Analysis: MACD"]

            # Get latest MACD values
            dates = sorted(macd_data.keys(), reverse=True)
            latest_date = dates[0]
            prev_date = dates[1] if len(dates) > 1 else None

            latest = macd_data[latest_date]
            macd_value = float(latest["MACD"])
            signal = float(latest["MACD_Signal"])
            hist = float(latest["MACD_Hist"])

            # Check for crossover
            crossover = None
            if prev_date:
                prev = macd_data[prev_date]
                prev_hist = float(prev["MACD_Hist"])

                if hist > 0 and prev_hist <= 0:
                    crossover = "bullish"
                elif hist < 0 and prev_hist >= 0:
                    crossover = "bearish"

            result = {
                "symbol": clean_symbol,
                "macd": macd_value,
                "signal": signal,
                "histogram": hist,
                "date": latest_date,
                "crossover": crossover,
                "interpretation": self._interpret_macd(macd_value, signal, hist, crossover)
            }

            logger.info(f"Successfully fetched MACD for {clean_symbol}")
            return result

        except (ValueError, TypeError, IndexError, KeyError) as e:
            logger.error(f"Failed to parse MACD data for {clean_symbol}: {e}")
            return None

    def get_sma(self, symbol: str, interval: str = "daily", time_period: int = 50) -> Optional[Dict[str, float]]:
        """
        Get Simple Moving Average (SMA).

        Args:
            symbol: Stock symbol (without .DE suffix)
            interval: Time interval (daily, weekly, monthly)
            time_period: Number of periods (50, 200 are common)

        Returns:
            SMA data or None on error
        """
        clean_symbol = symbol.replace(".DE", "")

        logger.info(f"Fetching SMA-{time_period} for {clean_symbol}")

        params = {
            "function": "SMA",
            "symbol": clean_symbol,
            "interval": interval,
            "time_period": str(time_period),
            "series_type": "close"
        }

        data = self._make_request(params)
        if not data or "Technical Analysis: SMA" not in data:
            logger.warning(f"No SMA data found for {clean_symbol}")
            return None

        try:
            sma_data = data["Technical Analysis: SMA"]

            # Get latest SMA value
            latest_date = sorted(sma_data.keys(), reverse=True)[0]
            latest_sma = float(sma_data[latest_date]["SMA"])

            result = {
                "symbol": clean_symbol,
                "sma": latest_sma,
                "period": time_period,
                "date": latest_date
            }

            logger.info(f"Successfully fetched SMA-{time_period} for {clean_symbol}: {latest_sma:.2f}")
            return result

        except (ValueError, TypeError, IndexError, KeyError) as e:
            logger.error(f"Failed to parse SMA data for {clean_symbol}: {e}")
            return None

    @staticmethod
    def _interpret_rsi(rsi: float) -> str:
        """Interpret RSI value."""
        if rsi >= 70:
            return "overbought"
        elif rsi <= 30:
            return "oversold"
        else:
            return "neutral"

    @staticmethod
    def _interpret_macd(macd: float, signal: float, hist: float, crossover: Optional[str]) -> str:
        """Interpret MACD indicator."""
        if crossover == "bullish":
            return "bullish_crossover"
        elif crossover == "bearish":
            return "bearish_crossover"
        elif hist > 0:
            return "bullish"
        elif hist < 0:
            return "bearish"
        else:
            return "neutral"

    def close(self):
        """Close the session."""
        self.session.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
