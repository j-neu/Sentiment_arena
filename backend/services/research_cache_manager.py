"""
Research Cache Manager

Manages caching of research results to optimize costs and reduce redundant API calls.
Implements intelligent cache invalidation and sharing across trading models.

Key Features:
- Time-based cache expiration (1-4 hours configurable)
- Major market event invalidation
- Multi-model research sharing
- Cost tracking and savings estimation
- Cache hit/miss metrics

Author: Sentiment Arena
Date: 2025-10-23
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import json
import hashlib
from pathlib import Path

from backend.logger import get_logger

logger = get_logger(__name__)


@dataclass
class CachedResearch:
    """Represents a cached research result."""
    symbol: str
    research_data: Dict[str, Any]
    timestamp: datetime
    cache_ttl_hours: float
    research_type: str  # "complete", "technical", "financial", "web"
    model_used: str
    quality_score: Optional[int] = None
    access_count: int = 0
    last_accessed: Optional[datetime] = None

    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        expiry_time = self.timestamp + timedelta(hours=self.cache_ttl_hours)
        return datetime.now() > expiry_time

    def time_until_expiry(self) -> timedelta:
        """Get time remaining until cache expiry."""
        expiry_time = self.timestamp + timedelta(hours=self.cache_ttl_hours)
        return max(expiry_time - datetime.now(), timedelta(0))

    def mark_accessed(self):
        """Mark cache entry as accessed."""
        self.access_count += 1
        self.last_accessed = datetime.now()


@dataclass
class CacheMetrics:
    """Tracks cache performance metrics."""
    total_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    invalidations: int = 0
    estimated_cost_saved: float = 0.0

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        if self.total_requests == 0:
            return 0.0
        return (self.cache_hits / self.total_requests) * 100

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "total_requests": self.total_requests,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "invalidations": self.invalidations,
            "hit_rate": f"{self.hit_rate:.2f}%",
            "estimated_cost_saved": f"${self.estimated_cost_saved:.4f}"
        }


class ResearchCacheManager:
    """
    Manages caching of research results across multiple trading models.

    Features:
    - Configurable TTL (time-to-live) for different research types
    - Automatic cache invalidation on market events
    - Cost tracking and optimization
    - Multi-model research sharing
    """

    # Default TTL values (in hours)
    DEFAULT_TTL = {
        "complete": 2.0,      # Complete research valid for 2 hours
        "technical": 1.0,     # Technical analysis valid for 1 hour
        "financial": 4.0,     # Fundamental data valid for 4 hours
        "web": 2.0            # Web research valid for 2 hours
    }

    # Cost estimates for different research types
    RESEARCH_COSTS = {
        "complete": 0.012,    # Complete research ~$0.012
        "technical": 0.0,     # Technical analysis free
        "financial": 0.0,     # APIs free (rate limited)
        "web": 0.01           # Web research with LLM ~$0.01
    }

    def __init__(
        self,
        cache_dir: Optional[str] = None,
        default_ttl_hours: Optional[Dict[str, float]] = None,
        enable_persistence: bool = True
    ):
        """
        Initialize research cache manager.

        Args:
            cache_dir: Directory for cache persistence (optional)
            default_ttl_hours: Custom TTL values per research type
            enable_persistence: Enable disk-based cache persistence
        """
        self.cache: Dict[str, CachedResearch] = {}
        self.metrics = CacheMetrics()
        self.enable_persistence = enable_persistence

        # Set custom TTL or use defaults
        self.ttl_config = default_ttl_hours or self.DEFAULT_TTL.copy()

        # Setup cache directory
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            self.cache_dir = Path(__file__).parent.parent.parent / "cache" / "research"

        if enable_persistence:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self._load_cache_from_disk()

        logger.info(f"ResearchCacheManager initialized (persistence: {enable_persistence})")

    def get_cached_research(
        self,
        symbol: str,
        research_type: str = "complete"
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached research if available and not expired.

        Args:
            symbol: Stock symbol (e.g., "SAP.DE")
            research_type: Type of research ("complete", "technical", etc.)

        Returns:
            Cached research data or None if not available/expired
        """
        self.metrics.total_requests += 1
        cache_key = self._generate_cache_key(symbol, research_type)

        # Check if cache exists
        if cache_key not in self.cache:
            self.metrics.cache_misses += 1
            logger.debug(f"Cache MISS: {symbol} ({research_type})")
            return None

        cached = self.cache[cache_key]

        # Check if expired
        if cached.is_expired():
            logger.debug(f"Cache EXPIRED: {symbol} ({research_type})")
            self._invalidate_entry(cache_key)
            self.metrics.cache_misses += 1
            return None

        # Cache HIT
        self.metrics.cache_hits += 1
        cached.mark_accessed()

        # Track cost savings
        cost_saved = self.RESEARCH_COSTS.get(research_type, 0.0)
        self.metrics.estimated_cost_saved += cost_saved

        time_remaining = cached.time_until_expiry()
        logger.info(
            f"Cache HIT: {symbol} ({research_type}) - "
            f"Valid for {time_remaining.total_seconds()/60:.1f} more minutes - "
            f"Saved ~${cost_saved:.4f}"
        )

        return cached.research_data

    def cache_research(
        self,
        symbol: str,
        research_data: Dict[str, Any],
        research_type: str = "complete",
        model_used: str = "unknown",
        quality_score: Optional[int] = None,
        custom_ttl_hours: Optional[float] = None
    ) -> bool:
        """
        Cache research results.

        Args:
            symbol: Stock symbol
            research_data: Research data to cache
            research_type: Type of research
            model_used: Model that generated the research
            quality_score: Quality score (0-100)
            custom_ttl_hours: Custom TTL (overrides default)

        Returns:
            True if cached successfully
        """
        try:
            cache_key = self._generate_cache_key(symbol, research_type)
            ttl = custom_ttl_hours if custom_ttl_hours is not None else self.ttl_config.get(research_type, 2.0)

            cached_entry = CachedResearch(
                symbol=symbol,
                research_data=research_data,
                timestamp=datetime.now(),
                cache_ttl_hours=ttl,
                research_type=research_type,
                model_used=model_used,
                quality_score=quality_score
            )

            self.cache[cache_key] = cached_entry

            # Persist to disk if enabled
            if self.enable_persistence:
                self._save_entry_to_disk(cache_key, cached_entry)

            logger.info(
                f"Cached research: {symbol} ({research_type}) - "
                f"TTL: {ttl}h - Quality: {quality_score or 'N/A'}"
            )

            return True

        except Exception as e:
            logger.error(f"Error caching research: {str(e)}", exc_info=True)
            return False

    def invalidate_symbol(self, symbol: str) -> int:
        """
        Invalidate all cached research for a specific symbol.

        Args:
            symbol: Stock symbol to invalidate

        Returns:
            Number of entries invalidated
        """
        count = 0
        keys_to_remove = []

        for key, cached in self.cache.items():
            if cached.symbol.upper() == symbol.upper():
                keys_to_remove.append(key)

        for key in keys_to_remove:
            self._invalidate_entry(key)
            count += 1

        logger.info(f"Invalidated {count} cache entries for {symbol}")
        return count

    def invalidate_by_event(self, event_type: str, symbols: Optional[List[str]] = None):
        """
        Invalidate cache based on market events.

        Args:
            event_type: Type of event ("earnings", "news", "market_crash", etc.)
            symbols: Affected symbols (None = invalidate all)
        """
        if symbols:
            total = 0
            for symbol in symbols:
                total += self.invalidate_symbol(symbol)
            logger.warning(f"Market event '{event_type}': Invalidated {total} entries for {len(symbols)} symbols")
        else:
            # Major event - clear entire cache
            count = len(self.cache)
            self.cache.clear()
            if self.enable_persistence:
                self._clear_disk_cache()
            logger.warning(f"Major market event '{event_type}': Cleared entire cache ({count} entries)")
            self.metrics.invalidations += count

    def cleanup_expired(self) -> int:
        """
        Remove all expired cache entries.

        Returns:
            Number of entries removed
        """
        keys_to_remove = []

        for key, cached in self.cache.items():
            if cached.is_expired():
                keys_to_remove.append(key)

        for key in keys_to_remove:
            self._invalidate_entry(key)

        if keys_to_remove:
            logger.info(f"Cleaned up {len(keys_to_remove)} expired cache entries")

        return len(keys_to_remove)

    def get_cache_status(self) -> Dict[str, Any]:
        """
        Get current cache status and metrics.

        Returns:
            Dictionary with cache statistics
        """
        # Categorize entries by type
        by_type: Dict[str, int] = {}
        by_symbol: Dict[str, int] = {}

        for cached in self.cache.values():
            by_type[cached.research_type] = by_type.get(cached.research_type, 0) + 1
            by_symbol[cached.symbol] = by_symbol.get(cached.symbol, 0) + 1

        # Find most accessed entries
        most_accessed = sorted(
            self.cache.values(),
            key=lambda x: x.access_count,
            reverse=True
        )[:5]

        return {
            "total_entries": len(self.cache),
            "by_type": by_type,
            "unique_symbols": len(by_symbol),
            "metrics": self.metrics.to_dict(),
            "most_accessed": [
                {
                    "symbol": e.symbol,
                    "type": e.research_type,
                    "access_count": e.access_count,
                    "quality_score": e.quality_score
                }
                for e in most_accessed
            ],
            "persistence_enabled": self.enable_persistence,
            "cache_directory": str(self.cache_dir) if self.enable_persistence else None
        }

    def _generate_cache_key(self, symbol: str, research_type: str) -> str:
        """Generate unique cache key for symbol and research type."""
        return f"{symbol.upper()}:{research_type}"

    def _invalidate_entry(self, cache_key: str):
        """Remove entry from cache and disk."""
        if cache_key in self.cache:
            del self.cache[cache_key]
            self.metrics.invalidations += 1

            if self.enable_persistence:
                self._delete_entry_from_disk(cache_key)

    def _save_entry_to_disk(self, cache_key: str, entry: CachedResearch):
        """Save cache entry to disk."""
        try:
            # Use hash of cache key for filename
            filename = hashlib.md5(cache_key.encode()).hexdigest() + ".json"
            filepath = self.cache_dir / filename

            data = {
                "symbol": entry.symbol,
                "research_type": entry.research_type,
                "timestamp": entry.timestamp.isoformat(),
                "cache_ttl_hours": entry.cache_ttl_hours,
                "model_used": entry.model_used,
                "quality_score": entry.quality_score,
                "access_count": entry.access_count,
                "last_accessed": entry.last_accessed.isoformat() if entry.last_accessed else None,
                "research_data": entry.research_data
            }

            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            logger.error(f"Error saving cache to disk: {str(e)}")

    def _load_cache_from_disk(self):
        """Load cache entries from disk."""
        try:
            if not self.cache_dir.exists():
                return

            count = 0
            for filepath in self.cache_dir.glob("*.json"):
                try:
                    with open(filepath, 'r') as f:
                        data = json.load(f)

                    entry = CachedResearch(
                        symbol=data["symbol"],
                        research_data=data["research_data"],
                        timestamp=datetime.fromisoformat(data["timestamp"]),
                        cache_ttl_hours=data["cache_ttl_hours"],
                        research_type=data["research_type"],
                        model_used=data["model_used"],
                        quality_score=data.get("quality_score"),
                        access_count=data.get("access_count", 0),
                        last_accessed=datetime.fromisoformat(data["last_accessed"]) if data.get("last_accessed") else None
                    )

                    # Only load if not expired
                    if not entry.is_expired():
                        cache_key = self._generate_cache_key(entry.symbol, entry.research_type)
                        self.cache[cache_key] = entry
                        count += 1
                    else:
                        # Delete expired entry from disk
                        filepath.unlink()

                except Exception as e:
                    logger.error(f"Error loading cache file {filepath}: {str(e)}")

            if count > 0:
                logger.info(f"Loaded {count} cache entries from disk")

        except Exception as e:
            logger.error(f"Error loading cache from disk: {str(e)}")

    def _delete_entry_from_disk(self, cache_key: str):
        """Delete cache entry from disk."""
        try:
            filename = hashlib.md5(cache_key.encode()).hexdigest() + ".json"
            filepath = self.cache_dir / filename

            if filepath.exists():
                filepath.unlink()

        except Exception as e:
            logger.error(f"Error deleting cache file: {str(e)}")

    def _clear_disk_cache(self):
        """Clear all cache files from disk."""
        try:
            if self.cache_dir.exists():
                for filepath in self.cache_dir.glob("*.json"):
                    filepath.unlink()
                logger.info("Cleared all cache files from disk")
        except Exception as e:
            logger.error(f"Error clearing disk cache: {str(e)}")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup expired entries."""
        self.cleanup_expired()
