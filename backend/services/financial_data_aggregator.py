"""
Financial Data Aggregator

Unified interface for combining data from multiple financial APIs:
- Alpha Vantage (fundamentals, earnings, technical indicators)
- Finnhub (news, analyst ratings, sentiment)
- Web research (existing DuckDuckGo integration)

Provides caching, error handling, and formatted output for LLM consumption.
"""

import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from backend.logger import get_logger
from backend.services.alphavantage_client import AlphaVantageClient
from backend.services.finnhub_client import FinnhubClient
from backend.database.base import SessionLocal
from backend.models.market_data import MarketData

logger = get_logger(__name__)


class FinancialDataAggregator:
    """Aggregate financial data from multiple sources."""

    def __init__(
        self,
        alphavantage_key: Optional[str] = None,
        finnhub_key: Optional[str] = None,
        use_cache: bool = True
    ):
        """
        Initialize aggregator with API clients.

        Args:
            alphavantage_key: Alpha Vantage API key
            finnhub_key: Finnhub API key
            use_cache: Whether to use database caching (default: True)
        """
        self.av_client = AlphaVantageClient(alphavantage_key)
        self.fh_client = FinnhubClient(finnhub_key)
        self.use_cache = use_cache
        self.db = SessionLocal() if use_cache else None

        logger.info("Initialized FinancialDataAggregator")

    def get_complete_analysis(
        self,
        symbol: str,
        include_news: bool = True,
        include_technicals: bool = True,
        include_fundamentals: bool = True,
        news_days_back: int = 7
    ) -> Dict[str, Any]:
        """
        Get complete financial analysis for a stock.

        Args:
            symbol: Stock symbol (e.g., "SAP.DE")
            include_news: Whether to fetch news data
            include_technicals: Whether to fetch technical indicators
            include_fundamentals: Whether to fetch fundamental data
            news_days_back: Days to look back for news (default: 7)

        Returns:
            Dictionary with all aggregated data
        """
        logger.info(f"Getting complete analysis for {symbol}")

        result = {
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
            "success": True,
            "errors": [],
            "data": {}
        }

        # Get fundamentals
        if include_fundamentals:
            try:
                result["data"]["fundamentals"] = self._get_fundamentals(symbol)
            except Exception as e:
                logger.error(f"Failed to get fundamentals: {e}")
                result["errors"].append(f"Fundamentals: {str(e)}")

        # Get technical indicators
        if include_technicals:
            try:
                result["data"]["technicals"] = self._get_technicals(symbol)
            except Exception as e:
                logger.error(f"Failed to get technicals: {e}")
                result["errors"].append(f"Technicals: {str(e)}")

        # Get news and sentiment
        if include_news:
            try:
                result["data"]["news"] = self._get_news_and_sentiment(symbol, news_days_back)
            except Exception as e:
                logger.error(f"Failed to get news: {e}")
                result["errors"].append(f"News: {str(e)}")

        # Get analyst ratings
        try:
            result["data"]["analyst_ratings"] = self._get_analyst_data(symbol)
        except Exception as e:
            logger.error(f"Failed to get analyst ratings: {e}")
            result["errors"].append(f"Analyst ratings: {str(e)}")

        result["success"] = len(result["errors"]) == 0

        logger.info(f"Complete analysis for {symbol}: {len(result['errors'])} errors")
        return result

    def _get_fundamentals(self, symbol: str) -> Dict[str, Any]:
        """Get fundamental data from Alpha Vantage."""
        logger.debug(f"Fetching fundamentals for {symbol}")

        fundamentals = {}

        # Company overview
        overview = self.av_client.get_company_overview(symbol)
        if overview:
            fundamentals["overview"] = overview

        # Earnings data
        earnings = self.av_client.get_earnings(symbol)
        if earnings:
            fundamentals["earnings"] = earnings

        return fundamentals

    def _get_technicals(self, symbol: str) -> Dict[str, Any]:
        """Get technical indicators from Alpha Vantage."""
        logger.debug(f"Fetching technicals for {symbol}")

        technicals = {}

        # RSI
        rsi = self.av_client.get_rsi(symbol)
        if rsi:
            technicals["rsi"] = rsi

        # MACD
        macd = self.av_client.get_macd(symbol)
        if macd:
            technicals["macd"] = macd

        # Moving averages
        sma_50 = self.av_client.get_sma(symbol, time_period=50)
        if sma_50:
            technicals["sma_50"] = sma_50

        sma_200 = self.av_client.get_sma(symbol, time_period=200)
        if sma_200:
            technicals["sma_200"] = sma_200

        return technicals

    def _get_news_and_sentiment(self, symbol: str, days_back: int) -> Dict[str, Any]:
        """Get news and sentiment from Finnhub."""
        logger.debug(f"Fetching news and sentiment for {symbol}")

        news_data = {}

        # Company news
        news = self.fh_client.get_company_news(symbol, days_back)
        if news:
            news_data["articles"] = news
            news_data["total_articles"] = len(news)

            # Aggregate sentiment from articles
            sentiment_counts = {"positive": 0, "negative": 0, "neutral": 0}
            for article in news:
                sentiment_counts[article["sentiment"]] += 1

            news_data["sentiment_distribution"] = sentiment_counts

        # Market sentiment score
        sentiment = self.fh_client.get_sentiment(symbol)
        if sentiment:
            news_data["sentiment_score"] = sentiment

        return news_data

    def _get_analyst_data(self, symbol: str) -> Dict[str, Any]:
        """Get analyst ratings and price targets from Finnhub."""
        logger.debug(f"Fetching analyst data for {symbol}")

        analyst_data = {}

        # Recommendations
        recommendations = self.fh_client.get_recommendation_trends(symbol)
        if recommendations:
            analyst_data["recommendations"] = recommendations

        # Price targets
        price_target = self.fh_client.get_price_target(symbol)
        if price_target:
            analyst_data["price_target"] = price_target

        return analyst_data

    def format_for_llm(self, analysis: Dict[str, Any]) -> str:
        """
        Format aggregated data for LLM consumption.

        Args:
            analysis: Output from get_complete_analysis()

        Returns:
            Formatted string for LLM prompt
        """
        if not analysis["success"]:
            return f"⚠️ Failed to fetch complete data. Errors: {', '.join(analysis['errors'])}"

        data = analysis["data"]
        symbol = analysis["symbol"]

        sections = []

        # Header
        sections.append(f"=== FINANCIAL ANALYSIS FOR {symbol} ===")
        sections.append(f"Generated: {analysis['timestamp']}\n")

        # Fundamentals
        if "fundamentals" in data:
            sections.append(self._format_fundamentals(data["fundamentals"]))

        # Technical Analysis
        if "technicals" in data:
            sections.append(self._format_technicals(data["technicals"]))

        # News & Sentiment
        if "news" in data:
            sections.append(self._format_news(data["news"]))

        # Analyst Ratings
        if "analyst_ratings" in data:
            sections.append(self._format_analyst_ratings(data["analyst_ratings"]))

        return "\n\n".join(sections)

    def _format_fundamentals(self, fundamentals: Dict[str, Any]) -> str:
        """Format fundamental data section."""
        lines = ["📊 FUNDAMENTALS"]

        if "overview" in fundamentals:
            ov = fundamentals["overview"]
            lines.append(f"Company: {ov.get('name', 'N/A')}")
            lines.append(f"Sector: {ov.get('sector', 'N/A')} | Industry: {ov.get('industry', 'N/A')}")
            lines.append(f"Market Cap: €{ov.get('market_cap', 0) / 1e9:.2f}B")

            lines.append("\nValuation:")
            lines.append(f"  • P/E Ratio: {ov.get('pe_ratio', 'N/A')}")
            lines.append(f"  • Forward P/E: {ov.get('forward_pe', 'N/A')}")
            lines.append(f"  • PEG Ratio: {ov.get('peg_ratio', 'N/A')}")
            lines.append(f"  • P/B Ratio: {ov.get('pb_ratio', 'N/A')}")

            lines.append("\nProfitability:")
            lines.append(f"  • Profit Margin: {ov.get('profit_margin', 0) * 100:.2f}%" if ov.get('profit_margin') else "  • Profit Margin: N/A")
            lines.append(f"  • Operating Margin: {ov.get('operating_margin', 0) * 100:.2f}%" if ov.get('operating_margin') else "  • Operating Margin: N/A")
            lines.append(f"  • ROE: {ov.get('roe', 0) * 100:.2f}%" if ov.get('roe') else "  • ROE: N/A")

            lines.append("\nPrice Range:")
            lines.append(f"  • 52-Week High: €{ov.get('52_week_high', 0):.2f}")
            lines.append(f"  • 52-Week Low: €{ov.get('52_week_low', 0):.2f}")

        if "earnings" in fundamentals:
            earn = fundamentals["earnings"]
            if earn.get("latest_quarter"):
                lq = earn["latest_quarter"]
                lines.append(f"\nLatest Earnings (Q ending {lq.get('fiscal_date_ending', 'N/A')}):")
                lines.append(f"  • Reported EPS: ${lq.get('reported_eps', 0):.2f}")
                lines.append(f"  • Estimated EPS: ${lq.get('estimated_eps', 0):.2f}")
                if lq.get('surprise_percentage') is not None:
                    surprise = lq['surprise_percentage']
                    symbol = "✅" if surprise > 0 else "❌"
                    lines.append(f"  • Surprise: {symbol} {surprise:+.2f}%")

        return "\n".join(lines)

    def _format_technicals(self, technicals: Dict[str, Any]) -> str:
        """Format technical indicators section."""
        lines = ["📈 TECHNICAL INDICATORS"]

        if "rsi" in technicals:
            rsi = technicals["rsi"]
            interpretation = rsi.get("interpretation", "neutral").upper()
            emoji = "🔥" if interpretation == "OVERBOUGHT" else "❄️" if interpretation == "OVERSOLD" else "⚖️"
            lines.append(f"RSI (14-day): {rsi.get('rsi', 0):.2f} {emoji} {interpretation}")

        if "macd" in technicals:
            macd = technicals["macd"]
            interp = macd.get("interpretation", "neutral")
            emoji = "🚀" if "bullish" in interp else "📉" if "bearish" in interp else "➡️"
            lines.append(f"MACD: {macd.get('macd', 0):.4f} {emoji} {interp.replace('_', ' ').upper()}")
            if macd.get("crossover"):
                lines.append(f"  ⚡ {macd['crossover'].upper()} CROSSOVER DETECTED")

        if "sma_50" in technicals:
            sma50 = technicals["sma_50"]
            lines.append(f"SMA-50: €{sma50.get('sma', 0):.2f}")

        if "sma_200" in technicals:
            sma200 = technicals["sma_200"]
            lines.append(f"SMA-200: €{sma200.get('sma', 0):.2f}")

        # Golden/Death cross detection
        if "sma_50" in technicals and "sma_200" in technicals:
            sma50_val = technicals["sma_50"].get("sma", 0)
            sma200_val = technicals["sma_200"].get("sma", 0)
            if sma50_val > sma200_val:
                lines.append("  ⚡ GOLDEN CROSS (50 > 200) - Bullish long-term trend")
            elif sma50_val < sma200_val:
                lines.append("  ⚠️ DEATH CROSS (50 < 200) - Bearish long-term trend")

        return "\n".join(lines)

    def _format_news(self, news_data: Dict[str, Any]) -> str:
        """Format news and sentiment section."""
        lines = ["📰 NEWS & SENTIMENT"]

        if "sentiment_score" in news_data:
            sent = news_data["sentiment_score"]
            interpretation = sent.get("interpretation", "neutral").upper()
            emoji = "🟢" if "bullish" in interpretation else "🔴" if "bearish" in interpretation else "⚪"
            lines.append(f"Overall Sentiment: {emoji} {interpretation}")
            lines.append(f"  • Bullish: {sent.get('sentiment_bullish', 0):.1f}%")
            lines.append(f"  • Bearish: {sent.get('sentiment_bearish', 0):.1f}%")
            lines.append(f"  • Articles this week: {sent.get('buzz_articles_in_last_week', 0)}")

        if "sentiment_distribution" in news_data:
            dist = news_data["sentiment_distribution"]
            total = sum(dist.values())
            if total > 0:
                lines.append(f"\nNews Article Sentiment (last 7 days):")
                lines.append(f"  • Positive: {dist.get('positive', 0)} ({dist.get('positive', 0)/total*100:.0f}%)")
                lines.append(f"  • Neutral: {dist.get('neutral', 0)} ({dist.get('neutral', 0)/total*100:.0f}%)")
                lines.append(f"  • Negative: {dist.get('negative', 0)} ({dist.get('negative', 0)/total*100:.0f}%)")

        if "articles" in news_data:
            articles = news_data["articles"][:5]  # Top 5 recent articles
            if articles:
                lines.append(f"\nRecent Headlines:")
                for i, article in enumerate(articles, 1):
                    sent_emoji = "🟢" if article["sentiment"] == "positive" else "🔴" if article["sentiment"] == "negative" else "⚪"
                    lines.append(f"  {i}. {sent_emoji} {article['headline']}")
                    lines.append(f"     Source: {article['source']} | {article['datetime'].strftime('%Y-%m-%d')}")

        return "\n".join(lines)

    def _format_analyst_ratings(self, analyst_data: Dict[str, Any]) -> str:
        """Format analyst ratings section."""
        lines = ["👔 ANALYST RATINGS"]

        if "recommendations" in analyst_data:
            rec = analyst_data["recommendations"]
            consensus = rec.get("consensus", "unknown").replace("_", " ").upper()
            emoji = "🟢" if "BUY" in consensus else "🔴" if "SELL" in consensus else "⚪"

            lines.append(f"Consensus: {emoji} {consensus}")
            lines.append(f"Total Analysts: {rec.get('total_analysts', 0)}")
            lines.append(f"  • Strong Buy: {rec.get('strong_buy', 0)}")
            lines.append(f"  • Buy: {rec.get('buy', 0)}")
            lines.append(f"  • Hold: {rec.get('hold', 0)}")
            lines.append(f"  • Sell: {rec.get('sell', 0)}")
            lines.append(f"  • Strong Sell: {rec.get('strong_sell', 0)}")

        if "price_target" in analyst_data:
            pt = analyst_data["price_target"]
            if pt.get("target_mean"):
                lines.append(f"\nPrice Targets ({pt.get('num_analysts', 0)} analysts):")
                lines.append(f"  • Mean: €{pt.get('target_mean', 0):.2f}")
                lines.append(f"  • High: €{pt.get('target_high', 0):.2f}")
                lines.append(f"  • Low: €{pt.get('target_low', 0):.2f}")

        return "\n".join(lines)

    def close(self):
        """Close all API clients and database connection."""
        self.av_client.close()
        self.fh_client.close()
        if self.db:
            self.db.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
