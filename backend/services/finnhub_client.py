"""
Finnhub API Client

Provides integration with Finnhub API for:
- Company news
- Market news
- Analyst ratings and recommendations
- Price targets
- Market sentiment scores
- Earnings calendar

Free tier limitations:
- 60 API calls per minute
- Limited historical data
"""

import os
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import requests
from backend.logger import get_logger

logger = get_logger(__name__)


class FinnhubClient:
    """Client for Finnhub financial data API."""

    BASE_URL = "https://finnhub.io/api/v1"
    CACHE_DURATION_HOURS = 1  # Cache news/sentiment for 1 hour

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Finnhub client.

        Args:
            api_key: Finnhub API key (defaults to env var FINNHUB_API_KEY)
        """
        self.api_key = api_key or os.getenv("FINNHUB_API_KEY")
        if not self.api_key:
            logger.warning("No Finnhub API key found. Set FINNHUB_API_KEY environment variable.")

        self.session = requests.Session()
        self.last_call_time = 0
        self.min_call_interval = 1.0  # 60 calls per minute = 1 second between calls

    def _rate_limit(self):
        """Enforce rate limiting (60 calls per minute)."""
        elapsed = time.time() - self.last_call_time
        if elapsed < self.min_call_interval:
            sleep_time = self.min_call_interval - elapsed
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)
        self.last_call_time = time.time()

    def _make_request(self, endpoint: str, params: Optional[Dict[str, str]] = None) -> Optional[Any]:
        """
        Make API request with error handling and rate limiting.

        Args:
            endpoint: API endpoint path
            params: Query parameters

        Returns:
            JSON response or None on error
        """
        if not self.api_key:
            logger.error("Cannot make request: API key not set")
            return None

        self._rate_limit()

        params = params or {}
        params["token"] = self.api_key

        url = f"{self.BASE_URL}/{endpoint}"

        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()

            # Check for API errors
            if isinstance(data, dict) and "error" in data:
                logger.error(f"Finnhub API error: {data['error']}")
                return None

            return data

        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            return None
        except ValueError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            return None

    def get_company_news(
        self,
        symbol: str,
        days_back: int = 7
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get company-specific news.

        Args:
            symbol: Stock symbol (without .DE suffix)
            days_back: Number of days to look back (default: 7)

        Returns:
            List of news articles or None on error
        """
        clean_symbol = symbol.replace(".DE", "")

        logger.info(f"Fetching company news for {clean_symbol}")

        # Calculate date range
        to_date = datetime.now()
        from_date = to_date - timedelta(days=days_back)

        params = {
            "symbol": clean_symbol,
            "from": from_date.strftime("%Y-%m-%d"),
            "to": to_date.strftime("%Y-%m-%d")
        }

        data = self._make_request("company-news", params)
        if not data:
            logger.warning(f"No company news found for {clean_symbol}")
            return None

        try:
            news = []
            for article in data[:20]:  # Limit to 20 most recent
                news.append({
                    "headline": article.get("headline", ""),
                    "summary": article.get("summary", ""),
                    "source": article.get("source", ""),
                    "url": article.get("url", ""),
                    "datetime": datetime.fromtimestamp(article.get("datetime", 0)),
                    "category": article.get("category", ""),
                    "sentiment": self._analyze_headline_sentiment(article.get("headline", ""))
                })

            logger.info(f"Successfully fetched {len(news)} news articles for {clean_symbol}")
            return news

        except (ValueError, TypeError, KeyError) as e:
            logger.error(f"Failed to parse news data for {clean_symbol}: {e}")
            return None

    def get_market_news(
        self,
        category: str = "general",
        min_id: Optional[int] = None
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get general market news.

        Args:
            category: News category (general, forex, crypto, merger)
            min_id: Minimum news ID (for pagination)

        Returns:
            List of news articles or None on error
        """
        logger.info(f"Fetching market news (category: {category})")

        params = {"category": category}
        if min_id:
            params["minId"] = str(min_id)

        data = self._make_request("news", params)
        if not data:
            logger.warning("No market news found")
            return None

        try:
            news = []
            for article in data[:20]:  # Limit to 20 most recent
                news.append({
                    "id": article.get("id"),
                    "headline": article.get("headline", ""),
                    "summary": article.get("summary", ""),
                    "source": article.get("source", ""),
                    "url": article.get("url", ""),
                    "datetime": datetime.fromtimestamp(article.get("datetime", 0)),
                    "category": article.get("category", ""),
                    "sentiment": self._analyze_headline_sentiment(article.get("headline", ""))
                })

            logger.info(f"Successfully fetched {len(news)} market news articles")
            return news

        except (ValueError, TypeError, KeyError) as e:
            logger.error(f"Failed to parse market news data: {e}")
            return None

    def get_recommendation_trends(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get analyst recommendation trends (buy, hold, sell ratings).

        Args:
            symbol: Stock symbol (without .DE suffix)

        Returns:
            Recommendation trends or None on error
        """
        clean_symbol = symbol.replace(".DE", "")

        logger.info(f"Fetching recommendation trends for {clean_symbol}")

        data = self._make_request(f"stock/recommendation", {"symbol": clean_symbol})
        if not data:
            logger.warning(f"No recommendation data found for {clean_symbol}")
            return None

        try:
            # Get latest month's recommendations
            latest = data[0] if data else None

            if not latest:
                return None

            recommendations = {
                "symbol": clean_symbol,
                "period": latest.get("period"),
                "strong_buy": latest.get("strongBuy", 0),
                "buy": latest.get("buy", 0),
                "hold": latest.get("hold", 0),
                "sell": latest.get("sell", 0),
                "strong_sell": latest.get("strongSell", 0),
                "total_analysts": (
                    latest.get("strongBuy", 0) +
                    latest.get("buy", 0) +
                    latest.get("hold", 0) +
                    latest.get("sell", 0) +
                    latest.get("strongSell", 0)
                ),
                "consensus": self._calculate_consensus(latest)
            }

            logger.info(f"Successfully fetched recommendations for {clean_symbol}")
            return recommendations

        except (ValueError, TypeError, IndexError, KeyError) as e:
            logger.error(f"Failed to parse recommendation data for {clean_symbol}: {e}")
            return None

    def get_price_target(self, symbol: str) -> Optional[Dict[str, float]]:
        """
        Get analyst price targets.

        Args:
            symbol: Stock symbol (without .DE suffix)

        Returns:
            Price target data or None on error
        """
        clean_symbol = symbol.replace(".DE", "")

        logger.info(f"Fetching price target for {clean_symbol}")

        data = self._make_request(f"stock/price-target", {"symbol": clean_symbol})
        if not data:
            logger.warning(f"No price target data found for {clean_symbol}")
            return None

        try:
            price_target = {
                "symbol": clean_symbol,
                "target_high": data.get("targetHigh"),
                "target_low": data.get("targetLow"),
                "target_mean": data.get("targetMean"),
                "target_median": data.get("targetMedian"),
                "last_updated": data.get("lastUpdated"),
                "num_analysts": data.get("numberOfAnalysts", 0)
            }

            logger.info(f"Successfully fetched price target for {clean_symbol}: ${price_target['target_mean']}")
            return price_target

        except (ValueError, TypeError, KeyError) as e:
            logger.error(f"Failed to parse price target data for {clean_symbol}: {e}")
            return None

    def get_earnings_calendar(
        self,
        symbol: Optional[str] = None,
        days_ahead: int = 30
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get upcoming earnings dates.

        Args:
            symbol: Stock symbol (without .DE suffix) or None for all
            days_ahead: Number of days to look ahead (default: 30)

        Returns:
            List of earnings events or None on error
        """
        logger.info(f"Fetching earnings calendar")

        # Calculate date range
        from_date = datetime.now()
        to_date = from_date + timedelta(days=days_ahead)

        params = {
            "from": from_date.strftime("%Y-%m-%d"),
            "to": to_date.strftime("%Y-%m-%d")
        }

        if symbol:
            clean_symbol = symbol.replace(".DE", "")
            params["symbol"] = clean_symbol

        data = self._make_request("calendar/earnings", params)
        if not data or "earningsCalendar" not in data:
            logger.warning("No earnings calendar data found")
            return None

        try:
            calendar = []
            for event in data["earningsCalendar"][:50]:  # Limit to 50 events
                calendar.append({
                    "symbol": event.get("symbol"),
                    "date": event.get("date"),
                    "eps_estimate": event.get("epsEstimate"),
                    "eps_actual": event.get("epsActual"),
                    "revenue_estimate": event.get("revenueEstimate"),
                    "revenue_actual": event.get("revenueActual")
                })

            logger.info(f"Successfully fetched {len(calendar)} earnings events")
            return calendar

        except (ValueError, TypeError, KeyError) as e:
            logger.error(f"Failed to parse earnings calendar: {e}")
            return None

    def get_sentiment(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get news sentiment for a symbol.

        Args:
            symbol: Stock symbol (without .DE suffix)

        Returns:
            Sentiment data or None on error
        """
        clean_symbol = symbol.replace(".DE", "")

        logger.info(f"Fetching sentiment for {clean_symbol}")

        data = self._make_request(f"news-sentiment", {"symbol": clean_symbol})
        if not data:
            logger.warning(f"No sentiment data found for {clean_symbol}")
            return None

        try:
            sentiment = {
                "symbol": clean_symbol,
                "buzz_articles_in_last_week": data.get("buzz", {}).get("articlesInLastWeek", 0),
                "buzz_weekly_average": data.get("buzz", {}).get("weeklyAverage", 0),
                "sentiment_score": data.get("sentiment", {}).get("bearishPercent", 0),
                "sentiment_bullish": data.get("sentiment", {}).get("bullishPercent", 0),
                "sentiment_bearish": data.get("sentiment", {}).get("bearishPercent", 0),
                "company_news_score": data.get("companyNewsScore", 0),
                "sector_average_news_score": data.get("sectorAverageNewsScore", 0),
                "interpretation": self._interpret_sentiment(
                    data.get("sentiment", {}).get("bullishPercent", 0),
                    data.get("sentiment", {}).get("bearishPercent", 0)
                )
            }

            logger.info(f"Successfully fetched sentiment for {clean_symbol}")
            return sentiment

        except (ValueError, TypeError, KeyError) as e:
            logger.error(f"Failed to parse sentiment data for {clean_symbol}: {e}")
            return None

    @staticmethod
    def _analyze_headline_sentiment(headline: str) -> str:
        """Simple headline sentiment analysis."""
        positive_words = ["surge", "soar", "beat", "exceed", "gain", "rise", "jump", "rally", "upgrade"]
        negative_words = ["plunge", "fall", "miss", "decline", "drop", "crash", "downgrade", "warning"]

        headline_lower = headline.lower()

        positive_count = sum(1 for word in positive_words if word in headline_lower)
        negative_count = sum(1 for word in negative_words if word in headline_lower)

        if positive_count > negative_count:
            return "positive"
        elif negative_count > positive_count:
            return "negative"
        else:
            return "neutral"

    @staticmethod
    def _calculate_consensus(recommendations: Dict[str, int]) -> str:
        """Calculate analyst consensus."""
        strong_buy = recommendations.get("strongBuy", 0)
        buy = recommendations.get("buy", 0)
        hold = recommendations.get("hold", 0)
        sell = recommendations.get("sell", 0)
        strong_sell = recommendations.get("strongSell", 0)

        total = strong_buy + buy + hold + sell + strong_sell
        if total == 0:
            return "unknown"

        buy_ratio = (strong_buy + buy) / total

        if buy_ratio >= 0.7:
            return "strong_buy"
        elif buy_ratio >= 0.5:
            return "buy"
        elif buy_ratio >= 0.3:
            return "hold"
        else:
            return "sell"

    @staticmethod
    def _interpret_sentiment(bullish_pct: float, bearish_pct: float) -> str:
        """Interpret sentiment percentages."""
        if bullish_pct > bearish_pct + 20:
            return "very_bullish"
        elif bullish_pct > bearish_pct + 10:
            return "bullish"
        elif bearish_pct > bullish_pct + 20:
            return "very_bearish"
        elif bearish_pct > bullish_pct + 10:
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
