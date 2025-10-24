"""
Interactive Demo: Complete Research Orchestrator

Demonstrates the unified research system combining:
- Technical Analysis (Phase 3.5.3)
- Financial Data APIs (Phase 3.5.2)
- Enhanced Research Pipeline (Phase 3.5.1)

Usage:
    python examples/test_complete_research.py

Author: Sentiment Arena
Date: 2025-10-23
"""

import sys
import os
from datetime import datetime
import json

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.services.complete_research_orchestrator import CompleteResearchOrchestrator
from backend.config import settings


def print_section_header(title: str):
    """Print a formatted section header."""
    print(f"\n{'=' * 80}")
    print(f" {title}")
    print(f"{'=' * 80}\n")


def display_timing_breakdown(timing: dict):
    """Display timing breakdown."""
    print_section_header("TIMING BREAKDOWN")

    if timing.get("technical_analysis"):
        print(f"⚡ Technical Analysis: {timing['technical_analysis']:.2f}s")

    if timing.get("financial_data"):
        print(f"💰 Financial Data APIs: {timing['financial_data']:.2f}s")

    if timing.get("enhanced_research"):
        print(f"🔍 Enhanced Research: {timing['enhanced_research']:.2f}s")

    if timing.get("unified_briefing"):
        print(f"📝 Unified Briefing: {timing['unified_briefing']:.2f}s")

    if timing.get("quality_verification"):
        print(f"✅ Quality Verification: {timing['quality_verification']:.2f}s")

    print(f"\n⏱️  TOTAL TIME: {timing.get('total', 0):.2f}s")


def display_data_sources(result: dict):
    """Display which data sources succeeded."""
    print_section_header("DATA SOURCES STATUS")

    # Technical Analysis
    tech = result.get("technical_analysis")
    if tech:
        status = "✅ SUCCESS" if tech.get("success") else "❌ FAILED"
        print(f"📊 Technical Analysis: {status}")
        if not tech.get("success"):
            print(f"   Error: {tech.get('error')}")

    # Financial Data
    fin = result.get("financial_data")
    if fin:
        status = "✅ SUCCESS" if fin.get("success") else "❌ FAILED"
        print(f"💰 Financial Data APIs: {status}")
        if fin.get("errors"):
            for error in fin["errors"]:
                print(f"   Warning: {error}")

    # Enhanced Research
    research = result.get("enhanced_research")
    if research:
        status = "✅ SUCCESS" if research.get("success") else "❌ FAILED"
        print(f"🔍 Enhanced Research: {status}")
        if not research.get("success"):
            print(f"   Error: {research.get('error')}")

    # Quality Score
    if result.get("quality_score"):
        score = result["quality_score"]
        emoji = "🟢" if score >= 80 else "🟡" if score >= 60 else "🔴"
        print(f"\n{emoji} Quality Score: {score}/100")


def display_unified_briefing(result: dict):
    """Display the unified briefing."""
    print_section_header("UNIFIED BRIEFING")

    briefing = result.get("unified_briefing")
    if briefing:
        print(briefing)
    else:
        print("⚠️ No unified briefing available")


def demo_complete_research(symbol: str, orchestrator: CompleteResearchOrchestrator):
    """Run complete research demo for a stock."""
    print_section_header(f"COMPLETE RESEARCH DEMO: {symbol}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    print(f"🚀 Starting comprehensive research for {symbol}...")
    print(f"This combines Technical Analysis + Financial APIs + Enhanced Research\n")

    # Conduct complete research
    result = orchestrator.conduct_complete_research(
        symbol=symbol,
        include_technical=True,
        include_financial_apis=True,
        include_web_research=True,
        include_quality_verification=True
    )

    # Display results
    if result.get("success"):
        print(f"\n✅ Research completed successfully!")

        display_data_sources(result)
        display_timing_breakdown(result.get("timing", {}))

        # Show errors if any
        if result.get("errors"):
            print_section_header("WARNINGS/ERRORS")
            for error in result["errors"]:
                print(f"⚠️  {error}")

        display_unified_briefing(result)

        # Export option
        export = input("\n\nExport briefing to file? (y/n): ").strip().lower()
        if export == 'y':
            filename = f"briefing_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(result.get("unified_briefing", ""))
            print(f"✅ Briefing exported to {filename}")

    else:
        print(f"\n❌ Research failed")
        print(f"Errors: {result.get('errors')}")


def demo_cost_estimate(orchestrator: CompleteResearchOrchestrator):
    """Display cost estimate."""
    print_section_header("COST ESTIMATE")

    cost = orchestrator.get_cost_estimate("SAP.DE")

    print("Cost breakdown per research:")
    for key, value in cost.items():
        if key != "note":
            print(f"  • {key.replace('_', ' ').title()}: {value}")

    if cost.get("note"):
        print(f"\nℹ️  {cost['note']}")


def demo_comparison():
    """Show comparison between basic and complete research."""
    print_section_header("BASIC VS COMPLETE RESEARCH")

    print("📊 BASIC RESEARCH (Phase 3 - Original)")
    print("  • Web search only")
    print("  • No data verification")
    print("  • Basic formatting")
    print("  • Time: ~10-15 seconds")
    print("  • Cost: Free")
    print("  • Quality: ⭐⭐⭐ (3/5)")

    print("\n🚀 COMPLETE RESEARCH (Phases 3.5.1 + 3.5.2 + 3.5.3)")
    print("  • Technical indicators (RSI, MACD, BB, MA, etc.)")
    print("  • Financial APIs (fundamentals, earnings, analyst ratings)")
    print("  • Enhanced web research with LLM synthesis")
    print("  • Quality verification")
    print("  • Unified briefing")
    print("  • Time: ~30-60 seconds")
    print("  • Cost: ~$0.01-0.02 per research")
    print("  • Quality: ⭐⭐⭐⭐⭐ (5/5)")


def main():
    """Main demo function."""
    print("\n" + "=" * 80)
    print(" COMPLETE RESEARCH ORCHESTRATOR - INTERACTIVE DEMO")
    print("=" * 80)
    print("\nThis demo showcases the unified research system combining:")
    print("  • Phase 3.5.1: Enhanced Research Pipeline")
    print("  • Phase 3.5.2: Financial Data APIs")
    print("  • Phase 3.5.3: Technical Analysis")
    print("\n")

    # Check API keys
    api_key = settings.OPENROUTER_API_KEY
    if not api_key:
        print("❌ Error: OPENROUTER_API_KEY not set in environment")
        print("Please set OPENROUTER_API_KEY in .env file")
        return

    alphavantage_key = getattr(settings, 'ALPHAVANTAGE_API_KEY', None)
    finnhub_key = getattr(settings, 'FINNHUB_API_KEY', None)

    print(f"✅ OpenRouter API Key: {'Set' if api_key else 'Not set'}")
    print(f"{'✅' if alphavantage_key else '⚠️ '} Alpha Vantage API Key: {'Set' if alphavantage_key else 'Not set (will skip)'}")
    print(f"{'✅' if finnhub_key else '⚠️ '} Finnhub API Key: {'Set' if finnhub_key else 'Not set (will skip)'}")

    # Initialize orchestrator
    print("\n🔧 Initializing Complete Research Orchestrator...")
    try:
        orchestrator = CompleteResearchOrchestrator(
            openrouter_api_key=api_key,
            alphavantage_api_key=alphavantage_key,
            finnhub_api_key=finnhub_key,
            model_identifier="openai/gpt-3.5-turbo"
        )
        print("✅ Orchestrator initialized successfully\n")
    except Exception as e:
        print(f"❌ Error initializing orchestrator: {e}")
        return

    # Demo stocks
    stocks = [
        ("SAP.DE", "SAP SE"),
        ("BMW.DE", "BMW AG"),
        ("SIE.DE", "Siemens AG"),
        ("VOW3.DE", "Volkswagen AG")
    ]

    while True:
        print("\n" + "=" * 80)
        print("MENU")
        print("=" * 80)
        print("\nAvailable options:")
        for i, (symbol, name) in enumerate(stocks, 1):
            print(f"  {i}. Analyze {symbol} - {name}")
        print(f"  {len(stocks) + 1}. Custom symbol")
        print(f"  {len(stocks) + 2}. View cost estimate")
        print(f"  {len(stocks) + 3}. Compare basic vs complete research")
        print(f"  {len(stocks) + 4}. Exit")

        try:
            choice = input("\nSelect option: ").strip()

            if choice == str(len(stocks) + 4):
                print("\n👋 Exiting demo. Goodbye!")
                break

            elif choice == str(len(stocks) + 1):
                custom_symbol = input("Enter stock symbol (e.g., ADS.DE): ").strip().upper()
                if not custom_symbol.endswith('.DE'):
                    custom_symbol += '.DE'
                demo_complete_research(custom_symbol, orchestrator)

            elif choice == str(len(stocks) + 2):
                demo_cost_estimate(orchestrator)

            elif choice == str(len(stocks) + 3):
                demo_comparison()

            elif choice.isdigit() and 1 <= int(choice) <= len(stocks):
                symbol, name = stocks[int(choice) - 1]
                demo_complete_research(symbol, orchestrator)

            else:
                print("❌ Invalid choice. Please try again.")

        except KeyboardInterrupt:
            print("\n\n👋 Interrupted. Exiting...")
            break
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")
            print("Please try again.")

    print("\n" + "=" * 80)
    print(" Demo complete. Thank you for using Complete Research Orchestrator!")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
