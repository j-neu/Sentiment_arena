"""
Internet research system for financial news and market sentiment.

This module provides functionality for searching and aggregating financial news
from multiple sources to inform trading decisions.
"""

import time
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import hashlib
import requests
from urllib.parse import quote_plus

from backend.config import settings
from backend.logger import get_logger

logger = get_logger(__name__)


class ResearchService:
    """Service for performing internet research on stocks and market news."""

    # Target financial news sources
    PREFERRED_SOURCES = [
        "thefly.com",
        "biztoc.com",
        "forexfactory.com",
        "finance.yahoo.com",
        "reuters.com",
        "bloomberg.com",
        "marketwatch.com",
        "cnbc.com",
        "wsj.com"
    ]

    def __init__(self):
        """Initialize the research service."""
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.cache_ttl = 300  # 5 minutes cache

        logger.info("Research service initialized")

    def search_stock_news(
        self,
        symbol: str,
        max_results: int = 10,
        time_range: str = "1d"
    ) -> List[Dict[str, Any]]:
        """
        Search for news about a specific stock.

        Args:
            symbol: Stock symbol (e.g., "SAP.DE")
            max_results: Maximum number of results to return
            time_range: Time range for news (1d, 1w, 1m)

        Returns:
            List of news articles with title, url, source, snippet, date
        """
        # Remove .DE suffix for search query
        search_symbol = symbol.replace(".DE", "")

        query = f"{search_symbol} stock news"

        logger.info(f"Searching news for {symbol} (query: {query})")

        # Check cache
        cache_key = self._get_cache_key(query, time_range)
        if cache_key in self.cache:
            cached_data = self.cache[cache_key]
            if time.time() - cached_data["timestamp"] < self.cache_ttl:
                logger.info(f"Returning cached results for {symbol}")
                return cached_data["results"]

        # Perform web search
        results = self._web_search(query, max_results, time_range)

        # Cache results
        self.cache[cache_key] = {
            "timestamp": time.time(),
            "results": results
        }

        logger.info(f"Found {len(results)} news articles for {symbol}")
        return results

    def search_market_sentiment(
        self,
        query: str,
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search for general market sentiment and news.

        Args:
            query: Search query (e.g., "German stock market today")
            max_results: Maximum number of results

        Returns:
            List of articles with sentiment information
        """
        logger.info(f"Searching market sentiment for: {query}")

        # Check cache
        cache_key = self._get_cache_key(query, "sentiment")
        if cache_key in self.cache:
            cached_data = self.cache[cache_key]
            if time.time() - cached_data["timestamp"] < self.cache_ttl:
                logger.info("Returning cached sentiment results")
                return cached_data["results"]

        # Perform web search
        results = self._web_search(query, max_results, "1d")

        # Cache results
        self.cache[cache_key] = {
            "timestamp": time.time(),
            "results": results
        }

        logger.info(f"Found {len(results)} sentiment articles")
        return results

    def _web_search(
        self,
        query: str,
        max_results: int,
        time_range: str = "1d"
    ) -> List[Dict[str, Any]]:
        """
        Perform web search using DuckDuckGo HTML interface (no API key needed).

        Args:
            query: Search query
            max_results: Maximum results to return
            time_range: Time range filter

        Returns:
            List of search results
        """
        try:
            # Use DuckDuckGo HTML search (no API key required)
            search_url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"

            response = self.session.get(search_url, timeout=10)
            response.raise_for_status()

            # Parse results (basic HTML parsing)
            results = self._parse_duckduckgo_results(response.text, max_results)

            # Filter by preferred sources if available
            filtered_results = self._filter_by_source(results)

            return filtered_results[:max_results]

        except requests.exceptions.RequestException as e:
            logger.error(f"Web search failed: {e}")
            return []

        except Exception as e:
            logger.error(f"Unexpected error during web search: {e}")
            return []

    def _parse_duckduckgo_results(
        self,
        html: str,
        max_results: int
    ) -> List[Dict[str, Any]]:
        """
        Parse DuckDuckGo HTML search results.

        Args:
            html: HTML response
            max_results: Maximum results to extract

        Returns:
            List of parsed results
        """
        results = []

        try:
            # Simple HTML parsing (looking for result links)
            # In production, you'd use BeautifulSoup, but keeping dependencies minimal
            import re

            # Find all result blocks
            result_pattern = r'result__a.*?href="([^"]+)".*?>([^<]+)</a>'
            snippet_pattern = r'result__snippet.*?>([^<]+)</a>'

            matches = re.finditer(result_pattern, html, re.DOTALL)

            for match in matches:
                if len(results) >= max_results:
                    break

                url = match.group(1)
                title = match.group(2).strip()

                # Try to extract snippet
                snippet = ""
                snippet_match = re.search(snippet_pattern, html[match.end():match.end()+500])
                if snippet_match:
                    snippet = snippet_match.group(1).strip()

                # Extract domain from URL
                domain_match = re.search(r'https?://([^/]+)', url)
                source = domain_match.group(1) if domain_match else "unknown"

                results.append({
                    "title": title,
                    "url": url,
                    "source": source,
                    "snippet": snippet,
                    "date": datetime.now().isoformat(),
                    "relevance": "high" if any(s in source for s in self.PREFERRED_SOURCES) else "medium"
                })

        except Exception as e:
            logger.error(f"Failed to parse search results: {e}")

        return results

    def _filter_by_source(
        self,
        results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Filter and rank results by preferred sources.

        Args:
            results: List of search results

        Returns:
            Filtered and sorted results (preferred sources first)
        """
        # Separate preferred and other sources
        preferred = []
        others = []

        for result in results:
            source = result.get("source", "")
            if any(preferred_source in source for preferred_source in self.PREFERRED_SOURCES):
                preferred.append(result)
            else:
                others.append(result)

        # Return preferred sources first
        return preferred + others

    def aggregate_research(
        self,
        symbols: List[str],
        general_queries: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Aggregate research for multiple symbols and general market queries.

        Args:
            symbols: List of stock symbols
            general_queries: List of general market queries

        Returns:
            Dictionary with aggregated research results
        """
        logger.info(f"Aggregating research for {len(symbols)} symbols")

        results = {
            "timestamp": datetime.now().isoformat(),
            "stock_news": {},
            "market_sentiment": [],
            "summary": ""
        }

        # Search news for each symbol
        for symbol in symbols:
            try:
                news = self.search_stock_news(symbol, max_results=5)
                results["stock_news"][symbol] = news
            except Exception as e:
                logger.error(f"Failed to fetch news for {symbol}: {e}")
                results["stock_news"][symbol] = []

        # Search general market sentiment
        if general_queries:
            for query in general_queries:
                try:
                    sentiment = self.search_market_sentiment(query, max_results=5)
                    results["market_sentiment"].extend(sentiment)
                except Exception as e:
                    logger.error(f"Failed to fetch sentiment for '{query}': {e}")

        # Generate summary
        total_articles = sum(len(news) for news in results["stock_news"].values())
        total_articles += len(results["market_sentiment"])

        results["summary"] = (
            f"Found {total_articles} articles across {len(symbols)} stocks. "
            f"Research completed at {results['timestamp']}."
        )

        logger.info(f"Research aggregation complete: {total_articles} total articles")

        return results

    def format_research_for_llm(
        self,
        research_data: Dict[str, Any],
        max_articles_per_symbol: int = 3
    ) -> str:
        """
        Format research data for LLM consumption.

        Args:
            research_data: Aggregated research data
            max_articles_per_symbol: Maximum articles to include per symbol

        Returns:
            Formatted string for LLM prompt
        """
        lines = []
        lines.append("=== MARKET RESEARCH ===")
        lines.append(f"Research Date: {research_data['timestamp']}")
        lines.append("")

        # Stock-specific news
        if research_data["stock_news"]:
            lines.append("--- Stock-Specific News ---")
            for symbol, articles in research_data["stock_news"].items():
                lines.append(f"\n{symbol}:")
                for i, article in enumerate(articles[:max_articles_per_symbol], 1):
                    lines.append(f"  {i}. {article['title']}")
                    lines.append(f"     Source: {article['source']}")
                    if article.get("snippet"):
                        lines.append(f"     {article['snippet']}")
                    lines.append("")

        # General market sentiment
        if research_data["market_sentiment"]:
            lines.append("--- General Market Sentiment ---")
            for i, article in enumerate(research_data["market_sentiment"][:5], 1):
                lines.append(f"{i}. {article['title']}")
                lines.append(f"   Source: {article['source']}")
                if article.get("snippet"):
                    lines.append(f"   {article['snippet']}")
                lines.append("")

        lines.append(f"Summary: {research_data['summary']}")
        lines.append("=" * 50)

        return "\n".join(lines)

    def _get_cache_key(self, query: str, time_range: str) -> str:
        """Generate cache key from query and time range."""
        key_string = f"{query}_{time_range}"
        return hashlib.md5(key_string.encode()).hexdigest()

    def clear_cache(self):
        """Clear the research cache."""
        self.cache.clear()
        logger.info("Research cache cleared")

    def close(self):
        """Close the session."""
        self.session.close()
        logger.info("Research service session closed")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
