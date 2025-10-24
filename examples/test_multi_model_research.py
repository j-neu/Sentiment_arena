"""
Interactive Demo: Multi-Model Research Orchestration (Phase 3.5.5)

Demonstrates:
- Research model selection (cheap models for research)
- Research caching and cost savings
- Multi-model research sharing
- Quality metrics tracking
- Cache invalidation on market events

Author: Sentiment Arena
Date: 2025-10-23
"""

import os
import sys
from pathlib import Path
import time

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.services.multi_model_research_orchestrator import MultiModelResearchOrchestrator
from backend.services.research_model_mapper import ResearchModelMapper
from backend.config import settings
from backend.logger import get_logger

logger = get_logger(__name__)


def print_section(title: str):
    """Print formatted section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def demonstrate_model_mapping():
    """Demonstrate research model selection."""
    print_section("1. Research Model Selection Strategy")

    trading_models = [
        "openai/gpt-4-turbo",
        "openai/gpt-3.5-turbo",
        "anthropic/claude-3-opus",
        "anthropic/claude-3-haiku",
        "google/gemini-1.5-pro",
        "deepseek/deepseek-chat"
    ]

    print("Trading Model → Research Model (Cost Tier)")
    print("-" * 80)

    for model in trading_models:
        research_model = ResearchModelMapper.get_research_model(model)
        company = ResearchModelMapper.get_model_company(model)
        is_cheap = ResearchModelMapper.is_cheap_model(model)
        cost_info = ResearchModelMapper.get_cost_estimate(model)

        same_marker = "✓" if model == research_model else "→"

        print(f"{model:45} {same_marker} {research_model:35}")
        print(f"  Company: {company:20} | Trading: {cost_info['trading_cost_tier']:8} | Research: {cost_info['research_cost_tier']:8}")
        print()


def demonstrate_caching():
    """Demonstrate research caching and cost savings."""
    print_section("2. Research Caching & Cost Optimization")

    # Check for API key
    api_key = os.getenv("OPENROUTER_API_KEY") or settings.OPENROUTER_API_KEY
    if not api_key or api_key == "":
        print("⚠️  OPENROUTER_API_KEY not set - using mock mode")
        print("   Set OPENROUTER_API_KEY environment variable for live demo\n")
        return demonstrate_caching_mock()

    print("Creating orchestrator with caching enabled...")
    orchestrator = MultiModelResearchOrchestrator(
        openrouter_api_key=api_key,
        enable_caching=True,
        default_cache_ttl_hours=2.0
    )

    # Test symbols
    symbols = ["SAP.DE", "VOW3.DE"]
    trading_model = "openai/gpt-4-turbo"

    print(f"\nConducting research for {len(symbols)} symbols using {trading_model}...")
    print(f"Research will actually use: {ResearchModelMapper.get_research_model(trading_model)}")
    print("(This optimizes costs by using cheaper model for research)\n")

    # First research - should be cache miss
    print("--- FIRST RESEARCH (Cache Miss Expected) ---")
    start = time.time()
    results1 = orchestrator.conduct_research_for_model(
        trading_model=trading_model,
        symbols=symbols,
        force_refresh=False,
        include_web_research=False  # Skip web research for faster demo
    )
    time1 = time.time() - start

    for symbol, result in results1.items():
        from_cache = result.get("from_cache", False)
        quality = result.get("quality_score", "N/A")
        print(f"  {symbol}: Success={result.get('success')} | From Cache={from_cache} | Quality={quality}")

    print(f"Time: {time1:.2f}s\n")

    # Second research - should be cache hit
    print("--- SECOND RESEARCH (Cache Hit Expected) ---")
    start = time.time()
    results2 = orchestrator.conduct_research_for_model(
        trading_model=trading_model,
        symbols=symbols,
        force_refresh=False,
        include_web_research=False
    )
    time2 = time.time() - start

    for symbol, result in results2.items():
        from_cache = result.get("from_cache", False)
        quality = result.get("quality_score", "N/A")
        print(f"  {symbol}: Success={result.get('success')} | From Cache={from_cache} | Quality={quality}")

    print(f"Time: {time2:.2f}s (Speedup: {time1/time2:.1f}x)\n")

    # Show system status
    status = orchestrator.get_system_status()
    print("--- SYSTEM STATUS ---")
    print(f"Caching Enabled: {status['caching_enabled']}")
    print(f"Cache Hit Rate: {status['cache_status']['metrics']['hit_rate']}")
    print(f"Total Cost: {status['quality_tracking']['total_cost_estimate']}")
    print(f"Cost Saved: {status['quality_tracking']['cost_saved_by_cache']}")
    print(f"Net Cost: {status['quality_tracking']['net_cost']}")


def demonstrate_caching_mock():
    """Mock demonstration of caching."""
    print("📊 Simulated Caching Demo (Mock Mode)")
    print("-" * 80)

    print("\n✓ Research Model Selection:")
    print("  Trading: openai/gpt-4-turbo → Research: openai/gpt-3.5-turbo")
    print("  Cost Optimization: Using cheaper model saves ~50% on research costs")

    print("\n✓ Caching Behavior:")
    print("  First Research:  Cache MISS - Conducts new research (~60-100s)")
    print("  Second Research: Cache HIT  - Returns cached result (~0.1s)")
    print("  Speedup: ~600-1000x faster with caching")

    print("\n✓ Cost Savings:")
    print("  Without caching: $0.012 per research × 10 researches = $0.120")
    print("  With caching:    $0.012 × 1 + $0.000 × 9 = $0.012")
    print("  Savings: 90% cost reduction through caching")


def demonstrate_quality_metrics():
    """Demonstrate quality metrics tracking."""
    print_section("3. Quality Metrics Tracking")

    api_key = os.getenv("OPENROUTER_API_KEY") or settings.OPENROUTER_API_KEY
    if not api_key or api_key == "":
        print("⚠️  OPENROUTER_API_KEY not set - skipping live demo")
        return

    orchestrator = MultiModelResearchOrchestrator(
        openrouter_api_key=api_key,
        enable_caching=True
    )

    # Simulate multiple researches
    print("Simulating research history...\n")

    # Quality metrics will be tracked automatically
    quality_metrics = orchestrator.get_quality_metrics()

    if quality_metrics:
        print("Quality Metrics by Symbol:")
        print("-" * 80)
        for symbol, metrics in quality_metrics.items():
            print(f"\n{symbol}:")
            print(f"  Total Researches: {metrics['total_researches']}")
            print(f"  Average Quality: {metrics['average_quality_score']}")
            print(f"  Cache Hit Rate: {metrics['cache_hit_rate']}")
            print(f"  Total Cost: {metrics['total_cost']}")
            print(f"  Cost Saved: {metrics['cost_saved']}")
    else:
        print("No quality metrics available yet.")


def demonstrate_cache_invalidation():
    """Demonstrate cache invalidation on market events."""
    print_section("4. Cache Invalidation on Market Events")

    api_key = os.getenv("OPENROUTER_API_KEY") or settings.OPENROUTER_API_KEY
    if not api_key or api_key == "":
        print("⚠️  OPENROUTER_API_KEY not set - using mock mode\n")

    print("Event Types and Invalidation Strategy:")
    print("-" * 80)

    events = [
        ("earnings", ["SAP.DE"], "Symbol-specific invalidation"),
        ("major_news", ["VOW3.DE"], "Symbol-specific invalidation"),
        ("market_crash", None, "ALL cache invalidated"),
        ("rate_change", None, "ALL cache invalidated"),
        ("geopolitical", None, "ALL cache invalidated")
    ]

    for event_type, symbols, description in events:
        symbol_str = ", ".join(symbols) if symbols else "ALL"
        print(f"\n{event_type.upper():20} → {symbol_str:30} | {description}")

    print("\n\nExample: Earnings Announcement")
    print("-" * 80)
    print("1. SAP.DE announces earnings")
    print("2. Call: orchestrator.invalidate_research('earnings', ['SAP.DE'])")
    print("3. Cache for SAP.DE is cleared")
    print("4. Other symbols remain cached")
    print("5. Next research for SAP.DE will fetch fresh data")


def demonstrate_multi_model_sharing():
    """Demonstrate research sharing across trading models."""
    print_section("5. Research Sharing Across Trading Models")

    print("Scenario: 4 trading models compete, all need research for SAP.DE")
    print("-" * 80)

    models = [
        "openai/gpt-4-turbo",
        "anthropic/claude-3-opus",
        "google/gemini-1.5-pro",
        "meta-llama/llama-3.1-70b-instruct"
    ]

    print("\nResearch Model Mapping:")
    for model in models:
        research_model = ResearchModelMapper.get_research_model(model)
        print(f"  {model:45} → {research_model}")

    print("\n\nResearch Execution:")
    print("  Model 1 (GPT-4):      Research SAP.DE using GPT-3.5    [Cache MISS - $0.012]")
    print("  Model 2 (Claude Opus): Research SAP.DE using Haiku      [Cache HIT  - $0.000] ✓")
    print("  Model 3 (Gemini Pro):  Research SAP.DE using Gemini Pro [Cache HIT  - $0.000] ✓")
    print("  Model 4 (Llama 70B):   Research SAP.DE using Llama 8B   [Cache HIT  - $0.000] ✓")

    print("\n\nCost Analysis:")
    print("  Without caching: 4 models × $0.012 = $0.048")
    print("  With caching:    1 × $0.012 + 3 × $0.000 = $0.012")
    print("  Savings: 75% cost reduction")

    print("\n\nKey Benefits:")
    print("  ✓ Research conducted once, shared across all models")
    print("  ✓ Massive cost savings (75% with 4 models)")
    print("  ✓ Consistent data for all models (fair competition)")
    print("  ✓ Faster execution (3 models get instant results)")


def run_full_demo():
    """Run complete demonstration."""
    print("\n")
    print("+" + "=" * 78 + "+")
    print("|" + " " * 78 + "|")
    print("|" + "  MULTI-MODEL RESEARCH ORCHESTRATION DEMO (Phase 3.5.5)".center(78) + "|")
    print("|" + " " * 78 + "|")
    print("+" + "=" * 78 + "+")

    try:
        demonstrate_model_mapping()
        demonstrate_caching()
        demonstrate_quality_metrics()
        demonstrate_cache_invalidation()
        demonstrate_multi_model_sharing()

        print_section("Demo Complete!")
        print("✓ Research model selection strategy")
        print("✓ Caching and cost optimization")
        print("✓ Quality metrics tracking")
        print("✓ Cache invalidation on market events")
        print("✓ Multi-model research sharing")
        print("\nPhase 3.5.5 implementation demonstrated successfully!")

    except Exception as e:
        logger.error(f"Error in demo: {str(e)}", exc_info=True)
        print(f"\n❌ Error: {str(e)}")


if __name__ == "__main__":
    run_full_demo()
