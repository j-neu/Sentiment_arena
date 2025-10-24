"""
Multi-Model Research Orchestrator

Coordinates research across multiple trading models with intelligent caching,
cost optimization, and quality tracking.

Key Features:
- Research model selection (cheap models for research, premium for trading)
- Intelligent caching with configurable TTL
- Research sharing across trading models
- Quality metrics tracking over time
- Cost optimization and monitoring
- Market event-based cache invalidation

Author: Sentiment Arena
Date: 2025-10-23
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass
import time

from backend.services.complete_research_orchestrator import CompleteResearchOrchestrator
from backend.services.research_cache_manager import ResearchCacheManager
from backend.services.research_model_mapper import ResearchModelMapper
from backend.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ResearchQualityMetrics:
    """Tracks research quality metrics over time."""
    symbol: str
    total_researches: int = 0
    average_quality_score: float = 0.0
    quality_scores: List[int] = None
    last_research_time: Optional[datetime] = None
    cache_hit_count: int = 0
    cache_miss_count: int = 0
    total_cost_estimate: float = 0.0
    cost_saved_by_cache: float = 0.0

    def __post_init__(self):
        if self.quality_scores is None:
            self.quality_scores = []

    def add_quality_score(self, score: int, from_cache: bool = False, cost: float = 0.0):
        """Add new quality score and update metrics."""
        if score is not None:
            self.quality_scores.append(score)
            self.total_researches += 1
            self.average_quality_score = sum(self.quality_scores) / len(self.quality_scores)
            self.last_research_time = datetime.now()

        if from_cache:
            self.cache_hit_count += 1
            self.cost_saved_by_cache += cost
        else:
            self.cache_miss_count += 1
            self.total_cost_estimate += cost

    @property
    def cache_hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.cache_hit_count + self.cache_miss_count
        if total == 0:
            return 0.0
        return (self.cache_hit_count / total) * 100

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "symbol": self.symbol,
            "total_researches": self.total_researches,
            "average_quality_score": round(self.average_quality_score, 2),
            "latest_score": self.quality_scores[-1] if self.quality_scores else None,
            "last_research": self.last_research_time.isoformat() if self.last_research_time else None,
            "cache_hit_rate": f"{self.cache_hit_rate:.1f}%",
            "total_cost": f"${self.total_cost_estimate:.4f}",
            "cost_saved": f"${self.cost_saved_by_cache:.4f}"
        }


class MultiModelResearchOrchestrator:
    """
    Orchestrates research across multiple trading models with caching and optimization.

    Strategy:
    1. Use cheaper models for research (GPT-3.5 vs GPT-4)
    2. Cache research results for 1-4 hours (configurable)
    3. Share research across multiple trading models
    4. Track quality metrics over time
    5. Invalidate cache on major market events
    """

    def __init__(
        self,
        openrouter_api_key: str,
        alphavantage_api_key: Optional[str] = None,
        finnhub_api_key: Optional[str] = None,
        enable_caching: bool = True,
        cache_dir: Optional[str] = None,
        default_cache_ttl_hours: float = 2.0
    ):
        """
        Initialize multi-model research orchestrator.

        Args:
            openrouter_api_key: OpenRouter API key
            alphavantage_api_key: Alpha Vantage API key (optional)
            finnhub_api_key: Finnhub API key (optional)
            enable_caching: Enable research caching (default: True)
            cache_dir: Custom cache directory (optional)
            default_cache_ttl_hours: Default cache TTL (default: 2 hours)
        """
        self.openrouter_api_key = openrouter_api_key
        self.alphavantage_api_key = alphavantage_api_key
        self.finnhub_api_key = finnhub_api_key
        self.enable_caching = enable_caching

        # Initialize cache manager
        if enable_caching:
            self.cache_manager = ResearchCacheManager(
                cache_dir=cache_dir,
                default_ttl_hours={"complete": default_cache_ttl_hours}
            )
        else:
            self.cache_manager = None

        # Track quality metrics per symbol
        self.quality_metrics: Dict[str, ResearchQualityMetrics] = {}

        # Track orchestrators per research model (reuse for efficiency)
        self._orchestrators: Dict[str, CompleteResearchOrchestrator] = {}

        logger.info(f"MultiModelResearchOrchestrator initialized (caching: {enable_caching})")

    def conduct_research_for_model(
        self,
        trading_model: str,
        symbols: List[str],
        force_refresh: bool = False,
        include_technical: bool = True,
        include_financial_apis: bool = True,
        include_web_research: bool = True,
        include_quality_verification: bool = True
    ) -> Dict[str, Dict[str, Any]]:
        """
        Conduct research for multiple symbols using optimal research model.

        Args:
            trading_model: Trading model identifier (e.g., "openai/gpt-4-turbo")
            symbols: List of stock symbols to research
            force_refresh: Force new research (ignore cache)
            include_technical: Include technical analysis
            include_financial_apis: Include financial API data
            include_web_research: Include web research
            include_quality_verification: Run quality verification

        Returns:
            Dictionary mapping symbols to research results
        """
        # Determine optimal research model
        research_model = ResearchModelMapper.get_research_model(trading_model)
        company = ResearchModelMapper.get_model_company(trading_model)
        is_same = trading_model == research_model

        logger.info(
            f"Research for {len(symbols)} symbols - "
            f"Trading: {trading_model}, Research: {research_model} "
            f"({company}) {'(same model)' if is_same else '(cheaper model)'}"
        )

        results = {}

        for symbol in symbols:
            try:
                result = self._conduct_symbol_research(
                    symbol=symbol,
                    research_model=research_model,
                    trading_model=trading_model,
                    force_refresh=force_refresh,
                    include_technical=include_technical,
                    include_financial_apis=include_financial_apis,
                    include_web_research=include_web_research,
                    include_quality_verification=include_quality_verification
                )
                results[symbol] = result

            except Exception as e:
                logger.error(f"Error researching {symbol}: {str(e)}", exc_info=True)
                results[symbol] = {
                    "success": False,
                    "error": str(e),
                    "symbol": symbol
                }

        return results

    def _conduct_symbol_research(
        self,
        symbol: str,
        research_model: str,
        trading_model: str,
        force_refresh: bool,
        include_technical: bool,
        include_financial_apis: bool,
        include_web_research: bool,
        include_quality_verification: bool
    ) -> Dict[str, Any]:
        """Conduct research for a single symbol with caching."""

        # Check cache first (unless force refresh)
        if self.enable_caching and not force_refresh:
            cached_result = self.cache_manager.get_cached_research(
                symbol=symbol,
                research_type="complete"
            )

            if cached_result:
                # Track cache hit
                if symbol not in self.quality_metrics:
                    self.quality_metrics[symbol] = ResearchQualityMetrics(symbol=symbol)

                quality_score = cached_result.get("quality_score")
                self.quality_metrics[symbol].add_quality_score(
                    score=quality_score,
                    from_cache=True,
                    cost=0.012  # Estimated cost saved
                )

                logger.info(f"Using cached research for {symbol} (Quality: {quality_score or 'N/A'})")
                cached_result["from_cache"] = True
                cached_result["trading_model"] = trading_model
                cached_result["research_model"] = research_model
                return cached_result

        # Cache miss - conduct new research
        logger.info(f"Conducting NEW research for {symbol} using {research_model}")

        # Get or create orchestrator for this research model
        orchestrator = self._get_orchestrator(research_model)

        # Conduct research
        start_time = time.time()
        result = orchestrator.conduct_complete_research(
            symbol=symbol,
            include_technical=include_technical,
            include_financial_apis=include_financial_apis,
            include_web_research=include_web_research,
            include_quality_verification=include_quality_verification
        )

        research_time = time.time() - start_time

        # Track quality metrics
        if symbol not in self.quality_metrics:
            self.quality_metrics[symbol] = ResearchQualityMetrics(symbol=symbol)

        quality_score = result.get("quality_score")
        self.quality_metrics[symbol].add_quality_score(
            score=quality_score,
            from_cache=False,
            cost=0.012  # Estimated research cost
        )

        # Cache result if successful
        if self.enable_caching and result.get("success"):
            self.cache_manager.cache_research(
                symbol=symbol,
                research_data=result,
                research_type="complete",
                model_used=research_model,
                quality_score=quality_score
            )

        # Add metadata
        result["from_cache"] = False
        result["trading_model"] = trading_model
        result["research_model"] = research_model
        result["research_time"] = research_time

        logger.info(
            f"Research complete for {symbol} - "
            f"Time: {research_time:.1f}s, Quality: {quality_score or 'N/A'}"
        )

        return result

    def _get_orchestrator(self, research_model: str) -> CompleteResearchOrchestrator:
        """Get or create orchestrator for research model."""
        if research_model not in self._orchestrators:
            self._orchestrators[research_model] = CompleteResearchOrchestrator(
                openrouter_api_key=self.openrouter_api_key,
                alphavantage_api_key=self.alphavantage_api_key,
                finnhub_api_key=self.finnhub_api_key,
                model_identifier=research_model
            )
            logger.info(f"Created new orchestrator for research model: {research_model}")

        return self._orchestrators[research_model]

    def invalidate_research(
        self,
        event_type: str,
        symbols: Optional[List[str]] = None,
        reason: Optional[str] = None
    ):
        """
        Invalidate cached research based on market events.

        Args:
            event_type: Type of event ("earnings", "major_news", "market_crash", etc.)
            symbols: Affected symbols (None = invalidate all)
            reason: Optional reason for invalidation
        """
        if not self.enable_caching:
            return

        event_severity = {
            "earnings": "symbol",      # Only invalidate specific symbol
            "major_news": "symbol",    # Only invalidate specific symbol
            "market_crash": "all",     # Invalidate everything
            "rate_change": "all",      # Invalidate everything
            "geopolitical": "all"      # Invalidate everything
        }

        severity = event_severity.get(event_type, "symbol")

        if severity == "all":
            logger.warning(f"Major market event '{event_type}': Invalidating ALL cached research")
            self.cache_manager.invalidate_by_event(event_type)
        elif symbols:
            logger.info(f"Market event '{event_type}': Invalidating research for {len(symbols)} symbols")
            for symbol in symbols:
                self.cache_manager.invalidate_symbol(symbol)
        else:
            logger.warning(f"Event '{event_type}' requires symbol list, but none provided")

    def get_quality_metrics(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """
        Get quality metrics for symbol(s).

        Args:
            symbol: Specific symbol (None = all symbols)

        Returns:
            Quality metrics dictionary
        """
        if symbol:
            if symbol in self.quality_metrics:
                return self.quality_metrics[symbol].to_dict()
            else:
                return {"error": f"No metrics available for {symbol}"}
        else:
            return {
                sym: metrics.to_dict()
                for sym, metrics in self.quality_metrics.items()
            }

    def get_system_status(self) -> Dict[str, Any]:
        """
        Get overall system status and metrics.

        Returns:
            System status dictionary
        """
        cache_status = self.cache_manager.get_cache_status() if self.enable_caching else {}

        # Calculate aggregate metrics
        total_researches = sum(m.total_researches for m in self.quality_metrics.values())
        total_cost = sum(m.total_cost_estimate for m in self.quality_metrics.values())
        total_saved = sum(m.cost_saved_by_cache for m in self.quality_metrics.values())

        avg_quality = 0.0
        if self.quality_metrics:
            avg_quality = sum(
                m.average_quality_score for m in self.quality_metrics.values()
            ) / len(self.quality_metrics)

        return {
            "caching_enabled": self.enable_caching,
            "cache_status": cache_status,
            "quality_tracking": {
                "symbols_tracked": len(self.quality_metrics),
                "total_researches": total_researches,
                "average_quality_score": round(avg_quality, 2),
                "total_cost_estimate": f"${total_cost:.4f}",
                "cost_saved_by_cache": f"${total_saved:.4f}",
                "net_cost": f"${(total_cost - total_saved):.4f}"
            },
            "active_orchestrators": len(self._orchestrators),
            "research_models_in_use": list(self._orchestrators.keys())
        }

    def cleanup(self):
        """Cleanup expired cache entries and release resources."""
        if self.enable_caching:
            expired = self.cache_manager.cleanup_expired()
            logger.info(f"Cleanup: Removed {expired} expired cache entries")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.cleanup()

        # Close orchestrators
        for orchestrator in self._orchestrators.values():
            orchestrator.__exit__(exc_type, exc_val, exc_tb)
