"""
Unit Tests for Multi-Model Research Orchestration (Phase 3.5.5)

Tests:
- Research cache manager (caching, invalidation, metrics)
- Multi-model research orchestrator (model selection, caching, quality tracking)
- Integration with existing components

Author: Sentiment Arena
Date: 2025-10-23
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import tempfile
import shutil
from pathlib import Path

from backend.services.research_cache_manager import (
    ResearchCacheManager,
    CachedResearch,
    CacheMetrics
)
from backend.services.multi_model_research_orchestrator import (
    MultiModelResearchOrchestrator,
    ResearchQualityMetrics
)
from backend.services.research_model_mapper import ResearchModelMapper


class TestCachedResearch(unittest.TestCase):
    """Test CachedResearch dataclass."""

    def test_is_expired_not_expired(self):
        """Test cache entry that hasn't expired."""
        entry = CachedResearch(
            symbol="SAP.DE",
            research_data={"test": "data"},
            timestamp=datetime.now(),
            cache_ttl_hours=2.0,
            research_type="complete",
            model_used="gpt-3.5"
        )
        self.assertFalse(entry.is_expired())

    def test_is_expired_expired(self):
        """Test cache entry that has expired."""
        entry = CachedResearch(
            symbol="SAP.DE",
            research_data={"test": "data"},
            timestamp=datetime.now() - timedelta(hours=3),
            cache_ttl_hours=2.0,
            research_type="complete",
            model_used="gpt-3.5"
        )
        self.assertTrue(entry.is_expired())

    def test_time_until_expiry(self):
        """Test time remaining until expiry."""
        entry = CachedResearch(
            symbol="SAP.DE",
            research_data={"test": "data"},
            timestamp=datetime.now(),
            cache_ttl_hours=2.0,
            research_type="complete",
            model_used="gpt-3.5"
        )
        time_left = entry.time_until_expiry()
        # Should be close to 2 hours
        self.assertGreater(time_left.total_seconds(), 7000)  # ~1.9 hours

    def test_mark_accessed(self):
        """Test marking entry as accessed."""
        entry = CachedResearch(
            symbol="SAP.DE",
            research_data={"test": "data"},
            timestamp=datetime.now(),
            cache_ttl_hours=2.0,
            research_type="complete",
            model_used="gpt-3.5"
        )

        self.assertEqual(entry.access_count, 0)
        self.assertIsNone(entry.last_accessed)

        entry.mark_accessed()

        self.assertEqual(entry.access_count, 1)
        self.assertIsNotNone(entry.last_accessed)


class TestCacheMetrics(unittest.TestCase):
    """Test CacheMetrics dataclass."""

    def test_hit_rate_zero_requests(self):
        """Test hit rate with zero requests."""
        metrics = CacheMetrics()
        self.assertEqual(metrics.hit_rate, 0.0)

    def test_hit_rate_calculation(self):
        """Test hit rate calculation."""
        metrics = CacheMetrics(
            total_requests=100,
            cache_hits=75,
            cache_misses=25
        )
        self.assertEqual(metrics.hit_rate, 75.0)

    def test_to_dict(self):
        """Test conversion to dictionary."""
        metrics = CacheMetrics(
            total_requests=50,
            cache_hits=30,
            cache_misses=20,
            invalidations=5,
            estimated_cost_saved=0.36
        )
        data = metrics.to_dict()

        self.assertEqual(data["total_requests"], 50)
        self.assertEqual(data["cache_hits"], 30)
        self.assertEqual(data["hit_rate"], "60.00%")
        self.assertEqual(data["estimated_cost_saved"], "$0.3600")


class TestResearchCacheManager(unittest.TestCase):
    """Test ResearchCacheManager."""

    def setUp(self):
        """Set up test cache manager with temp directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.cache_manager = ResearchCacheManager(
            cache_dir=self.temp_dir,
            enable_persistence=True
        )

    def tearDown(self):
        """Clean up temp directory."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_initialization(self):
        """Test cache manager initialization."""
        self.assertIsNotNone(self.cache_manager)
        self.assertTrue(self.cache_manager.enable_persistence)
        self.assertEqual(len(self.cache_manager.cache), 0)

    def test_cache_and_retrieve(self):
        """Test caching and retrieving research."""
        research_data = {
            "success": True,
            "symbol": "SAP.DE",
            "data": "test data"
        }

        # Cache research
        success = self.cache_manager.cache_research(
            symbol="SAP.DE",
            research_data=research_data,
            research_type="complete",
            model_used="gpt-3.5",
            quality_score=85
        )
        self.assertTrue(success)

        # Retrieve cached research
        cached = self.cache_manager.get_cached_research("SAP.DE", "complete")
        self.assertIsNotNone(cached)
        self.assertEqual(cached["symbol"], "SAP.DE")
        self.assertEqual(cached["data"], "test data")

        # Check metrics
        self.assertEqual(self.cache_manager.metrics.cache_hits, 1)
        self.assertEqual(self.cache_manager.metrics.cache_misses, 0)

    def test_cache_miss(self):
        """Test cache miss for non-existent entry."""
        cached = self.cache_manager.get_cached_research("UNKNOWN.DE", "complete")
        self.assertIsNone(cached)
        self.assertEqual(self.cache_manager.metrics.cache_misses, 1)

    def test_expired_cache_entry(self):
        """Test that expired entries are not returned."""
        import time
        research_data = {"success": True, "symbol": "SAP.DE"}

        # Cache with very short TTL
        self.cache_manager.cache_research(
            symbol="SAP.DE",
            research_data=research_data,
            research_type="complete",
            model_used="gpt-3.5",
            custom_ttl_hours=0.0001  # Expires in 0.36 seconds
        )

        # Wait for expiry
        time.sleep(0.5)

        # Try to retrieve (should be expired)
        cached = self.cache_manager.get_cached_research("SAP.DE", "complete")
        self.assertIsNone(cached)
        self.assertEqual(self.cache_manager.metrics.cache_misses, 1)

    def test_invalidate_symbol(self):
        """Test invalidating all cache for a symbol."""
        # Cache multiple types for same symbol
        for research_type in ["complete", "technical", "financial"]:
            self.cache_manager.cache_research(
                symbol="SAP.DE",
                research_data={"type": research_type},
                research_type=research_type,
                model_used="gpt-3.5"
            )

        self.assertEqual(len(self.cache_manager.cache), 3)

        # Invalidate all for SAP.DE
        count = self.cache_manager.invalidate_symbol("SAP.DE")
        self.assertEqual(count, 3)
        self.assertEqual(len(self.cache_manager.cache), 0)

    def test_invalidate_by_event_specific_symbols(self):
        """Test event-based invalidation for specific symbols."""
        # Cache for multiple symbols
        for symbol in ["SAP.DE", "VOW3.DE", "DAI.DE"]:
            self.cache_manager.cache_research(
                symbol=symbol,
                research_data={"symbol": symbol},
                research_type="complete",
                model_used="gpt-3.5"
            )

        # Invalidate only SAP.DE and VOW3.DE
        self.cache_manager.invalidate_by_event("earnings", ["SAP.DE", "VOW3.DE"])

        # DAI.DE should still be cached
        cached = self.cache_manager.get_cached_research("DAI.DE", "complete")
        self.assertIsNotNone(cached)

        # Others should be invalidated
        self.assertIsNone(self.cache_manager.get_cached_research("SAP.DE", "complete"))
        self.assertIsNone(self.cache_manager.get_cached_research("VOW3.DE", "complete"))

    def test_invalidate_by_event_all(self):
        """Test event-based invalidation of entire cache."""
        # Cache multiple entries
        for symbol in ["SAP.DE", "VOW3.DE", "DAI.DE"]:
            self.cache_manager.cache_research(
                symbol=symbol,
                research_data={"symbol": symbol},
                research_type="complete",
                model_used="gpt-3.5"
            )

        self.assertEqual(len(self.cache_manager.cache), 3)

        # Major event - clear all
        self.cache_manager.invalidate_by_event("market_crash")

        self.assertEqual(len(self.cache_manager.cache), 0)

    def test_cleanup_expired(self):
        """Test cleanup of expired entries."""
        import time

        # Cache one valid, one expired
        self.cache_manager.cache_research(
            symbol="VALID.DE",
            research_data={"valid": True},
            research_type="complete",
            model_used="gpt-3.5",
            custom_ttl_hours=10.0  # Valid for long time
        )

        self.cache_manager.cache_research(
            symbol="EXPIRED.DE",
            research_data={"expired": True},
            research_type="complete",
            model_used="gpt-3.5",
            custom_ttl_hours=0.0001  # Expires in 0.36 seconds
        )

        # Wait for expiry
        time.sleep(0.5)

        # Cleanup
        removed = self.cache_manager.cleanup_expired()

        self.assertEqual(removed, 1)
        self.assertEqual(len(self.cache_manager.cache), 1)

        # Valid entry should still be there
        cached = self.cache_manager.get_cached_research("VALID.DE", "complete")
        self.assertIsNotNone(cached)

    def test_get_cache_status(self):
        """Test getting cache status."""
        # Cache some entries
        for symbol in ["SAP.DE", "VOW3.DE"]:
            self.cache_manager.cache_research(
                symbol=symbol,
                research_data={},
                research_type="complete",
                model_used="gpt-3.5",
                quality_score=80
            )

        # Access one entry multiple times
        for _ in range(5):
            self.cache_manager.get_cached_research("SAP.DE", "complete")

        status = self.cache_manager.get_cache_status()

        self.assertEqual(status["total_entries"], 2)
        self.assertEqual(status["unique_symbols"], 2)
        self.assertEqual(status["by_type"]["complete"], 2)
        self.assertTrue(status["persistence_enabled"])
        self.assertGreater(len(status["most_accessed"]), 0)

    def test_persistence(self):
        """Test cache persistence to disk."""
        research_data = {"success": True, "data": "persisted"}

        # Cache data
        self.cache_manager.cache_research(
            symbol="SAP.DE",
            research_data=research_data,
            research_type="complete",
            model_used="gpt-3.5",
            quality_score=90
        )

        # Create new cache manager (should load from disk)
        new_manager = ResearchCacheManager(
            cache_dir=self.temp_dir,
            enable_persistence=True
        )

        # Should have loaded the entry
        cached = new_manager.get_cached_research("SAP.DE", "complete")
        self.assertIsNotNone(cached)
        self.assertEqual(cached["data"], "persisted")


class TestResearchQualityMetrics(unittest.TestCase):
    """Test ResearchQualityMetrics."""

    def test_initialization(self):
        """Test metrics initialization."""
        metrics = ResearchQualityMetrics(symbol="SAP.DE")
        self.assertEqual(metrics.symbol, "SAP.DE")
        self.assertEqual(metrics.total_researches, 0)
        self.assertEqual(metrics.average_quality_score, 0.0)

    def test_add_quality_score(self):
        """Test adding quality scores."""
        metrics = ResearchQualityMetrics(symbol="SAP.DE")

        metrics.add_quality_score(80, from_cache=False, cost=0.012)
        metrics.add_quality_score(90, from_cache=False, cost=0.012)
        metrics.add_quality_score(70, from_cache=True, cost=0.012)

        self.assertEqual(metrics.total_researches, 3)
        self.assertEqual(metrics.average_quality_score, 80.0)
        self.assertEqual(metrics.cache_hit_count, 1)
        self.assertEqual(metrics.cache_miss_count, 2)

    def test_cache_hit_rate(self):
        """Test cache hit rate calculation."""
        metrics = ResearchQualityMetrics(symbol="SAP.DE")

        # Add 3 cache misses and 7 cache hits
        for _ in range(3):
            metrics.add_quality_score(80, from_cache=False, cost=0.012)
        for _ in range(7):
            metrics.add_quality_score(85, from_cache=True, cost=0.012)

        self.assertEqual(metrics.cache_hit_rate, 70.0)

    def test_to_dict(self):
        """Test conversion to dictionary."""
        metrics = ResearchQualityMetrics(symbol="SAP.DE")
        metrics.add_quality_score(85, from_cache=False, cost=0.012)

        data = metrics.to_dict()

        self.assertEqual(data["symbol"], "SAP.DE")
        self.assertEqual(data["total_researches"], 1)
        self.assertEqual(data["average_quality_score"], 85.0)
        self.assertEqual(data["latest_score"], 85)


class TestMultiModelResearchOrchestrator(unittest.TestCase):
    """Test MultiModelResearchOrchestrator."""

    def setUp(self):
        """Set up test orchestrator."""
        self.temp_dir = tempfile.mkdtemp()
        self.orchestrator = MultiModelResearchOrchestrator(
            openrouter_api_key="test-key",
            enable_caching=True,
            cache_dir=self.temp_dir
        )

    def tearDown(self):
        """Clean up temp directory."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_initialization(self):
        """Test orchestrator initialization."""
        self.assertIsNotNone(self.orchestrator)
        self.assertTrue(self.orchestrator.enable_caching)
        self.assertIsNotNone(self.orchestrator.cache_manager)

    @patch('backend.services.multi_model_research_orchestrator.CompleteResearchOrchestrator')
    def test_research_model_selection(self, mock_orchestrator_class):
        """Test that correct research model is selected."""
        # Mock the orchestrator
        mock_orchestrator = Mock()
        mock_orchestrator.conduct_complete_research.return_value = {
            "success": True,
            "symbol": "SAP.DE",
            "quality_score": 85
        }
        mock_orchestrator_class.return_value = mock_orchestrator

        # Conduct research for GPT-4 (should use GPT-3.5 for research)
        results = self.orchestrator.conduct_research_for_model(
            trading_model="openai/gpt-4-turbo",
            symbols=["SAP.DE"],
            force_refresh=True
        )

        self.assertIn("SAP.DE", results)
        result = results["SAP.DE"]
        self.assertEqual(result["trading_model"], "openai/gpt-4-turbo")
        self.assertEqual(result["research_model"], "openai/gpt-3.5-turbo")

    @patch('backend.services.multi_model_research_orchestrator.CompleteResearchOrchestrator')
    def test_caching_behavior(self, mock_orchestrator_class):
        """Test that caching works correctly."""
        # Mock the orchestrator
        mock_orchestrator = Mock()
        mock_orchestrator.conduct_complete_research.return_value = {
            "success": True,
            "symbol": "SAP.DE",
            "quality_score": 85,
            "unified_briefing": "Test briefing"
        }
        mock_orchestrator_class.return_value = mock_orchestrator

        # First call - should do research
        results1 = self.orchestrator.conduct_research_for_model(
            trading_model="openai/gpt-3.5-turbo",
            symbols=["SAP.DE"],
            force_refresh=False
        )

        self.assertFalse(results1["SAP.DE"].get("from_cache", False))
        self.assertEqual(mock_orchestrator.conduct_complete_research.call_count, 1)

        # Second call - should use cache
        results2 = self.orchestrator.conduct_research_for_model(
            trading_model="openai/gpt-3.5-turbo",
            symbols=["SAP.DE"],
            force_refresh=False
        )

        self.assertTrue(results2["SAP.DE"].get("from_cache", False))
        # Should not have called research again
        self.assertEqual(mock_orchestrator.conduct_complete_research.call_count, 1)

    @patch('backend.services.multi_model_research_orchestrator.CompleteResearchOrchestrator')
    def test_force_refresh(self, mock_orchestrator_class):
        """Test force refresh bypasses cache."""
        # Mock the orchestrator
        mock_orchestrator = Mock()
        mock_orchestrator.conduct_complete_research.return_value = {
            "success": True,
            "symbol": "SAP.DE",
            "quality_score": 85
        }
        mock_orchestrator_class.return_value = mock_orchestrator

        # First call
        self.orchestrator.conduct_research_for_model(
            trading_model="openai/gpt-3.5-turbo",
            symbols=["SAP.DE"],
            force_refresh=False
        )

        # Second call with force refresh
        results = self.orchestrator.conduct_research_for_model(
            trading_model="openai/gpt-3.5-turbo",
            symbols=["SAP.DE"],
            force_refresh=True
        )

        self.assertFalse(results["SAP.DE"].get("from_cache", False))
        # Should have called research twice
        self.assertEqual(mock_orchestrator.conduct_complete_research.call_count, 2)

    def test_invalidate_research(self):
        """Test research invalidation."""
        # Cache some research
        self.orchestrator.cache_manager.cache_research(
            symbol="SAP.DE",
            research_data={"test": "data"},
            research_type="complete",
            model_used="gpt-3.5"
        )

        # Invalidate
        self.orchestrator.invalidate_research("earnings", ["SAP.DE"])

        # Should be invalidated
        cached = self.orchestrator.cache_manager.get_cached_research("SAP.DE", "complete")
        self.assertIsNone(cached)

    @patch('backend.services.multi_model_research_orchestrator.CompleteResearchOrchestrator')
    def test_quality_metrics_tracking(self, mock_orchestrator_class):
        """Test quality metrics are tracked correctly."""
        # Mock the orchestrator
        mock_orchestrator = Mock()
        mock_orchestrator.conduct_complete_research.return_value = {
            "success": True,
            "symbol": "SAP.DE",
            "quality_score": 85
        }
        mock_orchestrator_class.return_value = mock_orchestrator

        # Conduct research
        self.orchestrator.conduct_research_for_model(
            trading_model="openai/gpt-3.5-turbo",
            symbols=["SAP.DE"],
            force_refresh=True
        )

        # Check metrics
        metrics = self.orchestrator.get_quality_metrics("SAP.DE")
        self.assertEqual(metrics["total_researches"], 1)
        self.assertEqual(metrics["average_quality_score"], 85.0)
        self.assertEqual(metrics["latest_score"], 85)

    def test_get_system_status(self):
        """Test getting system status."""
        status = self.orchestrator.get_system_status()

        self.assertTrue(status["caching_enabled"])
        self.assertIn("cache_status", status)
        self.assertIn("quality_tracking", status)
        self.assertEqual(status["active_orchestrators"], 0)  # None created yet


class TestResearchModelMapper(unittest.TestCase):
    """Test ResearchModelMapper (already tested in Phase 3.5.1 but adding coverage)."""

    def test_get_research_model_premium_to_cheap(self):
        """Test mapping premium model to cheap research model."""
        research_model = ResearchModelMapper.get_research_model("openai/gpt-4-turbo")
        self.assertEqual(research_model, "openai/gpt-3.5-turbo")

        research_model = ResearchModelMapper.get_research_model("anthropic/claude-3-opus")
        self.assertEqual(research_model, "anthropic/claude-3-haiku-20240307")

    def test_get_research_model_already_cheap(self):
        """Test cheap model uses itself."""
        research_model = ResearchModelMapper.get_research_model("openai/gpt-3.5-turbo")
        self.assertEqual(research_model, "openai/gpt-3.5-turbo")

        research_model = ResearchModelMapper.get_research_model("deepseek/deepseek-chat")
        self.assertEqual(research_model, "deepseek/deepseek-chat")

    def test_is_cheap_model(self):
        """Test cheap model detection."""
        self.assertTrue(ResearchModelMapper.is_cheap_model("openai/gpt-3.5-turbo"))
        self.assertFalse(ResearchModelMapper.is_cheap_model("openai/gpt-4-turbo"))


if __name__ == "__main__":
    unittest.main()
